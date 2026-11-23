# ComicTypeset AI --- Antigravity Master Build Prompt

> Use this file as the autonomous implementation brief. The root
> `README.md` is the human-facing project overview; this file defines
> the build sequence, constraints, autonomous dataset acquisition,
> verification gates, and Git workflow.

You are an autonomous Principal AI and Full-Stack Software Architect.
Build **ComicTypeset AI --- Automated Speech Bubble Segmentation,
Translation, and Re-Lettering** in the current workspace.

**Repository:** `https://github.com/01mayankk/comictypeset-ai.git`

Do not stop after generating files. Implement, run available checks,
download and normalize the training dataset automatically, fix defects,
document anything that cannot be verified, and proceed milestone by
milestone. Never claim a test, dataset download, or deployment succeeded
unless it actually ran and passed.

------------------------------------------------------------------------

## 0. Mandatory session boot protocol

1.  At the start of every session, read `docs/PROJECT_STATUS.md` first
    if it exists.
2.  Use its checklist and append-only history to identify the next task.
3.  Inspect only files needed for that task. Do not rescan or rewrite
    verified modules without a concrete reason.
4.  Preserve established interfaces and naming conventions unless a
    failing test or documented design change requires an update.
5.  Keep code concise, modular, typed where practical, and documented
    where behavior is non-obvious.
6.  If a required external service, dataset mirror, GPU, or deployment
    target is unavailable, record the limitation and execute the
    documented fallback. Do not fabricate results.

## 1. Project identity and constraints

-   Name: `ComicTypeset AI`
-   Tagline:
    `Automated Speech Bubble Segmentation, Translation, and Re-Lettering.`
-   OS: Windows 11 with WSL2 Ubuntu for GPU experiments.
-   Hardware target: 24 GB system RAM and NVIDIA RTX 5050 Laptop GPU
    with 8 GB VRAM.
-   Keep training and backend environments isolated.
-   Never install Python dependencies globally.
-   Do not commit secrets, raw or processed datasets (`ml_experiments/data/`),
    copyrighted comic pages, or unreviewed large model artifacts.

### Environments

**Training:** `ml_experiments/.venv` inside WSL2 Ubuntu, using
`tensorflow[and-cuda]`, JupyterLab, `ipykernel`, Matplotlib,
Albumentations, OpenCV, PyYAML, tqdm, `huggingface-hub`, `datasets`,
and `requests`.

**Backend:** `backend/.venv`, using `tensorflow-cpu`, FastAPI, Uvicorn,
`python-multipart`, EasyOCR, `deep-translator`, OpenCV headless, Pillow,
NumPy, pytest, and httpx.

Create:

-   `ml_experiments/setup_env.sh`: create `ml_experiments/.venv`,
    install `requirements-train.txt`, and register the `comictypeset-ml`
    Jupyter kernel.
-   `backend/setup_env.ps1`: create `backend/.venv` and install
    `requirements.txt`.

Pin compatible dependency versions where practical. Verify actual
Python/TensorFlow compatibility rather than assuming package
combinations work.

## 2. Required repository structure

Create this exact structure, adjusting only when implementation evidence
justifies a change:

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
│   ├── models/.gitkeep
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
        └── lib/api.ts
