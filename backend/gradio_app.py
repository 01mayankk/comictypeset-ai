"""Hugging Face Gradio entrypoint that retains the FastAPI backend routes."""

from __future__ import annotations

import os

import gradio as gr
import spaces
import uvicorn

from app.main import app as api_app


@spaces.GPU(duration=5)
def check_zero_gpu() -> str:
    import torch

    if not torch.cuda.is_available():
        return "ZeroGPU allocation is unavailable."
    return f"ZeroGPU available: {torch.cuda.get_device_name(0)}"


with gr.Blocks(title="ComicTypeset AI") as demo:
    gr.Markdown("# ComicTypeset AI")
    gr.Markdown(
        "Speech bubble segmentation, OCR, translation, and typesetting are exposed "
        "through the FastAPI service."
    )
    gr.Markdown("[Open API documentation](/docs) | [Health status](/health)")
    gr.Markdown(
        "Inference currently runs on CPU; ZeroGPU acceleration is not configured "
        "for this TensorFlow model."
    )
    gpu_status = gr.Textbox(label="ZeroGPU diagnostic", interactive=False)
    gr.Button("Check ZeroGPU allocation").click(check_zero_gpu, outputs=gpu_status)


app = gr.mount_gradio_app(api_app, demo, path="/gradio")


if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", os.environ.get("PORT", "7860")))
    uvicorn.run(app, host="0.0.0.0", port=port)
