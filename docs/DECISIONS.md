# Architecture Decision Records (ADRs) — ComicTypeset AI

This document logs significant architectural, algorithmic, and infrastructure decisions made during the design and evolution of ComicTypeset AI.

---

## ADR-001: MobileNetV2-UNet Architecture for Speech Bubble Segmentation

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  Speech bubble segmentation requires pixel-accurate binary masks to accurately isolate text and separate bubble content from intricate comic/manga artwork. The target training device has 8 GB VRAM (RTX 5050), and deployment runs on CPU-only Hugging Face Docker Spaces (16 GB RAM). Heavy segmentation networks (Mask R-CNN, SAM, or large ResNet backbones) are too heavy for low-latency CPU inference.
- **Decision:**
  Implement a lightweight U-Net architecture employing a pre-trained `MobileNetV2` encoder with skip connections to an upsampling decoder. Train with a combined Dice loss and Binary Cross-Entropy (BCE) loss.
- **Alternatives Considered:**
  1. *YOLOv8-Seg:* Excellent speed, but introduces extra dependencies and polygon approximations that can clip irregular, expressive speech bubbles.
  2. *Segment Anything (SAM):* High quality, but memory-prohibitive (>2.5 GB weights, excessive CPU inference latency).
  3. *Classical Contour Detection Only:* Lightweight, but fails on translucent, borderless, or textured speech bubbles.
- **Consequences:**
  - MobileNetV2 encoder is lightweight (~3.5M parameters), fast on CPU, and fits easily within 8 GB VRAM during training.
  - Accurate spatial resolution achieved via high-resolution skip connections.

---

## ADR-002: Dual-Mode Segmentation Architecture with OpenCV Fallback

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  During early development, continuous integration, or in environments where trained `.keras` model weights have not been downloaded, the application must remain functional for testing, frontend integration, and demonstration.
- **Decision:**
  Implement a dual-mode segmentation interface in `backend/app/pipeline/segmenter.py`. If `backend/models/bubble_unet.keras` exists, load and execute the neural segmenter; otherwise, fall back to an adaptive-thresholding and contour-filtering OpenCV pipeline. The active mode (`unet` vs `opencv_fallback`) is explicitly returned in every API response.
- **Alternatives Considered:**
  - Hard failure if model checkpoint is absent: Blocks frontend development and automated CI integration.
  - Committing large model weights directly to Git: Bloats repository size and violates Git best practices.
- **Consequences:**
  - Developers and evaluators can immediately run and verify the entire backend/frontend loop without prior model training.
  - API consumers always know which detection mechanism produced the masks.

---

## ADR-003: EasyOCR for Text Extraction

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  Comic and manga pages feature multilingual lettering: Western comics use Latin scripts with stylized comic fonts; manga utilizes Japanese Kanji, Hiragana, and Katakana, often arranged in vertical text layouts.
- **Decision:**
  Select `EasyOCR` as the default OCR engine. EasyOCR natively supports 80+ languages (including English, Japanese, Korean, Simplified/Traditional Chinese), runs on PyTorch, and provides word/line bounding boxes with confidence scores.
- **Alternatives Considered:**
  1. *Tesseract (pytesseract):* Requires external C++ binary installation on host OS, which complicates cross-platform setup and Windows development.
  2. *Cloud Vision APIs (Google Cloud / AWS Rekognition):* Excellent accuracy, but requires paid API keys and internet egress, preventing self-contained offline execution.
  3. *Manga-OCR:* Highly accurate for Japanese, but limited to single-language Japanese and lacks general Latin script coverage.
- **Consequences:**
  - Python-native installation via PyPI.
  - First-run model weights (~120 MB) are cached locally in `/home/user/.EasyOCR` or user home directory.

---

## ADR-004: Translation Adapter Pattern with In-Memory Caching

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  Translation engines can vary across environments. Users may desire free web translation (e.g., Google Translator via `deep-translator`), local LLM translation (e.g., Ollama), or commercial APIs (DeepL, OpenAI). Network translation can also be slow or rate-limited.
- **Decision:**
  Implement a decoupled adapter pattern for machine translation in `backend/app/pipeline/ocr_translator.py`. Use `deep-translator` as the default provider, fronted by an in-memory LRU cache keyed by `(source_lang, target_lang, text_hash)`. In unit tests, replace the translation provider with a deterministic mock.
