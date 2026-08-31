"""The hideout carousel search is bounded, in both directions, and stops shoving at the ends.

Run:  python tests/test_hideout_swipe_limits.py

No game needed. The mouse, the clock, the matcher and the screen are stubbed, so this is about
how many swipes go out and which way, not about matching pixels.

What this pins. get_to_station used to swipe blindly left five times on every single navigation
before it started looking, and the bot re-navigates for every craft on every pass: one 71 minute
run on 2026-08-30 spent 366 swipes, most of them travelling past the station and back. Worse, a
loop with no end test is one bad screen away from swiping at a wall forever.

So both sweeps are capped, and each one also stops the moment the module row stops moving, which
is what the carousel sitting against its end looks like. The caps are the part that must never
quietly go away: an unbounded search here does not fail, it just keeps dragging the mouse.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from interact import craft  # noqa: E402

STATION = types.SimpleNamespace(station='nutrition unit', module_target='hideout_tabs/nutrition')
ICON = types.SimpleNamespace(left=1000, top=1580, width=200, height=24)


def search_with(found_after=None, stuck_after=None):
    """Run get_to_station with the station appearing after `found_after` swipes. (result, swipes).

    swipes is the dx of each swipe in order, so its length is the total and its sign is the
    direction. `stuck_after` makes the row stop moving after that many swipes, standing in for
    the carousel reaching one end.
    """
    swipes = []
    names = ('is_hideout_tab_active', 'hideout_icons', 'find', '_swipe', '_row_strip',
             '_row_moved', '_open_station', 'time')
    saved = {n: getattr(craft, n) for n in names}
    craft.is_hideout_tab_active = lambda *a, **k: True
    craft.hideout_icons = lambda *a, **k: [ICON]
    craft.find = types.SimpleNamespace(
        find=lambda *a, **k: ICON if found_after is not None and len(swipes) >= found_after
        else None,
        scale=lambda: 1.0)
    craft._swipe = lambda x, y, dx: swipes.append(dx)
    craft._row_strip = lambda *a, **k: None
    craft._row_moved = lambda *a, **k: stuck_after is None or len(swipes) < stuck_after
    craft._open_station = lambda *a, **k: True
    craft.time = types.SimpleNamespace(sleep=lambda s: None, monotonic=lambda: 0.0)
    try:
        return craft.get_to_station(STATION), swipes
    except LookupError:
        return 'raised', swipes
    finally:
        for name, value in saved.items():
            setattr(craft, name, value)


if __name__ == '__main__':
    right, left = craft.MAX_SEARCH_SWIPES, craft.MAX_SEARCH_SWIPES * 2

    # A station a couple of swipes to the right is found there, and nothing swipes after it.
    result, swipes = search_with(found_after=2)
    assert result is True, f'the station was on screen, got {result}'
    assert len(swipes) == 2 and all(d > 0 for d in swipes), f'wrong sweep: {swipes}'

    # A station that is never there stops, and stops at the caps: right first, then twice as far
    # back left, because the return sweep has to undo the outbound one to reach a station that
    # was behind the starting point.
    result, swipes = search_with(found_after=None)
    assert result == 'raised', 'a station that is never found has to raise'
    assert len(swipes) == right + left, f'{len(swipes)} swipes is not the {right + left} cap'
    assert swipes[:right] == [swipes[0]] * right, 'the first sweep changed direction mid-way'
    assert all(d > 0 for d in swipes[:right]), 'the first sweep should go right'
    assert all(d < 0 for d in swipes[right:]), 'the return sweep should go left'

    # Against the end of the carousel, the sweep gives up rather than dragging at a wall. One
    # swipe still goes out each way, because a row that has not been dragged yet cannot be known
    # to be stuck.
    result, swipes = search_with(found_after=None, stuck_after=0)
    assert result == 'raised', 'still a dead end'
    assert len(swipes) == 2, f'kept shoving a row that was not moving: {swipes}'
    assert swipes[0] > 0 > swipes[1], f'did not try both directions: {swipes}'

    # Stuck part way through: each sweep stops at its own wall, and the cap still holds.
    result, swipes = search_with(found_after=None, stuck_after=3)
    assert result == 'raised' and len(swipes) < right + left, f'no early stop: {swipes}'

    print(f'ok: bounded at {right} right and {left} left, and stops at the ends of the row')
