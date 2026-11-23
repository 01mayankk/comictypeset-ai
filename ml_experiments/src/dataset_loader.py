"""TensorFlow tf.data Dataset Loader for Speech Bubble Segmentation.

Loads processed real (or synthetic fallback) paired images and masks,
partitions into deterministic 80/10/10 train/val/test splits, performs
data leakage validation, and applies data augmentations.
"""

from __future__ import annotations

import glob
import os
import random
from typing import Any, Tuple

import numpy as np


def get_image_mask_pairs(data_dir: str) -> list[tuple[str, str]]:
    """Discovers and pairs matching images and binary masks."""
    images_dir = os.path.join(data_dir, "images")
    masks_dir = os.path.join(data_dir, "masks")

    if not os.path.exists(images_dir) or not os.path.exists(masks_dir):
        return []

    image_files = sorted(glob.glob(os.path.join(images_dir, "*.*")))
    pairs = []
    for img_path in image_files:
        basename = os.path.basename(img_path)
        name, _ = os.path.splitext(basename)
        # Search for corresponding mask with any standard image extension
        matching_masks = glob.glob(os.path.join(masks_dir, f"{name}.*"))
        if matching_masks:
            pairs.append((img_path, matching_masks[0]))

    return pairs


def create_deterministic_splits(
    pairs: list[tuple[str, str]],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
    seed: int = 42
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    """Splits pairs into disjoint train, val, and test partitions with leakage checks."""
    assert abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-5, "Split ratios must sum to 1.0"
    
    shuffled = list(pairs)
    rng = random.Random(seed)
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_pairs = shuffled[:n_train]
    val_pairs = shuffled[n_train:n_train + n_val]
    test_pairs = shuffled[n_train + n_val:]

    # Data leakage check: Verify zero intersection across sets
    train_imgs = {p[0] for p in train_pairs}
    val_imgs = {p[0] for p in val_pairs}
    test_imgs = {p[0] for p in test_pairs}

    assert train_imgs.isdisjoint(val_imgs), "Data leakage detected: train and val overlap!"
    assert train_imgs.isdisjoint(test_imgs), "Data leakage detected: train and test overlap!"
    assert val_imgs.isdisjoint(test_imgs), "Data leakage detected: val and test overlap!"

    return train_pairs, val_pairs, test_pairs


def parse_and_preprocess(img_path: str, mask_path: str, img_size: tuple[int, int] = (512, 512)) -> Any:
    """TensorFlow parsing function for an image and binary mask pair."""
    import tensorflow as tf

    # Read and decode image
    img_raw = tf.io.read_file(img_path)
    img = tf.io.decode_image(img_raw, channels=3, expand_animations=False)
    img = tf.image.resize(img, img_size, method="bilinear")
    img = tf.cast(img, tf.float32) / 255.0  # Normalize to [0, 1]

    # Read and decode mask
    mask_raw = tf.io.read_file(mask_path)
    mask = tf.io.decode_image(mask_raw, channels=1, expand_animations=False)
    mask = tf.image.resize(mask, img_size, method="nearest")
    # Mask values in {0, 255} converted to {0.0, 1.0}
    mask = tf.cast(mask > 127, tf.float32)

    return img, mask


def augment(img: Any, mask: Any) -> tuple[Any, Any]:
    """Applies random spatial and photometric augmentations preserving mask alignment."""
    import tensorflow as tf

    # Random horizontal flip
    if tf.random.uniform(()) > 0.5:
        img = tf.image.flip_left_right(img)
        mask = tf.image.flip_left_right(mask)

    # Photometric augmentations on image only
    img = tf.image.random_brightness(img, max_delta=0.1)
    img = tf.image.random_contrast(img, lower=0.8, upper=1.2)
    img = tf.clip_by_value(img, 0.0, 1.0)

    return img, mask


def build_tf_dataset(
    pairs: list[tuple[str, str]],
    batch_size: int = 8,
    img_size: tuple[int, int] = (512, 512),
    is_training: bool = True
) -> Any:
    """Builds an optimized tf.data.Dataset pipeline."""
    import tensorflow as tf

    if not pairs:
        return None

    img_paths = [p[0] for p in pairs]
    mask_paths = [p[1] for p in pairs]

    ds = tf.data.Dataset.from_tensor_slices((img_paths, mask_paths))

    if is_training:
        ds = ds.shuffle(buffer_size=min(len(pairs), 500), seed=42)

    ds = ds.map(lambda x, y: parse_and_preprocess(x, y, img_size), num_parallel_calls=tf.data.AUTOTUNE)

    if is_training:
        ds = ds.map(augment, num_parallel_calls=tf.data.AUTOTUNE)

    ds = ds.batch(batch_size, drop_remainder=is_training and len(pairs) >= batch_size)
    ds = ds.prefetch(buffer_size=tf.data.AUTOTUNE)

    return ds


def load_dataset_splits(
    base_data_dir: str = "data/processed/real",
    fallback_dir: str = "data/processed/synthetic",
    batch_size: int = 8,
    img_size: tuple[int, int] = (512, 512),
    seed: int = 42
) -> tuple[Any, Any, Any, dict[str, int]]:
    """Loads dataset splits, falling back to synthetic data if real data is absent."""
    pairs = get_image_mask_pairs(base_data_dir)
    data_source = "real"

    if not pairs and os.path.exists(fallback_dir):
        pairs = get_image_mask_pairs(fallback_dir)
        data_source = "synthetic"

    if not pairs:
        raise FileNotFoundError(
            f"No image/mask pairs found in primary '{base_data_dir}' or fallback '{fallback_dir}'."
        )

    train_pairs, val_pairs, test_pairs = create_deterministic_splits(pairs, seed=seed)

    train_ds = build_tf_dataset(train_pairs, batch_size=batch_size, img_size=img_size, is_training=True)
    val_ds = build_tf_dataset(val_pairs, batch_size=batch_size, img_size=img_size, is_training=False)
    test_ds = build_tf_dataset(test_pairs, batch_size=batch_size, img_size=img_size, is_training=False)

    counts = {
        "source": data_source,
        "total": len(pairs),
        "train": len(train_pairs),
        "val": len(val_pairs),
        "test": len(test_pairs)
    }

    return train_ds, val_ds, test_ds, counts
