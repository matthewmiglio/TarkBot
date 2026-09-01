"""Check craft.check_if_station_active against the live game.

Run:  python tests/hideout_nav/test_check_station_active.py

Real screen read, no clicks. Open a station panel first (any station). Prints the region it read
and whether the close (X) button was found there, i.e. whether a station is active.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import window  # noqa: E402
from interact import craft  # noqa: E402

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    scoped = craft._region_from_fractions(craft.CLOSE_BUTTON_REGION_FRACTIONS, region)
    print(f'window {region}')
    print(f'close-button region (l, t, w, h): {scoped}')

    active = craft.check_if_station_active(region)
    print('YES, a station is active (close button found)' if active
          else 'NO station active (close button not found in the region)')
    raise SystemExit(0 if active else 1)
