"""Tests for role A: detect_faces, clip_box, draw_boxes (docs/CONTRACT.md 3.1, 3.2, 3.5)."""

from pathlib import Path

import cv2
import numpy as np
import pytest

import detector

PORTRAIT = Path(__file__).parent / "data" / "portrait.jpg"


@pytest.fixture
def portrait():
    image = cv2.imread(str(PORTRAIT))
    assert image is not None
    return image


def assert_inside(box, shape):
    x, y, w, h = box
    assert all(isinstance(v, int) for v in box)
    assert x >= 0 and y >= 0 and w > 0 and h > 0
    assert x + w <= shape[1] and y + h <= shape[0]


# --- clip_box ---------------------------------------------------------------

@pytest.mark.parametrize("box, expected", [
    ((10, 20, 30, 40), (10, 20, 30, 40)),
    ((-10, -5, 30, 40), (0, 0, 20, 35)),
    ((80, 90, 50, 50), (80, 90, 20, 10)),
    ((-10, -10, 200, 200), (0, 0, 100, 100)),
])
def test_clip_box_clamps_to_image(box, expected):
    assert clip_box_result(box) == expected


@pytest.mark.parametrize("box", [
    (100, 10, 20, 20),   # starts on the right edge
    (10, 100, 20, 20),   # starts on the bottom edge
    (-30, 10, 20, 20),   # completely left of the image
    (10, 10, 0, 20),     # zero width
])
def test_clip_box_returns_none_when_nothing_left(box):
    assert clip_box_result(box) is None


def clip_box_result(box):
    return detector.clip_box(box, (100, 100, 3))


def test_clip_box_returns_plain_ints():
    box = detector.clip_box((np.int64(5), 5.7, 10, 10), (100, 100, 3))
    assert all(type(v) is int for v in box)


# --- detect_faces -----------------------------------------------------------

def test_detect_single_face(portrait):
    boxes = detector.detect_faces(portrait)
    assert len(boxes) == 1
    x, y, w, h = boxes[0]
    assert_inside(boxes[0], portrait.shape)
    # The face centre is around (400, 200) in the 820x1024 portrait.
    assert x < 400 < x + w
    assert y < 200 < y + h


def test_detect_no_face_returns_empty_list():
    blank = np.full((480, 640, 3), 127, dtype=np.uint8)
    assert detector.detect_faces(blank) == []


def test_detect_does_not_modify_input(portrait):
    original = portrait.copy()
    detector.detect_faces(portrait)
    assert np.array_equal(portrait, original)


def test_detect_multiple_faces_sorted_left_to_right(portrait):
    pair = np.hstack([portrait, portrait])
    boxes = detector.detect_faces(pair)
    assert len(boxes) == 2
    assert boxes[0][0] < boxes[1][0]
    for box in boxes:
        assert_inside(box, pair.shape)


def test_detect_face_on_image_edge(portrait):
    # Cut the image through the middle of the face.
    edge = np.ascontiguousarray(portrait[:, 400:])
    for box in detector.detect_faces(edge):
        assert_inside(box, edge.shape)


def place_faces(portrait, sizes):
    """Paste scaled copies of the portrait on a 1920x1080 canvas so each face is `size` px wide."""
    canvas = np.full((1080, 1920, 3), 120, dtype=np.uint8)
    x = 20
    for size in sizes:
        scale = size / 234  # the face in the portrait is about 234 px wide
        small = cv2.resize(portrait, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        h, w = min(small.shape[0], 1000), small.shape[1]
        canvas[40:40 + h, x:x + w] = small[:h]
        x += w + 20
    return canvas


@pytest.mark.parametrize("size", [200, 120, 80, 60, 50])
def test_detect_small_face_in_large_image(portrait, size):
    boxes = detector.detect_faces(place_faces(portrait, [size]))
    assert len(boxes) == 1


def test_detect_group_of_different_sizes(portrait):
    sizes = [160, 100, 70, 60, 50, 50]
    boxes = detector.detect_faces(place_faces(portrait, sizes))
    assert len(boxes) == len(sizes)


def test_high_min_confidence_filters_faces(portrait):
    assert detector.detect_faces(portrait, min_confidence=1.0) == []


def test_haar_fallback_when_mediapipe_unavailable(portrait, monkeypatch):
    def broken():
        raise RuntimeError("mediapipe not available")

    monkeypatch.setattr(detector, "_create_mediapipe_detector", broken)
    monkeypatch.setattr(detector, "_detector", None)
    boxes = detector.detect_faces(portrait)
    assert len(boxes) == 1
    x, y, w, h = boxes[0]
    assert x < 400 < x + w
    assert y < 200 < y + h


def test_detector_is_created_once(portrait, monkeypatch):
    calls = []
    real = detector._create_mediapipe_detector

    def counting():
        calls.append(1)
        return real()

    monkeypatch.setattr(detector, "_create_mediapipe_detector", counting)
    monkeypatch.setattr(detector, "_detector", None)
    detector.detect_faces(portrait)
    detector.detect_faces(portrait)
    assert len(calls) == 1


# --- draw_boxes -------------------------------------------------------------

def test_draw_boxes_returns_copy_with_green_frame():
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    result = detector.draw_boxes(image, [(10, 20, 30, 40)])
    assert result is not image
    assert not image.any()
    green = (0, 255, 0)
    assert tuple(result[20, 25]) == green      # top edge
    assert tuple(result[59, 25]) == green      # bottom edge
    assert tuple(result[40, 10]) == green      # left edge
    assert tuple(result[40, 39]) == green      # right edge
    assert tuple(result[40, 25]) == (0, 0, 0)  # inside stays untouched


def test_draw_boxes_without_boxes_returns_equal_copy():
    image = np.full((50, 50, 3), 7, dtype=np.uint8)
    result = detector.draw_boxes(image, [])
    assert result is not image
    assert np.array_equal(result, image)
