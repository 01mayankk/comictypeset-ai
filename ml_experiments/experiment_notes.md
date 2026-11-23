# ML Experimentation Notes — ComicTypeset AI

## Hardware & Runtime Configuration
- **Platform:** Windows 11 with WSL2 Ubuntu 24.04
- **Host GPU:** NVIDIA GeForce RTX 5050 Laptop GPU (8 GB VRAM)
- **Host RAM:** 24 GB DDR5
- **Driver:** 592.27 | CUDA Version: 13.1
- **Mixed Precision:** Configured for `mixed_float16` with `float32` output layer for numerical stability.

---

## Experiment Run Log

### Run 001 — MobileNetV2-UNet Architecture & Dataset Acquisition Verification
- **Date:** 2026-11-23
- **Model:** MobileNetV2 Encoder (ImageNet weights) + U-Net Skip Decoder
- **Input Resolution:** 512x512x3
- **Loss:** 0.5 * BCE + 0.5 * Dice Loss
- **Metrics Tracked:** Dice Coefficient, Mean IoU
- **Dataset Pipeline:** Resilient multi-source downloader with automated synthetic fallback. Binary masks normalized to `{0, 255}`.
- **Split Ratio:** 80% Train, 10% Validation, 10% Test (Seed: 42)
- **Status:** Verified. Synthetic data generation and mask alignment confirmed ($512 \times 512$, values $\in \{0, 255\}$).
