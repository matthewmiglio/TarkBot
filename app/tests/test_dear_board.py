"""An offer over the ceiling waits the board out instead of leaving on the first look.

Run:  python tests/test_dear_board.py

No game needed: the menu, the filters, the board and the clock are all stubbed, so this is about
how many looks buy_craft_input_item takes and what it does between them.

Why this exists. Backing out on the first dear reading threw away the whole trip to that board.
Getting there is a right click, a 'filter by item', the filter window opened and set, and about
twenty seconds of waits, and the board it lands on is a live market that turns over constantly.
So a dear top offer now costs a DEAR_DELAY wait and a refresh, up to DEAR_REFRESHES times, and
only then gives up.

The two counters are separate on purpose and that is checked here too: a purchase that loses a
race to another buyer spends BUY_ATTEMPTS, a dear board spends DEAR_REFRESHES, and neither eats
the other's tries.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

from interact import craft, sell, snipe  # noqa: E402

BOX = (100, 200, 60, 20)


def run(prices, buys=None):
    """buy_craft_input_item against a board whose top offer reads `prices` in turn.

    `buys` is what snipe.buy answers each time it is called, defaulting to always succeeding.
    Returns (outcome, prices read, keys pressed, seconds slept). outcome is True/False, or the
    Unbuyable it raised.
    """
    read, keys, slept, bought = [], [], [], iter(buys or [True] * 20)
    supply = iter(prices)
    saved = (craft._open_item_menu, sell.apply_flea_filters, craft._top_offer, snipe.read_price,
             snipe.buy, craft.return_to_station, pyautogui.press, pyautogui.click, craft.time.sleep)

    def price_of(button):
        value = next(supply)
        read.append(value)
        return value

    craft._open_item_menu = lambda location, region=None, attempts=2: BOX
    sell.apply_flea_filters = lambda *a, **k: True
    craft._top_offer = lambda region=None: BOX
    snipe.read_price = price_of
    snipe.buy = lambda button, region: next(bought)
    craft.return_to_station = lambda c, region=None: None
    pyautogui.press = lambda key, **kw: keys.append(key)
    pyautogui.click = lambda *a, **kw: None
    craft.time.sleep = lambda seconds: slept.append(seconds)
    try:
        try:
            return craft.buy_craft_input_item((5, 5), 20000), read, keys, slept
        except craft.Unbuyable as e:
            return e, read, keys, slept
    finally:
        (craft._open_item_menu, sell.apply_flea_filters, craft._top_offer, snipe.read_price,
         snipe.buy, craft.return_to_station, pyautogui.press, pyautogui.click,
         craft.time.sleep) = saved


if __name__ == '__main__':
    # A cheap offer on the first look is bought, and the board is never refreshed.
    out, read, keys, _ = run([18888])
    assert out is True, f'a cheap offer was not bought: {out}'
    assert read == [18888], read
    assert craft.REFRESH_KEY not in keys, f'refreshed a board it had already bought from: {keys}'
    print('  ok  cheap first look   bought, no refresh')

    # Dear, then cheap. One wait, one refresh, then the buy. This is the whole feature: the old
    # code left on the first reading and paid twenty seconds to come back to this same board.
    out, read, keys, slept = run([25000, 19000])
    assert out is True, f'a board that got cheaper was not bought from: {out}'
    assert read == [25000, 19000], read
    assert keys.count(craft.REFRESH_KEY) == 1, f'refreshed {keys.count(craft.REFRESH_KEY)} times'
    assert craft.DEAR_DELAY in slept, f'did not wait for the board to turn over: {slept}'
    print('  ok  dear then cheap    waited, refreshed once, then bought')

    # Dear every time. DEAR_REFRESHES refreshes, so DEAR_REFRESHES + 1 looks in all, and then
    # Unbuyable rather than a quiet False: the runner swaps craft on it.
    looks = craft.DEAR_REFRESHES + 1
    out, read, keys, slept = run([25000] * (looks + 3))
    assert isinstance(out, craft.Unbuyable), f'a permanently dear board did not raise: {out!r}'
    assert len(read) == looks, f'{len(read)} looks, wanted {looks}'
    assert keys.count(craft.REFRESH_KEY) == craft.DEAR_REFRESHES, keys.count(craft.REFRESH_KEY)
    assert slept.count(craft.DEAR_DELAY) == craft.DEAR_REFRESHES, slept.count(craft.DEAR_DELAY)
    assert '25000' in str(out), f'{out}: the message has to carry the price that was too high'
    print(f'  ok  always dear        {looks} looks, {craft.DEAR_REFRESHES} refreshes, '
          f'then Unbuyable')

    # An unreadable price is not a market condition, so there is nothing to wait for: out at
    # once, and False rather than Unbuyable, since the runner treats those differently.
    out, read, keys, _ = run([None, 1])
    assert out is False, f'an unreadable price did not come back False: {out!r}'
    assert read == [None], f'kept refreshing a price it cannot read: {read}'
    print('  ok  unreadable price   out on the first look, no refresh')

    # A cheap offer that keeps getting sniped spends BUY_ATTEMPTS, not DEAR_REFRESHES, and the
    # two counters do not borrow from each other.
    out, read, keys, slept = run([19000] * (craft.BUY_ATTEMPTS + 3),
                                 buys=[False] * (craft.BUY_ATTEMPTS + 3))
    assert isinstance(out, craft.Unbuyable), f'losing every race did not raise: {out!r}'
    assert len(read) == craft.BUY_ATTEMPTS, f'{len(read)} buy attempts, wanted {craft.BUY_ATTEMPTS}'
    assert craft.DEAR_DELAY not in slept, 'waited for a cheaper board over a lost race'
    print(f'  ok  lost every race    {craft.BUY_ATTEMPTS} attempts, no dear wait')

    print('ok, a dear board is waited out and the two retry counters stay separate')
