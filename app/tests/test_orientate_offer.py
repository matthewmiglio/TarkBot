"""Drag the offer creation window to the top left of the monitor.

Run:  python tests/test_orientate_offer.py        (countdown, then really drags)
      python tests/test_orientate_offer.py --dry  (locate it only, no dragging)

Writes tests/output/orientate_offer_before.png and _after.png so you can see whether
it moved. Exits non-zero if the window was not found. Tarkov must be the visible window.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the drag lands nowhere useful otherwise

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)

    box = find.find(sell.OFFER_TARGET, region=region)
    if not box:
        sys.exit(f'{sell.OFFER_TARGET}: not found (is the offer creation window open?)')
    print(f'{sell.OFFER_TARGET}: {box} -> grab {pyautogui.center(box)}')
    if dry:
        print(f'would drag to (0, 0) over {sell.DRAG_SECONDS}s')
        sys.exit(0)

    OUT.mkdir(exist_ok=True)
    before = pyautogui.screenshot(region=region)
    ImageDraw.Draw(before).rectangle([box.left - region[0], box.top - region[1],
                                      box.left + box.width - region[0],
                                      box.top + box.height - region[1]], outline='lime', width=3)
    before.save(OUT / 'orientate_offer_before.png')

    for n in range(DELAY, 0, -1):
        print(f'dragging in {n}...')
        time.sleep(1)

    point = sell.orientate_offer_creation(region)
    time.sleep(0.5)  # let the UI settle where it was dropped
    pyautogui.screenshot(region=region).save(OUT / 'orientate_offer_after.png')
    print(f'grabbed {point}' if point else 'window vanished before the drag')
    print(f'wrote {OUT / "orientate_offer_before.png"} and _after.png')
    sys.exit(0 if point else 1)
