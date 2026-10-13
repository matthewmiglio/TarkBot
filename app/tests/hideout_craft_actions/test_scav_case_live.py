"""The scav case's whole pass, against the live station: start what can be started, collect what is done.

Run:  python tests/hideout_craft_actions/test_scav_case_live.py --dry     read the rows, click nothing
      python tests/hideout_craft_actions/test_scav_case_live.py           run one pass for real
      python tests/hideout_craft_actions/test_scav_case_live.py --only moonshine --moonshine-max 250000

App layer: craft_bot.HideoutCraft.tend_scav_case, the scav case's own pass (not the ordinary
step() state machine): wheel the list once (craft.scroll_scav_case_list), then read both rolls and
act on each (_tend_scav_case_roll: collect a finished roll through its LOOT FROM SCAVS reveal,
START a ready one, buy the input of one whose START did nothing and START it again), round after
round until both are producing. Clicks START and GET ITEMS and can spend real roubles on a
moonshine bottle or an intelligence folder: it needs the live game.

Stand on the Scav Case with its panel open before running this. It checks that at the start and
again at the end, since finishing on the panel is half the contract. The pass never leaves the
panel except for a buy, which goes to the flea and back (craft.return_to_station). Only the final
_swap to the next station is stubbed.

--dry reads the rows where the list sits, with no wheel, so a roll below the fold reads absent.
"""
import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import craft_bot  # noqa: E402
import frames  # noqa: E402
import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import window  # noqa: E402
from interact import craft, find  # noqa: E402

ROLLS = {c.ingredients[0].name: c for c in (craft.SCAV_CASE, craft.SCAV_CASE_INTEL)}


def report(region, rolls):
    """Each roll's row and every lit GET ITEMS, read where the list sits, touching nothing."""
    for name, c in rolls.items():
        if not find.find(c.output_target, region):
            print(f'  {name:<13}not on the visible rows (the real pass scrolls for it)')
            continue
        read = craft.read_craft(c, region)
        inputs = ', '.join(f'{n} {"in the stash" if ok else "MISSING"}' for n, ok, _ in read.inputs or ())
        print(f'  {name:<13}{read.state}{"  (" + inputs + ")" if inputs else ""}')
    lit = craft.lit_get_items(region)
    print(f'  lit GET ITEMS {len(lit)} on the visible rows')
    return lit


def bot_on(region, rolls, ceilings, sources):
    """A HideoutCraft wired for the scav case rolls and nothing else.

    object.__new__ rather than the real __init__, which wants prefs and a window measure of its own.
    Only _swap is replaced: there is no next station, and it records that it was reached.
    """
    runner = object.__new__(craft_bot.HideoutCraft)
    runner.region = region
    runner.restart_as = None
    runner.one_pass = False
    runner.stats = {key: 0 for key, _ in craft_bot.STAT_LABELS}
    runner._stop = threading.Event()
    runner.index = 0
    runner.swapped = []
    runner._swap = lambda: runner.swapped.append(True)
    runner.jobs = [craft_bot.CraftJob(craft=c, max_prices={n: ceilings[n]}, sources={n: sources[n]})
                   for n, c in rolls.items()]
    return runner


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--dry', action='store_true', help='read the rows and click nothing')
    p.add_argument('--only', choices=list(ROLLS), help='tend just this roll (default: both)')
    for name in ROLLS:
        p.add_argument(f'--{name}-max', type=int, default=craft_bot.DEFAULT_MAX[name],
                       dest=f'{name}_max',
                       help=f'most roubles to pay for {name} (default {craft_bot.DEFAULT_MAX[name]})')
        p.add_argument(f'--{name}-source', default='players', dest=f'{name}_source',
                       choices=('players', 'traders'))
    args = p.parse_args()
    rolls = {n: c for n, c in ROLLS.items() if args.only in (None, n)}
    ceilings = {n: getattr(args, f'{n}_max') for n in rolls}
    sources = {n: getattr(args, f'{n}_source') for n in rolls}

    find.VERBOSE = True  # the same narration a real craft run writes into the session log
    frames.start()  # every click leaves a before and after png, which is the evidence on a miss

    hwnd = window.handle()  # raises WindowError if Tarkov is missing or duplicated
    rect = window.position(hwnd) + window.size(hwnd)
    region = screen.overlap(rect, screen.current().rect) or rect
    print(f'window {region}, at {find.scale():.3f}x the 1080p the crops are stored at')

    if not craft.station_active(craft.SCAV_CASE, region):
        sys.exit('FAILED: the Scav Case panel is not on screen. Open it yourself and run this again.')
    print(f'on the scav case panel, rolls {list(rolls)}')

    print('before:')
    before = report(region, rolls)

    if args.dry:
        print(f'\n--dry, so nothing was clicked. Without it this would spend up to {ceilings}.')
        raise SystemExit(0)

    runner = bot_on(region, rolls, ceilings, sources)
    print(f'\ntending the scav case, ceilings {ceilings}, sources {sources}')
    try:
        runner.tend_scav_case(runner.jobs[0])
    finally:
        frames.flush()

    print('\nafter:')
    after = report(region, rolls)
    started = {c.name: runner.stats[f'started:{c.name}'] for c in rolls.values()}
    print(f'  started     {started}')
    print(f'  lit GET ITEMS on the visible rows {len(before)} -> {len(after)}')
    print(f'  swapped     {"yes" if runner.swapped else "NO"} (a real run moves to the next station here)')

    if not craft.station_active(craft.SCAV_CASE, region):
        sys.exit('FAILED: the pass did not finish on the Scav Case panel. If it bought something, '
                 'craft.return_to_station is where to look.')
    print('  page        still the scav case panel')
    print('\nok, one scav case pass ran and finished on the station')
