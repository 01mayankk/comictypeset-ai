# Data Flow — ComicTypeset AI

This document specifies the exact data contracts, state transformations, image encodings, and schemas flowing through ComicTypeset AI.

---

## 1. Request and Response Flow

```mermaid
flowchart LR
    subgraph RequestPayload["Client Request (Multipart Form)"]
        F1["file: UploadFile (PNG / JPEG / WebP)"]
        F2["source_lang: str (e.g. 'ja', 'auto')"]
        F3["target_lang: str (e.g. 'en')"]
        F4["reading_direction: 'ltr' | 'rtl'"]
    end

    subgraph InternalPipeline["Backend Processing State"]
        P1["Decoded RGB Array (H, W, 3)"]
        P2["Binary Mask Array (H, W) {0, 255}"]
        P3["Bubble Regions: [BBox, Polygon, Crop]"]
        P4["OCR Detections: [RawText, Conf]"]
        P5["Translation: [TranslatedText]"]
        P6["Inpainted Background (H, W, 3)"]
        P7["Rendered Canvas (H, W, 3)"]
    end

    subgraph ResponsePayload["API Response (JSON)"]
        R1["success: bool"]
        R2["detector_mode: 'unet' | 'opencv_fallback'"]
        R3["bubbles: list[BubbleMetadata]"]
        R4["mask_overlay_base64: str (data:image/png)"]
        R5["final_image_base64: str (data:image/png)"]
        R6["timings_ms: dict[str, float]"]
        R7["warnings: list[str]"]
    end

    RequestPayload --> InternalPipeline
    InternalPipeline --> ResponsePayload
```

---

## 2. API Contract & Schemas (`backend/app/schemas.py` & `frontend/src/lib/api.ts`)

### 2.1 Bounding Box Schema
```json
{
  "x": 120,
  "y": 85,
  "width": 240,
  "height": 180
}
```

### 2.2 Bubble Data Schema (`BubbleItem`)
```json
{
  "id": 1,
  "order": 1,
  "bbox": {
    "x": 120,
    "y": 85,
    "width": 240,
    "height": 180
  },
  "raw_text": "こんにちは！",
  "translated_text": "Hello!",
  "confidence": 0.94,
  "polygon": [[120, 85], [360, 85], [360, 265], [120, 265]]
}
```

### 2.3 Complete API Response Schema (`TranslationResponse`)
```json
{
  "success": true,
  "detector_mode": "unet",
  "reading_direction": "rtl",
  "source_lang": "ja",
  "target_lang": "en",
  "total_bubbles_detected": 4,
  "bubbles": [
    {
      "id": 1,
      "order": 1,
      "bbox": { "x": 500, "y": 80, "width": 200, "height": 150 },
      "raw_text": "おい！早く来い！",
      "translated_text": "Hey! Come on quickly!",
      "confidence": 0.92,
      "polygon": []
    }
  ],
  "final_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "mask_overlay_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "timings_ms": {
    "segmentation": 124.5,
    "ocr": 350.2,
    "translation": 180.1,
    "typesetting": 65.4,
    "total": 720.2
  },
  "warnings": []
}
```

---

## 3. Image Transformation Lifecycle

| Stage | Input Representation | Operation | Output Representation | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Ingress** | HTTP Raw Bytes (JPEG/PNG) | PIL Decompression + EXIF Rotation check | `np.ndarray` (H, W, 3) uint8 RGB | Enforces max dimension $\le 4096\text{px}$ |
| **Segmentation** | RGB Page `(H, W, 3)` | Resize to $512 \times 512$, Normalize to $[0, 1]$, Inference | Binary mask `(H, W)` uint8 `{0, 255}` | Threshold at $0.5$, scaled to original $(H, W)$ |
| **Bubble Extraction** | Binary mask `(H, W)` | `cv2.findContours` + Area filter | List of bounding boxes & contours | Sorted by reading order (`ltr` or `rtl`) |
| **Inpainting** | RGB Page + OCR BBoxes | In-bubble text thresholding + Morphological dilation + `cv2.inpaint` | Clean RGB Page `(H, W, 3)` | Lettering removed; background tone preserved |
| **Typesetting** | Clean RGB Page + Bubble BBoxes | Word wrap + Font size binary search + `PIL.ImageDraw.text` | Final RGB Page `(H, W, 3)` | Centered text rendering |
| **Egress** | Final RGB Page + Alpha Mask | PNG encoding + Base64 serialization | `data:image/png;base64,...` string | Lossless PNG transmission to client |