- **Alternatives Considered:**
  - Hardcoding a single direct REST API call: Makes tests non-deterministic and prevents swapping translation engines.
  - No caching: Repeatedly translates repeated phrases (e.g., "Huh?", "What?!"), causing rate limits.
- **Consequences:**
  - Fast response times for identical or repetitive text.
  - Deterministic testing without live network connections.

---

## ADR-005: OpenCV Telea Inpainting with Dynamic Pillow Typesetting

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  Once text is extracted, the speech bubble must be cleaned of the original lettering before rendering the translated text. The replacement text must fit cleanly inside the bubble geometry without overflowing.
- **Decision:**
  1. **Inpainting:** Generate a dilated text mask from OCR bounding boxes or high-contrast foreground pixels, then apply OpenCV's fast Telea inpainting (`cv2.INPAINT_TELEA`) with an inpaint radius of 3px.
  2. **Typesetting:** Use Pillow (`PIL.ImageDraw`) with dynamic binary-search font size fitting and greedy word wrapping to center the translated text inside the speech bubble's inscribed bounding rectangle.
- **Alternatives Considered:**
  - Solid white fill: Obliterates textured backgrounds, halftone shading, or speech bubble gradients.
  - Deep learning inpainting (e.g., LaMa): High memory requirement, unfeasible for CPU-only 16 GB Space.
- **Consequences:**
  - Fast CPU performance (< 50ms per bubble).
  - Preserves comic paper tone, speech bubble tail, and exterior artwork.

---

## ADR-006: Resilient Autonomous Dataset Acquisition Cascade

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  Model training requires paired comic images and speech bubble binary masks. Public mirrors may suffer downtime, require API keys, or have inconsistent annotation formats (COCO JSON, YOLO polygons, Pascal VOC).
- **Decision:**
  Build a resilient multi-stage acquisition script `ml_experiments/src/download_dataset.py`:
  1. Check for `ROBOFLOW_API_KEY`; if present, pull the configured Roboflow public comic bubble dataset.
  2. If unauthenticated, pull from Hugging Face Hub (open dataset without authentication requirements).
  3. Normalize all incoming formats into a standardized structure: `data/processed/real/images/*.png` and `data/processed/real/masks/*.png` (single-channel 8-bit binary masks with values {0, 255}).
  4. Write `dataset_manifest.json` recording source, licenses, sample counts, and SHA256 checksums.
  5. If offline or all mirrors fail, automatically invoke `synthetic_data_gen.py` to synthesize valid training samples so the pipeline never stalls.
- **Consequences:**
  - Fully autonomous execution in headless environments.
  - Zero unhandled exceptions if external networks fail.

---

## ADR-007: Standardized Hugging Face Docker Space Containerization

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  The backend must deploy seamlessly to Hugging Face Docker Spaces without permission errors, missing shared library crashes, or port mismatches.
- **Decision:**
  Use a pinned `python:3.11-slim` base image. Install required OpenCV system dependencies (`libgl1`, `libglib2.0-0`). Create a non-root user with UID 1000 (`user`), establish `/home/user/.EasyOCR` with write permissions, expose port `7860`, and run Uvicorn. Include valid HF Space YAML frontmatter at the top of `backend/README.md`.
- **Consequences:**
  - Conforms strictly to Hugging Face Spaces security guidelines.
  - Prevents non-root filesystem permission failures during EasyOCR model weight download.

---

## ADR-008: Next.js 14 App Router and Tailwind CSS for Studio Frontend

- **Date:** 2026-11-23
- **Status:** Accepted
- **Context:**
  Users need an intuitive, responsive interface to upload comic pages, inspect segmented bubble masks, edit detected text, trigger re-renders, and download the finished page.
- **Decision:**
  Build the frontend with Next.js 14 App Router, TypeScript, and Tailwind CSS. Include a built-in synthetic comic page generator in the browser so users can test the application instantly without uploading private copyrighted comic scans.
- **Consequences:**
  - Modern, responsive UX with component isolation.
  - Immediate trialability via synthetic test page generator.
