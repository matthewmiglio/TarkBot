"""Print whether the flea market is open.

Run:  python tests/test_flea_open.py

Read-only, it never clicks. Prints the icon's bbox and measured brightness alongside the
verdict, so a surprising answer shows you which side of the threshold it landed on.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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
