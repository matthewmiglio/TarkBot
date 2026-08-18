"""A game closed mid-run stops the pass instead of clicking where it used to be.

Run:  python tests/test_window_gone.py

No game needed, nothing is clicked. open_offer_creation is driven with every screen-touching
call stubbed, so this is only about the one question asked just before the add offer click:
is Tarkov still there.

It matters because self.region is measured once at Start and never again. Every grab after that
is of the same rectangle whether or not the game is still behind it, so template matching cannot
tell a closed game from a missing button: it photographs the desktop and reports the add offer
button gone, which sends the reader looking at the flea.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sell_bot  # noqa: E402
import tarkov_window  # noqa: E402
from interact import sell  # noqa: E402
from sell_bot import Tarkbot  # noqa: E402


def check(ok, what):
    print(f'  {"ok" if ok else "FAILED"}  {what}')
    if not ok:
        sys.exit(1)


def run_open(window_open):
    """open_offer_creation with the screen faked out. Returns (what was raised, clicks made)."""
    bot = object.__new__(Tarkbot)
    bot.region = None
    bot._stop = threading.Event()
    bot._pause = lambda *a: None
    bot._await_offer_slot = lambda: None

    clicks = []
    original = {name: getattr(sell, name) for name in
                ('open_flea', 'apply_flea_filters', 'click_add_offer', 'wait_for',
                 'disable_autoselect_similar', 'orientate_offer_creation')}
    real_handle = tarkov_window.handle
    sell.open_flea = lambda region=None: True
    sell.apply_flea_filters = lambda region=None: True
    sell.click_add_offer = lambda region=None: clicks.append('add offer') or (1, 2)
    sell.wait_for = lambda target, region=None, **kw: True
    sell.disable_autoselect_similar = lambda region=None: True
    sell.orientate_offer_creation = lambda region=None: (1, 2)

    def fake_handle(title=tarkov_window.TITLE):
        if not window_open:
            raise tarkov_window.WindowError(f'No window titled {title!r} (is the game running?)')
        return 1234

    tarkov_window.handle = fake_handle
    try:
        raised = None
        try:
            bot.open_offer_creation()
        except Exception as e:  # noqa: BLE001  any raise is the answer, the type is checked below
            raised = e
        return raised, clicks
    finally:
        for name, func in original.items():
            setattr(sell, name, func)
        tarkov_window.handle = real_handle


print('Tarkov closed before the add offer click')
raised, clicks = run_open(window_open=False)
check(isinstance(raised, tarkov_window.WindowError), f'it raised WindowError, not {raised!r}')
check(clicks == [], 'and clicked nothing, so nothing landed on whatever is behind the game')
check('running' in str(raised), f'the message says the game is gone: {raised}')

print('Tarkov still open')
raised, clicks = run_open(window_open=True)
check(raised is None, f'the pass ran through, raised {raised!r}')
check(clicks == ['add offer'], 'and the add offer button was clicked as usual')

print('ok')
