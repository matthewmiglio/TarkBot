"""Click the inventory 'All' button on the live Tarkov screen.

Run:  python tests/test_click_all_button.py        (wait, then click it)
      python tests/test_click_all_button.py --dry  (locate only, no click)

Exits non-zero if the button was not found. On success writes tests/output/
all_button_before.png and _after.png so you can see whether the click landed.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find, sell  # noqa: E402

TARGET = 'inventory_all_button'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the click misses if the game isn't focused
OUT = Path(__file__).parent / 'output'


def main(dry=False):
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    print(f'searching window {region} for {TARGET}')

    box = find.find(TARGET, region=region)
    if not box:
        sys.exit(f'{TARGET}: not found (is the inventory open?)')
    print(f'found {box} -> center {pyautogui.center(box)}')
    if dry:
        return

    for n in range(DELAY, 0, -1):
        print(f'clicking in {n}...')
        time.sleep(1)

    OUT.mkdir(exist_ok=True)
    pyautogui.screenshot(region=region).save(OUT / 'all_button_before.png')
    point = sell.click_all_button(region)
    if not point:
        sys.exit(f'{TARGET}: vanished between locating and clicking')
    time.sleep(0.5)  # let the UI redraw
    pyautogui.screenshot(region=region).save(OUT / 'all_button_after.png')
    print(f'clicked {point} -> compare {OUT / "all_button_before.png"} with _after.png')


if __name__ == '__main__':
    main(dry='--dry' in sys.argv)
