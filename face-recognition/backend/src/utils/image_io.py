"""
src/utils/image_io.py

cv2.imread() reads raw pixel data and ignores the EXIF "Orientation" tag that
phone cameras write when a photo is taken in portrait mode (the sensor often
captures landscape pixels + a rotation flag). Browsers/Photos apps respect
that flag automatically; OpenCV does not -- so faces/boxes end up processed
and saved sideways relative to how the photo actually displays.

Use this helper anywhere a user-uploaded image is read, instead of cv2.imread.
"""

import numpy as np
import cv2
from PIL import Image, ImageOps


def read_image_respecting_exif(path: str) -> np.ndarray:
    """
    Returns a BGR numpy array (OpenCV's expected format), correctly oriented
    according to the file's EXIF Orientation tag, if present.
    """
    pil_img = Image.open(path)
    pil_img = ImageOps.exif_transpose(pil_img)  # rotates pixels, strips the tag
    pil_img = pil_img.convert("RGB")
    rgb_array = np.array(pil_img)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    return bgr_array