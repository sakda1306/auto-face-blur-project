"""Tests for role B: apply_gaussian_blur, apply_mosaic, blur_faces (docs/CONTRACT.md 3.3, 3.4, 3.6)."""

import time
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


@pytest.fixture
def noise():
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, size=(120, 80, 3), dtype=np.uint8)


# --- apply_gaussian_blur ----------------------------------------------------

@pytest.mark.parametrize("strength, k", [(1, 3), (50, 41), (100, 81)])
def test_blur_kernel_follows_contract(noise, strength, k):
    # min(h, w) = 80 -> k = max(3, int(80 * strength / 100)) | 1
    expected = cv2.GaussianBlur(noise, (k, k), 0)
    result = detector.apply_gaussian_blur(noise, strength)
    assert result.shape == noise.shape and result.dtype == np.uint8
    assert np.array_equal(result, expected)


def test_blur_tiny_roi_uses_minimum_kernel():
    roi = np.zeros((2, 2, 3), dtype=np.uint8)
    assert detector.apply_gaussian_blur(roi, 100).shape == (2, 2, 3)


def test_blur_large_face_is_fast_and_looks_the_same(portrait):
    # A close-up phone photo can have a 4000 px face; the contract kernel would then be
    # ~2000 px wide and take minutes. Large faces are blurred at a smaller size instead.
    roi = cv2.resize(portrait[100:500, 250:650], (600, 600), interpolation=cv2.INTER_CUBIC)
    exact = cv2.GaussianBlur(roi, (301, 301), 0)  # contract kernel for 600 px, strength 50
    result = detector.apply_gaussian_blur(roi, 50)
    assert result.shape == roi.shape and result.dtype == np.uint8
    assert np.abs(result.astype(int) - exact.astype(int)).mean() < 3

    huge = cv2.resize(roi, (3000, 3000), interpolation=cv2.INTER_LINEAR)
    start = time.perf_counter()
    assert detector.apply_gaussian_blur(huge, 100).shape == huge.shape
    assert time.perf_counter() - start < 1.0


def test_stronger_blur_removes_more_detail(noise):
    weak = detector.apply_gaussian_blur(noise, 10)
    strong = detector.apply_gaussian_blur(noise, 90)
    assert strong.std() < weak.std() < noise.std()


# --- apply_mosaic -----------------------------------------------------------

@pytest.mark.parametrize("strength, blocks", [(1, 32), (50, 17), (100, 2)])
def test_mosaic_blocks_follow_contract(noise, strength, blocks):
    small = cv2.resize(noise, (blocks, blocks), interpolation=cv2.INTER_LINEAR)
    expected = cv2.resize(small, (80, 120), interpolation=cv2.INTER_NEAREST)
    result = detector.apply_mosaic(noise, strength)
    assert result.shape == noise.shape and result.dtype == np.uint8
    assert np.array_equal(result, expected)


def test_mosaic_strength_100_gives_2x2_blocks(noise):
    result = detector.apply_mosaic(noise, 100)
    colours = np.unique(result.reshape(-1, 3), axis=0)
    assert len(colours) <= 4


# --- blur_faces -------------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    {"mode": "sharpen"},
    {"strength": 0},
    {"strength": 101},
])
def test_blur_faces_rejects_bad_arguments(portrait, kwargs):
    with pytest.raises(ValueError):
        detector.blur_faces(portrait, **kwargs)


def test_blur_faces_rejects_none():
    with pytest.raises(ValueError):
        detector.blur_faces(None)


def test_blur_faces_without_faces_returns_copy():
    blank = np.full((240, 320, 3), 200, dtype=np.uint8)
    result, count = detector.blur_faces(blank)
    assert count == 0
    assert result is not blank
    assert np.array_equal(result, blank)


@pytest.mark.parametrize("mode", ["blur", "mosaic"])
def test_blur_faces_only_changes_the_face(portrait, mode):
    original = portrait.copy()
    result, count = detector.blur_faces(portrait, mode=mode, strength=80)
    assert count == 1
    assert np.array_equal(portrait, original)

    x, y, w, h = detector.detect_faces(portrait)[0]
    face_before = original[y:y + h, x:x + w]
    face_after = result[y:y + h, x:x + w]
    assert not np.array_equal(face_before, face_after)

    mask = np.ones(portrait.shape[:2], dtype=bool)
    mask[y:y + h, x:x + w] = False
    assert np.array_equal(result[mask], original[mask])


def test_blur_faces_bbox_mode_draws_frame(portrait):
    result, count = detector.blur_faces(portrait, mode="bbox")
    assert count == 1
    x, y, w, h = detector.detect_faces(portrait)[0]
    assert tuple(result[y, x + w // 2]) == (0, 255, 0)
    # The face itself is left sharp.
    centre = (slice(y + 10, y + h - 10), slice(x + 10, x + w - 10))
    assert np.array_equal(result[centre], portrait[centre])


def test_blur_faces_counts_every_face(portrait):
    pair = np.hstack([portrait, portrait])
    _, count = detector.blur_faces(pair, mode="mosaic")
    assert count == 2
