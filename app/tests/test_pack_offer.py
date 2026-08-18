"""A suggested price quoted against a pack is refused, and the pass skips the item.

Run:  python tests/test_pack_offer.py

No game needed, nothing is clicked. find() and the OCR are both stubbed, so this is only about
what get_price decides once the pack text is or is not on the top comparable offer.

Worth a test rather than a careful reading because the failure is silent and one-directional.
A pack of 20 nails is listed at 20 nails' money; undercut that for one nail and the item goes
up at a twentieth of its worth, with a price the OCR read perfectly and every number in the
run's totals agreeing that it went well. The only moment the two can be told apart is this one,
before the number is read at all.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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
