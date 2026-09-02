"""Swipe the hideout module row once and measure how much the tab-list strip changed.

Run:  python tests/hideout_nav/test_hideout_tab_scroll_diff.py [direction]
  direction: 'left' (default, drag right-to-left toward the workbench end) or 'right'

Real drag against the live game, hideout open with the module row showing. It grabs the tab-list
strip (craft.hideout_tabs_strip), swipes once, settles, grabs the strip again, and prints the mean
grey difference (craft._hideout_tab_scroll_diff) between the two, plus what
craft.did_scroll_mode_hideout_tab makes of it at the current (provisional) threshold.

This is the calibration loop for craft.HIDEOUT_TAB_SCROLL_DIFF. Run it twice:
  1. with the row somewhere in the middle, so the swipe MOVES it  -> expect a big number
  2. with the row already at that end, so the swipe moves NOTHING  -> expect a small number
Report both numbers; the threshold goes in the gap between them, and did_scroll then tells a real
scroll from a swipe into the end of the list in one drag, so the sweep can reverse immediately
instead of wasting swipes discovering the row will not move.

Writes tests/output/hideout_tab_scroll_diff/{before,after,absdiff}.png so the two grabs and their
per-pixel difference can be eyeballed: a moved row shows the labels smeared across the whole diff,
an end-of-list swipe shows near-black.
"""
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import window  # noqa: E402
from interact import craft, find  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'hideout_tab_scroll_diff'


if __name__ == '__main__':
    direction = sys.argv[1] if len(sys.argv) > 1 else 'left'

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
    dx = -dist if direction == 'left' else dist  # negative dx drags the row right-to-left
    print(f'grab point ({x}, {y}) off {len(icons)} icons, dx {dx:+d} ({direction})\n')

    before = craft.hideout_tabs_strip(region)
    craft._swipe(x, y, dx)
    time.sleep(craft.SWIPE_SETTLE)
    after = craft.hideout_tabs_strip(region)

    diff = craft._hideout_tab_scroll_diff(before, after)
    scrolled = craft.did_scroll_mode_hideout_tab(before, after)

    OUT.mkdir(parents=True, exist_ok=True)
    before.save(OUT / 'before.png')
    after.save(OUT / 'after.png')
    absdiff = np.abs(np.asarray(after, dtype=float) - np.asarray(before, dtype=float))
    Image.fromarray(absdiff.astype(np.uint8), mode='L').save(OUT / 'absdiff.png')

    print(f'mean grey difference: {diff:.2f}')
    print(f'did_scroll_mode_hideout_tab (threshold {craft.HIDEOUT_TAB_SCROLL_DIFF}): {scrolled}')
    print(f'\n-> {OUT}')
    print('run once where the swipe MOVES the row (big number) and once at the end of the list '
          '(small number); the threshold goes between them.')
