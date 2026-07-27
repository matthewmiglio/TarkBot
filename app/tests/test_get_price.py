"""Read the suggested price off the offer creation window.

Run:  python tests/test_get_price.py

Prints the value sell.get_price() returns. Read-only, it never clicks. The offer creation
window must be open with an item selected. Exits non-zero if nothing readable was there.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tarkov_window  # noqa: E402
from interact import sell  # noqa: E402

if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    print(f'price region {sell.grab_price_region(region)}')

    price = sell.get_price(region)
    print(f'get_price() -> {price}')
    sys.exit(0 if price is not None else 'nothing readable in the price box')
