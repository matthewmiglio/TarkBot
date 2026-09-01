"""A water filter offer lost to another buyer is tried again, not given up on.

Run:  python tests/hideout_craft_actions/test_water_buy_race.py

App layer: interact/craft.py's buy_water_filter, the collector's flea-buy action, and its
race-retry loop (WATER_BUY_ATTEMPTS tries, WATER_BUY_RETRY_DELAY between them, and no board
refresh, unlike buy_craft_input_item). A craft-actions test with the flea, board, price and
clock all stubbed, so it needs no game.

No game needed: the flea, the board, the price and the clock are all stubbed, so this is about
how many tries buy_water_filter takes and what it waits between them.

Why this exists. On 2026-08-31 the collector found a water filter at 59,000 against a 70,000
ceiling, clicked purchase, and the confirmation dialog closed by itself with the rouble balance
untouched. snipe.buy reports that honestly as False, and buy_water_filter took it as the end of
the matter: back to the station, collector left empty, nothing bought for a whole lap. The board
still had eleven more filters on it between 61,111 and 64,000.

Losing a race is not a fault, it is Monday on a busy board, so it is worth five goes. And no
refresh between them, unlike buy_craft_input_item's dear-board loop: that one waits for the
market to move and must reload to see it, this one is racing for rows already on screen and a
reload would only throw them away. That difference is asserted here, because the two loops look
alike and the wrong one was copied once already.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

from interact import craft, sell, snipe  # noqa: E402

BOX = (100, 200, 60, 20)
CEILING = 70000
WINDOW = (0, 0, 2560, 1440)  # a 1440p screen, so the park's fractions land somewhere checkable


def run(buys, price=59000):
    """buy_water_filter against a board whose purchase clicks answer `buys` in turn.

    Returns (outcome, buy attempts, keys pressed, seconds slept).
    """
    tries, keys, slept, parked = [], [], [], []
    answers = iter(buys)
    saved = (snipe.open_clean_board, sell.apply_flea_filters, snipe.remove_filter_by_item_filter,
             snipe.find_search_box, snipe.search_for, snipe.purchase_buttons, snipe.read_price,
             snipe.buy, craft.return_to_station, pyautogui.press, pyautogui.moveTo,
             craft.screen.rect, craft.time.sleep)

    def buy(button, region):
        answer = next(answers)
        tries.append(answer)
        return answer

    snipe.open_clean_board = lambda region=None: True
    sell.apply_flea_filters = lambda *a, **k: True
    snipe.remove_filter_by_item_filter = lambda region=None: False
    snipe.find_search_box = lambda region=None, last=None: BOX
    snipe.search_for = lambda name, box, region=None: BOX
    snipe.purchase_buttons = lambda region=None: [BOX]
    snipe.read_price = lambda button: price
    snipe.buy = buy
    craft.return_to_station = lambda c, region=None: None
    pyautogui.press = lambda key, **kw: keys.append(key)
    pyautogui.moveTo = lambda *point, **kw: parked.append(point)
    craft.screen.rect = lambda: WINDOW  # so the park has a window to take its fractions of
    craft.time.sleep = lambda seconds: slept.append(seconds)
    try:
        return craft.buy_water_filter(CEILING), tries, keys, slept, parked
    finally:
        (snipe.open_clean_board, sell.apply_flea_filters, snipe.remove_filter_by_item_filter,
         snipe.find_search_box, snipe.search_for, snipe.purchase_buttons, snipe.read_price,
         snipe.buy, craft.return_to_station, pyautogui.press, pyautogui.moveTo,
         craft.screen.rect, craft.time.sleep) = saved


if __name__ == '__main__':
    # Bought first time: one attempt, and no waiting around for a race that never happened.
    # Note WATER_BUY_RETRY_DELAY and BOUGHT_SETTLE are both 2.0s, so a bare "was 2.0 slept"
    # cannot tell a retry wait from the settle after a purchase. The attempt count is the
    # unambiguous signal and the sleeps are counted rather than searched.
    assert craft.WATER_BUY_RETRY_DELAY == craft.BOUGHT_SETTLE, \
        'these two have diverged, so these asserts can name them separately now'
    out, tries, keys, slept, parked = run([True])
    assert out is True, f'a clean purchase did not come back True: {out!r}'
    assert len(tries) == 1, f'{len(tries)} purchase clicks for one clean buy: {tries}'
    assert slept.count(craft.BOUGHT_SETTLE) == 1, \
        f'a purchase that worked first go should sleep once, the settle: {slept}'
    print('  ok  bought first go   one attempt, no retry wait')

    # Lost one race, then bought. This is the whole feature: the old code stopped at the False.
    out, tries, keys, slept, parked = run([False, True])
    assert out is True, f'a second attempt that bought did not come back True: {out!r}'
    assert len(tries) == 2, f'{len(tries)} purchase clicks, wanted 2: {tries}'
    # One retry wait plus the settle after the buy that landed, and they are the same duration.
    assert slept.count(craft.WATER_BUY_RETRY_DELAY) == 2, \
        f'wanted one retry wait and one settle: {slept}'
    print('  ok  lost one race     waited once, went again, bought')

    # Lost every race. Exactly WATER_BUY_ATTEMPTS tries with a wait between each pair, so one
    # fewer wait than tries, and False rather than a raise: nothing is broken, the board was
    # just busy, and the runner comes back next lap.
    n = craft.WATER_BUY_ATTEMPTS
    out, tries, keys, slept, parked = run([False] * (n + 3))
    assert out is False, f'losing every race did not come back False: {out!r}'
    assert len(tries) == n, f'{len(tries)} attempts, wanted {n}'
    # n - 1 waits and no settle, since nothing was ever bought.
    assert slept.count(craft.WATER_BUY_RETRY_DELAY) == n - 1, \
        f'wanted {n - 1} retry waits and no settle: {slept}'
    print(f'  ok  lost every race   {n} attempts, {n - 1} waits, then False')

    # No refresh, ever. buy_craft_input_item reloads the board between looks and this must not:
    # the offers being raced for are already drawn, and REFRESH_KEY would discard them.
    assert craft.REFRESH_KEY not in keys, f'refreshed the board between races: {keys}'
    print(f'  ok  no refresh        never pressed {craft.REFRESH_KEY.upper()}, unlike the dear-'
          f'board loop')

    # An offer over the ceiling is still one look and out. Racing is for offers worth having.
    out, tries, keys, slept, parked = run([True], price=CEILING + 1)
    assert out is False, f'an offer over the ceiling was bought: {out!r}'
    assert tries == [], f'clicked purchase on an offer over the ceiling: {tries}'
    print('  ok  over the ceiling  not bought, and not retried either')

    # The cursor comes off the board between attempts. A PURCHASE button with the pointer on it
    # is drawn hovered, no crop matches it, and the next look silently takes the row underneath
    # (which on a cheapest-first board is always dearer than the one that went missing).
    out, tries, keys, slept, parked = run([False, True])
    assert len(parked) == 1, f'wanted one park between the two attempts: {parked}'
    x, y = parked[0]
    assert x < WINDOW[2] // 2, f'parked at x={x}, which is not the left half of {WINDOW[2]}'
    assert 0 < y < WINDOW[3], f'parked at y={y}, off the window'
    print(f'  ok  parked           cursor to {parked[0]}, left middle, between attempts')

    out, tries, keys, slept, parked = run([True])
    assert parked == [], f'parked after a purchase that worked, with nothing to re-read: {parked}'
    print('  ok  no needless park  a clean buy never moves the cursor')

    print('ok, a lost race is retried five times without refreshing, then left for next lap')
