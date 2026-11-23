"""Speech Bubble Segmentation Stage.

Dual-mode detector:
- Mode 1: MobileNetV2-UNet neural network (when backend/models/bubble_unet.keras is present).
- Mode 2: Classical OpenCV adaptive-thresholding & contour extraction fallback.
Supports left-to-right (ltr) and right-to-left (rtl) reading-order sorting.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def sort_bubbles_reading_order(
    bubbles: list[dict[str, Any]],
    reading_direction: str = "ltr",
    band_height: int = 120
) -> list[dict[str, Any]]:
    """Sorts detected bubbles into natural comic reading order.

    - 'ltr': Top-to-bottom, left-to-right.
    - 'rtl': Top-to-bottom, right-to-left (Japanese manga).
    """
    if not bubbles:
        return []

    # Sort key: band grouping on Y, then X position
    def get_sort_key(b: dict[str, Any]) -> tuple[int, int]:
        bx = b["bbox"]["x"]
        by = b["bbox"]["y"]
        band = by // band_height
        if reading_direction == "rtl":
            # For right-to-left, invert X so higher X comes first within the band
            return (band, -bx)
        return (band, bx)

    sorted_list = sorted(bubbles, key=get_sort_key)

    # Re-assign sequential reading order index
    for idx, b in enumerate(sorted_list):
        b["order"] = idx + 1
        b["id"] = idx + 1

    return sorted_list


class SpeechBubbleSegmenter:
    """Orchestrates speech bubble segmentation with graceful classical fallback."""

    def __init__(self, model_path: str = "models/bubble_unet.keras") -> None:
        self.model_path = model_path
        self.model = None
        self.active_mode = "opencv_fallback"
        self._init_detector()

    def _init_detector(self) -> None:
        """Attempts to load pre-trained U-Net weights or activates OpenCV fallback."""
        if os.path.exists(self.model_path):
            try:
                import tensorflow as tf
                # Custom metric definitions for loading Keras checkpoint
                def dice_coef(y_true, y_pred, smooth=1e-6):
                    y_true_f = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
                    y_pred_f = tf.cast(tf.reshape(y_pred, [-1]), tf.float32)
                    intersection = tf.reduce_sum(y_true_f * y_pred_f)
                    return (2.0 * intersection + smooth) / (tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f) + smooth)

                def iou_metric(y_true, y_pred, smooth=1e-6):
                    y_true_f = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
                    y_pred_f = tf.cast(tf.reshape(y_pred, [-1]) > 0.5, tf.float32)
                    intersection = tf.reduce_sum(y_true_f * y_pred_f)
                    total = tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f)
                    union = total - intersection
                    return (intersection + smooth) / (union + smooth)

                self.model = tf.keras.models.load_model(
                    self.model_path,
                    custom_objects={"dice_coef": dice_coef, "iou_metric": iou_metric},
                    compile=False
                )
                self.active_mode = "unet"
                logger.info(f"Loaded trained MobileNetV2-UNet checkpoint from '{self.model_path}'.")
                return
            except Exception as exc:
                logger.warning(f"Failed to load UNet weights at '{self.model_path}': {exc}. Using fallback.")

        logger.info(f"No checkpoint at '{self.model_path}'. Active mode: opencv_fallback.")
        self.active_mode = "opencv_fallback"

    def _segment_opencv_fallback(self, image_rgb: np.ndarray) -> np.ndarray:
        """Extracts bubble candidates using edge contours and luminance thresholding."""
        h, w = image_rgb.shape[:2]
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        mask = np.zeros((h, w), dtype=np.uint8)

        total_page_area = h * w
        min_area = max(500, int(total_page_area * 0.003))
        max_area = int(total_page_area * 0.45)

        # Method 1: Edge detection for line-drawn speech bubbles
        edges = cv2.Canny(gray, 40, 140)
        kernel_edge = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_edge)
        edge_contours, _ = cv2.findContours(closed_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in edge_contours:
            area = cv2.contourArea(cnt)
            if min_area <= area <= max_area:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = cw / float(ch) if ch > 0 else 0
                if 0.25 <= aspect_ratio <= 4.0:
                    temp_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.drawContours(temp_mask, [cnt], -1, 255, -1)
                    mean_val = cv2.mean(gray, mask=temp_mask)[0]
                    if mean_val > 180:  # Bright/white speech bubble interior
                        cv2.drawContours(mask, [cnt], -1, 255, -1)

        # Method 2: Adaptive thresholding for textured/halftone pages
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 4
        )
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        closed_thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        thresh_cnts, _ = cv2.findContours(closed_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in thresh_cnts:
            area = cv2.contourArea(cnt)
            if min_area <= area <= max_area:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = cw / float(ch) if ch > 0 else 0
                if 0.25 <= aspect_ratio <= 4.0:
                    cv2.drawContours(mask, [cnt], -1, 255, -1)

        return mask

    def _segment_unet(self, image_rgb: np.ndarray) -> np.ndarray:
        """Infers speech bubble probability map with MobileNetV2-UNet."""
        orig_h, orig_w = image_rgb.shape[:2]

        resized = cv2.resize(image_rgb, (512, 512), interpolation=cv2.INTER_LINEAR)
        normalized = (resized.astype(np.float32) / 255.0)[np.newaxis, ...]

        pred = self.model.predict(normalized, verbose=0)[0, :, :, 0]
        binary = (pred > 0.5).astype(np.uint8) * 255

        mask = cv2.resize(binary, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
        return mask

    def segment(
        self,
        image_rgb: np.ndarray,
        reading_direction: str = "ltr"
    ) -> tuple[np.ndarray, list[dict[str, Any]]]:
        """Segments speech bubbles from an RGB image and returns the binary mask and sorted bubble regions.

        Args:
            image_rgb: Input image (H, W, 3) in RGB format.
            reading_direction: 'ltr' (Western) or 'rtl' (Manga).

        Returns:
            Tuple of:
            - binary_mask: np.ndarray (H, W) uint8 with values {0, 255}.
            - bubbles: list of dictionaries with bounding boxes, order, and polygon coordinates.
        """
        orig_h, orig_w = image_rgb.shape[:2]

        if self.active_mode == "unet" and self.model is not None:
            mask = self._segment_unet(image_rgb)
        else:
            mask = self._segment_opencv_fallback(image_rgb)

        # Extract contours from the generated binary mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        raw_bubbles: list[dict[str, Any]] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            # Ensure within image boundaries
            x = max(0, min(x, orig_w - 1))
            y = max(0, min(y, orig_h - 1))
            w = max(10, min(w, orig_w - x))
            h = max(10, min(h, orig_h - y))

            # Approximate polygon
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            poly_points = [[int(pt[0][0]), int(pt[0][1])] for pt in approx]

            raw_bubbles.append({
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "polygon": poly_points,
                "area": float(area)
            })

        sorted_bubbles = sort_bubbles_reading_order(
            raw_bubbles,
            reading_direction=reading_direction,
            band_height=max(50, orig_h // 5)
        )

        return mask, sorted_bubbles
