"""MobileNetV2-UNet Architecture for Speech Bubble Segmentation.

Implements a lightweight U-Net with a pre-trained MobileNetV2 encoder
and multi-scale skip connections. Optimized for 8 GB VRAM training and fast CPU inference.
"""

from __future__ import annotations

from typing import Any, Tuple


def get_tensorflow():
    """Lazy-imports TensorFlow to avoid import-time overhead when only inspecting interfaces."""
    try:
        import tensorflow as tf
        return tf
    except ImportError as exc:
        raise ImportError(
            "TensorFlow is required for model_unet. Please install tensorflow or tensorflow-cpu."
        ) from exc


def dice_coef(y_true: Any, y_pred: Any, smooth: float = 1e-6) -> Any:
    """Computes the Dice coefficient between ground truth and predicted binary masks."""
    tf = get_tensorflow()
    y_true_f = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
    y_pred_f = tf.cast(tf.reshape(y_pred, [-1]), tf.float32)
    intersection = tf.reduce_sum(y_true_f * y_pred_f)
    return (2.0 * intersection + smooth) / (tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f) + smooth)


def dice_loss(y_true: Any, y_pred: Any) -> Any:
    """Computes Dice loss (1.0 - Dice coefficient)."""
    return 1.0 - dice_coef(y_true, y_pred)


def iou_metric(y_true: Any, y_pred: Any, smooth: float = 1e-6) -> Any:
    """Computes Intersection over Union (IoU / Jaccard Index) thresholded at 0.5."""
    tf = get_tensorflow()
    y_true_f = tf.cast(tf.reshape(y_true, [-1]), tf.float32)
    y_pred_f = tf.cast(tf.reshape(y_pred, [-1]) > 0.5, tf.float32)
    intersection = tf.reduce_sum(y_true_f * y_pred_f)
    total = tf.reduce_sum(y_true_f) + tf.reduce_sum(y_pred_f)
    union = total - intersection
    return (intersection + smooth) / (union + smooth)


def combined_bce_dice_loss(bce_weight: float = 0.5, dice_weight: float = 0.5):
    """Factory creating combined BCE + Dice loss."""
    tf = get_tensorflow()
    bce = tf.keras.losses.BinaryCrossentropy()

    def loss(y_true: Any, y_pred: Any) -> Any:
        return (bce_weight * bce(y_true, y_pred)) + (dice_weight * dice_loss(y_true, y_pred))

    loss.__name__ = "bce_dice_loss"
    return loss


def _decoder_block(inputs: Any, skip_features: Any, num_filters: int, block_name: str) -> Any:
    """Standard U-Net decoder block: Upsample -> Concat -> Double Conv2D."""
    tf = get_tensorflow()
    layers = tf.keras.layers

    x = layers.UpSampling2D((2, 2), interpolation="bilinear", name=f"{block_name}_upsample")(inputs)
    if skip_features is not None:
        x = layers.Concatenate(name=f"{block_name}_concat")([x, skip_features])

    x = layers.Conv2D(num_filters, (3, 3), padding="same", use_bias=False, name=f"{block_name}_conv1")(x)
    x = layers.BatchNormalization(name=f"{block_name}_bn1")(x)
    x = layers.ReLU(name=f"{block_name}_relu1")(x)

    x = layers.Conv2D(num_filters, (3, 3), padding="same", use_bias=False, name=f"{block_name}_conv2")(x)
    x = layers.BatchNormalization(name=f"{block_name}_bn2")(x)
    x = layers.ReLU(name=f"{block_name}_relu2")(x)
    return x


def build_mobilenet_unet(
    input_shape: Tuple[int, int, int] = (512, 512, 3),
    learning_rate: float = 1e-4,
    freeze_encoder: bool = False,
    mixed_precision: bool = False
) -> Any:
    """Constructs, compiles, and returns a MobileNetV2-UNet model for speech bubble segmentation.

    Args:
        input_shape: Input image dimensions (H, W, C). Defaults to (512, 512, 3).
        learning_rate: Adam optimizer learning rate.
        freeze_encoder: Whether to freeze pre-trained MobileNetV2 backbone weights.
        mixed_precision: Whether to set global policy to mixed_float16.

    Returns:
        tf.keras.Model compiled with combined BCE+Dice loss, Dice, and IoU metrics.
    """
    tf = get_tensorflow()
    layers = tf.keras.layers

    if mixed_precision:
        policy = tf.keras.mixed_precision.Policy("mixed_float16")
        tf.keras.mixed_precision.set_global_policy(policy)

    inputs = layers.Input(shape=input_shape, name="page_input")

    # MobileNetV2 base feature extractor
    encoder = tf.keras.applications.MobileNetV2(
        input_shape=input_shape,
        include_top=False,
        weights="imagenet"
    )

    if freeze_encoder:
        encoder.trainable = False

    # Extract intermediate skip connection layers:
    # 512x512 -> input
    # 256x256 -> block_1_expand_relu
    # 128x128 -> block_3_expand_relu
    #  64x64  -> block_6_expand_relu
    #  32x32  -> block_13_expand_relu
    #  16x16  -> out_relu (bottleneck)
    skip_names = [
        "block_1_expand_relu",   # 256x256
        "block_3_expand_relu",   # 128x128
        "block_6_expand_relu",   # 64x64
        "block_13_expand_relu",  # 32x32
        "out_relu",              # 16x16
    ]

    skip_outputs = [encoder.get_layer(name).output for name in skip_names]
    feature_extractor = tf.keras.Model(inputs=encoder.input, outputs=skip_outputs, name="mobilenetv2_features")
    skips = feature_extractor(inputs)

    bottleneck = skips[4]      # 16x16
    skip_32 = skips[3]         # 32x32
    skip_64 = skips[2]         # 64x64
    skip_128 = skips[1]        # 128x128
    skip_256 = skips[0]        # 256x256

    # Decoder stages
    d1 = _decoder_block(bottleneck, skip_32, 256, "dec_stage1")    # -> 32x32
    d2 = _decoder_block(d1, skip_64, 128, "dec_stage2")            # -> 64x64
    d3 = _decoder_block(d2, skip_128, 64, "dec_stage3")            # -> 128x128
    d4 = _decoder_block(d3, skip_256, 32, "dec_stage4")            # -> 256x256

    # Final upsample to original resolution 512x512
    d5 = _decoder_block(d4, None, 16, "dec_stage5")                # -> 512x512

    # Final 1x1 conv output layer. Must be float32 for numerical stability in mixed precision.
    output_mask = layers.Conv2D(
        1,
        (1, 1),
        padding="same",
        activation="sigmoid",
        dtype="float32",
        name="bubble_mask"
    )(d5)

    model = tf.keras.Model(inputs=inputs, outputs=output_mask, name="MobileNetV2_UNet")

    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)
    model.compile(
        optimizer=optimizer,
        loss=combined_bce_dice_loss(bce_weight=0.5, dice_weight=0.5),
        metrics=[dice_coef, iou_metric]
    )

    return model
