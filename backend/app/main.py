"""FastAPI REST Application for ComicTypeset AI.

Endpoints:
- GET /health
- POST /api/v1/translate-page
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import numpy as np
from PIL import Image, ImageOps
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.schemas import BoundingBox, BubbleItem, HealthResponse, TranslationResponse
from app.pipeline.segmenter import SpeechBubbleSegmenter
from app.pipeline.ocr_translator import OCRTranslator
from app.pipeline.typesetter import ComicTypesetter

# Prevent decompression bomb vulnerabilities
Image.MAX_IMAGE_PIXELS = 100_000_000

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("comictypeset-api")

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_IMAGE_DIMENSION = 4096


def encode_image_base64_png(image_rgb: np.ndarray) -> str:
    """Encodes an RGB numpy array to a PNG Base64 Data URI."""
    pil_img = Image.fromarray(image_rgb)
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG", optimize=True)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initializes models and pipeline stages once on worker startup."""
    logger.info("Initializing ComicTypeset AI pipeline services...")

    model_path = os.getenv("MODEL_PATH", "models/bubble_unet.keras")
    app.state.segmenter = SpeechBubbleSegmenter(model_path=model_path)
    app.state.ocr_translator = OCRTranslator(languages=["en"])
    app.state.typesetter = ComicTypesetter()

    logger.info(f"Pipeline ready. Active bubble detector mode: {app.state.segmenter.active_mode}")
    yield
    logger.info("Shutting down ComicTypeset AI pipeline services...")


app = FastAPI(
    title="ComicTypeset AI",
    description="Automated Speech Bubble Segmentation, Translation, and Re-Lettering API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Lightweight health check endpoint."""
    segmenter: SpeechBubbleSegmenter = getattr(app.state, "segmenter", None)
    active_mode = segmenter.active_mode if segmenter else "opencv_fallback"
    model_loaded = (active_mode == "unet")

    return HealthResponse(
        status="ok",
        version="1.0.0",
        detector_mode=active_mode,
        model_loaded=model_loaded
    )


@app.post("/api/v1/translate-page", response_model=TranslationResponse)
async def translate_page(
    file: UploadFile = File(..., description="Comic or manga page image"),
    source_lang: str = Form("auto", description="Source text language code (e.g. 'ja', 'en', 'auto')"),
    target_lang: str = Form("en", description="Target language code (e.g. 'en', 'es', 'fr')"),
    reading_direction: str = Form("ltr", description="Reading order direction: 'ltr' or 'rtl'")
) -> TranslationResponse:
    """Executes the complete 4-stage comic translation and typesetting pipeline."""
    t_start = time.perf_counter()
    warnings: list[str] = []

    # 1. Validation: MIME Type
    if file.content_type not in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file.content_type}'. Must be PNG, JPEG, or WebP."
        )

    # 2. Validation: Content Length
    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum permitted limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
        )

    # 3. Decode Image & Normalize EXIF Orientation
    try:
        pil_image = Image.open(io.BytesIO(raw_bytes))
        pil_image = ImageOps.exif_transpose(pil_image)
        pil_image = pil_image.convert("RGB")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed image file: {str(exc)}"
        )

    width, height = pil_image.size
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image dimensions ({width}x{height}) exceed maximum limit of {MAX_IMAGE_DIMENSION}px."
        )

    image_rgb = np.array(pil_image)

    segmenter: SpeechBubbleSegmenter = app.state.segmenter
    ocr_translator: OCRTranslator = app.state.ocr_translator
    typesetter: ComicTypesetter = app.state.typesetter

    # Stage 1: Speech Bubble Segmentation
    t_seg_start = time.perf_counter()
    clean_direction = "rtl" if reading_direction.lower() == "rtl" else "ltr"
    mask, raw_bubbles = segmenter.segment(image_rgb, reading_direction=clean_direction)
    t_seg = (time.perf_counter() - t_seg_start) * 1000

    # Stage 2: OCR Extraction
    t_ocr_start = time.perf_counter()
    bubble_items: list[BubbleItem] = []
    for b in raw_bubbles:
        text, conf = ocr_translator.extract_text(image_rgb, b["bbox"])
        b["raw_text"] = text
        b["confidence"] = conf
    t_ocr = (time.perf_counter() - t_ocr_start) * 1000

    # Stage 3: Translation
    t_trans_start = time.perf_counter()
    for b in raw_bubbles:
        translated, warn = ocr_translator.translate(
            b["raw_text"],
            source_lang=source_lang,
            target_lang=target_lang
        )
        b["translated_text"] = translated
        if warn:
            warnings.append(warn)
    t_trans = (time.perf_counter() - t_trans_start) * 1000

    # Stage 4: Inpainting and Typesetting
    t_ts_start = time.perf_counter()
    inpainted_rgb = typesetter.inpaint_lettering(image_rgb, raw_bubbles)
    final_rgb = typesetter.typeset(inpainted_rgb, raw_bubbles)
    mask_overlay_rgb = typesetter.create_mask_overlay(image_rgb, mask)
    t_ts = (time.perf_counter() - t_ts_start) * 1000

    # Base64 Serialization
    final_b64 = encode_image_base64_png(final_rgb)
    overlay_b64 = encode_image_base64_png(mask_overlay_rgb)

    # Format bubbles response
    for b in raw_bubbles:
        bbox_obj = BoundingBox(
            x=b["bbox"]["x"],
            y=b["bbox"]["y"],
            width=b["bbox"]["width"],
            height=b["bbox"]["height"]
        )
        bubble_items.append(BubbleItem(
            id=b["id"],
            order=b["order"],
            bbox=bbox_obj,
            raw_text=b["raw_text"],
            translated_text=b["translated_text"],
            confidence=b.get("confidence", 1.0),
            polygon=b.get("polygon", [])
        ))

    t_total = (time.perf_counter() - t_start) * 1000

    return TranslationResponse(
        success=True,
        detector_mode=segmenter.active_mode,
        reading_direction=clean_direction,
        source_lang=source_lang,
        target_lang=target_lang,
        total_bubbles_detected=len(bubble_items),
        bubbles=bubble_items,
        final_image_base64=final_b64,
        mask_overlay_base64=overlay_b64,
        timings_ms={
            "segmentation": round(t_seg, 2),
            "ocr": round(t_ocr, 2),
            "translation": round(t_trans, 2),
            "typesetting": round(t_ts, 2),
            "total": round(t_total, 2)
        },
        warnings=warnings
    )
