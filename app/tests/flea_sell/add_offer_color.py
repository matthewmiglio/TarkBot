"""Measure the add offer button's colour so its enabled/disabled states can be told apart.

A colour-measuring utility for interact/sell.py, not a pass/fail test. It feeds the threshold
sell.more_offers_available reads: run it once with a slot free and once with the offer list
full, then set sell.MORE_OFFERS_BRIGHTNESS between the two brightest-channel numbers it prints.
Reports the button's brightest pixel, the max channel (what add_offer_brightness returns and the
threshold acts on) and the mean channel, and writes the crop to
tests/flea_sell/output/add_offer_<state>.png so the two states can be compared side by side.

Read-only, it never clicks. Needs the live game, flea open with the offer creation window up.

Run:  python tests/flea_sell/add_offer_color.py            (just report)
      python tests/flea_sell/add_offer_color.py enabled    (also tag the saved crop with the state)
      python tests/flea_sell/add_offer_color.py disabled
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parents[1] / 'output'

if __name__ == '__main__':
    state = sys.argv[1] if len(sys.argv) > 1 else 'unlabelled'
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    box = find.find(sell.ADD_OFFER_TARGET, region)
    if not box:
        sys.exit('add offer button not on screen')
    rect = (int(box.left), int(box.top), int(box.width), int(box.height))
    crop = pyautogui.screenshot(region=rect).convert('RGB')
    pixels = np.asarray(crop)

    brightest = pixels.reshape(-1, 3)[pixels.sum(axis=2).argmax()]  # the single lightest pixel
    print(f'state:          {state}')
    print(f'button:         {rect}')
    print(f'brightest rgb:  {tuple(int(v) for v in brightest)}')
    print(f'max channel:    {sell.add_offer_brightness(region)}   <- what feeds the threshold')
    print(f'mean channel:   {pixels.mean():.1f}   (for comparison, the flea icon uses this)')

    OUT.mkdir(exist_ok=True)
    path = OUT / f'add_offer_{state}.png'
    crop.save(path)
    print(f'wrote {path}')
