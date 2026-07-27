"""Crop the suggested price readout and read the number out of it.

Run:  python tests/test_grab_price_window.py

Writes tests/output/price_window.png, which should show the price and its currency icon.
Read-only, it never clicks. The offer creation window must be open with an item selected.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import tarkov_window  # noqa: E402
from interact import ocr, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'

if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    rect = sell.grab_price_region(region)
    print(f'window {region} -> price region {rect}')

    crop = pyautogui.screenshot(region=rect)
    OUT.mkdir(exist_ok=True)
    path = OUT / 'price_window.png'
    crop.save(path)

    for digit, score in ocr.read_digits(crop):
        print(f'  {digit or "?"}  {score:.3f}')
    print(f'read_number -> {ocr.read_number(crop)}')
    print(f'wrote {path}')
