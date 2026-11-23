"""Inpainting and Dynamic Typesetting Stage.

Removes original comic lettering via morphological mask dilation and OpenCV Telea inpainting.
Dynamically wraps, scales, and centers translated text into speech bubbles using Pillow.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class ComicTypesetter:
    """Manages speech bubble inpainting and dynamic typography rendering."""

    def __init__(self, default_font_path: str | None = None) -> None:
        self.default_font_path = default_font_path

    def _get_font(self, font_size: int) -> ImageFont.ImageFont:
        """Loads TrueType font or falls back to standard bitmap font."""
        if self.default_font_path:
            try:
                return ImageFont.truetype(self.default_font_path, size=font_size)
            except Exception:
                pass
        
        # System font fallbacks
        system_fonts = [
            "arial.ttf",
            "DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arial.ttf"
        ]
        for f in system_fonts:
            try:
                return ImageFont.truetype(f, size=font_size)
            except Exception:
                continue

        return ImageFont.load_default()

    def inpaint_lettering(
        self,
        image_rgb: np.ndarray,
        bubbles: list[dict[str, Any]],
        dilation_iters: int = 2
    ) -> np.ndarray:
        """Inpaints original lettering inside speech bubbles while preserving outer artwork.

        Args:
            image_rgb: Source page in RGB format.
            bubbles: List of detected bubble metadata with 'bbox'.
            dilation_iters: Number of morphological dilation iterations.

        Returns:
            Inpainted RGB image array.
        """
        h, w = image_rgb.shape[:2]
        text_mask = np.zeros((h, w), dtype=np.uint8)

        # Detect dark text pixels inside each bubble region
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

        for b in bubbles:
            bx = b["bbox"]["x"]
            by = b["bbox"]["y"]
            bw = b["bbox"]["width"]
            bh = b["bbox"]["height"]

            pad_x = max(3, int(bw * 0.08))
            pad_y = max(3, int(bh * 0.08))

            x0 = max(0, bx + pad_x)
            y0 = max(0, by + pad_y)
            x1 = min(w, bx + bw - pad_x)
            y1 = min(h, by + bh - pad_y)

            if x1 <= x0 or y1 <= y0:
                continue

            crop_gray = gray[y0:y1, x0:x1]

            # In typical comic bubbles, text is dark against bright bubble background
            # Otsu or fixed thresholding isolates dark text characters
            _, thresh = cv2.threshold(crop_gray, 180, 255, cv2.THRESH_BINARY_INV)
            text_mask[y0:y1, x0:x1] = thresh

        # Dilate text mask slightly to cover character stroke anti-aliasing edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        dilated_mask = cv2.dilate(text_mask, kernel, iterations=dilation_iters)

        # Perform Telea inpainting (requires BGR for OpenCV)
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        inpainted_bgr = cv2.inpaint(image_bgr, dilated_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        return cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)

    def _fit_text_in_box(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        max_w: int,
        max_h: int,
        min_font_size: int = 8,
        max_font_size: int = 36
    ) -> tuple[list[str], ImageFont.ImageFont, int]:
        """Finds optimal font size and word wrapping to fit text into rectangular box."""
        best_lines = [text]
        best_font = self._get_font(min_font_size)
        best_line_height = min_font_size + 4

        # Binary search for font size
        low = min_font_size
        high = max_font_size

        while low <= high:
            mid = (low + high) // 2
            font = self._get_font(mid)

            # Estimate characters per line based on average character width
            sample_bbox = draw.textbbox((0, 0), "A", font=font)
            char_w = max(4, sample_bbox[2] - sample_bbox[0])
            line_h = max(10, int(sample_bbox[3] - sample_bbox[1] * 1.3) + 4)

            chars_per_line = max(1, max_w // char_w)
            wrapped = textwrap.wrap(text, width=chars_per_line) or [text]

            total_h = len(wrapped) * line_h
            max_line_w = max(
                (draw.textbbox((0, 0), line, font=font)[2] - draw.textbbox((0, 0), line, font=font)[0])
                for line in wrapped
            )

            if max_line_w <= max_w and total_h <= max_h:
                best_lines = wrapped
                best_font = font
                best_line_height = line_h
                low = mid + 1  # Try larger
            else:
                high = mid - 1  # Try smaller

        return best_lines, best_font, best_line_height

    def typeset(
        self,
        image_rgb: np.ndarray,
        bubbles: list[dict[str, Any]]
    ) -> np.ndarray:
        """Renders translated text centered inside each speech bubble."""
        pil_img = Image.fromarray(image_rgb)
        draw = ImageDraw.Draw(pil_img)

        for b in bubbles:
            text = b.get("translated_text") or b.get("raw_text", "")
            if not text.strip():
                continue

            bx = b["bbox"]["x"]
            by = b["bbox"]["y"]
            bw = b["bbox"]["width"]
            bh = b["bbox"]["height"]

            # Inscribed box with safety padding for curved ellipse borders
            inner_w = max(20, int(bw * 0.74))
            inner_h = max(15, int(bh * 0.70))
            cx = bx + (bw // 2)
            cy = by + (bh // 2)

            lines, font, line_height = self._fit_text_in_box(draw, text, inner_w, inner_h)

            total_h = len(lines) * line_height
            start_y = cy - (total_h // 2)

            for idx, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                line_w = bbox[2] - bbox[0]
                line_x = cx - (line_w // 2)
                line_y = start_y + (idx * line_height)
                draw.text((line_x, line_y), line, fill=(0, 0, 0), font=font)

        return np.array(pil_img)

    def create_mask_overlay(
        self,
        image_rgb: np.ndarray,
        mask: np.ndarray,
        color: tuple[int, int, int] = (255, 40, 40),
        alpha: float = 0.45
    ) -> np.ndarray:
        """Generates a semi-transparent colored mask overlay on top of the original page."""
        overlay = image_rgb.copy()
        mask_bool = mask > 127
        overlay[mask_bool] = (
            overlay[mask_bool] * (1.0 - alpha) + np.array(color) * alpha
        ).astype(np.uint8)
        return overlay
