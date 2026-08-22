"""Drag the offer creation window into a corner of the monitor.

Run:  python tests/test_orientate_offer.py                       (bottom left, the default)
      python tests/test_orientate_offer.py "bottom right"        (or any corner sell knows)
      python tests/test_orientate_offer.py "bottom right" --dry  (locate it only, no dragging)

The corner is whatever sell._corner_point takes, so bad ones are refused here with the list of
good ones rather than halfway through a drag.

Writes tests/output/orientate_offer_before.png and _after.png so you can see whether it moved,
and reports how far the window actually travelled, since a drag the game ignores still returns
the point it grabbed. Exits non-zero if the window was not found. Tarkov must be visible.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import screen  # noqa: E402
import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the drag lands nowhere useful otherwise

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    corners = [a for a in sys.argv[1:] if not a.startswith('--')]
    corner = corners[0] if corners else sell.OFFER_CORNER
    try:
        target = sell._corner_point(corner, screen.rect())
    except ValueError as e:
        sys.exit(str(e))

    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    box = find.find(sell.OFFER_TARGET, region=region)
    if not box:
        sys.exit(f'{sell.OFFER_TARGET}: not found (is the offer creation window open?)')
    start = pyautogui.center(box)
    print(f'{sell.OFFER_TARGET}: {box} -> grab {start}')
    print(f'{corner} of {screen.rect()} is {target}')
    if dry:
        print(f'would drag {tuple(start)} -> {target} over {sell.DRAG_SECONDS}s, '
              f'{sell.DRAG_REPEATS} passes')
        sys.exit(0)

    OUT.mkdir(exist_ok=True)
    before = pyautogui.screenshot(region=region)
    ImageDraw.Draw(before).rectangle([box.left - region[0], box.top - region[1],
                                      box.left + box.width - region[0],
                                      box.top + box.height - region[1]], outline='lime', width=3)
    before.save(OUT / 'orientate_offer_before.png')

    for n in range(DELAY, 0, -1):
        print(f'dragging to the {corner} in {n}...')
        time.sleep(1)

    point = sell.orientate_offer_creation(region, corner)
    time.sleep(0.5)  # let the UI settle where it was dropped
    pyautogui.screenshot(region=region).save(OUT / 'orientate_offer_after.png')

    # Where it ended up, not where it was grabbed. orientate_offer_creation returns the last
    # point it took hold of whether or not the window followed, so on a game that ignores the
    # drag a run reads as a success with a window that never moved.
    landed = find.find(sell.OFFER_TARGET, region=region)
    if point and landed:
        now = pyautogui.center(landed)
        print(f'grabbed {tuple(start)}, window centre now {tuple(now)}: '
              f'moved ({int(now[0]) - int(start[0]):+d}, {int(now[1]) - int(start[1]):+d}), '
              f'{int(now[0]) - target[0]:+d}, {int(now[1]) - target[1]:+d} from the {corner}')
        if (int(now[0]), int(now[1])) == (int(start[0]), int(start[1])):
            print('WARNING: it did not move at all. The game ignored the drag.')
    else:
        print('grabbed nothing' if not point else 'window vanished after the drag')
    print(f'wrote {OUT / "orientate_offer_before.png"} and _after.png')
    sys.exit(0 if point else 1)
