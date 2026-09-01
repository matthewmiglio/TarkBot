"""Find the flea icon and report the average colour inside its bbox.

A colour-measuring utility that feeds interact/sell.py's is_flea_open, not a pass/fail test.
The flea taskbar icon only inverts between open and closed, so open is read off mean channel
brightness rather than a second template. Run it once with the flea closed and once with it
open, then set the FLEA_OPEN_BRIGHTNESS threshold between the two means it prints. Matches
find's flea_icon at 0.9, 0.8 and 0.7 and prints mean, median and brightest per confidence, and
saves the crop to tests/flea_sell/output/flea_icon.png so the framing can be confirmed.

Read-only, it never clicks. Needs the live game.

Run:  python tests/flea_sell/flea_icon_color.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import find  # noqa: E402

OUT = Path(__file__).parents[1] / 'output'
TARGET = 'flea_icon'

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    for confidence in (0.9, 0.8, 0.7):
        box = find.find(TARGET, region, confidence=confidence)
        if not box:
            print(f'confidence {confidence}: no match')
            continue
        rect = (int(box.left), int(box.top), int(box.width), int(box.height))
        crop = pyautogui.screenshot(region=rect).convert('RGB')
        pixels = np.asarray(crop).reshape(-1, 3)
        mean = tuple(int(round(v)) for v in pixels.mean(axis=0))
        median = tuple(int(v) for v in np.median(pixels, axis=0))
        brightest = tuple(int(v) for v in pixels[pixels.sum(axis=1).argmax()])
        print(f'confidence {confidence}: {rect}  mean {mean}  median {median}  brightest {brightest}')
        if confidence == 0.9 or not (OUT / 'flea_icon.png').exists():
            OUT.mkdir(exist_ok=True)
            crop.save(OUT / 'flea_icon.png')
    print(f'crop saved to {OUT / "flea_icon.png"}')
