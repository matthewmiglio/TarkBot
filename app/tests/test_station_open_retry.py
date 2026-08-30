"""A station tab whose panel does not open on the first click is clicked again.

Run:  python tests/test_station_open_retry.py

No game needed. The mouse, the clock and the matcher are stubbed, so this is about how many
looks the open gets and where the second click lands, not about matching pixels.

What this pins. _open_station used to click once, read the panel once, and end the run on the
first no. That one look killed two hour-long craft runs in two days for reasons that had nothing
to do with the station: on 2026-08-29 a Windows low disk notification stole focus and the click
went into refocusing the game, and on 2026-08-30 the screen went black for a few seconds and the
panel simply could not be read. Both would have passed a second later.

The re-find between tries is the half that is easy to drop. The station carousel is still gliding
for a second or so after a swipe, about 165px in the three seconds before each of those two
crashes, so a retry that clicks the old box again is aiming at where the tab used to be.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from interact import craft  # noqa: E402

STATION = types.SimpleNamespace(station='nutrition unit', module_target='hideout_tabs/nutrition')


def box_at(left):
    return types.SimpleNamespace(left=left, top=1580, width=200, height=24)


def open_with(opens, boxes):
    """Run _open_station where station_active() answers `opens` in turn and find() gives `boxes`.

    Returns (result, clicks), clicks being the x of every click in the order it went out, or
    ('raised', clicks) when it gave up.
    """
    clicks = []
    saved = (craft.pyautogui, craft.find, craft.time, craft.sell, craft.station_active)
    craft.pyautogui = types.SimpleNamespace(
        click=lambda x, y: clicks.append(round(x)),
        center=lambda b: (b.left + b.width / 2, b.top + b.height / 2))
    craft.find = types.SimpleNamespace(find=lambda *a, **k: boxes.pop(0) if boxes else None)
    craft.time = types.SimpleNamespace(sleep=lambda s: None)
    craft.sell = types.SimpleNamespace(jitter=lambda point, **k: point)
    craft.station_active = lambda *a, **k: opens.pop(0) if opens else False
    try:
        return craft._open_station(STATION), clicks
    except LookupError:
        return 'raised', clicks
    finally:
        (craft.pyautogui, craft.find, craft.time, craft.sell,
         craft.station_active) = saved


if __name__ == '__main__':
    # The happy path is untouched: one click, one look, no second press on a panel already open.
    result, clicks = open_with([True], [box_at(1000)])
    assert result is True, f'a panel that opened should return True, got {result}'
    assert clicks == [1100], f'expected one click at the tab centre, got {clicks}'

    # A panel that does not open gets a second click, aimed at where the tab is *now*. The
    # carousel moved 165px between the reads, which is what the re-find is there for.
    result, clicks = open_with([False, True], [box_at(1000), box_at(835)])
    assert result is True, 'the second click opened it and that has to count'
    assert clicks == [1100, 935], f'the retry did not re-aim at the moved tab: {clicks}'

    # A screen that never comes back still gives up rather than clicking forever, and it gives
    # up with LookupError so craft_bot swaps craft instead of ending the run.
    result, clicks = open_with([], [box_at(1000)])
    assert result == 'raised', 'a station that never opens has to raise'
    assert len(clicks) == craft.OPEN_ATTEMPTS, f'{clicks} is not {craft.OPEN_ATTEMPTS} tries'

    # Losing the tab mid-retry is not a reason to stop: the last known box is clicked again.
    result, clicks = open_with([False, True], [box_at(1000), None])
    assert result is True and clicks == [1100, 1100], f'lost tab was not reused: {clicks}'

    print('ok: one click when it opens, a re-aimed second when it does not, then a clean raise')
