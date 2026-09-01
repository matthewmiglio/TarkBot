"""A read that comes back empty for something the game is drawing stops the run, and the row is
only read once a pass.

App layer under test: interact/craft.py's one-shot row READ, craft.read_craft, and the
craft.Blind it raises when an ingredient icon (or the water-collector filter slot) is missing from
a row the game is drawing. Also the craft_bot.HideoutCraft.step branch that lets Blind out while
still swapping crafts on a LookupError. This is the read layer plus the runner's reaction to it,
not navigation and not buying.

What it verifies: one read answers the state, frames the row and queues the inputs; the expensive
timer+output pair is searched once (not four times) a pass; a missing ingredient icon raises Blind
naming the crop folder; Blind is not a LookupError so step() cannot swallow it; step() swaps on
LookupError but propagates Blind; and the water collector slot reads fitted/empty as answers while
neither-or-both is Blind.

No game needed: find and get_items_highlighted are stubbed, so this is about what the pass does
with the answers rather than whether anything matches pixels.

Run:  python tests/hideout_craft_reads/test_craft_blind.py

Why this exists. On 2026-08-30 the crops for crafting/green_gunpowder stopped matching. craft_plan
reported the input as "not ready, nowhere to click", buy_input logged one line and returned False,
and step() only swapped on Unbuyable or LookupError, so the pass fell through to "still missing,
will retry" and did the identical thing every seven seconds for seven minutes. Nothing was
clicked, nothing was bought and nothing was raised. craft.Blind is what that failure raises now,
and step() does not catch it.

The second half is the cost of that same pass. It searched the row four times: once for the
state, twice inside craft_plan, and the whole of craft_plan again through validate_craftable
after buying. Each search is a find_all of the timer icon plus one of the output item, so 4.4 of
a 7.1 second lap went on re-answering a settled question. read_craft does it once.
"""
import sys
import types
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import craft_bot  # noqa: E402
from interact import craft, find  # noqa: E402

BOX = types.SimpleNamespace(left=100, top=200, width=60, height=20)
CRAFT = craft.CRAFTS['red_gunpowder']  # green gunpowder + matches, the craft that looped


def stub_find(present, counts):
    """A find/find_all pair answering from `present` (target -> box or None), tallying into
    `counts` so the number of searches a pass makes can be asserted on."""
    def one(name, region=None, **kw):
        counts[name] += 1
        return present.get(name)

    def many(name, region=None, **kw):
        counts[name] += 1
        box = present.get(name)
        return [box] if box else []
    return one, many


def read_with(present):
    """(what read_craft did, how many times each target was searched)."""
    counts = Counter()
    saved = (find.find, find.find_all, find.scale, craft.get_items_highlighted)
    find.find, find.find_all = stub_find(present, counts)
    find.scale = lambda: 1.0
    craft.get_items_highlighted = lambda box, threshold=None: True
    try:
        return craft.read_craft(CRAFT, (0, 0, 2560, 1440)), counts
    finally:
        (find.find, find.find_all, find.scale, craft.get_items_highlighted) = saved


if __name__ == '__main__':
    green, matches = CRAFT.ingredients[0].target, CRAFT.ingredients[1].target

    # Everything on screen: one read answers the state, frames the row and queues the inputs.
    ready = {craft.TIMER_TARGET: BOX, CRAFT.output_target: BOX, craft.START_TARGET: BOX,
             craft.CHECK_TARGET: BOX, green: BOX, matches: BOX}
    read, counts = read_with(ready)
    assert read.state == 'ready', read.state
    assert read.start is BOX, 'the START box has to come back, or start_craft searches again'
    assert [name for name, _, _ in read.inputs] == ['green_gunpowder', 'matches'], read.inputs
    print(f'  ok  ready            state, START box and {len(read.inputs)} inputs from one read')

    # The expensive pair is searched once, not four times. This is the 4.4 seconds.
    assert counts[craft.TIMER_TARGET] == 1, f'timer searched {counts[craft.TIMER_TARGET]}x'
    assert counts[CRAFT.output_target] == 1, f'output searched {counts[CRAFT.output_target]}x'
    print('  ok  one look          timer icon and output item searched once each')

    # An ingredient icon missing from a row the game is drawing is Blind, not "not ready". This
    # is the exact 2026-08-30 failure.
    blind = dict(ready, **{green: None})
    try:
        read_with(blind)
    except craft.Blind as e:
        assert 'green_gunpowder' in str(e), e
        assert green in str(e), f'{e}: the message has to name the folder to go and look at'
    else:
        raise AssertionError('a missing ingredient icon did not raise Blind')
    print('  ok  missing icon      raises Blind and names the crop folder')

    # Blind is not a LookupError, or step()'s catch would swallow it back into a swap.
    assert not issubclass(craft.Blind, LookupError), \
        'Blind must not be a LookupError: step() catches those and swaps, which is the loop'
    print('  ok  not a LookupError step() cannot swallow it into a swap')

    # And the runner really does let it out. A stubbed pass whose buy raises Blind must not be
    # caught, while one raising LookupError still swaps.
    def step_raising(error):
        did = []
        runner = object.__new__(craft_bot.HideoutCraft)
        runner.jobs = [types.SimpleNamespace(craft=CRAFT, max_prices={}, sources={})]
        runner.index, runner.region = 0, None
        runner._ensure_on = lambda job: None
        runner._pause = lambda *a: None
        runner._swap = lambda: did.append('swap')
        runner.start_craft = lambda job, read: did.append('start')

        def buy(job, item, location):
            raise error

        runner.buy_input = buy
        saved = craft.read_craft
        craft.read_craft = lambda *a, **k: craft.CraftRead(
            state='ready', output=None, band=None, start=None, get_items=None,
            inputs=[('green_gunpowder', False, (500, 400))])
        try:
            runner.step()
            return did
        finally:
            craft.read_craft = saved

    assert step_raising(LookupError('no menu')) == ['swap'], 'a menu that would not open must swap'
    try:
        step_raising(craft.Blind('green_gunpowder icon is not on the row'))
    except craft.Blind:
        pass
    else:
        raise AssertionError('step() swallowed a Blind, so the run would loop instead of stopping')
    print('  ok  step()            swaps on LookupError, stops on Blind')

    # The water collector slot reads three ways, and only the two real ones are answers.
    saved = find.find
    try:
        find.find = lambda name, region=None, **kw: (
            BOX if name == craft.WATER_FILTER_TARGET else None)
        assert craft.water_filter_state() == 'fitted'
        find.find = lambda name, region=None, **kw: (
            BOX if name == craft.MISSING_WATER_FILTER_TARGET else None)
        assert craft.water_filter_state() == 'empty'
        find.find = lambda name, region=None, **kw: None
        try:
            craft.water_filter_state()
        except craft.Blind:
            pass
        else:
            raise AssertionError('neither crop matching read as a state instead of Blind')
        find.find = lambda name, region=None, **kw: BOX
        try:
            craft.water_filter_state()
        except craft.Blind:
            pass
        else:
            raise AssertionError('both crops matching read as a state instead of Blind')
    finally:
        find.find = saved
    print('  ok  water collector   fitted / empty are answers, neither and both are Blind')

    print('ok, a blind read stops the run and the craft row is read once a pass')
