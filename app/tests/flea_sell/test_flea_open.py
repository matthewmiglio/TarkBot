"""Print whether the flea market is open.

Exercises interact/sell.py's find_flea_icon, flea_icon_brightness and is_flea_open. Open is
read off the flea taskbar icon's mean-channel brightness, which inverts when the market opens,
against FLEA_OPEN_BRIGHTNESS rather than a second template. Prints the icon's bbox and measured
brightness alongside the verdict, so a surprising answer shows which side of the threshold it
landed on.

Read-only, it never clicks. Needs the live game.

Run:  python tests/flea_sell/test_flea_open.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import window  # noqa: E402
from interact import sell  # noqa: E402

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    box = sell.find_flea_icon(region)
    print(f'{sell.FLEA_ICON_TARGET}: {box or "not on screen"}')
    brightness = sell.flea_icon_brightness(region)
    print(f'brightness: {brightness if brightness is None else round(brightness, 1)} '
          f'(open at >= {sell.FLEA_OPEN_BRIGHTNESS})')
    print(f'is_flea_open() -> {sell.is_flea_open(region)}')
