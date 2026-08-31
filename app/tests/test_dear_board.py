"""An offer over the ceiling waits the board out instead of leaving on the first look, an
unreadable one is waited out the same way rather than looping the runner, and a cheap offer is
taken before the filters are even opened.

Run:  python tests/test_dear_board.py

No game needed: the menu, the filters, the board and the clock are all stubbed, so this is about
how many looks buy_craft_input_item takes and what it does between them.

Why this exists. Backing out on the first dear reading threw away the whole trip to that board.
Getting there is a right click, a 'filter by item', the filter window opened and set, and about
twenty seconds of waits, and the board it lands on is a live market that turns over constantly.
So a dear top offer now costs a DEAR_DELAY wait and a refresh, up to DEAR_REFRESHES times, and
only then gives up.

An unreadable price shares that budget rather than bailing at once. The run of 2026-08-31 clipped
the top price every look and buy_craft_input_item returned a quiet False, which step() ignored,
so the runner escaped to the station, read the same still-missing input, and bought it again pass
after pass forever. It now ends in Unbuyable like a dear board, which is what makes the runner
swap craft.

And the pre-filter look: the right click already narrows the board to the one item, so a cheap
enough top offer is bought there and then, before the filter window is opened. `filtered` records
whether apply_flea_filters was reached, so that shortcut can be told from the full flow.

The dear and race counters are separate on purpose and that is checked here too: a purchase that
loses a race to another buyer spends BUY_ATTEMPTS, a dear board spends DEAR_REFRESHES, and neither
eats the other's tries.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

from interact import craft, sell, snipe  # noqa: E402

BOX = (100, 200, 60, 20)


def run(prices, buys=None):
    """buy_craft_input_item against a board whose top offer reads `prices` in turn.

    The first price is the pre-filter look; the rest are read on the filtered board. `buys` is
    what snipe.buy answers each time it is called, defaulting to always succeeding. Returns
    (outcome, prices read, keys pressed, seconds slept, filtered), where outcome is True or the
    Unbuyable it raised and filtered says whether apply_flea_filters was reached.
    """
    read, keys, slept, filtered, bought = [], [], [], [], iter(buys or [True] * 20)
    supply = iter(prices)
    saved = (craft._open_item_menu, sell.apply_flea_filters, craft._top_offer, snipe.read_price,
             snipe.buy, craft.return_to_station, pyautogui.press, pyautogui.click, craft.time.sleep)

    def price_of(button):
        value = next(supply)
        read.append(value)
        return value

    def filters(*a, **k):
        filtered.append(True)
        return True

    craft._open_item_menu = lambda location, region=None, attempts=2: BOX
    sell.apply_flea_filters = filters
    craft._top_offer = lambda region=None: BOX
    snipe.read_price = price_of
    snipe.buy = lambda button, region: next(bought)
    craft.return_to_station = lambda c, region=None: None
    pyautogui.press = lambda key, **kw: keys.append(key)
    pyautogui.click = lambda *a, **kw: None
    craft.time.sleep = lambda seconds: slept.append(seconds)
    try:
        try:
            return craft.buy_craft_input_item((5, 5), 20000), read, keys, slept, bool(filtered)
        except craft.Unbuyable as e:
            return e, read, keys, slept, bool(filtered)
    finally:
        (craft._open_item_menu, sell.apply_flea_filters, craft._top_offer, snipe.read_price,
         snipe.buy, craft.return_to_station, pyautogui.press, pyautogui.click,
         craft.time.sleep) = saved


if __name__ == '__main__':
    # A cheap offer on the pre-filter look is bought there and then: the filter window is never
    # opened and the board is never refreshed. This is the shortcut.
    out, read, keys, slept, filtered = run([18888])
    assert out is True, f'a cheap offer was not bought: {out}'
    assert read == [18888], read
    assert not filtered, 'opened the filters for an offer already cheap enough before filtering'
    assert craft.REFRESH_KEY not in keys, f'refreshed a board it had already bought from: {keys}'
    print('  ok  cheap pre-filter    bought before filtering, no filter window, no refresh')

    # Dear before the filters, cheap after them. The pre-filter look is over the ceiling, so it
    # falls through, the filters go on, and the filtered board's top offer is cheap first look.
    out, read, keys, slept, filtered = run([25000, 19000])
    assert out is True, f'a filtered board that was cheap was not bought: {out}'
    assert read == [25000, 19000], read
    assert filtered, 'never opened the filters after the pre-filter look came back dear'
    assert craft.REFRESH_KEY not in keys, f'refreshed a board it bought on the first look: {keys}'
    print('  ok  dear pre-filter     filtered, then bought on the first filtered look')

    # Dear on the filtered board too, then cheap. This is the wait-it-out feature: a dear filtered
    # look costs a DEAR_DELAY wait and a refresh. Prices: the pre-filter look, a dear filtered
    # look, then a cheap one.
    out, read, keys, slept, filtered = run([25000, 25000, 19000])
    assert out is True, f'a board that got cheaper was not bought from: {out}'
    assert read == [25000, 25000, 19000], read
    assert keys.count(craft.REFRESH_KEY) == 1, f'refreshed {keys.count(craft.REFRESH_KEY)} times'
    assert craft.DEAR_DELAY in slept, f'did not wait for the board to turn over: {slept}'
    print('  ok  dear filtered board  waited, refreshed once, then bought')

    # Dear every look. The pre-filter look plus DEAR_REFRESHES + 1 filtered looks, then Unbuyable
    # rather than a quiet False, so the runner swaps craft.
    looks = craft.DEAR_REFRESHES + 1
    out, read, keys, slept, filtered = run([25000] * (looks + 4))
    assert isinstance(out, craft.Unbuyable), f'a permanently dear board did not raise: {out!r}'
    assert len(read) == looks + 1, f'{len(read)} looks, wanted {looks + 1} (one before the filters)'
    assert keys.count(craft.REFRESH_KEY) == craft.DEAR_REFRESHES, keys.count(craft.REFRESH_KEY)
    assert slept.count(craft.DEAR_DELAY) == craft.DEAR_REFRESHES, slept.count(craft.DEAR_DELAY)
    assert '25000' in str(out), f'{out}: the message has to carry the price that was too high'
    print(f'  ok  always dear         {looks + 1} looks, {craft.DEAR_REFRESHES} refreshes, '
          f'then Unbuyable')

    # Unreadable every look: the 2026-08-31 loop. Waited out on the dear budget and ended in
    # Unbuyable, not a quiet False the runner would ignore and re-buy on.
    out, read, keys, slept, filtered = run([None] * (looks + 4))
    assert isinstance(out, craft.Unbuyable), f'a permanently unreadable board did not raise: {out!r}'
    assert len(read) == looks + 1, f'{len(read)} looks, wanted {looks + 1}'
    assert keys.count(craft.REFRESH_KEY) == craft.DEAR_REFRESHES, keys.count(craft.REFRESH_KEY)
    assert 'unreadable' in str(out), f'{out}: the message has to say the price could not be read'
    print(f'  ok  always unreadable   {looks + 1} looks, {craft.DEAR_REFRESHES} refreshes, '
          f'then Unbuyable (not a quiet False)')

    # Unreadable, then readable and cheap: a clipped price is not the end, the board turns over on
    # a refresh. Pre-filter None, filtered None (wait, refresh), filtered cheap (buy).
    out, read, keys, slept, filtered = run([None, None, 19000])
    assert out is True, f'a board that became readable was not bought from: {out!r}'
    assert read == [None, None, 19000], read
    assert keys.count(craft.REFRESH_KEY) == 1, f'refreshed {keys.count(craft.REFRESH_KEY)} times'
    print('  ok  unreadable then cheap  refreshed, then bought once it read')

    # A cheap offer that keeps getting sniped spends BUY_ATTEMPTS, not DEAR_REFRESHES, and the two
    # counters do not borrow from each other. The pre-filter look is cheap too, so it takes one
    # buy attempt of its own: BUY_ATTEMPTS + 1 buys in all.
    tries = craft.BUY_ATTEMPTS + 1
    out, read, keys, slept, filtered = run([19000] * (tries + 3), buys=[False] * (tries + 3))
    assert isinstance(out, craft.Unbuyable), f'losing every race did not raise: {out!r}'
    assert len(read) == tries, f'{len(read)} buy attempts, wanted {tries}'
    assert craft.DEAR_DELAY not in slept, 'waited for a cheaper board over a lost race'
    print(f'  ok  lost every race     {tries} attempts (one before the filters), no dear wait')

    print('ok, the pre-filter look, the dear wait and the unreadable wait all behave, and the two '
          'retry counters stay separate')
