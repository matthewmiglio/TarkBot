"""A craft input needing several of one item is bought that many in one flea trip, on a shared budget.

Run:  python tests/hideout_craft_actions/test_craft_buy_quantity.py

App layer: interact/craft.py's quantity_to_buy (reads the 'have / need' fraction under an
ingredient icon) and buy_craft_input_item's quantity loop. The mouse, clock, matcher, flea and
the escape back to the station are all stubbed, so this is about how many buys go out and how the
two round-again budgets are spent, not about pixels.

What this pins:
  - quantity_to_buy turns the fraction crop that scored highest into need - have ('0/2' -> 2,
    '1/3' -> 2, '0/1' -> 1), and falls back to 1 when nothing clears QTY_FLOOR, so a row whose
    fraction will not read still buys the one unit the cross already proved is missing.
  - buy_craft_input_item(quantity=n) buys n and returns True only once all n are in the stash,
    the pre-filter opportunistic buy counting as one of them.
  - the dear and race budgets are shared across every unit, not reset per unit. This is the whole
    point of the nuance: four dear looks spent buying the first must leave only one before the
    second gives up, not a fresh five. A reset-per-unit budget would let a two-item buy sit on a
    dear board for twice as long.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from interact import craft  # noqa: E402

BUTTON = types.SimpleNamespace(left=1800, top=600, width=120, height=30)
MENU = types.SimpleNamespace(left=900, top=500, width=180, height=6)
CEILING = 50000
DEAR = CEILING + 1  # a top-offer price over the ceiling: a dear look
GOOD = CEILING - 1  # at or under: buyable


def buy_with(prices, buys, quantity=1, offers=True):
    """buy_craft_input_item where read_price answers `prices` in turn and buy answers `buys`.

    Returns (result, tries, presses, reads): result is True or the Unbuyable message, tries the
    purchase clicks that went out, presses the keys (board refreshes), reads how many prices were
    consumed. quantity_to_buy is stubbed to `quantity` so the fraction read is not what is under
    test here (its own read is exercised below); this is the buy loop given a count.
    """
    tries, presses, reads = [], [], []
    names = ('pyautogui', 'find', 'sell', 'snipe', 'time', 'return_to_station', '_open_item_menu',
             'quantity_to_buy')
    saved = {n: getattr(craft, n) for n in names}
    price_answers, buy_answers = list(prices), list(buys)

    def read_price(button):
        price = price_answers.pop(0) if price_answers else DEAR
        reads.append(price)
        return price

    def buy(button, region):
        tries.append(button)
        return buy_answers.pop(0) if buy_answers else False

    craft.pyautogui = types.SimpleNamespace(
        click=lambda *a: None, press=lambda key: presses.append(key),
        center=lambda b: (b.left + b.width / 2, b.top + b.height / 2), moveTo=lambda *a: None)
    craft.find = types.SimpleNamespace(find=lambda *a, **k: MENU, scale=lambda: 1.0)
    craft.sell = types.SimpleNamespace(jitter=lambda point, **k: point,
                                       apply_flea_filters=lambda *a, **k: True)
    craft.snipe = types.SimpleNamespace(
        purchase_buttons=lambda *a, **k: [BUTTON] if offers else [],
        read_price=read_price, buy=buy)
    now = {'t': 0.0}  # a moving clock so _top_offer's poll gives up rather than spinning

    def monotonic():
        now['t'] += 1.0
        return now['t']
    craft.time = types.SimpleNamespace(sleep=lambda s: None, monotonic=monotonic)
    craft.return_to_station = lambda *a, **k: True
    craft._open_item_menu = lambda *a, **k: MENU
    craft.quantity_to_buy = lambda *a, **k: quantity
    try:
        result = craft.buy_craft_input_item((100, 200), CEILING, quantity=quantity)
        return result, tries, presses, reads
    except craft.Unbuyable as e:
        return str(e), tries, presses, reads
    finally:
        for name, value in saved.items():
            setattr(craft, name, value)


def quantity_from(scores):
    """craft.quantity_to_buy with find.best_score stubbed to `scores` (a {target: score} map) and
    the screen grab stubbed away. Returns the count it read."""
    saved_find, saved_screen = craft.find, craft.screen
    craft.find = types.SimpleNamespace(
        scale=lambda: 1.0, best_score=lambda target, haystack=None: (scores.get(target, 0.0), None))
    craft.screen = types.SimpleNamespace(grab=lambda box: None)
    try:
        return craft.quantity_to_buy((100.0, 200.0))
    finally:
        craft.find, craft.screen = saved_find, saved_screen


if __name__ == '__main__':
    # 1. quantity_to_buy: the crop that scores highest names the count, as need - have.
    assert quantity_from({'crafting/0_of_2': 0.94, 'crafting/0_of_1': 0.80}) == 2, \
        '0/2 scoring highest means two still to buy'
    assert quantity_from({'crafting/1_of_3': 0.93, 'crafting/0_of_3': 0.71}) == 2, \
        '1/3 means three needed, one had, two to buy'
    assert quantity_from({'crafting/0_of_1': 0.91}) == 1, '0/1 is one to buy'
    # Nothing clears the floor: fall back to 1 rather than trust the loudest of a field of noise.
    assert quantity_from({'crafting/0_of_3': 0.3, 'crafting/1_of_2': 0.25}) == 1, \
        'below QTY_FLOOR must fall back to one, not the best of the noise'

    # 2. quantity=1 is the old behaviour exactly: one good offer, one buy, no refresh.
    result, tries, presses, _ = buy_with([GOOD], [True], quantity=1)
    assert result is True and len(tries) == 1 and presses == [], \
        f'a single buy regressed: {result}, {len(tries)} tries, presses {presses}'

    # 3. quantity=2, both offers good. The pre-filter look buys the first; the filtered board buys
    #    the second. Two buys, True, and the one refresh is the pre-filter board reload for unit 2.
    result, tries, presses, _ = buy_with([GOOD, GOOD], [True, True], quantity=2)
    assert result is True, f'buying two good offers should return True, got {result}'
    assert len(tries) == 2, f'wanted two buys, {len(tries)} went out'
    assert presses == [craft.REFRESH_KEY], f'expected one refresh between the two, got {presses}'

    # 4. The shared budget, the nuance itself. Buying two: the first unit is bought only after
    #    spending all but one of the dear budget, and the second must then give up on its next dear
    #    look rather than getting a fresh budget. So exactly DEAR_REFRESHES dear looks are spent in
    #    all, across both units, and only one item is ever bought.
    #
    #    Prices: a dear pre-filter look (falls through, uncounted), then DEAR_REFRESHES-1 dear looks
    #    (the budget for unit 1), a good one (buy unit 1), then dear forever. With a shared budget
    #    the run raises after one more dear look; with a per-unit reset it would sit for another
    #    whole DEAR_REFRESHES. read count tells the two apart.
    d = craft.DEAR_REFRESHES
    prices = [DEAR] + [DEAR] * (d - 1) + [GOOD] + [DEAR] * (d + 2)
    result, tries, presses, reads = buy_with(prices, [True], quantity=2)
    assert 'ceiling' in result, f'a board that stayed dear should raise over-ceiling, got {result!r}'
    assert len(tries) == 1, f'only the first unit should have been bought, got {len(tries)}'
    # 1 pre-filter read + (d-1) dear + 1 good + 2 more dear (one to reach the cap, one to trip it).
    expected_reads = 1 + (d - 1) + 1 + 2
    assert len(reads) == expected_reads, \
        (f'read {len(reads)} prices, expected {expected_reads}: the second unit got a fresh dear '
         f'budget instead of sharing the first unit\'s')

    print(f'ok: reads need-have off the fraction, buys that many in one trip, and the {d}-look dear '
          f'budget is shared across the units, not reset per item')
