"""Hugging Face Gradio entrypoint that retains the FastAPI backend routes."""

from __future__ import annotations

import os

import gradio as gr
import spaces
import uvicorn

os.environ.setdefault("COMICTYPESET_LIGHTWEIGHT", "1")

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
        "The free Space uses OpenCV segmentation and placeholder OCR. The full "
        "U-Net and EasyOCR pipeline remains available in the local backend."
    )
    gr.Markdown("[Open API documentation](/docs) | [Health status](/health)")
    gr.Markdown(
        "Use the API documentation to submit a page. Translation and typesetting "
        "remain enabled."
    )
    gpu_status = gr.Textbox(label="ZeroGPU diagnostic", interactive=False)
    gr.Button("Check ZeroGPU allocation").click(check_zero_gpu, outputs=gpu_status)

demo.queue()
app = gr.mount_gradio_app(api_app, demo, path="/gradio", ssr_mode=False)


if __name__ == "__main__":
    port = int(os.environ.get("GRADIO_SERVER_PORT", os.environ.get("PORT", "7860")))
    uvicorn.run(app, host="0.0.0.0", port=port)
