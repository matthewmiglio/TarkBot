"""Paint every non-empty inventory pixel yellow, so you can see what
find_sell_pixels() considers an item.

Run:  python tests/test_sell_pixels.py

Writes tests/output/sell_pixels.png: the inventory region cropped out of a live
screenshot, with a yellow dot on each live pixel. Dead slots keep their original
colour, so anything still dark grey is what the bot will ignore.

Tarkov must be the visible window; anything covering it gets captured instead.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402
from PIL import Image  # noqa: E402

import tarkov_window  # noqa: E402
from interact import sell  # noqa: E402

OUT = Path(__file__).parent / 'output'

if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    inv = sell.infer_inventory_region(region)
    print(f'window {region}, inventory {inv}')

    crop = np.asarray(pyautogui.screenshot(region=inv).convert('RGB')).copy()
    points = sell.find_sell_pixels(region)  # ponytail: takes its own shot, so a frame may differ
    total = crop.shape[0] * crop.shape[1]
    print(f'{len(points)} live of {total} pixels ({len(points) / total:.1%})')

    if points:
        pts = np.array(points)
        xs, ys = pts[:, 0] - inv[0], pts[:, 1] - inv[1]
        crop[ys, xs] = (255, 255, 0)

    OUT.mkdir(exist_ok=True)
    path = OUT / 'sell_pixels.png'
    Image.fromarray(crop).save(path)
    print(f'wrote {path}')
