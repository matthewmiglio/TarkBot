"""Save the price box on screen right now as a fixture, labelled with its true value.

App layer: grows the corpus that interact/ocr.py is tested against. It reads the live price box
via interact/sell.py (sell.grab_price_region) and interact/ocr.py (ocr.read_number) to report
whether the reader already agrees with the value you typed.

Run:  python tests/detection/capture_price.py 177777

Needs the LIVE GAME: it screenshots the Tarkov window's price region, so window.handle() raises
with no game up. The filename is the ground truth, so there is no manifest to fall out of step
with the images. A second capture of the same value lands as 177777__2.png and so on.
Run tests/detection/test_price_corpus.py to check the reader against everything collected.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import ocr, sell  # noqa: E402

PRICES = Path(__file__).resolve().parents[1] / 'fixtures' / 'prices'


def fixture_path(value):
    """prices/<value>.png, or <value>__2.png, __3.png if that value is already collected."""
    PRICES.mkdir(parents=True, exist_ok=True)
    path = PRICES / f'{value}.png'
    n = 2
    while path.exists():
        path = PRICES / f'{value}__{n}.png'
        n += 1
    return path


if __name__ == '__main__':
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.exit('usage: python tests/capture_price.py <the number shown on screen>')
    value = int(sys.argv[1])

    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    crop = pyautogui.screenshot(region=sell.grab_price_region(region))

    path = fixture_path(value)
    crop.save(path)
    got = ocr.read_number(crop)
    print(f'saved {path.relative_to(PRICES.parent.parent)}  truth {value}  reader says {got} '
          f'{"ok" if got == value else "<-- MISMATCH"}')
