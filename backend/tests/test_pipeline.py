"""Comprehensive Unit & Integration Test Suite for ComicTypeset AI Pipeline."""

import io
import os
import sys
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

# Ensure backend root is on Python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.pipeline.segmenter import SpeechBubbleSegmenter, sort_bubbles_reading_order
from app.pipeline.ocr_translator import OCRTranslator, TranslationCache
from app.pipeline.typesetter import ComicTypesetter


@pytest.fixture
def test_image_rgb() -> np.ndarray:
    """Creates a synthetic comic test image with two speech bubbles."""
    img = Image.new("RGB", (512, 512), color=(240, 240, 240))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Panel
    draw.rectangle([20, 20, 492, 492], fill=(255, 255, 255), outline=(0, 0, 0), width=3)
    # Bubble 1 (Top Left)
    draw.ellipse([50, 60, 220, 160], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.text((80, 100), "HELLO WORLD", fill=(0, 0, 0))
    # Bubble 2 (Top Right)
    draw.ellipse([280, 60, 450, 160], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.text((310, 100), "SECOND BUBBLE", fill=(0, 0, 0))
    return np.array(img)


@pytest.fixture
def mock_client() -> TestClient:
    """FastAPI TestClient with mocked translation provider for deterministic testing."""
    with TestClient(app) as client:
        # Mock translation provider to avoid external network requests during unit tests
        def mock_translate(text: str, src: str, tgt: str) -> str:
            return f"[{tgt.upper()}] {text}"

        app.state.ocr_translator.set_translation_provider(mock_translate)
        yield client


def test_health_endpoint(mock_client: TestClient):
    """Verifies that GET /health returns 200 OK and valid status schema."""
    resp = mock_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "detector_mode" in data
    assert isinstance(data["model_loaded"], bool)


def test_opencv_fallback_segmentation(test_image_rgb: np.ndarray):
    """Verifies that the OpenCV fallback segmenter generates a valid binary mask and contours."""
    segmenter = SpeechBubbleSegmenter(model_path="non_existent_model.keras")
    assert segmenter.active_mode == "opencv_fallback"

    mask, bubbles = segmenter.segment(test_image_rgb, reading_direction="ltr")
    assert mask.shape == test_image_rgb.shape[:2]
    # Check binary values
    unique_vals = set(np.unique(mask))
    assert unique_vals.issubset({0, 255})
    assert len(bubbles) >= 1
    assert "bbox" in bubbles[0]
    assert bubbles[0]["order"] == 1


def test_reading_order_sorting():
    """Verifies that bubbles are sorted correctly for LTR (Western) and RTL (Manga) modes."""
    raw_bubbles = [
        {"bbox": {"x": 300, "y": 50, "width": 100, "height": 80}},  # Top right
        {"bbox": {"x": 50, "y": 50, "width": 100, "height": 80}},   # Top left
        {"bbox": {"x": 100, "y": 300, "width": 100, "height": 80}}, # Bottom left
    ]

    # LTR sorting: Top-left first, then Top-right, then Bottom
    ltr_sorted = sort_bubbles_reading_order(raw_bubbles, reading_direction="ltr", band_height=100)
    assert ltr_sorted[0]["bbox"]["x"] == 50
    assert ltr_sorted[1]["bbox"]["x"] == 300
    assert ltr_sorted[2]["bbox"]["x"] == 100
    assert ltr_sorted[0]["order"] == 1
    assert ltr_sorted[1]["order"] == 2

    # RTL sorting: Top-right first, then Top-left, then Bottom
    rtl_sorted = sort_bubbles_reading_order(raw_bubbles, reading_direction="rtl", band_height=100)
    assert rtl_sorted[0]["bbox"]["x"] == 300
    assert rtl_sorted[1]["bbox"]["x"] == 50
    assert rtl_sorted[2]["bbox"]["x"] == 100
    assert rtl_sorted[0]["order"] == 1
    assert rtl_sorted[1]["order"] == 2


def test_translation_caching_and_mock():
    """Verifies LRU translation caching and mock adapter behavior."""
    cache = TranslationCache(maxsize=10)
    cache.set("en", "es", "Hello", "Hola")
    assert cache.get("en", "es", "Hello") == "Hola"
    assert cache.get("en", "es", "Unknown") is None

    # Translator with mock provider
    call_count = [0]
    def counting_mock(text, src, tgt):
        call_count[0] += 1
        return f"Translated_{text}"

    translator = OCRTranslator(translation_provider=counting_mock)
    t1, _ = translator.translate("Test Sentence", "en", "fr")
    assert t1 == "Translated_Test Sentence"
    assert call_count[0] == 1

    # Second call should hit cache and not increment provider counter
    t2, _ = translator.translate("Test Sentence", "en", "fr")
    assert t2 == "Translated_Test Sentence"
    assert call_count[0] == 1


def test_inpainting_and_typesetting(test_image_rgb: np.ndarray):
    """Verifies that inpainting cleans lettering and typesetting renders translated text."""
    typesetter = ComicTypesetter()
    bubbles = [
        {
            "id": 1,
            "order": 1,
            "bbox": {"x": 50, "y": 60, "width": 170, "height": 100},
            "translated_text": "RE-LETTERED TEXT"
        }
    ]

    inpainted = typesetter.inpaint_lettering(test_image_rgb, bubbles)
    assert inpainted.shape == test_image_rgb.shape

    typeset = typesetter.typeset(inpainted, bubbles)
    assert typeset.shape == test_image_rgb.shape

    # Check overlay generation
    mask = np.zeros(test_image_rgb.shape[:2], dtype=np.uint8)
    mask[60:160, 50:220] = 255
    overlay = typesetter.create_mask_overlay(test_image_rgb, mask)
    assert overlay.shape == test_image_rgb.shape


def test_api_translate_page_success(mock_client: TestClient, test_image_rgb: np.ndarray):
    """Tests full POST /api/v1/translate-page pipeline with synthetic image."""
    buffer = io.BytesIO()
    Image.fromarray(test_image_rgb).save(buffer, format="PNG")
    buffer.seek(0)

    files = {"file": ("test_page.png", buffer, "image/png")}
    data = {
        "source_lang": "en",
        "target_lang": "es",
        "reading_direction": "ltr"
    }

    resp = mock_client.post("/api/v1/translate-page", files=files, data=data)
    assert resp.status_code == 200
    res_json = resp.json()

    assert res_json["success"] is True
    assert res_json["detector_mode"] in ["unet", "opencv_fallback"]
    assert res_json["source_lang"] == "en"
    assert res_json["target_lang"] == "es"
    assert res_json["reading_direction"] == "ltr"
    assert "final_image_base64" in res_json
    assert res_json["final_image_base64"].startswith("data:image/png;base64,")
    assert "mask_overlay_base64" in res_json
    assert "timings_ms" in res_json
    assert "segmentation" in res_json["timings_ms"]


def test_api_invalid_mime_rejected(mock_client: TestClient):
    """Verifies that non-image MIME types are rejected with 400 Bad Request."""
    fake_file = io.BytesIO(b"Not an image")
    files = {"file": ("document.pdf", fake_file, "application/pdf")}
    resp = mock_client.post("/api/v1/translate-page", files=files, data={"target_lang": "en"})
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


def test_api_corrupt_image_rejected(mock_client: TestClient):
    """Verifies that corrupt images are rejected with 400 Bad Request."""
    corrupt_file = io.BytesIO(b"PNGcorruptbytes123456789")
    files = {"file": ("corrupt.png", corrupt_file, "image/png")}
    resp = mock_client.post("/api/v1/translate-page", files=files, data={"target_lang": "en"})
    assert resp.status_code == 400
    assert "Malformed image" in resp.json()["detail"]
