"""The craft cycle is grouped by station, and swapping within a station does not navigate.

Run:  python tests/test_craft_station_grouping.py

No game needed. The screen, the matcher and the navigation are stubbed, so this is about the
order the jobs come out in and whether a trip through the carousel goes out, not about pixels.

What this pins. Two crafts run at the lavatory and two at the workbench, and craft.CRAFTS lists
them interleaved, so an ungrouped cycle walks the carousel to the lavatory, away, and back to it
again every lap. Navigation is the slowest and least reliable thing this mode does. Worse, the
old _swap navigated unconditionally, and clicking the tab of the station already on screen
navigates back out of it, so the cheapest swap there is was also the one most likely to break.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402


def built():
    """build() with every craft enabled, screen.use stubbed out. Returns the job list."""
    saved = craft_bot.screen
    craft_bot.screen = types.SimpleNamespace(use=lambda m: None, AUTO='auto')
    try:
        return craft_bot.build({}, {key: 0 for key, _ in craft_bot.STAT_LABELS}).jobs
    finally:
        craft_bot.screen = saved


def swaps(jobs, on_station):
    """Swap once from job 0. Returns (name swapped to, stations navigated to).

    on_station is the station the panel claims to be showing, which is what decides whether the
    swap has to navigate at all.
    """
    went = []
    runner = craft_bot.HideoutCraft(jobs, stats={key: 0 for key, _ in craft_bot.STAT_LABELS})
    saved = (craft.station_active, craft.get_to_station)
    craft.station_active = lambda c, r=None: c.station == on_station
    craft.get_to_station = lambda c, r=None: went.append(c.station)
    try:
        runner._swap()
        return jobs[runner.index].craft.name, went
    finally:
        craft.station_active, craft.get_to_station = saved


if __name__ == '__main__':
    jobs = built()
    stations = [job.craft.station for job in jobs]

    # Every station appears as one unbroken run, which is the whole point: no station is left and
    # come back to. Checked by counting the blocks rather than by naming an expected order, so
    # adding a craft does not need this test edited.
    blocks = [s for i, s in enumerate(stations) if i == 0 or stations[i - 1] != s]
    assert len(blocks) == len(set(stations)), f'a station is visited twice a lap: {stations}'
    assert len(jobs) == len(craft.CRAFTS), f'grouping lost or duplicated a craft: {stations}'

    # The two stations that actually have two crafts each are the reason this exists.
    for station in ('lavatory', 'workbench'):
        assert stations.count(station) == 2, f'{station} should hold two crafts: {stations}'

    # Grouping only moves the duplicates: the order craft.CRAFTS lists the stations in is kept,
    # so the cycle a user watches is the one the GUI's craft list implies.
    first_seen = []
    for craft_desc in craft.CRAFTS.values():
        if craft_desc.station not in first_seen:
            first_seen.append(craft_desc.station)
    assert blocks == first_seen, f'the station order changed: {blocks} vs {first_seen}'

    # Swapping to another craft at the station already on screen navigates nowhere. This is the
    # half that used to click the selected tab and navigate straight back out.
    name, went = swaps(jobs, on_station=jobs[0].craft.station)
    assert jobs[1].craft.station == jobs[0].craft.station or went, 'test picked a bad pair'
    if jobs[1].craft.station == jobs[0].craft.station:
        assert went == [], f'navigated within one station: {went}'

    # Swapping to a craft at a different station still navigates there.
    _, went = swaps(jobs, on_station='somewhere else')
    assert went == [jobs[1].craft.station], f'did not navigate to the next station: {went}'

    print(f'ok: {len(blocks)} stations, one visit each per lap, no navigation within a station')
