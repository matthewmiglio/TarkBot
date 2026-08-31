"""The moonshine craft's whole pass, against the live booze generator, with no navigation.

Run:  python tests/test_booze_generator.py --dry     read the row, click nothing
      python tests/test_booze_generator.py           run one pass for real
      python tests/test_booze_generator.py --purified-water-max 140000 --sugar-max 48900

Stand in front of the booze generator with its panel open before running this. It does not
navigate: it checks the station is already on screen and it finishes on that same panel, which
is checked at both ends.

The sister of tests/test_water_collector.py, and deliberately not the same shape underneath,
because the two stations are not. The collector has its own pass (no START, no ingredient row).
The booze generator is an ordinary craft, so this runs craft_bot.HideoutCraft.step, the same
state machine every other craft goes through, with only the carousel taken out:

  producing    -> nothing to do, swap
  done         -> click GET ITEMS, book the profit
  ready, inputs in the stash    -> click START and confirm the handover dialog
  ready, an input missing       -> buy each off the flea at its ceiling, then end the pass
  not started (greyed GET ITEMS) -> nothing this loop can do, swap

Moonshine is purified water plus sugar, and both are bought off the flea by right clicking the
ingredient on the craft row and picking 'filter by item'. That is the path with the money on it:
a pass that finds either input missing will spend up to the two ceilings below. --dry first.

The read everything turns on is craft.read_craft, which reads the row exactly once and hands
back the state, the START and GET ITEMS boxes and the per-input ready flags together. It raises
craft.Blind when the output item or an input icon will not match, rather than guessing: an
unreadable row used to answer 'producing', which is the one state the runner reacts to by doing
nothing, so a craft it could not see was skipped silently every pass. A Blind here means go and
look at the crop folder it names.
"""
import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import craft_bot  # noqa: E402
import frames  # noqa: E402
import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import window  # noqa: E402
from interact import craft, find  # noqa: E402

CRAFT = craft.CRAFTS['moonshine']
# craft_bot.DEFAULT_MAX, read rather than copied so this cannot drift from what a real run pays.
CEILINGS = {name: craft_bot.DEFAULT_MAX[name] for name, _ in CRAFT.ingredients}


def bot_on(region, ceilings, sources):
    """A HideoutCraft wired for this one craft and nothing else.

    object.__new__ rather than the real __init__, which wants a window, a monitor and a set of
    prefs, none of which is what this is about. Two behaviours are replaced and only two:
    _ensure_on, because this test does no navigating and the caller has already parked us at the
    station, and _swap, because there is no cycle to move along to. Both record that they were
    reached, so the pass's own decisions are still visible.
    """
    runner = object.__new__(craft_bot.HideoutCraft)
    runner.region = region
    runner.stats = {key: 0 for key, _ in craft_bot.STAT_LABELS}
    runner._stop = threading.Event()
    runner.index = 0
    runner.swapped = []
    runner._swap = lambda: runner.swapped.append(True)
    runner._ensure_on = lambda job: None  # already there, by this test's contract
    job = craft_bot.CraftJob(craft=CRAFT, max_prices=dict(ceilings), sources=dict(sources))
    runner.jobs = [job]
    return runner, job


