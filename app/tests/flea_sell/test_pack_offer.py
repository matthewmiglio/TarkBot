"""A suggested price quoted against a pack is refused, so the pass skips the item.

Exercises interact/sell.py's get_price and the first_offer_is_a_pack guard in front of it: a
pack is detected by finding flea_item_pack_sale_text in grab_first_offer_region (the top
comparable offer row), and when it is there get_price returns None before the OCR is ever
reached. Asserts both directions: pack present reads as None and never calls the reader, pack
absent still reads the number, and that the pack text is looked for in the first-offer region.

A no-game, stubbed test: interact/find.find and interact/ocr.read_region are both replaced, so
nothing is clicked and no window is needed. Worth a test rather than a careful reading because
the failure is silent and one-directional. A pack of 20 nails is priced at 20 nails' money;
undercut that for one nail and the item lists at a twentieth of its worth, with a price the OCR
read perfectly and every counter in the run's totals agreeing it went well. This is the only
moment the two can be told apart.

Run:  python tests/flea_sell/test_pack_offer.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyscreeze  # noqa: E402

from interact import find, ocr, sell  # noqa: E402

WINDOW = (0, 0, 2560, 1440)
BOX = pyscreeze.Box(1200, 200, 60, 20)  # a match, wherever it landed


def price_with(pack_text_found):
    """sell.get_price against a screen where the pack text is or is not on the top offer."""
    looked_in = []

    def fake_find(name, region=None, *a, **k):
        looked_in.append((name, region))
        return BOX if (name == 'flea_item_pack_sale_text' and pack_text_found) else None

    real_find, real_read = find.find, ocr.read_region
    find.find = fake_find
    ocr.read_region = lambda crop: 45000
    try:
        return sell.get_price(WINDOW), looked_in
    finally:
        find.find, ocr.read_region = real_find, real_read


if __name__ == '__main__':
    price, looked_in = price_with(pack_text_found=True)
    assert price is None, f'a pack offer must read as unreadable, got {price}'
    print(f'pack on the top offer -> {price}, and the OCR was never reached')

    name, region = looked_in[0]
    assert name == 'flea_item_pack_sale_text', f'looked for {name} first, not the pack text'
    assert region == sell.grab_first_offer_region(WINDOW), f'looked in {region}, not the top offer'
    print(f'it looked for {name} in {region}, which is the top offer row')

    price, _ = price_with(pack_text_found=False)
    assert price == 45000, f'a normal offer must still read its price, got {price}'
    print(f'no pack on the top offer -> {price}, read as usual')

    print('PASSED')
