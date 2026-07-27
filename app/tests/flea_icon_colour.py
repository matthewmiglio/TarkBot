"""Find the flea icon and report the average colour inside its bbox.

Run:  python tests/flea_icon_colour.py

Not a pass/fail test, a measuring tool. Run it once with the flea closed and once with
it open, then feed the two averages into sell.is_flea_open. Saves the crop it measured
to tests/output/flea_icon.png so you can confirm it framed the right thing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find  # noqa: E402

OUT = Path(__file__).parent / 'output'
TARGET = 'flea_icon'

if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)

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
