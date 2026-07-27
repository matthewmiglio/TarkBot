"""Infer the inventory region on the live Tarkov screen and save an annotated screenshot.

Run:  python tests/test_inventory_region.py

Writes tests/output/inventory_region.png: the framing buttons boxed in lime, the
inferred inventory region in magenta. Read-only, it never clicks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'


def box(draw, rect, origin, color, label, width=2):
    """Outline a screen-coord (left, top, w, h) on a screenshot that starts at origin."""
    left, top = rect[0] - origin[0], rect[1] - origin[1]
    draw.rectangle([left, top, left + rect[2], top + rect[3]], outline=color, width=width)
    draw.text((left + 2, max(0, top - 10)), label, fill=color)


if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    print(f'searching window {region}')

    shot = pyautogui.screenshot(region=region)
    draw = ImageDraw.Draw(shot)

    for name in sell.EDGES:
        found = find.find(name, region=region)
        print(f'{name}: {found or "NOT FOUND"}')
        if found:
            box(draw, found, region, 'lime', name)

    inventory = sell.infer_inventory_region(region)  # raises LookupError if a button is missing
    print(f'inventory region: {inventory}')
    box(draw, inventory, region, 'magenta', 'inventory', width=3)

    OUT.mkdir(exist_ok=True)
    path = OUT / 'inventory_region.png'
    shot.save(path)
    print(f'wrote {path}')
