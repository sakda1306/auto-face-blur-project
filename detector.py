"""Face detection and face obfuscation (Gaussian blur / mosaic)."""

import cv2
import numpy as np


def detect_faces(image):
    """Return a list of face bounding boxes as (x, y, w, h)."""
    raise NotImplementedError


def apply_gaussian_blur(roi, intensity):
    """Blur the ROI with a Gaussian filter (kernel size must be odd)."""
    raise NotImplementedError


def apply_mosaic(roi, blocks):
    """Pixelate the ROI: shrink to (blocks, blocks) then enlarge with nearest-neighbor."""
    raise NotImplementedError


def blur_faces(image, mode="blur", strength=51):
    """Detect every face in the image and obfuscate it in place of the original ROI."""
    raise NotImplementedError
