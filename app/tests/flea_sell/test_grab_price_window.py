"""Crop the suggested price readout and read the number out of it, glyph by glyph.

Exercises interact/sell.py's grab_price_region (the fixed window-fraction crop, used because
the digits inside change and nothing stable can be matched) together with interact/ocr.py's
read_digits and read_number, the bitmap-font reader the seller prices against. Prints each
glyph and its match score, then read_number's verdict, and writes the crop to
tests/flea_sell/output/price_window.png so the price and its currency icon can be eyeballed.

The picture is the point: it shows whether the region actually framed the number, so a misread
can be told from a miscrop. Read-only, it never clicks. Needs the live game, with the offer
creation window open and an item selected.

Run:  python tests/flea_sell/test_grab_price_window.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import ocr, sell  # noqa: E402

OUT = Path(__file__).parents[1] / 'output'

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
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
