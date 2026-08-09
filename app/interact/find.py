"""
This module is for locating elements on the tarkov screen
"""
import time
from functools import lru_cache
from pathlib import Path

import pyautogui
import pyscreeze
from PIL import Image

import screen
from narrate import log

# pyautogui and pyscreeze each define their own ImageNotFoundException and both can surface
NOT_FOUND = (pyautogui.ImageNotFoundException, pyscreeze.ImageNotFoundException)

# Off by default: the selling loop calls find() several times a second and this is a line per
# reference image per call. The test scripts turn it on, since there the whole point is seeing
# which crop matched and which ones were tried and missed. ponytail: a module flag, not a
# logging level; set find.VERBOSE = True.
VERBOSE = False

REFS = Path(__file__).parent / 'reference_images'
CONFIDENCE = 0.9  # ponytail: one global threshold; go per-image if some refs need looser matching
IOU_TOLERANCE = 0.5  # overlap at which two matches are treated as the same thing
REFERENCE_HEIGHT = 1080  # every png under reference_images/ was cropped from a 1080p screen


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


def scale():
    """How much bigger the live screen is than the 1080p the references were cropped at.

    Read off the screen, not off the region being searched: most calls pass some small part of
    the window (a button's box, the inventory grid) and its height says nothing about the
    game's. The game runs fullscreen, so the screen is the window.

    The working monitor's height rather than pyautogui's, which only ever reports the primary
    one: with the game on a second screen of a different height, that is the wrong number and
    every reference image gets resized by it.
    """
    return screen.size()[1] / REFERENCE_HEIGHT


@lru_cache(maxsize=None)
def _resized(path, factor):
    """A reference image redrawn at `factor` of its size. Cached: find() runs in tight loops."""
    image = Image.open(path)
    size = (max(1, round(image.width * factor)), max(1, round(image.height * factor)))
    return image.resize(size, Image.LANCZOS)


def needle(path):
    """What to hand the matcher for `path`: the file itself, or a copy resized to this screen.

    A 1080p screen gets the path unchanged, so the resolution everything was cropped at keeps
    matching exactly the bytes it always did. Anything else gets the reference stretched to the
    size that element is actually drawn at, since the matcher does not scale and a 1440p button
    simply never matches the 1080p crop of it.

    ponytail: an interpolated needle matches a little worse than a native crop. If a bigger
    screen finds nothing at CONFIDENCE, lower that before reaching for multi-scale matching.
    """
    factor = scale()
    if factor == 1.0:
        return str(path)
    return _resized(str(path), factor)


def _haystack(region, haystack):
    """What to search and where its top left corner sits on the screen: (image, (dx, dy)).

    The screen is grabbed here rather than left to pyautogui's locateOnScreen, which throws the
    region away and grabs the primary monitor whatever it was told, so a game on the second one
    was never in the picture being searched. Grabbing the region ourselves also means only that
    rectangle is matched against instead of a whole screen.

    Grabbed once per find() rather than once per reference image, since every image in a folder
    is looking at the same moment in time anyway.
    """
    if haystack is not None:
        return haystack, (0, 0)  # a caller-supplied image is its own coordinate system
    return screen.grab(region), tuple((region or screen.rect())[:2])


def _shift(box, offset):
    """A box found inside a grabbed region, moved back into screen coordinates."""
    if box is None:
        return None
    return pyscreeze.Box(int(box.left) + offset[0], int(box.top) + offset[1],
                         int(box.width), int(box.height))


def find(name, region=None, confidence=CONFIDENCE, haystack=None):
    """First match for `name` as Box(left, top, width, height), or None.

    region: optional (left, top, width, height) to search in, e.g. the Tarkov window rect.
    haystack: optional PIL image to search instead of the live screen (boxes are then in its coords).
    """
    paths = images(name)
    started = time.monotonic()
    image, offset = _haystack(region, haystack)
    for index, path in enumerate(paths, start=1):
        try:
            box = _shift(pyautogui.locate(needle(path), image, confidence=confidence), offset)
        except NOT_FOUND:
            box = None
        if box:  # pyautogui.locate returns None instead of raising when given a haystack
            if VERBOSE:
                log(f'find {name}: {path.name} ({index}/{len(paths)}) matched at '
                    f'({int(box.left)}, {int(box.top)}) {int(box.width)}x{int(box.height)} '
                    f'in {time.monotonic() - started:.2f}s', 2)
            return box
    if VERBOSE:
        log(f'find {name}: none of {len(paths)} reference images matched at confidence '
            f'{confidence} in {time.monotonic() - started:.2f}s '
            f'({", ".join(p.name for p in paths)})', 2)
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
    started = time.monotonic()
    image, offset = _haystack(region, haystack)
    for path in images(name):
        try:  # locateAll raises rather than yielding nothing when there is no match
            hits = [_shift(box, offset)
                    for box in pyautogui.locateAll(needle(path), image, confidence=confidence)]
        except NOT_FOUND:
            hits = []
        if VERBOSE and hits:
            log(f'find_all {name}: {path.name} matched {len(hits)}x', 2)
        boxes.extend(hits)
    kept = dedupe(boxes, tolerance)
    if VERBOSE:
        log(f'find_all {name}: {len(boxes)} raw matches, {len(kept)} after dedupe, '
            f'{time.monotonic() - started:.2f}s', 2)
    return kept


def find_center(name, region=None, confidence=CONFIDENCE, haystack=None):
    """(x, y) to click, or None."""
    box = find(name, region, confidence, haystack)
    return pyautogui.center(box) if box else None


if __name__ == '__main__':
    # Scaling, against a fake 1440p screen. No game needed: a real reference image is grown the
    # way a 1440p screen would draw it, pasted at a known point, and find() has to land on it.
    name = next(d.name for d in sorted(REFS.iterdir()) if d.is_dir() and any(d.glob('*.png')))
    path = images(name)[0]
    reference = Image.open(path)
    factor = 1440 / REFERENCE_HEIGHT

    scale = lambda: factor  # noqa: E731  what a 1440p screen reports, without owning one
    grown = needle(path)
    assert grown.size == (round(reference.width * factor), round(reference.height * factor)), \
        f'{grown.size} is not {reference.size} grown by {factor}'

    fake = Image.new('RGB', (2560, 1440), (30, 30, 30))  # not `screen`: that is the module
    spot = (600, 400)
    fake.paste(grown, spot)
    box = find(name, haystack=fake)
    assert box is not None, f'{name} grown to 1440p did not match a 1440p screen'
    assert abs(box.left - spot[0]) <= 2 and abs(box.top - spot[1]) <= 2, \
        f'matched {name} at {box.left, box.top}, pasted it at {spot}'

    # A region shifts the search into screen coordinates: the same paste, found through a
    # region whose origin is negative the way a monitor left of the primary one is, has to come
    # back at the point it was pasted plus that origin, not at the point inside the crop.
    offset_box = _shift(box, (-1920, -1))
    assert (offset_box.left, offset_box.top) == (box.left - 1920, box.top - 1), \
        f'a box found in a region at (-1920, -1) reads back at {offset_box}'
    assert (offset_box.width, offset_box.height) == (box.width, box.height), 'the size is untouched'

    scale = lambda: 1.0  # noqa: E731
    assert needle(path) == str(path), '1080p hands the matcher the file itself, unresized'

    print(f'ok, {name} {reference.size} -> {grown.size} found at {box.left, box.top}')
