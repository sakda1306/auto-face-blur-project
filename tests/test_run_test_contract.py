"""Tests for run_test_contract.py (the Test Contract runner, docs/CONTRACT.md section 6)."""

import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

import run_test_contract as runner

PORTRAIT = Path(__file__).parent / "data" / "portrait.jpg"


@pytest.fixture
def image_dir(tmp_path):
    portrait = cv2.imread(str(PORTRAIT))
    shutil.copy(PORTRAIT, tmp_path / "single_face.jpg")
    shutil.copy(PORTRAIT, tmp_path / "side_face.jpg")
    cv2.imwrite(str(tmp_path / "group_photo.jpg"), np.hstack([portrait, portrait, portrait]))
    cv2.imwrite(str(tmp_path / "no_face.jpg"), np.full((480, 640, 3), 90, dtype=np.uint8))
    cv2.imwrite(str(tmp_path / "edge_face.jpg"), portrait[:, 400:])
    return tmp_path


def by_file(results):
    return {r.file: r for r in results}


def test_all_cases_pass(image_dir):
    results = runner.run_cases(image_dir, group_faces=3)
    assert [r.file for r in results] == list(runner.CASES)
    results = by_file(results)
    for result in results.values():
        assert result.status == "PASS", result
    assert results["group_photo.jpg"].faces == 3


def test_missing_images_are_skipped(tmp_path):
    results = runner.run_cases(tmp_path)
    assert {r.status for r in results} == {"SKIP"}


def test_wrong_count_fails(image_dir):
    shutil.copy(image_dir / "group_photo.jpg", image_dir / "single_face.jpg")
    assert by_file(runner.run_cases(image_dir))["single_face.jpg"].status == "FAIL"


def test_group_needs_80_percent(image_dir):
    # 3 found out of 4 is 75%, below the 80% target.
    assert by_file(runner.run_cases(image_dir, group_faces=4))["group_photo.jpg"].status == "FAIL"
    # 3 found out of 3 passes.
    assert by_file(runner.run_cases(image_dir, group_faces=3))["group_photo.jpg"].status == "PASS"


def test_group_without_count_needs_manual_check(image_dir):
    result = by_file(runner.run_cases(image_dir))["group_photo.jpg"]
    assert result.status == "CHECK"
    assert result.faces == 3


def test_unreadable_image_fails(image_dir):
    (image_dir / "no_face.jpg").write_bytes(b"not an image")
    assert by_file(runner.run_cases(image_dir))["no_face.jpg"].status == "FAIL"


def test_save_writes_boxed_images(image_dir, tmp_path):
    out = tmp_path / "out"
    runner.run_cases(image_dir, group_faces=3, save_dir=out)
    assert (out / "single_face_bbox.png").exists()
    assert (out / "group_photo_bbox.png").exists()


def test_main_exit_code(image_dir):
    assert runner.main([str(image_dir), "--group-faces", "3"]) == 0
    assert runner.main([str(image_dir), "--group-faces", "10"]) == 1
