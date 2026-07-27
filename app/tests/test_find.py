"""Locate every reference image set on the live Tarkov screen and save an annotated screenshot.

Run:  python tests/test_find.py              (every folder under interact/reference_images)
      python tests/test_find.py scav_case    (just one)

Writes tests/output/find.png: the window screenshot with a box per match and a
stat overlay listing which targets were found.
"""
import colorsys
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw, ImageFont  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find  # noqa: E402

OUT = Path(__file__).parent / 'output'
MISSING, SKIPPED = (255, 60, 60), (255, 200, 0)
FONT = ImageFont.truetype('arialbd.ttf', 15)


def colour(name):
    """A stable colour per target, so boxes and legend lines agree and runs are comparable.

    Hashed rather than picked off a palette: there are 28 targets and counting, and a palette
    would need extending every time a reference folder is added. md5 rather than hash(), which
    is salted per process and would recolour everything on every run.
    """
    hue = int(hashlib.md5(name.encode()).hexdigest(), 16) % 360 / 360
    return tuple(round(channel * 255) for channel in colorsys.hsv_to_rgb(hue, 0.85, 1.0))


# Folders that are data rather than things to find on screen: dead_pixels is a colour palette
# for sell.py, and price_digits is hundreds of generated glyphs that ocr.py matches inside an
# already-cropped price. Naming either one explicitly still runs it.
NOT_TARGETS = {'dead_pixels', 'price_digits'}


def targets():
    return sorted(p.name for p in find.REFS.iterdir()
                  if p.is_dir() and p.name not in NOT_TARGETS and any(p.glob('*.png')))


def check(name, shot):
    """Boxes for `name` in the captured screenshot, or None when it has no reference images."""
    try:
        return find.find_all(name, haystack=shot)
    except FileNotFoundError:
        return None


def annotate(shot, results):
    draw = ImageDraw.Draw(shot)
    for name, boxes in results.items():
        for box in boxes or []:
            xy = (box.left, box.top, box.left + box.width, box.top + box.height)
            draw.rectangle(xy, outline=colour(name), width=2)
            draw.text((box.left, box.top - 16), name, font=FONT, fill=colour(name))

    # The legend swatch carries the target's colour and the text carries its state, so a
    # target that matched nothing is still readable as red rather than as its own colour.
    lines = [(f'{name}: {len(boxes)} found' if boxes else
              f'{name}: none' if boxes is not None else f'{name}: no refs',
              colour(name) if boxes else MISSING if boxes is not None else SKIPPED)
             for name, boxes in results.items()]
    draw.rectangle((8, 8, 268, 20 + 20 * len(lines)), fill=(0, 0, 0))
    for i, (text, state) in enumerate(lines):
        draw.text((16, 14 + 20 * i), text, font=FONT, fill=state)


if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    shot = pyautogui.screenshot(region=region)  # one capture, every target matched against it
    print(f'searching window {region}')

    results = {name: check(name, shot) for name in (sys.argv[1:] or targets())}
    annotate(shot, results)
    OUT.mkdir(exist_ok=True)
    shot.save(OUT / 'find.png')
    for name, boxes in results.items():
        print(f'  {name}: {"no reference images" if boxes is None else f"{len(boxes)} found"}')
    print(f'-> {OUT / "find.png"}')
