"""Read the suggested price off the live offer creation window through sell.get_price.

Exercises interact/sell.py: grab_price_region (the fixed-fraction crop of the price readout)
and get_price (which reads that crop, but only after first_offer_is_a_pack has cleared the top
comparable offer). Prints the region it measured and the value get_price returns. Read-only, it
never clicks.

Guards the reader end to end on a real screen: a price the crop clips, a pack offer the seller
must skip, or a window that has moved all surface here rather than as a silently mislisted item.
Needs the live game, with the offer creation window open and an item selected. Exits non-zero
when nothing readable was in the price box (which is also get_price's pack answer, None).

Run:  python tests/flea_sell/test_get_price.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import window  # noqa: E402
from interact import sell  # noqa: E402

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    print(f'price region {sell.grab_price_region(region)}')

    price = sell.get_price(region)
    print(f'get_price() -> {price}')
    sys.exit(0 if price is not None else 'nothing readable in the price box')
