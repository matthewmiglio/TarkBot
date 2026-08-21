"""Grab a random item from the inventory screen and filter by it on the flea.

Run:  python tests/test_select_item.py        (countdown, then really right-clicks)
      python tests/test_select_item.py --dry  (show the pixel it would pick, no clicking)

Writes tests/output/select_item.png: the window afterwards with the chosen point ringed.
Exits non-zero if no attempt landed. Tarkov must be the visible window.
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import window  # noqa: E402
from interact import sell  # noqa: E402

OUT = Path(__file__).parent / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; clicks land nowhere useful otherwise

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    points = sell.find_sell_pixels(region)
    print(f'{len(points)} sellable pixels in {sell.infer_inventory_region(region)}')
    if not points:
        sys.exit('nothing sellable on screen')

    if dry:
        point = random.choice(points)
        print(f'would right-click {point}, then look for filter_by_item')
    else:
        for n in range(DELAY, 0, -1):
            print(f'starting in {n}...')
            time.sleep(1)
        point = sell.select_item_from_inventory(region)
        print(f'clicked filter_by_item at {point}' if point
              else f'no attempt landed in {sell.SELECT_ATTEMPTS} tries')

    shot = pyautogui.screenshot(region=region)
    if point:
        x, y = point[0] - region[0], point[1] - region[1]
        ImageDraw.Draw(shot).ellipse([x - 14, y - 14, x + 14, y + 14], outline='magenta', width=3)
    OUT.mkdir(exist_ok=True)
    path = OUT / 'select_item.png'
    shot.save(path)
    print(f'wrote {path}')
    sys.exit(0 if point or dry else 1)
