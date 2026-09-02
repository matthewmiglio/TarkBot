"""One-pass craft mode visits every station once and then stops.

Run:  python tests/hideout_craft_actions/test_one_pass.py

App layer: craft_bot.HideoutCraft._swap with one_pass=True (set by the CLI's --one-pass, threaded
through craft_bot.build via prefs['one_pass']). A one-pass runner swaps forward through the jobs
exactly once and raises Stopped the moment a swap would wrap back to the first station, rather than
cycling forever like a normal run.

No game needed. The runner is built without __init__ (which wants a Tarkov window and a monitor),
the same trick test_scav_only_fallback uses, and station_active/get_to_station are stubbed. This is
about how many times the cycle swaps before it stops, not about pixels or real navigation.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402


def job(station, name):
    """A stand-in CraftJob: _swap and _ensure_on only touch job.craft.station and job.craft.name."""
    return types.SimpleNamespace(craft=types.SimpleNamespace(station=station, name=name))


def runner(jobs, one_pass):
    """A HideoutCraft with only the attributes _swap/_ensure_on read, no window or monitor."""
    r = object.__new__(craft_bot.HideoutCraft)
    r.jobs = list(jobs)
    r.index = 0
    r.one_pass = one_pass
    r.region = None
    return r


# Four jobs across three stations (a duplicate station, like the two lavatory crafts), so "once per
# station" really means once per job in the grouped cycle.
JOBS = [job('nutrition', 'slickers'), job('lavatory', 'fleece'),
        job('lavatory', 'cordura'), job('workbench', 'wires')]


if __name__ == '__main__':
    saved = (craft.station_active, craft.get_to_station)
    craft.station_active = lambda c, r=None: False  # never already on the station, so every swap navigates
    craft.get_to_station = lambda c, r=None: None
    try:
        # A one-pass runner walks the whole cycle once, then stops on the wrap.
        r = runner(JOBS, one_pass=True)
        visited = [JOBS[0].craft.name]  # we start already on job 0
        swaps = 0
        try:
            while True:
                r._swap()
                swaps += 1
                assert swaps <= len(JOBS), 'one-pass never stopped: it wrapped past every station'
                visited.append(r.jobs[r.index].craft.name)
        except craft_bot.Stopped:
            pass
        assert swaps == len(JOBS) - 1, f'expected {len(JOBS) - 1} swaps, got {swaps}'
        assert visited == [j.craft.name for j in JOBS], f'not every job visited once, in order: {visited}'

        # A single-craft one-pass run has nothing to swap to, so the first swap ends it.
        solo = runner(JOBS[:1], one_pass=True)
        try:
            solo._swap()
            raise AssertionError('single-job one-pass did not stop on the first swap')
        except craft_bot.Stopped:
            pass

        # Without one_pass the cycle wraps back to the first station and keeps going (no Stopped).
        looping = runner(JOBS, one_pass=False)
        for _ in range(len(JOBS)):
            looping._swap()
        assert looping.index == 0, f'a normal cycle should wrap back to job 0, got {looping.index}'
    finally:
        craft.station_active, craft.get_to_station = saved

    print(f'ok: one-pass visited {len(visited)} crafts once then stopped; normal run wraps and continues')
