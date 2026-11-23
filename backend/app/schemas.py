"""Pydantic Request and Response Schemas for ComicTypeset AI API."""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Bounding box coordinates of a detected speech bubble."""
    x: int = Field(..., description="Top-left X coordinate")
    y: int = Field(..., description="Top-left Y coordinate")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")


class BubbleItem(BaseModel):
    """Metadata and extracted text for an individual speech bubble."""
    id: int = Field(..., description="Unique bubble ID")
    order: int = Field(..., description="Reading order sequence index (1-based)")
    bbox: BoundingBox = Field(..., description="Bounding box")
    raw_text: str = Field(default="", description="Original OCR extracted text")
    translated_text: str = Field(default="", description="Translated text")
    confidence: float = Field(default=1.0, description="OCR detection confidence score")
    polygon: List[List[int]] = Field(default_factory=list, description="Contour polygon points [[x, y], ...]")


class TranslationResponse(BaseModel):
    """Primary API response model for POST /api/v1/translate-page."""
    success: bool = Field(default=True, description="Indicates if pipeline processing succeeded")
    detector_mode: str = Field(..., description="Active bubble detector: 'unet' or 'opencv_fallback'")
    reading_direction: str = Field(default="ltr", description="Applied reading order: 'ltr' or 'rtl'")
    source_lang: str = Field(..., description="Source language code")
    target_lang: str = Field(..., description="Target language code")
    total_bubbles_detected: int = Field(..., description="Total number of segmented speech bubbles")
    bubbles: List[BubbleItem] = Field(default_factory=list, description="List of detected bubbles")
    final_image_base64: str = Field(..., description="Data URI string of final typeset PNG")
    mask_overlay_base64: str = Field(..., description="Data URI string of bubble mask overlay PNG")
    timings_ms: dict[str, float] = Field(default_factory=dict, description="Stage latency breakdown in milliseconds")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal execution warnings")


class HealthResponse(BaseModel):
    """API health check response model."""
    status: str = Field(default="ok", description="Service status")
    version: str = Field(default="1.0.0", description="Application version")
    detector_mode: str = Field(default="opencv_fallback", description="Active segmentation detector mode")
    model_loaded: bool = Field(default=False, description="True if trained Keras weights are loaded")
