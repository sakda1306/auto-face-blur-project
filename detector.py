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
YUNET_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
HAAR_MODEL = MODEL_DIR / "haarcascade_frontalface_default.xml"

# Every image is resized so its long side is WORK_SIZE before detection: a 300 px web image
# has faces too small for the models (issue #6), and a 6000 px photo is slow for no gain.
WORK_SIZE = 1920

# Two detectors run on every image and their boxes are merged. MediaPipe short range is
# good at big, close and side faces but misses small faces; YuNet finds small faces in a
# crowd but misses very close faces and full profiles. YuNet boxes need this score; lower
# scores gave false faces on the test photos.
YUNET_MIN_SCORE = 0.7

# Faces larger than this (shorter side, px) are blurred on a scaled-down copy for speed.
BLUR_MAX_SIDE = 256

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

    def run(image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = model.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        faces = []
        for detection in result.detections:
            box = detection.bounding_box
            score = detection.categories[0].score if detection.categories else 1.0
            faces.append((box.origin_x, box.origin_y, box.width, box.height, score))
        return faces

    return run


def _create_yunet_detector():
    """Build an OpenCV YuNet face detector. Returns fn(bgr) -> [(x, y, w, h, score)]."""
    # Load from bytes for the same path reason as MediaPipe.
    model = cv2.FaceDetectorYN.create(
        "onnx", np.frombuffer(YUNET_MODEL.read_bytes(), np.uint8), np.empty(0, np.uint8),
        (320, 320), YUNET_MIN_SCORE, 0.3, 5000,
    )

    def run(image):
        model.setInputSize((image.shape[1], image.shape[0]))
        _, found = model.detect(image)
        if found is None:
            return []
        # Each row is x, y, w, h, 10 landmark values, score.
        return [(int(f[0]), int(f[1]), int(f[2]), int(f[3]), float(f[-1])) for f in found]

    return run


def _merge_overlapping(boxes, threshold=0.5):
    """Merge boxes that cover the same face (found by both detectors) into their union."""
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
        # minNeighbors=6 (not the usual 5) drops a false face that appears at WORK_SIZE.
        found = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(30, 30))
        return [(x, y, w, h, 1.0) for x, y, w, h in found]

    return run


def _get_detector():
    """Build MediaPipe and YuNet once; use Haar only if neither of them loads."""
    global _detector
    if _detector is None:
        runs = []
        for create in (_create_mediapipe_detector, _create_yunet_detector):
            try:
                runs.append(create())
            except Exception:
                pass
        if not runs:
            runs.append(_create_haar_detector())
        _detector = lambda image: [face for run in runs for face in run(image)]
    return _detector


def detect_faces(image, min_confidence=0.5):
    """Return a list of (x, y, w, h) boxes, clipped to the image, sorted by x."""
    scale = WORK_SIZE / max(image.shape[:2])
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    work = cv2.resize(image, None, fx=scale, fy=scale, interpolation=interpolation)

    found = [face[:4] for face in _get_detector()(work) if face[4] >= min_confidence]
    boxes = []
    for x, y, w, h in _merge_overlapping(found):
        # Back to original pixels; round the corners so the box does not shrink.
        x1, y1 = int(x / scale), int(y / scale)
        x2, y2 = int(np.ceil((x + w) / scale)), int(np.ceil((y + h) / scale))
        box = clip_box((x1, y1, x2 - x1, y2 - y1), image.shape)
        if box is not None:
            boxes.append(box)
    return sorted(boxes)


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
    if min(h, w) > BLUR_MAX_SIDE:
        # The kernel grows with the face, so a 4000 px face would take minutes. Blur a
        # smaller copy with the same relative kernel and scale it back; the result looks
        # the same because only coarse detail is left after such a strong blur.
        scale = BLUR_MAX_SIDE / min(h, w)
        small = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        return cv2.resize(apply_gaussian_blur(small, strength), (w, h), interpolation=cv2.INTER_LINEAR)
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
