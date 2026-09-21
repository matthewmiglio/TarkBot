"""The bitcoin farm's pass: a lit GET ITEMS is collected, a greyed one is left, and either way
the runner swaps.

Run:  python tests/hideout_craft_actions/test_bitcoin_farm.py

App layer: craft_bot.HideoutCraft.step's bitcoin branch and the _collect_if_lit helper it shares
with the water collector. The matcher, the mouse and the clock are stubbed, so this is about
which steps run, not about pixels. No game needed.

What this pins, and it is the whole reason the branch is not just the state machine: the farm has
no START, no ingredient row and no output crop, so craft.read_craft cannot be run over it at all.
Route it down the normal path and read_craft raises LookupError on a missing output, which is in
craft_bot's auto-restart tuple: the farm would restart the game every lap.

Three states, and the last two are load-bearing. A lit button is clicked once and books the
532,000 roubles. A greyed one, and a panel with no button on it at all, are both clicked *nowhere*
and book nothing, because a click there would book profit every single pass for a bitcoin that
never arrived. All three swap, so the farm can never hold the cycle.

The no-button case is the farm's real resting state and is here because of it: measured on the
laptop on 2026-09-21, collecting a bitcoin does not grey the button, it removes it, and the row
goes back to a timer ('Farming (42:15:07)...', 0/3 bitcoins). So the branch that runs on nearly
every pass is the absent one, not the greyed one, and the greyed case is kept only because
get_items_highlighted is what stands between a dim button and a false collect.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402

BUTTON = types.SimpleNamespace(left=1700, top=500, width=120, height=26)


def run_pass(lit, present=True):
    """One step() over the bitcoin farm with GET ITEMS in the given state. present False is no
    button on the panel at all, which is the farm's resting state (see main).

    object.__new__ rather than the real __init__, which wants a window and a monitor, neither of
    which is what this turns on. Returns (clicks, swaps, stats).
    """
    bot = object.__new__(craft_bot.HideoutCraft)
    bot.jobs = [craft_bot.CraftJob(craft.BITCOIN, {}, {})]
    bot.index = 0
    bot.region = (0, 0, 1920, 1080)
    bot.stats = dict.fromkeys(('total_started', 'total_profit', 'profit:bitcoin',
                               'started:bitcoin'), 0)
    clicks, swaps = [], []
    bot._ensure_on = lambda job: None
    bot._swap = lambda: swaps.append(True)
    bot._pause = lambda seconds=0: None
    bot._park = lambda point: None

    saved = {n: getattr(craft_bot, n) for n in ('find', 'sell', 'pyautogui')}
    saved_craft = {n: getattr(craft, n) for n in ('get_items_highlighted', 'check_stash_full')}
    craft_bot.find = types.SimpleNamespace(find=lambda *a, **k: BUTTON if present else None)
    craft_bot.sell = types.SimpleNamespace(jitter=lambda point, **k: point)
    craft_bot.pyautogui = types.SimpleNamespace(
        click=lambda *point: clicks.append(point),
        center=lambda b: (b.left + b.width // 2, b.top + b.height // 2))
    craft.get_items_highlighted = lambda box: lit
    craft.check_stash_full = lambda region=None: False
    try:
        bot.step()
    finally:
        for name, value in saved.items():
            setattr(craft_bot, name, value)
        for name, value in saved_craft.items():
            setattr(craft, name, value)
    return clicks, swaps, bot.stats


def main():
    assert craft.BITCOIN_NAME in craft.CRAFTS, 'the farm is not in craft.CRAFTS'
    assert craft.BITCOIN.ingredients == (), 'the farm buys nothing; it must have no ingredients'

    clicks, swaps, stats = run_pass(lit=True)
    print(f'lit:    clicks={clicks} swaps={len(swaps)} profit={stats["profit:bitcoin"]}')
    assert len(clicks) == 1, f'a lit GET ITEMS should be clicked once, got {clicks}'
    assert stats['profit:bitcoin'] == craft_bot.PROFIT_PER_CRAFT['bitcoin'], stats
    assert stats['total_profit'] == craft_bot.PROFIT_PER_CRAFT['bitcoin'], stats
    assert len(swaps) == 1, 'a collected farm must still swap'

    for label, kwargs in (('greyed', {'lit': False}), ('absent', {'lit': False, 'present': False})):
        clicks, swaps, stats = run_pass(**kwargs)
        print(f'{label}: clicks={clicks} swaps={len(swaps)} profit={stats["profit:bitcoin"]}')
        assert clicks == [], f'a {label} GET ITEMS must not be clicked, got {clicks}'
        assert stats['profit:bitcoin'] == 0, f'nothing collected, so nothing may be booked: {stats}'
        assert stats['total_profit'] == 0, stats
        assert len(swaps) == 1, 'a farm with nothing ready must swap rather than sit there'

    print('OK')


if __name__ == '__main__':
    main()
