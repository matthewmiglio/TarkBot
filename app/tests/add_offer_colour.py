"""Measure the add offer button's colour so its enabled/disabled states can be told apart.

Run:  python tests/add_offer_colour.py            (just report)
      python tests/add_offer_colour.py enabled    (also tag the saved crop with the state)
      python tests/add_offer_colour.py disabled

Read-only, it never clicks. Run it once in each state, then set
sell.MORE_OFFERS_BRIGHTNESS somewhere between the two numbers. Writes the crop to
tests/output/add_offer_<state>.png so both can be compared side by side afterwards.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'

if __name__ == '__main__':
    state = sys.argv[1] if len(sys.argv) > 1 else 'unlabelled'
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)

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
