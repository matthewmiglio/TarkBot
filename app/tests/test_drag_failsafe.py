"""A drag that raises still leaves the cursor off the corner it was dragging to.

Run:  python tests/test_drag_failsafe.py

No game needed, nothing is dragged. pyautogui and find are faked out, so this is only about the
order _drag_to_corner does things in when something goes wrong.

Windows are dragged by their title bar into a screen corner, and every corner is one of
pyautogui's panic points, so the fail-safe is switched off for the trip. The cursor therefore
sits on a live panic point for the whole drag. If an exception gets out while it is there and
the fail-safe comes back on around it, the next pyautogui call anywhere in the bot raises
FailSafeException, with a message about corners and a traceback pointing at whatever innocent
click happened to be next.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import screen  # noqa: E402
from interact import find, sell  # noqa: E402

CORNER = (0, 1079)  # bottom left, where the offer creation window gets dragged every pass
MIDDLE = (960, 540)  # where _park_cursor should leave it, clear of all four panic points


def drag_with(find_center):
    """_drag_to_corner with the screen faked. Returns (where the cursor ended, what was raised)."""
    at = [None]
    originals = (find.find_center, pyautogui.moveTo, pyautogui.dragTo, screen.rect,
                 pyautogui.FAILSAFE)
    find.find_center = find_center
    pyautogui.moveTo = lambda x, y=None, **kw: at.__setitem__(0, (x, y))
    pyautogui.dragTo = lambda x, y=None, **kw: at.__setitem__(0, (x, y))
    screen.rect = lambda: (0, 0, 1920, 1080)
    pyautogui.FAILSAFE = True
    try:
        raised = None
        try:
            sell._drag_to_corner(sell.OFFER_TARGET, 'bottom left', duration=0, repeats=1)
        except Exception as e:
            raised = e
        assert pyautogui.FAILSAFE is True, 'the fail-safe was not put back'
        return at[0], raised
    finally:
        (find.find_center, pyautogui.moveTo, pyautogui.dragTo, screen.rect,
         pyautogui.FAILSAFE) = originals


def boom(*args, **kwargs):
    raise RuntimeError('the window vanished mid drag')


if __name__ == '__main__':
    ended, raised = drag_with(lambda *a, **kw: (71, 121))
    assert raised is None, f'a clean drag should not raise, got {raised}'
    assert ended == MIDDLE, f'clean drag left the cursor at {ended}, wanted {MIDDLE}'
    print(f'  ok  clean drag      cursor parked at {ended}, fail-safe back on')

    ended, raised = drag_with(boom)
    assert raised is not None, 'the real failure was swallowed'
    assert ended == MIDDLE, (f'the drag raised and left the cursor at {ended}, a panic point; '
                             f'the next pyautogui call anywhere would die with a fail-safe error')
    assert ended != CORNER, 'parked on the corner it was dragging to'
    print(f'  ok  drag raised     cursor parked at {ended}, "{raised}" still raised')

    print('ok, the cursor comes off the corner before the fail-safe comes back on')
