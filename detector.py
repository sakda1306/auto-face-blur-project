"""Face detection and face obfuscation (Gaussian blur / mosaic).

See docs/CONTRACT.md for the full specification of every function.
Images are numpy uint8 arrays of shape (H, W, 3) in BGR order.
"""

from pathlib import Path

import cv2
import numpy as np

MODES = ("blur", "mosaic", "bbox")

MODEL_DIR = Path(__file__).resolve().parent / "models"
MEDIAPIPE_MODEL = MODEL_DIR / "blaze_face_short_range.tflite"
HAAR_MODEL = MODEL_DIR / "haarcascade_frontalface_default.xml"

# The short-range model shrinks its input to 128x128, so small faces in a big photo
# vanish. Run it on the whole image and again on overlapping tiles of these sizes.
TILE_SIZES = (640, 320)
TILE_OVERLAP = 0.25
# Tiles cut objects out of context, so the model also finds false faces there (an eagle
# seal scored 0.66). A tile detection is kept only if the model finds it again in a crop
# RECHECK_CONTEXT times the box size around it: real faces score ~0.9 there, the seal 0.13.
TILE_MIN_SCORE = 0.5
RECHECK_CONTEXT = 2

# The detector is built once per process; see CONTRACT.md 4.3.
_detector = None


def _create_mediapipe_detector():
    """Build a MediaPipe Tasks FaceDetector. Returns fn(bgr) -> [(x, y, w, h, score)]."""
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    options = vision.FaceDetectorOptions(
        # Load from bytes so paths with spaces or non-ASCII characters still work.
        base_options=BaseOptions(model_asset_buffer=MEDIAPIPE_MODEL.read_bytes()),
        # Keep low-score faces here; detect_faces filters by min_confidence per call.
        min_detection_confidence=0.05,
    )
    model = vision.FaceDetector.create_from_options(options)

    def detect(rgb, x0, y0):
        result = model.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        faces = []
        for detection in result.detections:
            box = detection.bounding_box
            score = detection.categories[0].score if detection.categories else 1.0
            faces.append((box.origin_x + x0, box.origin_y + y0, box.width, box.height, score))
        return faces

    def run(image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        faces = detect(rgb, 0, 0)
        for size in TILE_SIZES:
            for x0, y0 in _tiles(rgb.shape[:2], size):
                tile = np.ascontiguousarray(rgb[y0:y0 + size, x0:x0 + size])
                for face in detect(tile, x0, y0):
                    if face[4] >= TILE_MIN_SCORE:
                        faces.append(face[:4] + (recheck(rgb, face),))
        return faces

    def recheck(rgb, face):
        """Score of the face when detected again in a square crop around it, else 0."""
        x, y, w, h = face[:4]
        cx, cy = x + w / 2, y + h / 2
        side = int(max(w, h) * RECHECK_CONTEXT)
        x0, y0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
        crop = np.ascontiguousarray(rgb[y0:y0 + side, x0:x0 + side])
        scores = [
            score for fx, fy, fw, fh, score in detect(crop, x0, y0)
            if fx <= cx <= fx + fw and fy <= cy <= fy + fh
        ]
        return max(scores, default=0.0)

    return run


def _tiles(shape, size):
    """Top-left corners of overlapping size x size tiles covering an image of this shape."""
    height, width = shape
    if max(height, width) <= size:
        return []
    step = int(size * (1 - TILE_OVERLAP))

    def starts(length):
        if length <= size:
            return [0]
        points = list(range(0, length - size + 1, step))
        if points[-1] + size < length:
            points.append(length - size)
        return points

    return [(x, y) for y in starts(height) for x in starts(width)]


def _merge_overlapping(boxes, threshold=0.5):
    """Merge boxes that cover the same face (from overlapping tiles) into their union."""
    boxes = [tuple(box) for box in boxes]
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                ax, ay, aw, ah = boxes[i]
                bx, by, bw, bh = boxes[j]
                iw = min(ax + aw, bx + bw) - max(ax, bx)
                ih = min(ay + ah, by + bh) - max(ay, by)
                if iw > 0 and ih > 0 and iw * ih > threshold * min(aw * ah, bw * bh):
                    x, y = min(ax, bx), min(ay, by)
                    boxes[i] = (x, y, max(ax + aw, bx + bw) - x, max(ay + ah, by + bh) - y)
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    return boxes


def _create_haar_detector():
    """Build a Haar cascade detector. It has no score, so every face counts as 1.0."""
    cascade = cv2.CascadeClassifier(str(HAAR_MODEL))
    if cascade.empty():
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        raise RuntimeError(f"cannot load Haar cascade: {HAAR_MODEL}")

    def run(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        found = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return [(x, y, w, h, 1.0) for x, y, w, h in found]

    return run


def _get_detector():
    global _detector
    if _detector is None:
        try:
            _detector = _create_mediapipe_detector()
        except Exception:
            _detector = _create_haar_detector()
    return _detector


def detect_faces(image, min_confidence=0.5):
    """Return a list of (x, y, w, h) boxes, clipped to the image, sorted by x."""
    found = [face[:4] for face in _get_detector()(image) if face[4] >= min_confidence]
    boxes = (clip_box(box, image.shape) for box in _merge_overlapping(found))
    return sorted(box for box in boxes if box is not None)


def clip_box(box, image_shape):
    """Clamp (x, y, w, h) to the image bounds; return None if nothing is left."""
    x, y, w, h = (int(v) for v in box)
    height, width = image_shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(width, x + w), min(height, y + h)
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1, y1, x2 - x1, y2 - y1)


def apply_gaussian_blur(roi, strength):
    """Blur the ROI with an odd kernel that scales with face size and strength (1-100)."""
    h, w = roi.shape[:2]
    k = max(3, int(min(h, w) * strength / 100)) | 1
    return cv2.GaussianBlur(roi, (k, k), 0)


def apply_mosaic(roi, strength):
    """Pixelate the ROI: shrink with INTER_LINEAR, enlarge back with INTER_NEAREST."""
    h, w = roi.shape[:2]
    blocks = max(2, 32 - (strength * 30) // 100)
    small = cv2.resize(roi, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def draw_boxes(image, boxes):
    """Return a copy of the image with a green rectangle around every box."""
    result = image.copy()
    for x, y, w, h in boxes:
        cv2.rectangle(result, (x, y), (x + w - 1, y + h - 1), (0, 255, 0), 2)
    return result


def blur_faces(image, mode="blur", strength=50):
    """Detect and obfuscate every face. Return (result_image, face_count)."""
    if image is None:
        raise ValueError("image is None")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    if not 1 <= strength <= 100:
        raise ValueError(f"strength must be in 1-100, got {strength}")

    boxes = detect_faces(image)
    if mode == "bbox":
        return draw_boxes(image, boxes), len(boxes)

    obfuscate = apply_gaussian_blur if mode == "blur" else apply_mosaic
    result = image.copy()
    for x, y, w, h in boxes:
        result[y:y + h, x:x + w] = obfuscate(result[y:y + h, x:x + w], strength)
    return result, len(boxes)
