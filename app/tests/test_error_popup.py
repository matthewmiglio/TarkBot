"""Where sell.dismiss_error_popup clicks, and that a screen without the dialog is left alone.

Run:  python tests/test_error_popup.py

No game needed, nothing is really clicked: find and pyautogui are stubbed, so this is about the
arithmetic that turns a matched box into a point, not about matching pixels.

Tarkov drops a plain "Error / 0 / OK" dialog over the flea on its own schedule. While it is up
every read underneath it fails, so a run meets it as pass after pass (or item after item) failing
for no reason either mode can name, until Stop. Clicking its OK is what unsticks that.

The click is aimed off the dialog's own box rather than off a reference crop of the OK button.
Two plain glyphs on flat black have no false-positive headroom, the same problem the note on
find.CONFIDENCES describes for the checkmark, while the dialog around them is wide, carries a
title bar and matches at the default 0.9. So the safe thing is what gets found and the button is
a fraction down it, which is the arithmetic worth a test: get the fraction wrong and this clicks
the dialog's empty middle, reports that it recovered, and the run stays stuck.

CROPS below is measured off the five pngs in error_0_popup/ rather than assumed, so a sixth crop
that frames the dialog differently belongs in that list. Rebuild it with:

    python -c "import numpy as np; from pathlib import Path; from PIL import Image
    for p in sorted(Path('interact/reference_images/error_0_popup').glob('*.png')):
        a = np.asarray(Image.open(p).convert('L')); h = a.shape[0]
        ys = np.flatnonzero(a[h//2:].max(axis=1) > 150) + h//2
        print(a.shape[1], h, ys.min(), ys.max())"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
import pyscreeze  # noqa: E402
from interact import find, sell  # noqa: E402

# (width, height, first row of the OK glyphs, last row), at the 1080p size these are stored at.
# The clickable button is taller than its glyphs, so landing inside these rows is the strict
# version of landing on the button.
CROPS = [(456, 116, 79, 95), (456, 119, 80, 96), (456, 117, 80, 96),
         (455, 114, 77, 93), (456, 118, 80, 96)]


def click_for(box):
    """Where dismiss_error_popup clicks given a match at `box`, or None if it found nothing."""
    clicked = []
    real_find, real_click, real_sleep = find.find, pyautogui.click, sell.time.sleep
    find.find = lambda *a, **k: box
    pyautogui.click = lambda *point: clicked.append(point)
    sell.time.sleep = lambda seconds: None  # the 2s settle, which this test has no use for
    try:
        found = sell.dismiss_error_popup()
    finally:
        find.find, pyautogui.click, sell.time.sleep = real_find, real_click, real_sleep
    assert found == bool(clicked), f'said {found} but clicked {clicked}'
    return clicked[0] if clicked else None


print('no dialog on screen:')
assert click_for(None) is None, 'clicked at a dialog that was not there'
print('  ok  nothing found, nothing clicked')

# The dialog can be anywhere, and the second position is a monitor sitting left of the primary,
# where screen coords go negative. Nothing in this repo may assume a screen starts at (0, 0).
print('every crop in error_0_popup/, at two screen positions:')
for left, top in ((700, 400), (-1520, 130)):
    for width, height, ok_top, ok_bottom in CROPS:
        x, y = click_for(pyscreeze.Box(left, top, width, height))
        assert abs(x - (left + width // 2)) <= sell.CLICK_JITTER, (
            f'{width}x{height}: clicked x {x}, wanted the box middle {left + width // 2}')
        # Every draw the jitter can produce has to be on the button, not just the middle one.
        low, high = y - sell.CLICK_JITTER, y + sell.CLICK_JITTER
        assert top + ok_top <= low and high <= top + ok_bottom, (
            f'{width}x{height}: clicked y {y} (jitter reaches {low}-{high}), and OK is at '
            f'{top + ok_top}-{top + ok_bottom}. ERROR_POPUP_OK_FRACTION is '
            f'{sell.ERROR_POPUP_OK_FRACTION}, which puts part of the click off the button')
        print(f'  ok  {width}x{height} at ({left}, {top}): clicked ({x}, {y}), OK spans '
              f'{top + ok_top}-{top + ok_bottom}')

print(f'ok, dismiss_error_popup lands on OK for every crop in the folder at '
      f'{sell.ERROR_POPUP_OK_FRACTION} of the box, and does nothing when no dialog is up')
