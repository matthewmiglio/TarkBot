"""
This module is for locating elements on the tarkov screen
"""
from pathlib import Path

import pyautogui
import pyscreeze

# pyautogui and pyscreeze each define their own ImageNotFoundException and both can surface
NOT_FOUND = (pyautogui.ImageNotFoundException, pyscreeze.ImageNotFoundException)

REFS = Path(__file__).parent / 'reference_images'
CONFIDENCE = 0.9  # ponytail: one global threshold; go per-image if some refs need looser matching
IOU_TOLERANCE = 0.5  # overlap at which two matches are treated as the same thing


def images(name):
    """Reference images for `name`: a folder (every .png inside) or a single image, relative to reference_images/."""
    target = REFS / name
    if target.is_dir():
        pngs = sorted(target.glob('*.png'))
        if not pngs:
            raise FileNotFoundError(f'{target} has no .png reference images yet')
        return pngs
    if target.is_file():
        return [target]
    if target.with_suffix('.png').is_file():
        return [target.with_suffix('.png')]
    raise FileNotFoundError(f'No reference images for {name!r} under {REFS}')


def _locate(path, region, confidence, haystack, every):
    """One reference image against the screen, or against `haystack` if given."""
    locate = (pyautogui.locateAll if every else pyautogui.locate) if haystack is not None else \
             (pyautogui.locateAllOnScreen if every else pyautogui.locateOnScreen)
    args = (str(path), haystack) if haystack is not None else (str(path),)
    return locate(*args, region=region, confidence=confidence)


def find(name, region=None, confidence=CONFIDENCE, haystack=None):
    """First match for `name` as Box(left, top, width, height), or None.

    region: optional (left, top, width, height) to search in, e.g. the Tarkov window rect.
    haystack: optional PIL image to search instead of the live screen (boxes are then in its coords).
    """
    for path in images(name):
        try:
            box = _locate(path, region, confidence, haystack, every=False)
        except NOT_FOUND:
            continue
        if box:  # pyautogui.locate returns None instead of raising when given a haystack
            return box
    return None


def iou(a, b):
    """Intersection over union of two Boxes, 0.0 to 1.0."""
    x = max(0, min(a.left + a.width, b.left + b.width) - max(a.left, b.left))
    y = max(0, min(a.top + a.height, b.top + b.height) - max(a.top, b.top))
    overlap = x * y
    union = a.width * a.height + b.width * b.height - overlap
    return overlap / union if union else 0.0


def dedupe(boxes, tolerance=IOU_TOLERANCE):
    """Drop boxes overlapping an earlier one by >= tolerance (1.0 = only exact duplicates)."""
    kept = []  # ponytail: O(n^2); fine for the handful of matches a screen produces
    for box in boxes:
        if not any(iou(box, k) >= tolerance for k in kept):
            kept.append(box)
    return kept


def find_all(name, region=None, confidence=CONFIDENCE, tolerance=IOU_TOLERANCE, haystack=None):
    """Every match for `name`, across every reference image, deduped. [] if none.

    tolerance: IOU at or above which two boxes count as the same hit. 1.0 keeps near-misses.
    """
    boxes = []
    for path in images(name):
        try:  # locateAll raises rather than yielding nothing when there is no match
            boxes.extend(_locate(path, region, confidence, haystack, every=True))
        except NOT_FOUND:
            continue
    return dedupe(boxes, tolerance)


def find_center(name, region=None, confidence=CONFIDENCE, haystack=None):
    """(x, y) to click, or None."""
    box = find(name, region, confidence, haystack)
    return pyautogui.center(box) if box else None
