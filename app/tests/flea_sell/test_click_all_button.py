"""Click the inventory 'All' button on the live Tarkov screen.

Exercises interact/sell.py's click_all_button, which finds inventory_all_button and clicks it
(through jitter) to switch the stash to the All view the seller reads its sell pixels from.
Locates the button, counts down, clicks, and writes the before/after screenshots to
tests/flea_sell/output/ so it can be seen whether the click landed and the view changed.

Guards the one step that has to happen before find_sell_pixels can see the whole stash. This
one clicks (unless --dry, which locates only). Needs the live game with the inventory open.
Exits non-zero if the button was not found or vanished between locating and clicking.

Run:  python tests/flea_sell/test_click_all_button.py        (wait, then click it)
      python tests/flea_sell/test_click_all_button.py --dry  (locate only, no click)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

TARGET = 'inventory_all_button'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the click misses if the game isn't focused
OUT = Path(__file__).parents[1] / 'output'


def main(dry=False):
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
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
