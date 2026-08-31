"""A craft input that loses the race to another buyer is retried on the same board, up to six.

Run:  python tests/test_craft_buy_retry.py

No game needed. The mouse, the clock, the matcher, the flea and the escape back to the station
are stubbed, so this is about how many buys go out and what comes back, not about pixels.

What this pins. snipe.buy already answers whether the money actually left the stash, read off
the rouble balance either side of the click, so an offer someone else took a moment earlier
comes back False rather than as a silent nothing. buy_craft_input_item threw that answer away
and returned it unlooked at: the runner escaped to the station, saw the ingredient still
missing, and started the whole right click -> filter by item -> apply filters trip again, about
twenty seconds to arrive back at the board it had just left.

Now it refreshes in place and goes again. The two things worth guarding are the cap, since a
loop that retries a board forever never returns and the run just stops, and that running out of
tries raises Unbuyable: that is what makes the runner leave this ingredient and go tend
another craft, exactly as it does for an offer over the ceiling.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from interact import craft  # noqa: E402

BUTTON = types.SimpleNamespace(left=1800, top=600, width=120, height=30)
MENU = types.SimpleNamespace(left=900, top=500, width=180, height=6)
CEILING = 62000


def buy_with(buys, price=50000, offers=True):
    """Run buy_craft_input_item where snipe.buy answers `buys` in turn. (result, buys, presses).

    result is True/False, or the Unbuyable message when it raised, so the three reasons that
    share that exception can be told apart here the same way they are told apart in a log. buys
    is how many purchase clicks went out, presses are the keys pressed (the board refreshes).
    """
    tries, presses = [], []
    names = ('pyautogui', 'find', 'sell', 'snipe', 'time', 'return_to_station', '_open_item_menu')
    saved = {n: getattr(craft, n) for n in names}
    answers = list(buys)

    def buy(button, region):
        tries.append(button)
        return answers.pop(0) if answers else False

    craft.pyautogui = types.SimpleNamespace(
        click=lambda *a: None, press=lambda key: presses.append(key),
        center=lambda b: (b.left + b.width / 2, b.top + b.height / 2))
    craft.find = types.SimpleNamespace(find=lambda *a, **k: MENU, scale=lambda: 1.0)
    craft.sell = types.SimpleNamespace(jitter=lambda point, **k: point,
                                       apply_flea_filters=lambda *a, **k: True)
    craft.snipe = types.SimpleNamespace(
        purchase_buttons=lambda *a, **k: [BUTTON] if offers else [],
        read_price=lambda b: price, buy=buy)
    # A monotonic that moves on every read. It has to move: _top_offer polls until OFFER_WAIT
    # has passed, so a frozen clock makes the empty-board case spin forever instead of failing.
    now = {'t': 0.0}

    def monotonic():
        now['t'] += 1.0
        return now['t']
    craft.time = types.SimpleNamespace(sleep=lambda s: None, monotonic=monotonic)
    craft.return_to_station = lambda *a, **k: True
    craft._open_item_menu = lambda *a, **k: MENU
    try:
        return craft.buy_craft_input_item((100, 200), CEILING), tries, presses
    except craft.Unbuyable as e:
        return str(e), tries, presses
    finally:
        for name, value in saved.items():
            setattr(craft, name, value)


if __name__ == '__main__':
    # A purchase that lands first time costs one buy and no refresh. The retry must not make the
    # normal case slower.
    result, tries, presses = buy_with([True])
    assert result is True, f'a landed purchase should return True, got {result}'
    assert len(tries) == 1, f'bought {len(tries)} times when once was enough'
    assert presses == [], f'refreshed a board it had no reason to refresh: {presses}'

    # A lost race is retried, and the buy that finally lands still returns True. The first attempt
    # is the pre-filter look, which does not refresh (it goes on to set the filters); the lost
    # race on the filtered board refreshes before its retry. Three attempts, one refresh.
    result, tries, presses = buy_with([False, False, True])
    assert result is True, f'the third attempt bought it, got {result}'
    assert len(tries) == 3, f'expected three attempts, got {len(tries)}'
    assert presses == [craft.REFRESH_KEY], f'wrong refreshes between attempts: {presses}'

    # The cap. A board that never sells is not retried forever: BUY_ATTEMPTS on the filtered
    # board, then out. The pre-filter look is a lost race of its own, so BUY_ATTEMPTS + 1 buys go
    # out in all, and the filtered board refreshes between its retries. A loop with no cap here
    # does not fail, it simply never returns.
    result, tries, presses = buy_with([False] * 20)
    assert 'attempts' in result, f'being outbid should say so, said {result!r}'
    assert len(tries) == craft.BUY_ATTEMPTS + 1, \
        f'{len(tries)} attempts is not the {craft.BUY_ATTEMPTS} cap plus the pre-filter look'
    assert len(presses) == craft.BUY_ATTEMPTS - 1, f'wrong refresh count: {presses}'
    outbid = result

    # An offer over the ceiling buys nothing: it spends the dear budget (a refresh may bring a
    # cheaper offer) and never the race budget, so no purchase click goes out, and then raises.
    result, tries, presses = buy_with([True], price=CEILING + 1)
    assert 'ceiling' in result, f'an over-ceiling offer should say so, said {result!r}'
    assert tries == [], f'bought at a price over the ceiling: {len(tries)} times'
    dear = result

    # An unreadable price is no longer bailed on at once: the board is a live market, so it is
    # waited out on the dear budget and then raises Unbuyable, the same as a permanently dear
    # board. Before 2026-08-31 it returned a quiet False the runner ignored and re-bought on.
    result, tries, _ = buy_with([True], price=None)
    assert 'unreadable' in result, f'an unreadable board should say so, said {result!r}'
    assert tries == [], 'bought at a price it could not read'
    unreadable = result

    # No PURCHASE button on any row: a trader whose per-hour limit is spent shows its offer as
    # LOCKED, at a price that still reads as a bargain, so a bot that waits on it waits until the
    # hour turns over. Handed back like an over-ceiling offer, and answered at once rather than
    # after six refreshes of a board that has nothing to click.
    result, tries, presses = buy_with([True], offers=False)
    assert 'PURCHASE' in result, f'a locked board should say so, said {result!r}'
    assert tries == [] and presses == [], f'retried a board with nothing to buy: {presses}'
    locked = result

    # The three share one exception so the runner answers them alike, and that is the whole
    # reason they must not share a message. A trader whose hourly limit is spent is sat there at
    # a price that is perfectly good, and reading a run back afterwards, this string is the only
    # thing that says so rather than "the power cord was too expensive again".
    assert len({dear, locked, outbid, unreadable}) == 4, \
        f'two of these read the same in a log: {dear!r}, {locked!r}, {outbid!r}, {unreadable!r}'
    assert 'ceiling' not in locked and 'ceiling' not in outbid, \
        'a locked or an outbid ingredient must never be reported as too expensive'

    print(f'ok: retries a lost race in place, capped at {craft.BUY_ATTEMPTS}, and the four ways '
          f'of giving up read differently')