```

## 3. ML implementation requirements

### Autonomous dataset acquisition (`ml_experiments/src/download_dataset.py`)

-   The agent MUST write and execute `download_dataset.py` during
    Milestone 2 to automatically download and prepare real speech-bubble
    segmentation training data into `ml_experiments/data/` without manual
    user intervention.
-   Implement a resilient multi-source acquisition cascade:
    1.  **Optional Roboflow Source:** Check environment variables for
        `ROBOFLOW_API_KEY`; if present, download the configured public
        comic/manga speech-bubble segmentation dataset via Roboflow REST
        API into `ml_experiments/data/raw/roboflow/`.
    2.  **Unauthenticated Hugging Face Hub Source (Default):** If no API
        key is set, query/pull an open, publicly accessible comic or manga
        speech-bubble segmentation dataset from Hugging Face Hub using
        `datasets` / `huggingface_hub` (requiring no manual login or
        gated approval) into `ml_experiments/data/raw/hf/`.
    3.  **Annotation Format Normalization:** Convert whatever annotation
        format the downloaded dataset uses (COCO JSON polygons, YOLO
        segmentation `.txt` polygons, bounding-box-to-ellipse approximations
        only if polygon masks are absent, or existing mask images) into
        one unified, pixel-aligned directory layout:
        -   `ml_experiments/data/processed/real/images/*.png`
        -   `ml_experiments/data/processed/real/masks/*.png` (single-channel
            8-bit binary masks: `0` = background, `255` = speech bubble)
    4.  **Manifest & Provenance:** Write
        `ml_experiments/data/processed/real/dataset_manifest.json`
        recording the exact dataset source/repo ID, license metadata,
        annotation conversion method, total sample count, and SHA256
        checksums.
    5.  **Offline / Mirror Fallback:** If offline or all external dataset
        mirrors fail, log the exact error in `dataset_manifest.json` and
        automatically invoke `synthetic_data_gen.py` to populate
        `ml_experiments/data/processed/synthetic/` so training never
        stalls.

### Model, training, and data loader

-   Implement a Keras MobileNetV2 encoder with a U-Net-style decoder
    (`model_unet.py`).
-   Use Dice plus binary cross-entropy loss and report Dice and IoU.
-   Use an initial image size of 512 × 512, batch size 8, and learning
    rate `1e-4`; make these configurable via `config.yaml`.
-   Enable mixed precision (`mixed_float16`) only when supported by the
    detected GPU and keep the final segmentation output layer in
    `float32` for numerical stability.
-   Make the segmentation target explicit: bubble-region masks and
    text-only masks are distinct labels; do not conflate them.
-   Build `synthetic_data_gen.py` to generate synthetic comic pages with
    panels, speech bubbles, text, halftone texture, and pixel-aligned
    binary masks.
-   Build `dataset_loader.py` (`tf.data`) to load
    `data/processed/real/` automatically when available (with optional
    synthetic pretraining/mixing), using deterministic `80/10/10`
    train/val/test splits, fixed random seeds, and leakage checks.
-   Do not claim general real-world performance if training ran only on
    synthetic fallback data.

### Notebooks

1.  `01_dataset_and_mask_visualization.ipynb`: inspects
    `dataset_manifest.json`, loads real (or synthetic fallback) samples,
    validates image/mask shapes and binary values, and renders
    side-by-side grids of source images, binary masks, and overlays.
2.  `02_train_mobilenet_unet.ipynb`: trains MobileNetV2-UNet on RTX
    5050 (or CPU smoke test), plots train/validation loss, Dice, and
    IoU curves, visualizes epoch mask predictions, saves the best
    checkpoint to `backend/models/bubble_unet.keras`, and appends run
    metrics and dataset source to `experiment_notes.md`.
3.  `03_end_to_end_pipeline_visual_debug.ipynb`: displays each inference
    stage from input page through predicted mask, reading-order boxes,
    inpainted bubbles, and final typeset output.

Keep reusable code in `ml_experiments/src/`; notebooks must import those
modules. All notebooks must be valid nbformat 4 JSON files.

Save the local trained artifact to `backend/models/bubble_unet.keras`,
but keep it gitignored by default. Document versioning, SHA256 checksum,
and external artifact storage or Git LFS in `docs/DEPLOYMENT.md`.

## 4. Backend implementation requirements

Implement FastAPI with:

-   `GET /health`
-   `POST /api/v1/translate-page`

Pipeline modules:

-   `segmenter.py`: load `backend/models/bubble_unet.keras` when present;
    otherwise use a clearly identified OpenCV adaptive-threshold/contour
    fallback for demo/testing. Log and expose in API metadata which
    detector is active. Support `ltr` and `rtl` reading-order modes.
-   `ocr_translator.py`: EasyOCR extraction and translation through
    replaceable adapters (`deep-translator`), with in-memory caching and
    clear error handling.
-   `typesetter.py`: morphological mask dilation, OpenCV inpainting, and
    Pillow dynamic text wrapping, font-size scaling, and centering with
    configurable fonts.

Additional requirements:

-   Validate MIME type, file size, image dimensions, and decoded image
    content.
-   Normalize EXIF orientation and handle malformed or decompression-bomb
    images safely.
-   Initialize expensive models once per worker via FastAPI lifespan, not
    once per request.
-   Use bounded resource consumption and clear stage timeouts.
-   Return structured bubble metadata, Base64 mask overlay and final
    typeset PNG, stage statuses, detector mode (`unet` vs `opencv_fallback`),
    and non-fatal warnings.
-   Do not log uploaded images or extracted text by default.
-   Use explicit CORS origins in production.
-   Mock network translation in unit tests.
-   Keep `backend/app/schemas.py` synchronized with `frontend/src/lib/api.ts`.

## 5. Frontend implementation requirements

Build a responsive Next.js App Router application using TypeScript and
Tailwind CSS.

Components:

-   `UploadZone.tsx`: drag/drop, file picker, and a browser-generated
    sample comic page clearly labeled as synthetic demo content.
-   `ComparisonViewer.tsx`: original page, bubble mask overlay, and
    final typeset result; support final PNG download.
-   `BubbleEditor.tsx`: editable OCR and translated text per detected
    bubble, with a re-render action.
-   `PipelineStatus.tsx`: accurate progress, active detector badge
    (trained U-Net vs. OpenCV fallback), and stage states.

The UI must include source/target language and reading direction (`ltr` /
`rtl`) controls, validation errors, loading states, and recoverable API
errors. Do not report completion until the backend returns a successful
result. Revoke temporary object URLs when no longer needed.

## 6. Documentation requirements

Create:

-   Root `README.md`: project overview, pipeline, architecture Mermaid
    diagram, repository tree, setup, dataset download & training
    workflow, testing, deployment, limitations, and contribution guide.
-   `ml_experiments/README.md`: WSL2 GPU setup, autonomous dataset
    downloader usage, dataset licensing notes, notebook order, and
    training workflow.
-   `backend/README.md`: Hugging Face YAML frontmatter, API contract,
    local run, Docker instructions, and backend Mermaid diagram.
-   `frontend/README.md`: UI components, state flow Mermaid diagram,
    local run, and Vercel configuration.
-   `docs/ARCHITECTURE.md`: system boundaries, runtime environments,
    memory budgets (8 GB VRAM / 16 GB HF CPU RAM), and deployment topology.
-   `docs/DECISIONS.md`: dated architecture decision records with
    context, decision, alternatives, and consequences.
-   `docs/PIPELINE_FLOW.md`: dataset acquisition, training, and 4-stage
    inference flow.
-   `docs/DATA_FLOW.md`: request, image, mask, OCR, translation, and
    response transformations.
-   `docs/DEPLOYMENT.md`: GitHub, Hugging Face Docker Space, Vercel,
    environment variables, model artifact hosting, and troubleshooting.
-   `docs/PROJECT_STATUS.md`: master checklist plus append-only
    chronological milestone ledger.

All Mermaid diagrams must accurately reflect implemented behavior.

## 7. Hugging Face Docker Space requirements

The first lines of `backend/README.md` must be:

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

Use a pinned `python:3.11-slim` image with required OpenCV system
libraries (`libgl1`, `libglib2.0-0`). Create and run as a non-root user
with UID 1000. Configure a writable EasyOCR cache directory
(`/home/user/.EasyOCR`). Expose port `7860` and run:

``` bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

Account for CPU-only inference, cold starts, EasyOCR weight download
time, writable storage, and 16 GB RAM limits. Do not assume a GPU is
available in the deployed Space.

## 8. Verification gates

### Milestone 1 --- Docs and status ledger

-   Validate Markdown structure and Mermaid blocks.
-   Confirm all planned documents exist and cross-references are valid.

### Milestone 2 --- ML experiments and autonomous dataset download

-   Execute `python ml_experiments/src/download_dataset.py` and verify
    `ml_experiments/data/processed/real/` (or documented offline
    fallback) contains aligned `images/`, binary `masks/` (`{0, 255}`),
    and `dataset_manifest.json`.
-   Parse all three `.ipynb` notebooks with `nbformat`.
-   Run `python -m py_compile ml_experiments/src/*.py`.
-   Validate synthetic and real image/mask dimension alignment and mask
    value ranges.
-   Run a small smoke test (1–2 epochs on a subset) if the training
    environment and GPU are available; if GPU execution is unavailable in
    the current shell, record that explicitly in `PROJECT_STATUS.md`.
-   Confirm `git status` shows `ml_experiments/data/` (except `.gitkeep`)
    is properly ignored.

### Milestone 3 --- Backend

-   Create `backend/.venv` and install dependencies.
-   Run `pytest -q` from `backend/`.
-   Test fallback segmentation, model loading behavior, reading order,
    OCR/translation error paths, inpainting, typesetting, request
    validation, and API responses.
-   Verify Docker configuration. Build the image if Docker is available;
    otherwise document that the image build was not run.

### Milestone 4 --- Frontend

Run inside `frontend/`:

``` bash
npm install
npm run lint
npm run build
```

Manually verify the sample page, upload, progress, comparison, editing,
re-render, error handling, and PNG download where the running backend is
available.

### Milestone 5 --- Global audit

-   Review all three READMEs and `docs/*.md` for consistency.
-   Verify `.gitignore` covers `.venv/`, caches, `.ipynb_checkpoints`,
    `node_modules`, `.next`, local env files, `ml_experiments/data/`,
    and `backend/models/*.keras`.
-   Verify no secrets, raw datasets, or unlicensed assets are staged.
-   Run all feasible checks and record skipped checks with reasons.

Do not describe a gate as passed unless it was executed successfully.

## 9. Append-only status update format

After each milestone, append a timestamped entry to
`docs/PROJECT_STATUS.md`. Never overwrite earlier entries.

Use this structure:

``` markdown
## YYYY-MM-DD HH:MM — Milestone N: Name

- [COMPLETED] ...
- [VERIFIED] ...
- [NEXT TODO] ...
- Verification evidence:
  - Command:
  - Result:
  - Environment:
- Known limitations:
  - ...
```

Tick the master checklist only when the corresponding milestone is
genuinely complete.

## 10. Git initialization, commits, and pushes

First inspect the workspace and Git state. Do not destroy existing
history.

If Git is not initialized:

``` bash
git init
git branch -M main
```

Inspect remotes. Add the target only if needed:

``` bash
git remote -v
git remote add origin https://github.com/01mayankk/comictypeset-ai.git
```

For each milestone, follow this sequence:

1.  Build.
2.  Verify and fix.
3.  Append the status ledger.
4.  Review `git status` and `git diff`.
5.  Stage only intended files.
6.  Commit using the specified message.
7.  Inspect the commit and remote branch.
8.  Push to `origin main`.

Commit messages:

1.  `docs(architecture): initialize ComicTypeset AI docs and append-only status ledger`
2.  `feat(ml): add MobileNetV2-UNet, autonomous dataset loader, and notebooks`
3.  `feat(backend): add FastAPI translation pipeline and Hugging Face Docker config`
4.  `feat(frontend): add Next.js comic typeset studio and comparison viewer`
5.  `docs(readme): add global README with full system architecture diagram`

Before pushing:

``` bash
git status
git diff --cached
git remote -v
git log -1 --oneline
```

Push with:

``` bash
git push -u origin main
```

Never force-push as a shortcut. If remote history differs, inspect and
reconcile it. Do not push secrets, raw datasets, or unreviewed model
artifacts.

## 11. Execution instruction

Start with **Milestone 1**. Read `docs/PROJECT_STATUS.md` first if it
exists. Then inspect the minimum required workspace state, implement the
documentation milestone, validate it, append the status entry, and
commit/push only after the checks and Git review succeed.

Continue to the next milestone only after the current milestone is
verified and recorded. At the end of each milestone, report:

-   Files created or changed.
-   Checks actually executed and their results.
-   Commit hash and push result, if applicable.
-   Remaining risks and the next TODO.