"""Paint every non-empty inventory pixel yellow, to see what find_sell_pixels counts as an item.

Exercises interact/sell.py's infer_inventory_region and find_sell_pixels, the read that decides
which stash slots hold something worth listing. find_sell_pixels masks out empty slots with a
256-cubed boolean built from every colour in reference_images/dead_pixels/ (plus or minus 5 a
channel) and excludes scav case boxes. Writes tests/flea_sell/output/sell_pixels.png: the
inventory crop with a yellow dot on each live pixel, so anything still dark grey is a slot the
bot will ignore. Prints the live pixel count and its fraction of the region.

Read-only, it never clicks. Needs the live game with the inventory open and Tarkov the visible
window, since anything covering it is captured instead.

Run:  python tests/flea_sell/test_sell_pixels.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402
from PIL import Image  # noqa: E402

import window  # noqa: E402
from interact import sell  # noqa: E402

OUT = Path(__file__).parents[1] / 'output'

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
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
