"""A station tab is clicked once, then waited on. It is never clicked twice.

Run:  python tests/hideout_craft_actions/test_station_open_retry.py

App layer: interact/craft.py, the _open_station navigation action (its single-click-then-poll
retry, bounded by craft.PANEL_TIMEOUT). A craft-actions test, not a plain read: it pins how the
opening click behaves, not whether a panel matches.

No game needed. The mouse, the clock and the matcher are stubbed, so this is about how many
clicks go out and how long the wait lasts, not about matching pixels.

What this pins, and it is the opposite of what this file used to pin. _open_station briefly
clicked the tab a second time when the panel did not appear. That is actively harmful: by then
the tab is the selected one, so clicking it again navigates back out of the station it just
entered. The frame that ended a run on 2026-08-30 showed exactly that, the Medstation tab lit up
as selected with the room still flying in behind it.

So the click landed and the game obeyed, and the only thing wrong was the reading. The hideout
flies its camera to the room before drawing the panel, and a fixed three second sleep plus a
single look lands inside that animation. One click, then poll until the panel is there or
PANEL_TIMEOUT runs out.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from interact import craft  # noqa: E402

STATION = types.SimpleNamespace(station='nutrition unit', module_target='hideout_tabs/nutrition')


def box_at(left):
    return types.SimpleNamespace(left=left, top=1580, width=200, height=24)


def ticking_clock(step):
    """A monotonic that moves `step` seconds every read, so a wait that never wins still ends."""
    state = {'now': 0.0}

    def monotonic():
        state['now'] += step
        return state['now']
    return types.SimpleNamespace(monotonic=monotonic, sleep=lambda s: None)


def open_with(opens, box=None, step=1.0):
    """Run _open_station where station_active() answers `opens` in turn. (result, clicks, looks).

    result is 'raised' when it gave up, clicks are the x of each click in order, and looks is how
    many times the panel was read before it stopped.
    """
    clicks = []
    looks = []
    saved = (craft.pyautogui, craft.find, craft.time, craft.sell, craft.station_active)
    craft.pyautogui = types.SimpleNamespace(
        click=lambda x, y: clicks.append(round(x)),
        center=lambda b: (b.left + b.width / 2, b.top + b.height / 2))
    craft.find = types.SimpleNamespace(find=lambda *a, **k: box)
    craft.time = ticking_clock(step)
    craft.sell = types.SimpleNamespace(jitter=lambda point, **k: point)

    def active(*a, **k):
        looks.append(1)
        return opens.pop(0) if opens else False
    craft.station_active = active
    try:
        return craft._open_station(STATION), clicks, len(looks)
    except LookupError:
        return 'raised', clicks, len(looks)
    finally:
        (craft.pyautogui, craft.find, craft.time, craft.sell, craft.station_active) = saved


if __name__ == '__main__':
    # A panel already up costs one click and one look. The wait is free when there is nothing
    # to wait for.
    result, clicks, looks = open_with([True], box_at(1000))
    assert result is True, f'a panel that opened should return True, got {result}'
    assert clicks == [1100], f'expected one click at the tab centre, got {clicks}'
    assert looks == 1, f'a panel already up should be read once, not {looks} times'

    # The whole point: a panel that takes a few seconds to draw is waited for, not clicked at
    # again. Still one click, however many looks it takes.
    result, clicks, looks = open_with([False, False, False, True], box_at(1000))
    assert result is True, 'a panel that appeared during the wait has to count as opened'
    assert clicks == [1100], f'the tab was clicked more than once: {clicks}'
    assert looks == 4, f'expected to keep looking until it appeared, looked {looks} times'

    # A station that never opens still gives up, with LookupError so craft_bot swaps craft rather
    # than ending the run, and still without a second click.
    result, clicks, looks = open_with([], box_at(1000))
    assert result == 'raised', 'a station that never opens has to raise'
    assert clicks == [1100], f'gave up but clicked {len(clicks)} times: {clicks}'
    assert looks > 1, 'gave up on the very first look, so nothing was actually waited for'

    # The wait is bounded by the clock, not by a look count: a fast clock ends it sooner.
    _, _, few = open_with([], box_at(1000), step=craft.PANEL_TIMEOUT / 2)
    _, _, many = open_with([], box_at(1000), step=craft.PANEL_TIMEOUT / 20)
    assert many > few, f'the timeout is not driving the wait ({many} vs {few} looks)'

    # Losing the tab while the screen settles is a dead end, before any click goes out.
    result, clicks, looks = open_with([True], None)
    assert result == 'raised', 'a tab that vanished before the click has to raise'
    assert clicks == [], f'clicked at a tab that was not there: {clicks}'

    print('ok: one click, then a bounded wait, and never a second click on a selected tab')
