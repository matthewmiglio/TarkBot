"""Swipe the hideout module row and measure whether each swipe actually moves it.

Run:  python tests/hideout_nav/test_scroll_progress.py [swipes] [mode]
  swipes: how many drags to do (default 12)
  mode:   'alt' (default, alternate left/right so it never sits against a wall),
          'left'  (+dist, toward the medstation) or 'right' (-dist, toward the workbench)

Real drags against the live game with the hideout open and the module row visible. For each swipe
it grabs the tab-row strip before and after and reports the mean grey difference. A swipe that
moves the row changes it by tens of levels; one that changed nothing (a dropped drag, a grab point
off the row, or input the game ignored) reads near zero and is a FAIL. This isolates the scroll
mechanic from any tab detection, to catch the 'scrolling made no progress' seen after a station
panel had been opened.
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import window  # noqa: E402
from interact import craft, find  # noqa: E402

THRESHOLD = craft.SWIPE_STUCK_DIFF  # mean grey diff below this means the row did not move


if __name__ == '__main__':
    swipes = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    mode = sys.argv[2] if len(sys.argv) > 2 else 'alt'

    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    for n in range(3, 0, -1):
        print(f'focus Tarkov (hideout open, module row showing)... {n}')
        time.sleep(1)

    icons = craft.hideout_icons(region)
    if not icons:
        print('no hideout module icons on screen; open the hideout with the module row showing')
        raise SystemExit(1)
    x = round(sum(craft._center(b)[0] for b in icons) / len(icons))
    y = round(sum(craft._center(b)[1] for b in icons) / len(icons))
    dist = round(craft.SWIPE_DISTANCE * find.scale())
    print(f'grab point ({x}, {y}) off {len(icons)} icons, dist {dist}, mode {mode}, '
          f'threshold {THRESHOLD}\n')

    def dx_for(i):
        if mode == 'left':
            return dist
        if mode == 'right':
            return -dist
        return dist if i % 2 == 0 else -dist  # alt: never sits against a wall

    before = craft._row_strip(y, region)
    fails = 0
    for i in range(swipes):
        dx = dx_for(i)
        craft._swipe(x, y, dx)
        time.sleep(craft.SWIPE_SETTLE)
        after = craft._row_strip(y, region)
        diff = float(np.abs(after - before).mean())
        moved = diff >= THRESHOLD
        print(f'[{"PASS" if moved else "FAIL"}] swipe {i:2d} dx={dx:+5d}: row changed {diff:6.2f}')
        fails += 0 if moved else 1
        before = after

    print(f'\n{swipes - fails}/{swipes} swipes moved the row')
    raise SystemExit(0 if fails == 0 else 1)