def report(region):
    """What the craft row says right now, without touching it. Returns the CraftRead."""
    read = craft.read_craft(CRAFT, region)  # raises craft.Blind if the row will not read
    print(f'  state       {read.state}')
    print(f'  START       {"at " + str(read.start) if read.start else "not on the row"}')
    print(f'  GET ITEMS   {"at " + str(read.get_items) if read.get_items else "not on the row"}')
    # inputs is None outside the ready state, and that is deliberate rather than missing: a
    # producing or finished row has no checkmarks under its ingredients to read, so read_craft
    # does not pay for the search. Only 'ready' has a queue worth printing.
    for name, ready, location in read.inputs or ():
        where = f'at {location}' if location else 'icon not found on the row'
        print(f'  {name:<12}{"in the stash" if ready else "MISSING, would be bought"}, {where}')
    if read.inputs is None:
        print(f'  inputs      not read, which is right for a {read.state!r} row')

    missing = [name for name, ready, _ in read.inputs or () if not ready]
    if read.state == 'producing':
        print('  -> producing, so a real pass would swap away and leave it alone')
    elif read.state == 'done':
        print('  -> done, so a real pass would click GET ITEMS and book the profit')
    elif read.state == 'not started':
        print('  -> not started, so a real pass would swap away')
    elif missing:
        print(f'  -> ready but short of {missing}, so a real pass would go to the flea and BUY')
    else:
        print('  -> ready with everything in the stash, so a real pass would click START')
    return read


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--dry', action='store_true', help='read the row and click nothing')
    for name, _ in CRAFT.ingredients:
        p.add_argument(f'--{name.replace("_", "-")}-max', type=int, default=CEILINGS[name],
                       dest=f'{name}_max',
                       help=f'most roubles to pay for {name} (default {CEILINGS[name]})')
        p.add_argument(f'--{name.replace("_", "-")}-source', default='players',
                       dest=f'{name}_source', choices=('players', 'traders'))
    args = p.parse_args()
    ceilings = {name: getattr(args, f'{name}_max') for name, _ in CRAFT.ingredients}
    sources = {name: getattr(args, f'{name}_source') for name, _ in CRAFT.ingredients}

    find.VERBOSE = True  # the same narration a real craft run writes into the session log
    frames.start()  # every click leaves a before and after png, which is the evidence on a miss

    hwnd = window.handle()  # raises WindowError if Tarkov is missing or duplicated
    rect = window.position(hwnd) + window.size(hwnd)
    region = screen.overlap(rect, screen.current().rect) or rect
    print(f'window {region}, at {find.scale():.3f}x the 1080p the crops are stored at')

    # No navigation, so being on the wrong station is the caller's mistake and worth saying
    # plainly rather than discovering it as a row that will not read.
    if not craft.station_active(CRAFT, region):
        sys.exit(f'FAILED: the {CRAFT.station} panel is not on screen. This test does no '
                 f'navigating: open the station yourself and run it again.')
    print(f'on the {CRAFT.station} panel, craft {CRAFT.name} '
          f'({" + ".join(name for name, _ in CRAFT.ingredients)} -> {CRAFT.name})')

    print('before:')
    before = report(region)

    if args.dry:
        print(f'\n--dry, so nothing was clicked. Without it this would spend up to '
              f'{ceilings} on the flea.')
        raise SystemExit(0)

    runner, job = bot_on(region, ceilings, sources)
    print(f'\nworking the craft, ceilings {ceilings}, sources {sources}')
    runner.step()

    print('\nafter:')
    after = craft.read_craft(CRAFT, region)
    print(f'  state       {before.state} -> {after.state}')
    print(f'  started     {runner.stats[f"started:{CRAFT.name}"]}')
    print(f'  profit      {runner.stats[f"profit:{CRAFT.name}"]} for {CRAFT.name}, '
          f'{runner.stats["total_profit"]} total')
    print(f'  swapped     {"yes" if runner.swapped else "no"} (a real run would move to the '
          f'next craft in the cycle here)')

    # Finishing where it started is half the contract. buy_input goes to the flea and comes back
    # through craft.return_to_station, so a pass that ends anywhere else has lost its way home
    # and the next one navigates from somewhere it does not expect.
    if not craft.station_active(CRAFT, region):
        sys.exit(f'FAILED: the pass did not finish on the {CRAFT.station} panel. If it bought '
                 f'something, craft.return_to_station is where to look.')
    print(f'  page        still the {CRAFT.station} panel')

    # What actually happened, said plainly, because every one of these is a legitimate outcome
    # and the interesting part is which one it was.
    if before.state == 'done' and after.state != 'done':
        print('\nok, a finished craft was collected')
    elif before.state == 'ready' and after.state == 'producing':
        print('\nok, the craft was started and is producing')
    elif before.state == 'producing':
        print('\nok, a producing craft was left alone')
    elif after.state == 'ready':
        missing = [name for name, ready, _ in after.inputs or () if not ready]
        print(f'\nthe craft is still ready and short of {missing or "nothing"}. Buying ends the '
              f'pass without starting: the next pass reads the row once and starts it. Run this '
              f'again to do that.' if missing else
              '\nthe craft is ready with everything in the stash. Run this again to start it.')
    else:
        print(f'\nfinished with the craft {after.state!r}. That is an outcome, not a crash; the '
              f'narration above says how it got there.')
