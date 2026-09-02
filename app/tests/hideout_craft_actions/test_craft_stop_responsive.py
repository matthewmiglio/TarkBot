"""Stop lands mid-buy: the flea buy flows check the runner's checkpoint and drop out at once.

Run:  python tests/hideout_craft_actions/test_craft_stop_responsive.py

App layer: interact/craft.py's buy_craft_input_item / buy_water_filter, and the `checkpoint`
they now take. craft_bot passes its _pause in as that checkpoint; _pause waits on the stop Event
and raises Stopped the instant Stop was pressed. Before this, a Stop pressed while buying an
input waited out the whole ~20s flea trip (open the menu, set the filters, read, retry the
purchase) because the buy flow's only Stop check sat between whole ingredients, never inside one.

What this pins, with the mouse/clock/matcher/flea all stubbed so it needs no game: the checkpoint
is actually called at the guarded points (before the menu, either side of the filter window,
between purchase attempts), and a checkpoint that raises there stops the flow before the next
action rather than after the buy. The counter is how many purchase clicks escaped; a Stop that
lands late shows up here as a buy that went out after the stop was asked for.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from interact import craft  # noqa: E402

BUTTON = types.SimpleNamespace(left=1800, top=600, width=120, height=30)
MENU = types.SimpleNamespace(left=900, top=500, width=180, height=6)
CEILING = 62000


class Stop(Exception):
    """Stand-in for sell_bot.Stopped: what a real _pause raises. craft.py re-raises whatever the
    checkpoint throws, so the type only has to be something buy_*_item does not itself catch."""


def _stub(price=50000, buys=(True,), offers=True):
    """Point craft's collaborators at fakes and return (restore, buys_list). buys answers snipe.buy
    in turn; buys_list records each purchase click that went out."""
    buys_out = []
    answers = list(buys)
    names = ('pyautogui', 'find', 'sell', 'snipe', 'time', 'return_to_station', '_open_item_menu')
    saved = {n: getattr(craft, n) for n in names}

    def buy(button, region):
        buys_out.append(button)
        return answers.pop(0) if answers else False

    now = {'t': 0.0}

    def monotonic():
        now['t'] += 1.0
        return now['t']

    craft.pyautogui = types.SimpleNamespace(click=lambda *a: None, press=lambda k: None,
                                            center=lambda b: (b.left, b.top))
    craft.find = types.SimpleNamespace(find=lambda *a, **k: MENU, scale=lambda: 1.0)
    craft.sell = types.SimpleNamespace(jitter=lambda p, **k: p, apply_flea_filters=lambda *a, **k: True)
    craft.snipe = types.SimpleNamespace(purchase_buttons=lambda *a, **k: [BUTTON] if offers else [],
                                        read_price=lambda b: price, buy=buy)
    craft.time = types.SimpleNamespace(sleep=lambda s: None, monotonic=monotonic)
    craft.return_to_station = lambda *a, **k: True
    craft._open_item_menu = lambda *a, **k: MENU

    def restore():
        for name, value in saved.items():
            setattr(craft, name, value)
    return restore, buys_out


def raise_on(n):
    """A checkpoint that raises Stop on its n-th call (1-based), counting like _pause: each call is
    a Stop check. Returns (checkpoint, calls) so the test can see how far the flow got."""
    calls = {'n': 0}

    def checkpoint(seconds=0):
        calls['n'] += 1
        if calls['n'] >= n:
            raise Stop()
    return checkpoint, calls


if __name__ == '__main__':
    # 1. Stop before we even open the menu: first checkpoint raises, nothing is bought, and the
    #    flow never reaches _open_item_menu.
    restore, buys = _stub()
    checkpoint, _ = raise_on(1)
    opened = []
    craft._open_item_menu = lambda *a, **k: opened.append(1) or MENU
    try:
        craft.buy_craft_input_item((100, 200), CEILING, checkpoint=checkpoint)
        raised = False
    except Stop:
        raised = True
    finally:
        restore()
    assert raised, 'a Stop at the very first checkpoint should have propagated out'
    assert buys == [], 'bought something after Stop was pressed before the buy even started'
    assert opened == [], 'opened the flea menu after Stop was pressed first'

    # 2. Stop is checked on both sides of the filter window. With a price already under the ceiling
    #    the pre-filter look would buy at once, so raise before that (checkpoint 1 is entry). Push
    #    the raise to a later call and confirm no purchase escaped once Stop was asked for: however
    #    many checks the flow makes, a raising one must end it with zero buys still going out.
    for stop_at in (2, 3, 4):
        restore, buys = _stub(price=CEILING + 1)  # over ceiling: no pre-filter buy, reaches filters
        checkpoint, calls = raise_on(stop_at)
        try:
            craft.buy_craft_input_item((100, 200), CEILING, checkpoint=checkpoint)
        except (Stop, craft.Unbuyable):
            pass
        finally:
            restore()
        assert buys == [], f'a Stop at checkpoint {stop_at} still let {len(buys)} purchase(s) out'
        assert calls['n'] >= stop_at, f'checkpoint fired {calls["n"]} times, expected >= {stop_at}'

    # 3. The default checkpoint never stops: a normal buy still goes through with no checkpoint
    #    passed, so an ordinary run is untouched by the new arg.
    restore, buys = _stub(buys=(True,))
    try:
        result = craft.buy_craft_input_item((100, 200), CEILING)
    finally:
        restore()
    assert result is True, f'the default (no-stop) checkpoint broke an ordinary buy: {result}'
    assert len(buys) == 1, f'ordinary buy went out {len(buys)} times, expected once'

    # 4. The water-filter flow takes the same checkpoint. A Stop before it opens the board buys
    #    nothing.
    restore, buys = _stub()
    craft.snipe.open_clean_board = lambda *a, **k: True
    checkpoint, _ = raise_on(1)
    try:
        craft.buy_water_filter(CEILING, checkpoint=checkpoint)
        raised = False
    except Stop:
        raised = True
    finally:
        restore()
    assert raised, 'a Stop at the first checkpoint of buy_water_filter should propagate'
    assert buys == [], 'the water-filter flow bought after Stop was pressed'

    print('ok: Stop lands mid-buy (before the menu, around the filters, between attempts); '
          'the default checkpoint leaves an ordinary buy unchanged')
