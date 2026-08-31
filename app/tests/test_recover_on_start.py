"""What Start escapes out of before it goes looking for the flea.

Run:  python tests/test_recover_on_start.py

No game needed, nothing is clicked. sell.close_leftover_windows is driven with find() faked, so
this is only about which screens it decides to back out of.

Start is the one moment the bot does not know what is in front of it: the user may have hit it
with a scav case open, or over a run that was stopped mid pass. Every other screen a pass meets
is one it opened itself.

The case worth protecting is the inventory. The offer creation window is recognised by two
buttons together, and the ALL button on its own is just the inventory, which is a normal place
to start from. Escaping out of that would close the thing the user was looking at, every time.

The filter window is here for the opposite reason. A dropdown whose option cannot be found now
leaves that window open deliberately, so the state can be read, which means recovery is the only
thing that ever clears it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

from interact import find, sell  # noqa: E402


def recover_with(on_screen):
    """close_leftover_windows against a screen showing exactly `on_screen`. Returns the presses."""
    keys, clicks = [], []
    originals = (find.find_center, pyautogui.press, pyautogui.click)
    find.find_center = lambda name, region=None, **kw: (10, 20) if name in on_screen else None
    pyautogui.press = keys.append
    pyautogui.click = lambda x, y=None, **kw: clicks.append((x, y))
    try:
        presses = sell.close_leftover_windows(delay=0)
        assert presses == len(keys), f'reported {presses} escapes, actually pressed {len(keys)}'
        assert all(k == 'esc' for k in keys), f'pressed something other than esc: {keys}'
        # Every escape is preceded by a click on that window's title bar, to focus it first.
        assert len(clicks) == presses, f'{presses} escapes but {len(clicks)} focusing clicks'
        return presses
    finally:
        find.find_center, pyautogui.press, pyautogui.click = originals


SCAV = sell.SCAV_WINDOW_TARGET
OFFER = (sell.OFFER_TARGET,)
FILTERS = sell.FILTERS_WINDOW_TARGET

CASES = (
    ((), 0, 'a clean flea screen, nothing to back out of'),
    ((SCAV,), 1, 'a scav case window left open'),
    (OFFER, 1, 'the offer creation window left open'),
    ((SCAV,) + OFFER, 2, 'both, so both get an escape'),
    ((sell.ALL_BUTTON_TARGET,), 0, 'the plain inventory, which must NOT be escaped'),
    ((sell.AUTOSELECT_TARGET,), 0, 'a control inside a window is never what is matched on'),
    # The reported failure: an interrupted scav run leaves the offer window over the case, and
    # over a scav case there is no inventory ALL tab, which is what detection used to need.
    ((SCAV, sell.OFFER_TARGET), 2, 'offer window over a scav case, no inventory in sight'),
    # _pick_from_dropdown gives up with the filter window open and a list unrolled over it,
    # so that it can be read. Recovery is what clears it, and it is matched on the title bar
    # because the open list can be sat over everything below it.
    ((FILTERS,), 1, 'the flea filter window a failed dropdown left open'),
    ((FILTERS, sell.CURRENCY_ANY_TARGET), 1, 'the same, list still unrolled, still one escape'),
    ((SCAV, FILTERS) + OFFER, 3, 'all three, so all three get an escape'),
)

if __name__ == '__main__':
    for on_screen, expected, what in CASES:
        got = recover_with(set(on_screen))
        assert got == expected, f'{what}: escaped {got} times, wanted {expected}'
        print(f'  ok  {expected} escape(s)  {what}')
    print('ok, it backs out of leftover windows and leaves an ordinary screen alone')
