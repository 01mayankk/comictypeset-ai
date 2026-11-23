# ComicTypeset AI

**Automated Speech Bubble Segmentation, Translation, and Re-Lettering**

ComicTypeset AI is an end-to-end computer-vision and NLP application
that helps localize speech bubbles on comic and manga pages, extract
their text, translate it, remove the original lettering, and render the
translated text back into the bubbles.

The project combines a trainable segmentation model, OCR, translation,
image inpainting, and a browser-based editing studio. It is designed as
an intermediate-to-advanced learning and portfolio project, with
reproducible experiments, explicit verification gates, and deployment
documentation.

> **Project status:** Active development. A working demo may use a
> classical computer-vision fallback until a trained segmentation
> checkpoint is available. Model quality must be evaluated on held-out
> real comic pages before describing the system as production-ready.

## Table of contents

-   [What it does](#what-it-does)
-   [Pipeline](#pipeline)
-   [Architecture](#architecture)
-   [Repository layout](#repository-layout)
-   [Hardware and environment](#hardware-and-environment)
-   [Getting started](#getting-started)
-   [Training workflow](#training-workflow)
-   [Backend API](#backend-api)
-   [Frontend workflow](#frontend-workflow)
-   [Datasets, licensing, and model
    assets](#datasets-licensing-and-model-assets)
-   [Testing and quality gates](#testing-and-quality-gates)
-   [Deployment](#deployment)
-   [Milestones and Git workflow](#milestones-and-git-workflow)
-   [Known limitations and planned
    improvements](#known-limitations-and-planned-improvements)
-   [Contributing](#contributing)

## What it does

Given a comic or manga page, the intended workflow is:

1.  Detect speech-bubble regions and create masks.
2.  Extract text from each detected bubble using OCR.
3.  Translate the extracted text into the selected target language.
4.  Remove the original lettering with image inpainting.
5.  Wrap, scale, and center the translated text inside the bubble.
6.  Let the user inspect detections, correct OCR/translation text, and
    download the resulting page.

The application should preserve the original page dimensions and return
a PNG result. It should also expose intermediate results so users can
inspect where an error occurred.

## Pipeline

``` mermaid
flowchart TD
    A[Comic page upload] --> B[Image validation and preprocessing]
    B --> C[Speech-bubble segmentation]
    C --> D[Bubble masks and regions]
    D --> E[Reading-order sorting]
    E --> F[OCR text extraction]
    F --> G[Text translation]
    G --> H[Original lettering removal]
    H --> I[Translated text layout]
    I --> J[Final page and editable bubble data]
    J --> K[Browser preview and PNG download]
```

### Four principal stages

  -----------------------------------------------------------------------
  Stage                   Component               Responsibility
  ----------------------- ----------------------- -----------------------
  1\. Segmentation        Keras MobileNetV2-UNet  Predict speech-bubble
                                                  masks and derive
                                                  regions

  2\. OCR                 EasyOCR                 Extract text from each
                                                  bubble crop

  3\. Translation         `deep-translator`       Translate extracted
                          adapter                 text with error
                                                  handling and caching

  4\. Inpainting and      OpenCV + Pillow         Remove original
  typesetting                                     lettering and render
                                                  translated text
  -----------------------------------------------------------------------

**Important distinction:** the model should learn the intended
segmentation target. A speech-bubble-region mask is not the same as a
text-only mask. Keep these labels and downstream operations explicit in
the dataset, model output, and documentation. If the system needs both
bubble boundaries and lettering masks, treat them as separate prediction
targets or clearly documented processing stages.

### Reading order

The backend should support:

-   `ltr`: top-to-bottom, then left-to-right ordering for Western comics
    and many manhwa pages.
-   `rtl`: top-to-bottom, then right-to-left ordering for Japanese
    manga.

Reading order is an approximation. Multi-column layouts, overlapping
bubbles, vertical text, and irregular panel layouts may require user
correction or a more advanced layout-analysis stage.

## Architecture

``` mermaid
flowchart LR
    U[User] --> FE[Next.js studio<br/>Vercel]
    FE -->|HTTP upload and options| API[FastAPI service<br/>Hugging Face Docker Space]
    API --> SEG[Segmentation model]
    SEG --> OCR[OCR adapter]
    OCR --> TR[Translation adapter]
    TR --> TS[Inpainting and typesetting]
    TS --> API
    API -->|Final image and bubble metadata| FE
    TRAIN[WSL2 Jupyter training workflow] -->|Versioned model artifact| SEG
    DATA[Licensed datasets and synthetic samples] --> TRAIN
```

### Main technologies

-   **ML:** TensorFlow/Keras, MobileNetV2 encoder, U-Net-style decoder,
    Dice/BCE loss, IoU and Dice metrics.
-   **Image processing:** OpenCV and Pillow.
-   **OCR:** EasyOCR.
-   **Translation:** `deep-translator` behind a replaceable adapter.
-   **Backend:** FastAPI and Uvicorn.
-   **Frontend:** Next.js App Router, TypeScript, and Tailwind CSS.
-   **Experiments:** JupyterLab notebooks with reusable Python modules.
-   **Deployment targets:** Hugging Face Docker Spaces for the API and
    Vercel for the frontend.

## Repository layout

``` text
comictypeset-ai/
├── README.md
├── .gitignore
├── project-prompt.md
├── docs/
│   ├── PROJECT_STATUS.md
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   ├── PIPELINE_FLOW.md
│   ├── DATA_FLOW.md
│   └── DEPLOYMENT.md
├── ml_experiments/
│   ├── README.md
│   ├── setup_env.sh
│   ├── requirements-train.txt
│   ├── config.yaml
│   ├── experiment_notes.md
│   ├── data/
│   │   └── .gitkeep
│   ├── src/
│   │   ├── __init__.py
│   │   ├── download_dataset.py
│   │   ├── synthetic_data_gen.py
│   │   ├── dataset_loader.py
│   │   └── model_unet.py
│   └── notebooks/
│       ├── 01_dataset_and_mask_visualization.ipynb
│       ├── 02_train_mobilenet_unet.ipynb
│       └── 03_end_to_end_pipeline_visual_debug.ipynb
├── backend/
│   ├── README.md
│   ├── setup_env.ps1
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .dockerignore
│   ├── models/
│   │   └── .gitkeep
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── pipeline/
│   │       ├── __init__.py
│   │       ├── segmenter.py
│   │       ├── ocr_translator.py
│   │       └── typesetter.py
│   └── tests/
│       └── test_pipeline.py
└── frontend/
    ├── README.md
    ├── package.json
    ├── next.config.mjs
    ├── tailwind.config.ts
    ├── tsconfig.json
    ├── .env.example
    └── src/
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   └── globals.css
        ├── components/
        │   ├── UploadZone.tsx
        │   ├── ComparisonViewer.tsx
        │   ├── BubbleEditor.tsx
        │   └── PipelineStatus.tsx
        └── lib/
            └── api.ts
```

The exact tree may evolve as implementation reveals better module
boundaries. Update this document and the architecture records when a
structural change is made.

## Hardware and environment

### Development machine

The initial development target is:

-   Windows 11
-   24 GB system RAM
-   NVIDIA RTX 5050 Laptop GPU with 8 GB VRAM
-   WSL2 with Ubuntu for GPU training

The memory targets are engineering constraints, not guarantees. Monitor
actual peak VRAM and RAM during training and inference.

### Environment isolation

Do not install project dependencies globally. Use separate environments
because training and deployment have different requirements.

  --------------------------------------------------------------------------------------
  Environment              Platform          Purpose           Main dependencies
  ------------------------ ----------------- ----------------- -------------------------
  `ml_experiments/.venv`   WSL2 Ubuntu       GPU training and  `tensorflow[and-cuda]`,
                                             notebooks         JupyterLab, NumPy,
                                                               OpenCV, Matplotlib,
                                                               Albumentations

  `backend/.venv`          Windows or Linux  Local API         `tensorflow-cpu`,
                                             development and   FastAPI, Uvicorn,
                                             CPU inference     EasyOCR, Pillow, OpenCV,
                                                               pytest
  --------------------------------------------------------------------------------------

The training environment is configured with mixed precision where
supported. Keep the final model output/loss computation numerically
stable (for example, use float32 for the final logits or loss-sensitive
operations when needed).

### Create environments

**WSL2 / Linux training environment**

``` bash
cd ml_experiments
chmod +x setup_env.sh
./setup_env.sh
```

The script should create `ml_experiments/.venv`, install
`requirements-train.txt`, and register the `comictypeset-ml` Jupyter
kernel.

**Windows backend environment**

Run PowerShell from the repository root:

``` powershell
.\backend\setup_env.ps1
```

Activate manually if needed:

``` powershell
.\backend\.venv\Scripts\Activate.ps1
```

Then start the API:

``` powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 7860
```

API health check: `http://127.0.0.1:7860/health`

## Getting started

### 1. Clone the repository

``` bash
git clone https://github.com/01mayankk/comictypeset-ai.git
cd comictypeset-ai
```

### 2. Start the backend

Create the backend environment using the appropriate setup script, then:

``` bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 7860
```

### 3. Start the frontend

Create `frontend/.env.local` from `.env.example` and set:

``` env
NEXT_PUBLIC_API_URL=http://127.0.0.1:7860
```

Then run:

``` bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

The frontend should provide a **Load Sample Comic Page** action so a
visitor can try the UI without sourcing a comic page. The sample should
be generated locally in the browser and clearly identified as
synthetic/demo content.

## Training workflow

All model experimentation should happen in notebooks, while reusable
logic stays in `ml_experiments/src/`.

### Notebook 1: dataset and mask visualization

`01_dataset_and_mask_visualization.ipynb`

-   Generate synthetic comic-like pages containing panels, speech
    bubbles, lettering, and visual texture.
-   Generate pixel-aligned segmentation masks.
-   Display source images, masks, and alpha overlays.
-   Validate image/mask dimensions, value ranges, and label semantics.
-   Inspect failure cases before training.

### Notebook 2: train MobileNetV2-UNet

`02_train_mobilenet_unet.ipynb`

Initial configuration:

  Parameter                           Initial value
  --------------- ---------------------------------
  Input size                              512 × 512
  Batch size                                      8
  Learning rate                              0.0001
  Precision         `mixed_float16` where supported
  Loss                  Dice + binary cross-entropy
  Metrics                              Dice and IoU

These are starting values, not immutable requirements. Reduce batch size
or image size if the 8 GB VRAM limit is exceeded. Use reproducible
train/validation/test splits, save the best checkpoint based on a
validation metric, and never tune against the held-out test set.

The notebook should:

-   Print TensorFlow version and GPU availability.
-   Record configuration and random seeds.
-   Plot training/validation loss, Dice, and IoU.
-   Display predictions against ground-truth masks.
-   Save the best model to `backend/models/bubble_unet.keras` for local
    integration.
-   Append run metadata and metrics to `experiment_notes.md`.

### Notebook 3: end-to-end visual debugging

`03_end_to_end_pipeline_visual_debug.ipynb`

Display each intermediate output:

`Raw page → Predicted mask → Bubble regions → Reading order → OCR → Translation → Inpainted page → Typeset page`

This notebook is for debugging and qualitative review. It should not
silently replace failed stages with fabricated outputs.

### Synthetic-to-real data warning

Synthetic data is useful for bootstrapping and testing, but it does not
establish real-world model performance. The model must be evaluated on
appropriately licensed, held-out real comic/manga pages. Report the
dataset source, license, split method, class balance, and metrics. Do
not claim general manga/comic accuracy based only on synthetic
validation data.

## Backend API

The FastAPI service is responsible for validation, orchestration, image
processing, and returning structured results.

### `GET /health`

Returns a lightweight health response indicating that the API process is
running. It should not trigger expensive model loading or OCR
initialization.

### `POST /api/v1/translate-page`

Accepts a comic page and processing options. The exact multipart field
names and response schema must be defined in `backend/README.md` and
kept synchronized with `backend/app/schemas.py` and frontend types.

Expected options include:

-   Source and target language.
-   Reading direction (`ltr` or `rtl`).
-   Optional rendering preferences.

Expected response data should include:

-   Final rendered page (or a stable result URL/encoded image
    representation).
-   Detected bubble IDs and bounding boxes.
-   OCR text and translated text for each bubble.
-   Per-stage status and non-fatal warnings.
-   Enough intermediate data for the frontend comparison view.

### Recommended API design improvements

-   Add a request-size limit, image dimension/pixel limit, and accepted
    MIME/format validation.
-   Normalize EXIF orientation and reject malformed or
    decompression-bomb images.
-   Add request timeouts and clear stage-specific errors.
-   Avoid loading the segmentation model repeatedly; initialize it once
    per worker.
-   Cache translation results using a key that includes source text,
    source language, target language, and provider.
-   Keep OCR and translation behind interfaces so providers can be
    replaced.
-   Do not log uploaded page contents or extracted private text by
    default.
-   Configure CORS with explicit frontend origins rather than a wildcard
    in production.
-   Return stable error codes and user-readable messages.

## Frontend workflow

The Next.js App Router application should provide a responsive studio
with:

-   Drag-and-drop upload and file picker.
-   Built-in synthetic sample page generator.
-   Source language, target language, and reading direction controls.
-   Pipeline progress with clear stage states.
-   Original / mask overlay / translated result comparison.
-   Editable detected-bubble table for OCR and translation corrections.
-   Re-render action after text correction.
-   Final PNG download.

The UI should distinguish between **processing completed**, **processing
completed with warnings**, and **processing failed**. Do not show a
success state merely because the request was submitted.

For large pages, use an explicit loading state and prevent duplicate
submissions. Revoke temporary browser object URLs when they are no
longer needed.

## Datasets, licensing, and model assets

Dataset licensing is a project requirement, not an afterthought.

-   Verify the current terms of use before downloading or redistributing
    Manga109, Roboflow, or any other dataset.
-   Do not commit raw datasets, private data, or copyrighted comic pages
    to GitHub.
-   Keep dataset download instructions and expected directory structure
    in `ml_experiments/README.md`.
-   Record annotation format, mask semantics, source, license, and
    preprocessing steps.
-   Treat Roboflow dataset licenses as project/version-specific; do not
    assume every public project permits commercial use or
    redistribution.
-   Use only fonts whose licenses permit the intended deployment and
    redistribution. Include attribution/license notices where required.

### Model artifact handling

Do not assume the trained `.keras` model should be committed directly to
Git. Model files can be large and may require Git LFS or external
artifact storage. Document the exact artifact source, version, checksum,
and download/setup procedure. The backend must fail clearly or use its
documented fallback when the model artifact is absent.

## Testing and quality gates

Verification must be repeatable and should test real behavior, not just
whether files exist.

### ML checks

-   Notebook files parse as valid nbformat 4 notebooks.
-   Python modules pass `py_compile`.
-   Dataset samples have matching image/mask dimensions and valid label
    values.
-   Model output shape matches the target mask shape.
-   Metrics are computed correctly and are not accidentally evaluated on
    training data.
-   A small smoke-training run completes when the training environment
    is available.

### Backend checks

``` bash
cd backend
pytest -q
```

Test segmentation fallback, model loading behavior, reading-order
sorting, OCR/translation error handling, inpainting, text wrapping, API
validation, and response serialization. Mock external translation calls
in unit tests so tests are deterministic and do not require network
access.

### Frontend checks

``` bash
cd frontend
npm install
npm run lint
npm run build
```

Also manually verify upload errors, sample-page flow, API failure
states, comparison modes, text correction, re-rendering, and PNG
download.

### Repository checks

-   All three READMEs and the docs agree with the actual implementation.
-   `.venv/`, `node_modules/`, build outputs, raw datasets, secrets, and
    local environment files are ignored.
-   `.env.example` contains names/placeholders only, never real secrets.
-   No test requires a live external service unless explicitly marked as
    an integration test.

A milestone is complete only when its checks pass or when an unavailable
check is explicitly documented with the reason and a follow-up action.
Avoid claiming "100% verified" when a dependency, GPU, network service,
or deployment target was not actually tested.

## Deployment

### Backend: Hugging Face Docker Space

The backend is intended to run as a Docker Space on port `7860`. The
`backend/README.md` should begin with the required Hugging Face YAML
metadata:

``` yaml
---
title: ComicTypeset AI
emoji: 💬
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
---
```

The Docker image should:

-   Use a pinned Python 3.11 base image (prefer a specific patch tag or
    digest for reproducibility).
-   Install the system libraries required by OpenCV.
-   Run as a non-root user.
-   Store EasyOCR model/cache files in a writable user directory.
-   Expose port `7860`.
-   Start Uvicorn with `app.main:app`.

Example runtime command:

``` bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

Plan for cold starts, limited CPU/RAM, model download time, and
temporary storage constraints on the selected Space hardware. Do not
assume the deployment has a GPU.

### Frontend: Vercel

-   Import the frontend project into Vercel.
-   Set `NEXT_PUBLIC_API_URL` to the deployed backend URL.
-   Add that exact Vercel origin to backend CORS configuration.
-   Deploy and verify the health endpoint and a complete sample-page
    request.
-   Keep secrets out of `NEXT_PUBLIC_*` variables; those values are
    exposed to the browser.

See `docs/DEPLOYMENT.md` for the deployment checklist and
troubleshooting.

## Milestones and Git workflow

The intended implementation sequence is five milestones:

  -------------------------------------------------------------------------------------------------------------------------------------------
  Milestone         Scope             Verification gate Conventional commit
  ----------------- ----------------- ----------------- -------------------------------------------------------------------------------------
  1                 Architecture docs Markdown and      `docs(architecture): initialize ComicTypeset AI docs and append-only status ledger`
                    and status ledger Mermaid review    

  2                 ML experiments    Notebook          `feat(ml): add MobileNetV2-UNet, synthetic generator, and Jupyter notebooks`
                    and notebooks     validation and    
                                      Python compile    
                                      checks            

  3                 Backend and       Backend tests and `feat(backend): add FastAPI translation pipeline and Hugging Face Docker config`
                    Docker            Docker            
                                      configuration     
                                      review            

  4                 Frontend          Lint and          `feat(frontend): add Next.js comic typeset studio and comparison viewer`
                                      production build  

  5                 Root README and   Full repository   `docs(readme): add global README with full system architecture diagram`
                    final audit       audit             
  -------------------------------------------------------------------------------------------------------------------------------------------

For every milestone:

1.  Read `docs/PROJECT_STATUS.md` before exploring or changing files.
2.  Build only the current milestone.
3.  Run the milestone's verification checks and fix failures.
4.  Append a timestamped entry to `docs/PROJECT_STATUS.md`; never erase
    historical entries.
5.  Commit with the specified Conventional Commit message.
6.  Push to `origin main` only after verifying the remote, branch,
    staged diff, and commit contents.

Initialize the repository only if it is not already initialized:

``` bash
git init
git branch -M main
git remote -v
```

If the intended remote is not configured, add it:

``` bash
git remote add origin https://github.com/01mayankk/comictypeset-ai.git
```

Before pushing, inspect:

``` bash
git status
git diff --cached
git remote -v
git log -1 --oneline
```

Then push:

``` bash
git push -u origin main
```

Do not overwrite an existing remote history with force-push. If the
remote contains commits not present locally, inspect and reconcile them
first. Never commit secrets, raw datasets, or large model artifacts
accidentally.

## Known limitations and planned improvements

The initial implementation is a foundation, not a solved
comic-localization system. Likely next improvements include:

1.  **Better layout understanding:** panel detection, bubble-to-panel
    association, overlapping bubble handling, and improved reading-order
    inference.
2.  **More reliable segmentation:** separate bubble-region and
    text-region masks where needed; evaluate on real held-out pages.
3.  **Vertical text support:** OCR and rendering for Japanese vertical
    writing, rotated text, and mixed scripts.
4.  **Translation quality:** glossary support, character-name
    consistency, context-aware translation, and human review.
5.  **Typesetting quality:** speech-tail preservation, font selection,
    stroke/outline support, line-break constraints, and per-language
    font fallback.
6.  **Editable geometry:** allow users to adjust bubble regions and
    masks, not only text.
7.  **Operational reliability:** background jobs for large pages,
    progress polling, cancellation, rate limiting, and bounded
    concurrency.
8.  **Observability:** structured logs, request IDs, stage timings,
    model version reporting, and privacy-conscious diagnostics.
9.  **Evaluation:** maintain a small, licensed benchmark with
    segmentation Dice/IoU, OCR character error rate, translation review,
    and typesetting failure categories.
10. **Model lifecycle:** versioned model artifacts, checksums,
    reproducible training configs, and documented rollback.

## Contributing

Before contributing:

1.  Read `docs/PROJECT_STATUS.md`.
2.  Read the relevant architecture and decision records.
3.  Keep reusable ML logic in `.py` modules and experiments in
    notebooks.
4.  Add or update tests for behavior changes.
5.  Update documentation when interfaces, data formats, or deployment
    behavior change.
6.  Never commit secrets, raw datasets, or unlicensed assets.

## License

A license has not yet been selected. Until a license is added to the
repository, do not assume that the code is available for reuse,
redistribution, or commercial use. Add a `LICENSE` file after choosing a
license and checking the licenses of bundled assets and dependencies.
