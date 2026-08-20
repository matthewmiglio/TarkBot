"""A refused offer is not counted as a sale, and backs out by the right number of escapes.

Run:  python tests/test_cheap_offer_popup.py

No game needed, nothing is clicked. sell_one is driven with every screen-touching call stubbed,
so this is only about what the pass decides once the popup is or is not there.

Tarkov answers some place-offer clicks with a "below market value, are you sure" confirmation
instead of listing the item. The offer has not gone up, so counting it inflates two numbers that
cannot be recovered afterwards: items posted, and the money asked for. That second one is the
GUI's headline figure, which is why this is worth a test rather than a careful reading.

The escape count is the other half, and it is checked for both ways a pass can end without an
offer going up. The popup sits on top of whatever the pass already had open, so backing out takes
one more press than that pass would otherwise need: two from the stash, three with a scav case
open. An unreadable price adds no window of its own, so it takes exactly what the pass had open:
one from the stash, two with a case. Get either wrong and the next pass starts inside a window it
cannot see, which is not a failed pass but a failed run: on 2026-08-20 a scav case price failure
escaped once, left the offer creation window sat over the flea taskbar icon, and the next pass
raised 'could not open the flea market' after 132 good ones.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sell_bot  # noqa: E402
from interact import sell  # noqa: E402
from sell_bot import FleaSeller, Retry, Selection  # noqa: E402


def run_pass(popup, source, escapes, price=50000):
    """One sell_one with the screen faked out. Returns (stats, escapes pressed, what was raised).

    price=None is a suggested price the reader would not trust, which ends the pass before the
    offer is ever placed and so before the popup can be reached.
    """
    bot = object.__new__(FleaSeller)
    bot.region = None
    bot.undercut = (0.90, 2000)
    bot.stats = {key: 0 for key, _ in sell_bot.STAT_LABELS}
    bot._stop = threading.Event()
    pressed = []

    bot._pause = lambda *a: None
    bot.open_offer_creation = lambda: None
    bot.select_item = lambda: Selection((100, 200), escapes, source)
    bot._escape = pressed.append

    # Everything from here reads or drives the screen, so all of it is stubbed. The one that
    # matters is cheap_offer_popup; the rest just have to not touch a real game.
    original = {name: getattr(sell, name) for name in
                ('get_price', 'enter_price', 'click_place_offer', 'cheap_offer_popup')}
    sell.get_price = lambda region=None: price
    sell.enter_price = lambda price, region=None: True
    sell.click_place_offer = lambda region=None: (1, 2)
    sell.cheap_offer_popup = lambda region=None: popup
    try:
        raised = None
        try:
            bot.sell_one()
        except Retry as e:
            raised = e
        return bot.stats, pressed, raised
    finally:
        for name, func in original.items():
            setattr(sell, name, func)


if __name__ == '__main__':
    print('the popup is up, so the offer was refused:')
    for source, escapes, expected in (('inventory', sell_bot.INVENTORY_ESCAPES, 2),
                                      ('scav', sell_bot.SCAV_ESCAPES, 3)):
        stats, pressed, raised = run_pass(True, source, escapes)
        assert raised is not None, f'{source}: the pass carried on as if the offer had been placed'
        assert stats['posted'] == 0, f'{source}: counted a sale that did not happen'
        assert stats[sell_bot.MONEY_STAT] == 0, f'{source}: added money for an offer never placed'
        assert stats[f'posted_{source}'] == 0, f'{source}: counted it against {source} too'
        assert stats['price_missing'] == 1, f'{source}: not counted as a price failure'
        assert pressed == [expected], f'{source}: escaped {pressed}, wanted [{expected}]'
        print(f'  ok  {source:10} {expected} escapes, price failure, no sale, "{raised}"')

    print('no popup, so the offer went up as normal:')
    stats, pressed, raised = run_pass(False, 'inventory', sell_bot.INVENTORY_ESCAPES)
    assert raised is None, f'a clean pass should not retry, got "{raised}"'
    assert stats['posted'] == 1 and stats['posted_inventory'] == 1, stats
    assert stats[sell_bot.MONEY_STAT] > 0, 'a real sale still counts its money'
    assert stats['price_missing'] == 0, 'and is not a price failure'
    assert pressed == [], f'nothing to escape out of, pressed {pressed}'
    print(f'  ok  {"inventory":10} posted 1, asked {stats[sell_bot.MONEY_STAT]}, no escapes')

    # The other way a pass ends with nothing listed. No window of its own, so it backs out by
    # exactly what the pass had open: one press from the stash, two with a scav case under it.
    # A flat 1 here is what ended the run of 2026-08-20, so the scav case row is the regression.
    print('the price could not be read, so nothing was listed:')
    for source, escapes in (('inventory', sell_bot.INVENTORY_ESCAPES),
                            ('scav', sell_bot.SCAV_ESCAPES)):
        stats, pressed, raised = run_pass(False, source, escapes, price=None)
        assert raised is not None, f'{source}: the pass carried on without a price'
        assert stats['posted'] == 0, f'{source}: counted a sale with no price'
        assert stats[sell_bot.MONEY_STAT] == 0, f'{source}: added money for an unpriced offer'
        assert stats['price_missing'] == 1, f'{source}: not counted as a price failure'
        assert pressed == [escapes], (
            f'{source}: escaped {pressed}, wanted [{escapes}]. Escaping fewer times than the '
            f'pass has windows open leaves one up, and the offer creation window covers the '
            f'flea taskbar icon the next pass looks for')
        print(f'  ok  {source:10} {escapes} escapes, price failure, no sale, "{raised}"')

    print('ok, a pass that lists nothing costs a retry and a price failure, never a sale, '
          'and backs out of every window it opened')
