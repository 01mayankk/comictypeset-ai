"""Synthetic Comic Page & Speech Bubble Dataset Generator.

Generates realistic synthetic comic pages with panels, speech bubbles,
hand-lettered styled text, halftone patterns, and pixel-aligned binary masks.
Speech bubble regions are marked as 255 in the binary mask (0 = background).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SAMPLE_DIALOGUES = [
    ["WAIT!", "WHAT IS THAT OVER THERE?", "DON'T MOVE!"],
    ["WE MADE IT...", "BUT AT WHAT COST?", "LET'S KEEP MOVING."],
    ["HAHAHA!", "YOU'RE TOO LATE!", "THE POWER IS MINE!"],
    ["LOOK OUT!", "BEHIND YOU!", "TAKE COVER!"],
    ["I NEVER THOUGHT", "WE'D SEE THIS DAY.", "IT'S BEAUTIFUL."],
    ["IS ANYONE THERE?", "PLEASE ANSWER...", "HELLO?"],
    ["GET READY!", "THE FINAL BATTLE", "BEGINS NOW!"],
    ["HUH?!", "WHERE DID HE GO?", "HE DISAPPEARED!"],
    ["STAY CALM.", "WE HAVE A PLAN.", "FOLLOW MY LEAD."],
    ["THIS IS IT!", "DON'T GIVE UP NOW!", "FULL POWER!"]
]


def draw_halftone_pattern(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int], spacing: int = 8, radius: int = 2) -> None:
    """Renders a comic halftone dot pattern inside a bounding box."""
    x0, y0, x1, y1 = bbox
    for x in range(x0 + spacing // 2, x1, spacing):
        for y in range(y0 + spacing // 2, y1, spacing):
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(220, 220, 225))


def draw_speech_bubble(
    img_draw: ImageDraw.ImageDraw,
    mask_draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text_lines: list[str],
    tail_dir: str = "bottom-left"
) -> dict[str, Any]:
    """Draws an elliptical speech bubble with a tail and text onto both image and binary mask."""
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0

    # Calculate tail coordinates
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    
    if tail_dir == "bottom-left":
        p_base1 = (x0 + int(w * 0.25), y1 - int(h * 0.1))
        p_base2 = (x0 + int(w * 0.45), y1 - int(h * 0.05))
        p_tip = (max(5, x0 - int(w * 0.15)), min(y1 + int(h * 0.35), 505))
    elif tail_dir == "bottom-right":
        p_base1 = (x1 - int(w * 0.45), y1 - int(h * 0.05))
        p_base2 = (x1 - int(w * 0.25), y1 - int(h * 0.1))
        p_tip = (min(505, x1 + int(w * 0.15)), min(y1 + int(h * 0.35), 505))
    else:
        p_base1 = (cx - 15, y1 - 5)
        p_base2 = (cx + 15, y1 - 5)
        p_tip = (cx, min(y1 + int(h * 0.3), 505))

    tail_poly = [p_base1, p_tip, p_base2]

    # Draw tail and ellipse onto binary mask (Value = 255)
    mask_draw.polygon(tail_poly, fill=255)
    mask_draw.ellipse(box, fill=255)

    # Draw on image: tail fill + outline
    img_draw.polygon(tail_poly, fill=(255, 255, 255), outline=None)
    img_draw.line([p_base1, p_tip], fill=(0, 0, 0), width=3)
    img_draw.line([p_tip, p_base2], fill=(0, 0, 0), width=3)

    # Draw bubble ellipse on image
    img_draw.ellipse(box, fill=(255, 255, 255), outline=(0, 0, 0), width=3)

    # Inscribe text lines inside bubble
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    line_height = 14
    total_text_h = len(text_lines) * line_height
    start_y = cy - (total_text_h // 2)

    for i, line in enumerate(text_lines):
        line_w = len(line) * 6
        line_x = max(x0 + 8, cx - (line_w // 2))
        line_y = start_y + (i * line_height)
        img_draw.text((line_x, line_y), line, fill=(0, 0, 0), font=font)

    return {
        "bbox": [int(x0), int(y0), int(w), int(h)],
        "text": " ".join(text_lines),
        "tail": [list(p_base1), list(p_tip), list(p_base2)]
    }


def generate_synthetic_page(
    width: int = 512,
    height: int = 512,
    num_panels: int = 3,
    num_bubbles: int = 3,
    seed: int | None = None
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Generates a synthetic comic page and its pixel-aligned binary mask."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # Background canvas
    page_img = Image.new("RGB", (width, height), color=(248, 248, 246))
    mask_img = Image.new("L", (width, height), color=0)

    page_draw = ImageDraw.Draw(page_img)
    mask_draw = ImageDraw.Draw(mask_img)

    margin = 16
    gutter = 12

    # Layout panels
    panel_boxes: list[tuple[int, int, int, int]] = []
    if num_panels == 2:
        split_y = height // 2
        panel_boxes.append((margin, margin, width - margin, split_y - gutter // 2))
        panel_boxes.append((margin, split_y + gutter // 2, width - margin, height - margin))
    elif num_panels == 3:
        split_y = int(height * 0.48)
        panel_boxes.append((margin, margin, width - margin, split_y - gutter // 2))
        split_x = width // 2
        panel_boxes.append((margin, split_y + gutter // 2, split_x - gutter // 2, height - margin))
        panel_boxes.append((split_x + gutter // 2, split_y + gutter // 2, width - margin, height - margin))
    else:
        split_y = height // 2
        split_x = width // 2
        panel_boxes.append((margin, margin, split_x - gutter // 2, split_y - gutter // 2))
        panel_boxes.append((split_x + gutter // 2, margin, width - margin, split_y - gutter // 2))
        panel_boxes.append((margin, split_y + gutter // 2, split_x - gutter // 2, height - margin))
        panel_boxes.append((split_x + gutter // 2, split_y + gutter // 2, width - margin, height - margin))

    # Draw panels with background texture and comic elements
    for p_idx, p_box in enumerate(panel_boxes):
        px0, py0, px1, py1 = p_box
        page_draw.rectangle(p_box, fill=(255, 255, 255), outline=(0, 0, 0), width=3)

        # Halftone or speed lines
        if p_idx % 2 == 0:
            draw_halftone_pattern(page_draw, (px0 + 4, py0 + 4, px1 - 4, py1 - 4), spacing=10, radius=1)
        else:
            # Action lines radiating towards center
            cx = (px0 + px1) // 2
            cy = (py0 + py1) // 2
            for angle in range(0, 360, 40):
                rad = math.radians(angle)
                lx0 = cx + int(40 * math.cos(rad))
                ly0 = cy + int(40 * math.sin(rad))
                lx1 = cx + int(120 * math.cos(rad))
                ly1 = cy + int(120 * math.sin(rad))
                page_draw.line([(lx0, ly0), (lx1, ly1)], fill=(215, 215, 220), width=1)

        # Draw a silhouette / character placeholder
        char_cx = px0 + (px1 - px0) // 3
        char_cy = py1 - 30
        page_draw.ellipse([char_cx - 20, char_cy - 40, char_cx + 20, char_cy], fill=(40, 40, 45))
        page_draw.rectangle([char_cx - 25, char_cy - 5, char_cx + 25, py1 - 4], fill=(40, 40, 45))

    # Draw speech bubbles
    bubbles_metadata: list[dict[str, Any]] = []
    actual_bubble_count = min(num_bubbles, len(panel_boxes) * 2)

    for b_idx in range(actual_bubble_count):
        p_box = panel_boxes[b_idx % len(panel_boxes)]
        px0, py0, px1, py1 = p_box
        pw = px1 - px0
        ph = py1 - py0

        bw = random.randint(min(110, pw - 20), min(180, pw - 10))
        bh = random.randint(min(60, ph - 30), min(100, ph - 20))

        bx0 = px0 + random.randint(8, max(9, pw - bw - 8))
        by0 = py0 + random.randint(8, max(9, int(ph * 0.4)))
        bx1 = bx0 + bw
        by1 = by0 + bh

        dialogue = random.choice(SAMPLE_DIALOGUES)
        tail_dir = random.choice(["bottom-left", "bottom-right", "center"])
        b_meta = draw_speech_bubble(page_draw, mask_draw, (bx0, by0, bx1, by1), dialogue, tail_dir=tail_dir)
        bubbles_metadata.append(b_meta)

    image_array = np.array(page_img, dtype=np.uint8)
    mask_array = np.array(mask_img, dtype=np.uint8)

    return image_array, mask_array, bubbles_metadata


def generate_synthetic_dataset(
    output_dir: str,
    count: int = 50,
    width: int = 512,
    height: int = 512,
    seed: int = 42
) -> dict[str, Any]:
    """Generates and writes a batch of synthetic comic pages and masks."""
    images_dir = os.path.join(output_dir, "images")
    masks_dir = os.path.join(output_dir, "masks")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(masks_dir, exist_ok=True)

    manifest_entries: list[dict[str, Any]] = []

    for idx in range(count):
        cur_seed = seed + idx
        panels = random.choice([2, 3, 4])
        bubbles = random.randint(2, 4)
        img_np, mask_np, meta = generate_synthetic_page(
            width=width, height=height, num_panels=panels, num_bubbles=bubbles, seed=cur_seed
        )

        filename = f"synth_{idx:04d}.png"
        img_path = os.path.join(images_dir, filename)
        mask_path = os.path.join(masks_dir, filename)

        Image.fromarray(img_np).save(img_path)
        Image.fromarray(mask_np).save(mask_path)

        manifest_entries.append({
            "id": idx,
            "filename": filename,
            "width": width,
            "height": height,
            "bubbles": meta
        })

    manifest = {
        "dataset_name": "ComicTypeset Synthetic Speech Bubbles",
        "sample_count": count,
        "width": width,
        "height": height,
        "classes": {"0": "background", "255": "speech_bubble"},
        "samples": manifest_entries
    }

    manifest_path = os.path.join(output_dir, "synthetic_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic comic pages with speech bubble masks")
    parser.add_argument("--out_dir", type=str, default="data/processed/synthetic", help="Output directory")
    parser.add_argument("--count", type=int, default=20, help="Number of pages to generate")
    parser.add_argument("--size", type=int, default=512, help="Image resolution (width and height)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    manifest = generate_synthetic_dataset(args.out_dir, count=args.count, width=args.size, height=args.size, seed=args.seed)
    print(f"Generated {manifest['sample_count']} synthetic pages in '{args.out_dir}'.")
