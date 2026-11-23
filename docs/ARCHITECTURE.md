# System Architecture — ComicTypeset AI

## 1. Overview & System Boundaries

ComicTypeset AI is an autonomous, end-to-end comic and manga translation and re-lettering system. The system ingests raw comic or manga page scans, segments speech bubbles, extracts text using OCR, translates text into target languages, removes original lettering using image inpainting, and typesets translated text dynamically back into speech bubbles.

```mermaid
flowchart TB
    subgraph Client["Client Tier (Web Browser)"]
        UI["Next.js 14 Web Studio<br/>(Tailwind CSS + React)"]
        Canvas["Interactive Comparison &<br/>Bubble Editor Canvas"]
    end

    subgraph FrontendHosting["Frontend Host (Vercel)"]
        Edge["Vercel Edge Network / SSR"]
    end

    subgraph BackendHost["Backend Host (Hugging Face Docker Space / Cloud)"]
        API["FastAPI REST Application<br/>(Uvicorn on Port 7860)"]
        
        subgraph Pipeline["4-Stage Core Pipeline"]
            S1["Stage 1: Bubble Segmentation<br/>(MobileNetV2-UNet or OpenCV Fallback)"]
            S2["Stage 2: Text Extraction<br/>(EasyOCR Engine)"]
            S3["Stage 3: Machine Translation<br/>(deep-translator Adapter + Cache)"]
            S4["Stage 4: Inpainting & Typesetting<br/>(OpenCV Telea + Pillow Dynamic Wrap)"]
        end
    end

    subgraph OfflineTraining["Offline / Local ML Training (WSL2 Ubuntu)"]
        WSL["WSL2 Ubuntu 24.04 Environment"]
        GPU["NVIDIA RTX 5050 Laptop GPU (8 GB VRAM)"]
        TrainLoop["Keras MobileNetV2-UNet Training<br/>(tf.data + Dice/BCE Loss)"]
        DataSources["Hugging Face Hub / Roboflow / Synthetic Data"]
    end

    UI --> Edge
    Edge --> API
    API --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> API
    API --> UI

    DataSources --> TrainLoop
    TrainLoop -->|Export Checkpoint| S1
```

---

## 2. Runtime Environments & Isolation

To prevent dependency conflicts and maintain reproducibility across diverse operating environments, the system strictly separates execution contexts:

| Domain | Platform | Path | Main Dependencies | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Training** | WSL2 Ubuntu 24.04 | `ml_experiments/.venv` | `tensorflow[and-cuda]`, JupyterLab, Albumentations, OpenCV, PyYAML, `huggingface-hub`, `datasets` | Model development, hyperparameter tuning, GPU training, and dataset synthesis |
| **Backend API** | Windows / Linux / Docker | `backend/.venv` | `tensorflow-cpu`, FastAPI, Uvicorn, EasyOCR, `deep-translator`, OpenCV-headless, Pillow, pytest | REST API execution, CPU-optimized inference, inpainting, and typesetting |
| **Frontend UI** | Node.js / Vercel | `frontend/` | Next.js 14 (App Router), React 18+, TypeScript, Tailwind CSS, Lucide icons | User interface, drag-and-drop uploads, comparison preview, and interactive text editing |

---

## 3. Memory Budgets & Hardware Constraints

### 3.1 Local Development & GPU Training Budget
- **System RAM:** 24 GB DDR5.
- **GPU Accelerator:** NVIDIA GeForce RTX 5050 Laptop GPU (8 GB VRAM, Compute Capability 8.9+, CUDA 13.1).
- **VRAM Allocation Budget:**
  - Base TensorFlow Runtime: ~1.5 GB.
  - MobileNetV2-UNet Model Weights & Gradients: ~250 MB.
  - Forward/Backward Activation Buffer ($512 \times 512 \times 3$, Batch Size 8): ~2.8 GB.
  - Mixed Precision (`mixed_float16`) reduces peak activation overhead by ~40%.
  - Headroom for system OS and display buffers: ~3.0 GB.
- **Rule:** If batch size 8 exceeds available VRAM on complex augmentations, reduce batch size to 4 or input spatial dimension to $384 \times 384$.

### 3.2 Hugging Face Docker Space Runtime Budget (Free Tier)
- **CPU Architecture:** 2 vCPU Intel/AMD x86_64 (CPU inference mode).
- **System Memory (RAM):** 16 GB maximum.
- **Disk Space:** 50 GB container disk layer.
- **Cold-Start Allocation Plan:**
  - EasyOCR Model Weights (CRAFT detector + Latin/Japanese recognition models): ~120 MB loaded into `/home/user/.EasyOCR`.
  - MobileNetV2-UNet (or OpenCV Fallback): ~45 MB loaded into system RAM.
  - Peak per-request processing footprint: < 1.2 GB per $2048 \times 2048$ image.
  - Concurrency: Bounded by semaphore to 2 concurrent image pipelines to guarantee stability within 16 GB RAM.

---

## 4. Deployment Topology & Service Interaction

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant FE as Next.js Studio (Vercel)
    participant API as FastAPI Gateway (HF Spaces)
    participant Seg as Bubble Segmenter
    participant OCR as EasyOCR Engine
    participant Trans as Translation Adapter
    participant TS as Inpainter & Typesetter

    User->>FE: Upload Comic Page (PNG/JPEG) + Select Languages (e.g., JA -> EN)
    FE->>API: POST /api/v1/translate-page (Multipart Form)
    API->>API: Validate MIME, EXIF orientation, image dimensions
    API->>Seg: Segment Page (image array, reading direction)
    Seg-->>API: Bubble Masks, Contours & Sorted Bounding Boxes
    API->>OCR: Extract Text from Bubble Crops
    OCR-->>API: Raw Text & Line Bounding Boxes
    API->>Trans: Translate Text per Bubble (with Cache check)
    Trans-->>API: Translated Strings
    API->>TS: Inpaint Lettering & Render Translated Text
    TS-->>API: Mask Overlay & Typeset Image (PNG)
    API-->>FE: JSON Response (Base64 Images, Bubbles metadata, Timings)
    FE->>User: Display Side-by-Side Comparison & Editable Bubble Table
```

---

## 5. Security & Reliability Boundaries

1. **Input Sanitization:** Reject files exceeding 15 MB or pixel dimensions greater than $4096 \times 4096$ to prevent decompression bomb vulnerabilities (PIL `Image.MAX_IMAGE_PIXELS` safe ceiling).
2. **Data Privacy:** Raw uploaded images and extracted text are processed entirely in-memory and are never written to permanent disk storage or telemetry logs by default.
3. **CORS Governance:** Explicit origins permitted in production (e.g., production Vercel domain and local development host); wildcards disabled in production deployments.
4. **Graceful Fallbacks:** If the neural network model checkpoint (`bubble_unet.keras`) is absent, the backend automatically falls back to classical OpenCV contour and morphological bubble segmentation, signaling its active mode in the API response headers and payload.
