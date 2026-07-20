"""
Small geometry helpers shared by the cascade:
  - distance gating (is this vehicle box close enough to bother with?)
  - cropping a vehicle region out of the frame and upscaling it so a
    small/distant plate becomes a larger target for the plate detector
"""

import cv2
import numpy as np


def is_close_enough(vehicle_box: tuple[int, int, int, int], frame_height: int, min_height_frac: float) -> bool:
    _, y1, _, y2 = vehicle_box
    box_height = y2 - y1
    return (box_height / frame_height) >= min_height_frac


def crop_and_upscale(
    frame: np.ndarray,
    box: tuple[int, int, int, int],
    target_size: int,
    pad_frac: float = 0.03,
) -> tuple[np.ndarray, tuple[int, int, float, float]]:
    """
    Crop `box` out of `frame` with a little padding, then resize to a
    target_size x target_size square (letterboxed, aspect preserved).

    Returns (upscaled_crop, transform) where transform = (crop_x1, crop_y1,
    scale_x, scale_y) — enough info to map a box found in the upscaled
    crop back to original-frame coordinates, if you need that later
    (e.g. for drawing on the full frame instead of just OCR-ing the crop).
    """
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = box
    box_w, box_h = x2 - x1, y2 - y1
    pad_x, pad_y = int(box_w * pad_frac), int(box_h * pad_frac)

    cx1, cy1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
    cx2, cy2 = min(w, x2 + pad_x), min(h, y2 + pad_y)

    crop = frame[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return crop, (cx1, cy1, 1.0, 1.0)

    crop_h, crop_w = crop.shape[:2]
    scale = target_size / max(crop_h, crop_w)
    new_w, new_h = int(crop_w * scale), int(crop_h * scale)
    resized = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    # letterbox pad to a square so the plate detector always gets a
    # consistent target_size x target_size input
    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    canvas[0:new_h, 0:new_w] = resized

    return canvas, (cx1, cy1, scale, scale)


def map_box_to_frame(
    box_in_crop: tuple[int, int, int, int], transform: tuple[int, int, float, float]
) -> tuple[int, int, int, int]:
    """Map a box detected in the upscaled crop back to original frame coordinates."""
    cx1, cy1, scale_x, scale_y = transform
    x1, y1, x2, y2 = box_in_crop
    return (
        int(cx1 + x1 / scale_x),
        int(cy1 + y1 / scale_y),
        int(cx1 + x2 / scale_x),
        int(cy1 + y2 / scale_y),
    )
