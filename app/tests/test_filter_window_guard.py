"""The filter window has to actually open before anything reads the controls inside it.

Run:  python tests/test_filter_window_guard.py

No game and no screen: the finder and the mouse are both stubbed, so this is about what
open_filters does with the answers, not about matching pixels.

The run of 19 Aug is what this guards. A plain Error dialog sat over the flea, the gear click
landed on nothing, and the first thing to notice was the currency dropdown read, which reported
'matched neither ..._any nor ..._rub' and sent us looking for a missing reference crop of a
window that was never on screen.
"""
import sys
from pathlib import Path

import pyautogui
import pyscreeze

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from interact import find, sell  # noqa: E402

BOX = pyscreeze.Box(100, 100, 40, 20)  # stands in for anything the finder is asked for

if __name__ == '__main__':
    clicks = []
    pyautogui.click = lambda *point, **kw: clicks.append(point)
    # open_filters ends by dragging the window into a corner, and without these two that drag
    # is a real one: it takes hold of the mouse and throws it across whatever is on screen.
    pyautogui.moveTo = lambda *point, **kw: None
    pyautogui.dragTo = lambda *point, **kw: None
    find.find_center = lambda name, region=None, **kw: (100, 100)  # the gear is always there
    sell.FILTERS_WINDOW_TIMEOUT = 0.4  # the real 3s only makes the test slower

    find.find = lambda name, region=None, **kw: None  # nothing ever draws
    if sell.open_filters() is not False:
        sys.exit('open_filters said yes with no filter window on screen')
    if len(clicks) != 1:
        sys.exit(f'the gear should be clicked once and nothing else, got {clicks}')

    clicks.clear()
    if sell.apply_flea_filters() is not False:
        sys.exit('apply_flea_filters carried on without its window')
    if len(clicks) != 1:
        sys.exit(f'it went on clicking controls inside a window that never opened: {clicks}')

    clicks.clear()
    if sell.apply_flea_filters(reset=True) is not False:
        sys.exit('the reset pass carried on without its window')
    if len(clicks) != 1:
        sys.exit(f'it clicked reset on a screen with no filter window: {clicks}')

    clicks.clear()
    find.find = lambda name, region=None, **kw: BOX  # the window is up and grabs fine
    if not sell.open_filters():
        sys.exit('open_filters said no with the window title right there')

    # Up for the wait, gone by the drag. The title bar was matched a moment earlier, so this is
    # the window vanishing or something being drawn over it between two reads, not a window in
    # an awkward spot. Carrying on would set dropdowns by template match on a screen that has
    # already disagreed with itself once, and the first thing to fail would be a dropdown read
    # blaming a reference crop, which is the exact confusion this file exists to prevent.
    clicks.clear()
    seen = []

    def once_then_gone(name, region=None, **kw):
        seen.append(name)
        return BOX if len(seen) == 1 else None

    find.find = once_then_gone
    if sell.open_filters() is not False:
        sys.exit('open_filters said yes about a window it could not find to drag')

    print('ok: no filter window, no clicking on where its controls would have been')
