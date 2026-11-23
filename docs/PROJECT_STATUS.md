# ComicTypeset AI — Project Status

## Master Checklist
- [x] Milestone 1 — Architecture docs and status ledger
- [x] Milestone 2 — ML experiments and autonomous dataset download
- [ ] Milestone 3 — Backend and Docker
- [ ] Milestone 4 — Frontend
- [ ] Milestone 5 — Root README and final audit

---

## Append-Only Milestone Ledger

## 2026-11-23 19:26 — Milestone 1: Architecture docs and status ledger

- [COMPLETED] Repository initialized and Git remote synced with `https://github.com/01mayankk/comictypeset-ai.git`.
- [COMPLETED] Created comprehensive root `.gitignore` protecting `.venv`, caches, Node modules, `.next`, dataset artifacts in `ml_experiments/data/`, and `.keras` model weights.
- [COMPLETED] Authored complete system architecture documentation:
  - `docs/ARCHITECTURE.md`: Detailed component boundaries, WSL2/Linux/Windows runtime platforms, memory budgets (8 GB VRAM RTX 5050 / 16 GB HF CPU RAM), and deployment topologies.
  - `docs/DECISIONS.md`: Eight formal Architecture Decision Records (ADRs) covering model architecture, dual-mode fallback, OCR selection, translation caching, typesetting, dataset cascade, Docker containerization, and frontend UI.
  - `docs/PIPELINE_FLOW.md`: Detailed dataset acquisition cascade, training loop, and 4-stage inference pipeline with reading order support (`ltr` and `rtl`).
  - `docs/DATA_FLOW.md`: Complete request/response lifecycle, data schemas, image transformation, mask generation, OCR extraction, inpainting, and typesetting serialization.
  - `docs/DEPLOYMENT.md`: Hugging Face Docker Space, Vercel frontend, model artifact storage, environment variable specifications, and troubleshooting steps.
- [VERIFIED] Markdown files and Mermaid diagrams validated for correct syntax and structure.
- [VERIFIED] Cross-references between architectural docs, pipeline specifications, and master build prompts confirmed.
- [NEXT TODO] Milestone 2: Autonomous dataset acquisition (`ml_experiments/src/download_dataset.py`), synthetic data generator, MobileNetV2-UNet model, and Jupyter experimentation notebooks.
- Verification evidence:
  - Command: `Get-ChildItem -Path docs/` & Markdown/Mermaid syntax review
  - Result: All planned docs created, consistent terminology, valid Mermaid blocks.
  - Environment: Windows 11 / PowerShell 7+ / Git 2.51.2
- Known limitations:
  - Hardware target RTX 5050 with 8 GB VRAM requires mixed precision and batch size constraint (<= 8) for 512x512 inputs.
  - Hugging Face Spaces free tier operates under CPU-only inference and 16 GB RAM; Cold starts and EasyOCR initialization must be buffered by the client.


## 2026-11-23 19:43 — Milestone 2: ML experiments and autonomous dataset download

- [COMPLETED] Created `ml_experiments/requirements-train.txt`, `ml_experiments/setup_env.sh`, `ml_experiments/config.yaml`, and `ml_experiments/experiment_notes.md`.
- [COMPLETED] Built `ml_experiments/src/synthetic_data_gen.py` capable of generating multi-panel comic pages with speech bubbles (tails, text, and halftone comic textures) and pixel-aligned binary masks.
- [COMPLETED] Built `ml_experiments/src/download_dataset.py` with an autonomous cascade (Roboflow -> unauthenticated Hugging Face Hub -> synthetic fallback generator), format normalization to `{0, 255}` binary masks, and `dataset_manifest.json` generation with SHA256 checksums.
- [COMPLETED] Built `ml_experiments/src/model_unet.py` providing Keras MobileNetV2-UNet, combined BCE + Dice loss, Dice metric, and IoU metric.
- [COMPLETED] Built `ml_experiments/src/dataset_loader.py` providing `tf.data` pipelines with deterministic 80/10/10 split, data leakage verification, and augmentations.
- [COMPLETED] Authored 3 Jupyter notebooks conforming to nbformat 4:
  - `01_dataset_and_mask_visualization.ipynb`
  - `02_train_mobilenet_unet.ipynb`
  - `03_end_to_end_pipeline_visual_debug.ipynb`
- [VERIFIED] Executed `python ml_experiments/src/download_dataset.py --count 15`, validating autonomous fallback and mask generation.
- [VERIFIED] Verified 100% of generated images and masks match spatial dimensions and contain binary values strictly in `{0, 255}`.
- [VERIFIED] All three notebooks validated via `nbformat.validate` (nbformat v4 schema).
- [VERIFIED] Python compilation verified on all `ml_experiments/src/*.py` modules (`python -m py_compile`).
- [VERIFIED] Confirmed `git status` ignores `ml_experiments/data/processed/` and `ml_experiments/data/raw/` while preserving `.gitkeep`.
- [NEXT TODO] Milestone 3: FastAPI backend (`backend/app`), Uvicorn server, schemas, dual-mode segmenter (U-Net + OpenCV fallback), EasyOCR & deep-translator integration, inpainting/typesetting pipeline, tests, and Hugging Face Docker setup.
- Verification evidence:
  - Command: `python ml_experiments/src/download_dataset.py`, `python -m py_compile ml_experiments/src/*.py`, `nbformat.validate`
  - Result: All files compiled, validated, dataset populated with manifest and SHA256 hashes.
  - Environment: Windows 11 / Python 3.10 / PowerShell 5.1
- Known limitations:
  - Hugging Face Hub unauthenticated download for gated comic datasets gracefully triggered synthetic generation fallback.
  - GPU-accelerated training environment is configured for WSL2 Ubuntu (`ml_experiments/setup_env.sh`), while current host execution shell is Windows PowerShell.
