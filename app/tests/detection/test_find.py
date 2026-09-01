"""Locate every reference image set on the live Tarkov screen and save an annotated screenshot.

App layer: the matching primitives in interact/find.py (find.find_all, find.images, find.REFS)
against every reference-image folder, plus find.scale() implicitly on any non-1080p screen.

Run:  python tests/detection/test_find.py              (every folder under interact/reference_images)
      python tests/detection/test_find.py scav_case    (just one)

Needs the LIVE GAME: it grabs the Tarkov window and matches against those real pixels, so with
no game up window.handle() raises before anything is drawn. Writes tests/output/find.png: the
window screenshot with a labelled box per match, and nothing else drawn over it. Which targets
were found, and how many of each, goes to the terminal.
"""
import colorsys
import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402
from PIL import ImageDraw, ImageFont  # noqa: E402

import window  # noqa: E402
from interact import find  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output'
FONT = ImageFont.truetype('arialbd.ttf', 15)


def color(name):
    """A stable color per target, so the same target boxes the same color between runs.

    Hashed rather than picked off a palette: there are 28 targets and counting, and a palette
    would need extending every time a reference folder is added. md5 rather than hash(), which
    is salted per process and would recolor everything on every run.
    """
    hue = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360 / 360
    return tuple(round(channel * 255) for channel in colorsys.hsv_to_rgb(hue, 0.85, 1.0))


# Folders that are data rather than things to find on screen: dead_pixels is a color palette
# for sell.py, and price_digits is hundreds of generated glyphs that ocr.py matches inside an
# already-cropped price. Naming either one explicitly still runs it.
NOT_TARGETS = {'dead_pixels', 'price_digits'}


def targets():
    # rglob, not iterdir, so a nested folder like crafting/start is found too. A target is any
    # folder holding pngs directly; a name in NOT_TARGETS is skipped wherever it sits. Names come
    # back as forward-slashed paths relative to REFS, which is what find.images() takes.
    return sorted(p.relative_to(find.REFS).as_posix() for p in find.REFS.rglob('*')
                  if p.is_dir() and p.name not in NOT_TARGETS and any(p.glob('*.png')))


def check(name, shot):
    """Boxes for `name` in the captured screenshot, or None when it has no reference images."""
    try:
        return find.find_all(name, haystack=shot)
    except FileNotFoundError:
        return None


def annotate(shot, results):
    """Box and label every match, in place.

    No summary panel. There used to be a black legend in the top left listing every target and
    its count, and it covered that corner of the screen: anything matching under it could not be
    seen, which is the one thing this picture is for. The same counts are printed to the
    terminal, per target, so nothing was lost by dropping it.
    """
    draw = ImageDraw.Draw(shot)
    for name, boxes in results.items():
        for box in boxes or []:
            xy = (box.left, box.top, box.left + box.width, box.top + box.height)
            draw.rectangle(xy, outline=color(name), width=2)
            draw.text((box.left, box.top - 16), name, font=FONT, fill=color(name))


if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    shot = pyautogui.screenshot(region=region)  # one capture, every target matched against it
    print(f'searching window {region}')

    names = sys.argv[1:] or targets()
    # Threaded because cv2.matchTemplate (all the work here) releases the GIL, so N targets
    # match in parallel. Each check() is independent and only reads `shot`. ponytail: default
    # worker count is fine; this is a test script, not a hot path to tune.
    with ThreadPoolExecutor() as pool:
        results = dict(zip(names, pool.map(lambda name: check(name, shot), names)))
    annotate(shot, results)
    OUT.mkdir(exist_ok=True)
    shot.save(OUT / 'find.png')
    for name, boxes in results.items():
        print(f'  {name}: {"no reference images" if boxes is None else f"{len(boxes)} found"}')
    print(f'-> {OUT / "find.png"}')
