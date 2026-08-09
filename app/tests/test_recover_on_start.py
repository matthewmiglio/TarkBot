"""What Start escapes out of before it goes looking for the flea.

Run:  python tests/test_recover_on_start.py

No game needed, nothing is clicked. sell.close_leftover_windows is driven with find() faked, so
this is only about which screens it decides to back out of.

Start is the one moment the bot does not know what is in front of it: the user may have hit it
with a scav case open, or over a run that was stopped mid pass. Every other screen a pass meets
is one it opened itself.

The case worth protecting is the last one. The offer creation window is recognised by two
buttons together, and the ALL button on its own is just the inventory, which is a normal place
to start from. Escaping out of that would close the thing the user was looking at, every time.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

from interact import find, sell  # noqa: E402


def recover_with(on_screen):
    """close_leftover_windows against a screen showing exactly `on_screen`. Returns the presses."""
    keys = []
    original_find, original_press = find.find, pyautogui.press
    find.find = lambda name, region=None, **kw: 'a box' if name in on_screen else None
    pyautogui.press = keys.append
    try:
        presses = sell.close_leftover_windows(delay=0)
        assert presses == len(keys), f'reported {presses} escapes, actually pressed {len(keys)}'
        assert all(k == 'esc' for k in keys), f'pressed something other than esc: {keys}'
        return presses
    finally:
        find.find, pyautogui.press = original_find, original_press


SCAV = sell.SCAV_WINDOW_TARGET
OFFER = (sell.ALL_BUTTON_TARGET, sell.AUTOSELECT_TARGET)

CASES = (
    ((), 0, 'a clean flea screen, nothing to back out of'),
    ((SCAV,), 1, 'a scav case window left open'),
    (OFFER, 1, 'the offer creation window left open'),
    ((SCAV,) + OFFER, 2, 'both, so both get an escape'),
    ((sell.ALL_BUTTON_TARGET,), 0, 'the plain inventory, which must NOT be escaped'),
    ((sell.AUTOSELECT_TARGET,), 0, 'half a match is not the offer window either'),
)

if __name__ == '__main__':
    for on_screen, expected, what in CASES:
        got = recover_with(set(on_screen))
        assert got == expected, f'{what}: escaped {got} times, wanted {expected}'
        print(f'  ok  {expected} escape(s)  {what}')
    print('ok, it backs out of leftover windows and leaves an ordinary screen alone')
