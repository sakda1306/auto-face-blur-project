"""Face detection and face obfuscation (Gaussian blur / mosaic).

See docs/CONTRACT.md for the full specification of every function.
Images are numpy uint8 arrays of shape (H, W, 3) in BGR order.
"""

import cv2
import numpy as np

MODES = ("blur", "mosaic", "bbox")


def detect_faces(image, min_confidence=0.5):
    """Return a list of (x, y, w, h) boxes, clipped to the image, sorted by x."""
    raise NotImplementedError


def clip_box(box, image_shape):
    """Clamp (x, y, w, h) to the image bounds; return None if nothing is left."""
    raise NotImplementedError


def apply_gaussian_blur(roi, strength):
    """Blur the ROI with an odd kernel that scales with face size and strength (1-100)."""
    raise NotImplementedError


def apply_mosaic(roi, strength):
    """Pixelate the ROI: shrink with INTER_LINEAR, enlarge back with INTER_NEAREST."""
    raise NotImplementedError


def draw_boxes(image, boxes):
    """Return a copy of the image with a green rectangle around every box."""
    raise NotImplementedError


def blur_faces(image, mode="blur", strength=50):
    """Detect and obfuscate every face. Return (result_image, face_count)."""
    raise NotImplementedError
