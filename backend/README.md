---
title: ComicTypeset AI
emoji: 💬
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.32.0
python_version: 3.12.12
app_file: gradio_app.py
---

# ComicTypeset AI — Backend API & Gradio Space

The ComicTypeset AI backend is a production-ready FastAPI service orchestrating speech bubble segmentation, text extraction (OCR), neural machine translation, lettering inpainting, and typography re-lettering.

The Hugging Face entrypoint mounts a small Gradio landing page while preserving the FastAPI endpoints used by the Vercel frontend. To keep the free ZeroGPU Space simple and reliable, it runs OpenCV segmentation and placeholder OCR. The full TensorFlow U-Net and EasyOCR pipeline remains available in the local backend.

---

## 1. Backend Architecture

```mermaid
flowchart TD
    Req([HTTP POST /api/v1/translate-page]) --> Val[Request & Image Sanitization]
    Val --> EXIF[EXIF Orientation Normalization]
    EXIF --> Seg[Stage 1: Speech Bubble Segmenter]
    
    subgraph SegmentationMode["Dual-Mode Detector"]
        UNet[MobileNetV2-UNet Model]
        CVFallback[OpenCV Adaptive & Contour Fallback]
    end
    
    Seg -->|Checkpoint present| UNet
    Seg -->|No Checkpoint| CVFallback
    
    UNet --> Order[Reading Order Sorter: LTR / RTL]
    CVFallback --> Order
    
    Order --> OCR[Stage 2: EasyOCR Text Extraction]
    OCR --> Trans[Stage 3: deep-translator + LRU Cache]
    Trans --> Inpaint[Stage 4A: Telea Morphological Inpainting]
    Inpaint --> TS[Stage 4B: Pillow Dynamic Typesetting]
    TS --> Resp([JSON Response: Base64 Images & Bubble JSON])
```

---

## 2. API Contract

### 2.1 `GET /`
Returns a basic service status and the documentation path.

### 2.2 `GET /health`
Returns service availability, version, and the active segmentation detector mode.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "detector_mode": "opencv_fallback",
  "model_loaded": false
}
```

---

### 2.3 `POST /api/v1/translate-page`
Processes a comic or manga page scan and returns the translated page, mask overlay, and extracted text.

**Multipart Form Parameters:**
- `file`: Image file (`image/png`, `image/jpeg`, `image/webp`). Max size: 15 MB.
- `source_lang`: Source language code (e.g., `"ja"`, `"en"`, `"auto"`). Default: `"auto"`.
- `target_lang`: Target language code (e.g., `"en"`, `"es"`, `"fr"`, `"ja"`). Default: `"en"`.
- `reading_direction`: Reading order direction (`"ltr"` or `"rtl"`). Default: `"ltr"`.

**Curl Example:**
```bash
curl -X POST "http://localhost:7860/api/v1/translate-page" \
  -F "file=@sample_page.png" \
  -F "source_lang=ja" \
  -F "target_lang=en" \
  -F "reading_direction=rtl"
```

**Response Example:**
```json
{
  "success": true,
  "detector_mode": "opencv_fallback",
  "reading_direction": "rtl",
  "source_lang": "ja",
  "target_lang": "en",
  "total_bubbles_detected": 2,
  "bubbles": [
    {
      "id": 1,
      "order": 1,
      "bbox": { "x": 300, "y": 60, "width": 150, "height": 90 },
      "raw_text": "こんにちは！",
      "translated_text": "Hello!",
      "confidence": 0.94,
      "polygon": [[300, 60], [450, 60], [450, 150], [300, 150]]
    }
  ],
  "final_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "mask_overlay_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "timings_ms": {
    "segmentation": 12.4,
    "ocr": 110.2,
    "translation": 45.6,
    "typesetting": 34.1,
    "total": 202.3
  },
  "warnings": []
}
```

---

## 3. Local Setup & Execution

### 3.1 Setup Virtual Environment (Windows)
```powershell
.\backend\setup_env.ps1
```

### 3.2 Run Backend Locally
```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 7860
```
Open interactive Swagger documentation: `http://127.0.0.1:7860/docs`.

### 3.3 Run Unit Tests
```bash
cd backend
pytest -q
```

---

## 4. Hugging Face ZeroGPU Space

The Space uses the Gradio SDK because Hugging Face ZeroGPU does not support Docker SDK Spaces. `gradio_app.py` enables lightweight mode, mounts the API, and exposes the landing page at `/gradio/`; the REST API remains available at `/api/v1/translate-page`, `/health`, and `/docs`. A ZeroGPU diagnostic button is optional and does not accelerate the API pipeline.

In this free Space, `/health` is expected to report `detector_mode: opencv_fallback` and `model_loaded: false`. Each page response warns that placeholder OCR text is used. For a Vercel deployment, set `NEXT_PUBLIC_API_URL=https://01mayankk-comic.hf.space` and set `ALLOWED_ORIGINS` in the Space variables to the exact Vercel origin.
