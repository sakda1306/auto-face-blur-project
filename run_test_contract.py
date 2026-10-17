"""Run every case of the Test Contract (docs/CONTRACT.md section 6) on test_images/.

Usage:
    python run_test_contract.py                     # test_images/, group photo checked by hand
    python run_test_contract.py --group-faces 12    # group_photo.jpg really has 12 faces
    python run_test_contract.py --save              # also write boxed images to output/

Exit code is 0 when no case FAILs, so it can be used before opening a PR.
"""

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from detector import blur_faces, detect_faces, draw_boxes

ROOT = Path(__file__).resolve().parent

# file -> what the contract expects
CASES = {
    "single_face.jpg": "one face: face_count == 1",
    "group_photo.jpg": "group photo: at least 80% of faces found",
    "side_face.jpg": "slightly turned face: found",
    "no_face.jpg": "no people: face_count == 0, no error",
    "edge_face.jpg": "face on the image edge: no error, boxes inside the image",
}
GROUP_MIN_RATIO = 0.8


@dataclass
class Result:
    file: str
    status: str  # PASS, FAIL, SKIP or CHECK (needs a human to count faces)
    faces: int | None = None
    detail: str = ""
    ms: float = 0.0


def read_image(path):
    """Read an image as BGR; works with non-ASCII paths on Windows, unlike cv2.imread."""
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None


def check(file, image, boxes, group_faces):
    """Return (status, detail) for one case."""
    count = len(boxes)
    if file == "single_face.jpg":
        return ("PASS", "") if count == 1 else ("FAIL", f"expected 1 face, found {count}")
    if file == "side_face.jpg":
        return ("PASS", "") if count >= 1 else ("FAIL", "no face found")
    if file == "no_face.jpg":
        return ("PASS", "") if count == 0 else ("FAIL", f"expected 0 faces, found {count}")
    if file == "edge_face.jpg":
        h, w = image.shape[:2]
        outside = [b for b in boxes if b[0] < 0 or b[1] < 0 or b[0] + b[2] > w or b[1] + b[3] > h]
        if outside:
            return "FAIL", f"boxes outside the image: {outside}"
        return "PASS", f"{count} face(s), all boxes inside"
    if file == "group_photo.jpg":
        if not group_faces:
            return "CHECK", "count the faces and rerun with --group-faces N"
        ratio = count / group_faces
        detail = f"found {count}/{group_faces} = {ratio:.0%} (need {GROUP_MIN_RATIO:.0%})"
        if count > group_faces:
            detail += ", more than real: check output/ for false faces (--save)"
        return ("PASS" if ratio >= GROUP_MIN_RATIO else "FAIL"), detail
    raise ValueError(f"unknown case: {file}")


def run_cases(image_dir, group_faces=None, save_dir=None):
    """Run every contract case found in image_dir and return a list of Result."""
    image_dir = Path(image_dir)
    results = []
    for file in CASES:
        path = image_dir / file
        if not path.exists():
            results.append(Result(file, "SKIP", detail="image not found"))
            continue
        image = read_image(path)
        if image is None:
            results.append(Result(file, "FAIL", detail="cannot read image"))
            continue
        start = time.perf_counter()
        try:
            # Run the full pipeline too, so an error in blur_faces fails the case.
            boxes = detect_faces(image)
            _, count = blur_faces(image, "blur", 50)
        except Exception as error:
            results.append(Result(file, "FAIL", detail=f"{type(error).__name__}: {error}"))
            continue
        ms = (time.perf_counter() - start) * 1000
        status, detail = check(file, image, boxes, group_faces)
        if count != len(boxes):
            status, detail = "FAIL", f"blur_faces counted {count} but detect_faces found {len(boxes)}"
        results.append(Result(file, status, len(boxes), detail, ms))
        if save_dir:
            save_dir = Path(save_dir)
            save_dir.mkdir(parents=True, exist_ok=True)
            ok, png = cv2.imencode(".png", draw_boxes(image, boxes))
            if ok:
                png.tofile(str(save_dir / f"{path.stem}_bbox.png"))
    return results


def print_table(results):
    print(f"{'file':<17} {'status':<6} {'faces':>5} {'time':>8}  detail")
    print("-" * 78)
    for r in results:
        faces = "-" if r.faces is None else r.faces
        ms = f"{r.ms:.0f} ms" if r.ms else "-"
        print(f"{r.file:<17} {r.status:<6} {faces:>5} {ms:>8}  {r.detail or CASES[r.file]}")
    totals = {s: sum(r.status == s for r in results) for s in ("PASS", "FAIL", "CHECK", "SKIP")}
    print("-" * 78)
    print("  ".join(f"{s}: {n}" for s, n in totals.items()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image_dir", nargs="?", default=ROOT / "test_images", help="folder with the test images")
    parser.add_argument("--group-faces", type=int, help="real number of faces in group_photo.jpg")
    parser.add_argument("--save", action="store_true", help="write images with face boxes to output/")
    args = parser.parse_args(argv)

    save_dir = ROOT / "output" if args.save else None
    results = run_cases(args.image_dir, args.group_faces, save_dir)
    print_table(results)
    if save_dir:
        print(f"boxed images saved to {save_dir}")
    return 1 if any(r.status == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
