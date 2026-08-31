"""Navigate between every pair of craft stations and check each leg lands on the right panel.

This is the net for craft.get_to_station's smart carousel navigation: the direction pick
(craft._preferred_first_dx) reads the fixed station order off whatever icons are on screen and
sweeps the likely way first. This test walks every ordered pair of craft stations and confirms
each navigation opens the right panel, so a direction guess that is backwards (or a crop that
stops matching) shows up as a failed or swipe-heavy leg rather than in a live run.

Setup, what the game has to look like before this is started
------------------------------------------------------------
- Tarkov open and in the foreground, fullscreen, on the monitor screen.current() picks (the same
  one the GUI's MONITOR dropdown would). A window on the other monitor exits early with a message.
- On the HIDEOUT screen. It does not matter which station, or whether any station panel is open at
  all: the first thing each navigation does is make the hideout tab active and then find its way
  along the module carousel, so starting on no station is fine and is the normal case. The one
  requirement is that the hideout tab in the left-hand list is reachable (ie you are on the hideout
  and not, say, the flea or the raid map).
- Nothing else needs opening or positioning. The control panel (our own GUI) does not need to be
  running; if it is, keep it off the game so it is not read as part of the screen.
- Hands off the mouse once it starts: this drives the real cursor to swipe and click, for minutes.

What it does
------------
Walks all ordered pairs (from, to) of the unique stations the crafts use (nutrition unit,
lavatory, workbench, medstation, booze generator, water collector; crafts that share a station,
like fleece and cordura at the lavatory, collapse to one). For each pair it makes a SETUP hop to
'from' (navigate there, uncounted and ungraded, just to place the carousel), then a MEASURED leg
to 'to': navigate and confirm 'to's panel opened. The swipes of the measured leg are counted, by
wrapping craft._swipe, so the whole run's total and per-leg average are the headline number the
smart pick is meant to bring down; an adjacent station should land in zero or one swipe.

A leg that fails (get_to_station raises LookupError, ie it never found or opened the station)
leaves the carousel in an unknown place, so 'current' is reset to None and the next 'from' is
always re-navigated fresh rather than assumed. The setup hop itself can fail too; that pair is
recorded as a failure and skipped rather than measured against a carousel we are not sure of.

Output and exit
---------------
Prints each leg live ([setup]/[leg] lines), then a table of every pair with OK/FAIL and its swipe
count, the leg total and average, and how many of the pairs landed. Saves a full-window frame per
FAILED leg to tests/output/craft_nav/<from>_to_<to>.png, so a miss can be read back (successful
legs write nothing). Exits non-zero if any leg failed.

    python tests/test_craft_nav_permutations.py

find.VERBOSE is turned on for the run, like craft_bot does, so every reference match is narrated:
which crop matched, or did not, is exactly what a swipe-heavy or failed leg needs explaining.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import screen  # noqa: E402  (importing patches pyautogui.screenshot onto the chosen monitor)
import window  # noqa: E402
from interact import craft, find  # noqa: E402

OUT = Path(__file__).parent / 'output' / 'craft_nav'


def region():
    """The game window clipped to its monitor, the (left, top, width, height) craft functions take.

    Built exactly as craft_bot.__init__ does, so this test searches the same rectangle the shipping
    runner would: the Tarkov window rect (position + size) clipped to the current monitor. Exits
    with a message if the window is off that monitor, the one setup mistake this can name for you.
    """
    hwnd = window.handle()  # raises WindowError if Tarkov is not open or is duplicated
    r = screen.overlap(window.position(hwnd) + window.size(hwnd), screen.current().rect)
    if r is None:
        raise SystemExit('Tarkov is not on the current monitor; pick the other one or move it.')
    return r


def craft_stations():
    """One representative Craft per unique station the crafts use, ordered along STATION_ORDER.

    Several crafts can share a station (fleece and cordura at the lavatory, wires and red gunpowder
    at the workbench); they collapse to one entry, since any craft at a station navigates there the
    same way. Sorted left to right so the printed table reads in carousel order.
    """
    by_station = {}
    for c in craft.CRAFTS.values():
        by_station.setdefault(c.station, c)  # first craft wins; any at that station navigates the same
    order = {name: i for i, name in enumerate(craft.STATION_ORDER)}
    return sorted(by_station.values(), key=lambda c: order.get(craft._module_basename(c.module_target), 99))


def count_swipes():
    """Wrap craft._swipe so navigations tally their swipes; returns (reset, read) closures.

    get_to_station calls the module-level _swipe, so replacing craft._swipe counts every drag a
    navigation makes. reset() zeroes the tally before a measured leg, read() gives its count after.
    This is the metric the whole test exists to produce: fewer swipes is the smart pick working.
    """
    n = {'v': 0}
    original = craft._swipe

    def counting(*args, **kwargs):
        n['v'] += 1
        return original(*args, **kwargs)

    craft.counting = counting  # keep a ref so it is not gc'd
    craft._swipe = counting
    return (lambda: n.update(v=0)), (lambda: n['v'])


def go(c, reg):
    """Navigate to c's station. True if the panel opened, False on any LookupError."""
    try:
        return bool(craft.get_to_station(c, reg))
    except LookupError as e:
        print(f'    LookupError: {e}')
        return False


if __name__ == '__main__':
    find.VERBOSE = True  # this mode leans hardest on detection; narrate every match like the runner
    reg = region()
    stations = craft_stations()
    print(f'window {reg}, {len(stations)} craft stations: {[c.station for c in stations]}')
    print(f'{len(stations) * (len(stations) - 1)} ordered pairs to walk\n')

    reset, swipes = count_swipes()
    OUT.mkdir(parents=True, exist_ok=True)
    results = []  # (from, to, ok, swipe_count)
    current = None  # which station we believe the carousel is showing; None means unknown

    for src in stations:
        for dst in stations:
            if src.station == dst.station:
                continue
            if current != src.station:  # setup hop, not measured
                print(f'[setup] -> {src.station}')
                current = src.station if go(src, reg) else None
                if current is None:
                    print(f'    could not reach {src.station} to start the leg, skipping\n')
                    results.append((src.station, dst.station, False, None))
                    continue
            reset()
            print(f'[leg]   {src.station} -> {dst.station}')
            ok = go(dst, reg)
            n = swipes()
            results.append((src.station, dst.station, ok, n))
            print(f'    {"OK" if ok else "FAIL"} in {n} swipe(s)\n')
            current = dst.station if ok else None
            if not ok:
                pyautogui.screenshot(region=reg).save(OUT / f'{src.station}_to_{dst.station}.png'.replace(' ', '_'))
            time.sleep(0.5)

    print('=== nav permutation results ===')
    fails = [r for r in results if not r[2]]
    measured = [r for r in results if r[3] is not None]
    total = sum(r[3] for r in measured)
    for s, d, ok, n in results:
        print(f'  {"OK  " if ok else "FAIL"} {s:>16} -> {d:<16} {"" if n is None else f"{n} swipe(s)"}')
    if measured:
        print(f'\n{len(measured)} legs, {total} swipes total, {total / len(measured):.1f} avg per leg')
    print(f'{len(results) - len(fails)}/{len(results)} legs landed on the right panel')
    if fails:
        print(f'-> failure frames in {OUT}')
        sys.exit(1)
    print('all navigations correct')
