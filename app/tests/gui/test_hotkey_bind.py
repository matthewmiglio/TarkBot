"""Rebinding the start key: does the new key get claimed and the old one given back.

App layer: gui/app.py's start-key RegisterHotKey rebind (gui.app.hotkey and the bind callable
it returns, over gui.app.HOTKEYS), which must hand the old key back when it claims a new one.

Run:  python tests/gui/test_hotkey_bind.py

NO GAME and no GUI. It registers real Windows hotkeys, briefly: F7 and F8 are pressed by
nothing here, but do not hold either of them down while this runs. Exits non-zero on the first
thing that fails.

The trap this guards is the one that has no visible symptom until you try the old key: the
registration belongs to the thread that made it, so a rebind that only starts a new thread
leaves the previous key claimed system wide for the rest of the session.
"""
import ctypes
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gui.app import HOTKEYS, hotkey  # noqa: E402

SETTLE = 0.3  # seconds for a pump thread to register, or to unwind and unregister


def claimable(name):
    """True if this key is free right now, taking it and letting it go to find out."""
    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, 9, 0, HOTKEYS[name]):  # id 9: nothing else here uses it
        return False
    user32.UnregisterHotKey(None, 9)
    return True


if __name__ == '__main__':
    # F5 stays out: sell_bot presses it itself, and a system wide claim would send the bot's
    # own flea refresh back as a press of its own Stop button.
    if HOTKEYS['F1'] != 0x70 or HOTKEYS['F12'] != 0x7B or 'F5' in HOTKEYS:
        sys.exit(f'the virtual key codes are wrong: {HOTKEYS}')

    bind = hotkey(lambda: None)
    bind('F7')
    time.sleep(SETTLE)
    if claimable('F7'):
        print('F7 was not claimed, so the hotkey never registered')
        sys.exit('nothing is listening for the start key')

    bind('F8')
    time.sleep(SETTLE)
    if claimable('F8'):
        sys.exit('the new key F8 was not claimed, so the rebind did not take')
    if not claimable('F7'):
        sys.exit('the old key F7 is still held, so it is dead to every other program')

    print('ok: F8 is claimed and F7 was handed back')
