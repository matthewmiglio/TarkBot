"""The water collector's whole pass, against the live station, with no navigation.

Run:  python tests/hideout_craft_actions/test_water_collector.py --dry     read the panel, click nothing
      python tests/hideout_craft_actions/test_water_collector.py           run it for real
      python tests/hideout_craft_actions/test_water_collector.py --max 70000 --source players

App layer: craft_bot.HideoutCraft.tend_water_collector, the collector's own pass (over
interact/craft.py's water_filter_state / fit_water_filter / buy_water_filter), which collects
finished water, fits a filter, and buys one off the flea when the stash has none. A craft-actions
test that clicks, fits and (branch 3b) spends real roubles: it needs the live game.

Stand in front of the water collector with its panel open before running this. It does not
navigate: it assumes the station is already on screen and it finishes on that same panel, which
is checked at both ends by looking for the panel header.

What it exercises is craft_bot.HideoutCraft.tend_water_collector, the real one, with only the
carousel taken out of it:

  1. a lit GET ITEMS is clicked, a greyed one is left alone
  2. the slot reads 'fitted'   -> the collector is producing, nothing to do
  3a. the slot reads 'empty'   -> open the dropdown, and if it lists any filters fit one at
      random, then read the slot back to check it took
  3b. the dropdown lists none  -> buy one off the flea (typed search, not a right click, since a
      filter the collector has not got sits on no craft row), come back to the panel, open the
      dropdown again, fit one, read the slot back

Step 3b really does go to the flea and really does spend roubles, up to the --max ceiling. Use
--dry first: it reports which branch the panel is currently in and stops before clicking.

The read the whole thing turns on is craft.water_filter_state, which answers 'fitted' or 'empty'
from two separate crops and raises craft.Blind when neither or both match. That is deliberate: it
used to ask one question, "is the missing-filter icon on screen", so a crop that stopped matching
read as a collector quietly producing and the runner swapped away from a station doing nothing.
A Blind here means go and look at crafting/water_filter and crafting/missing_water_filter.
"""
import argparse
import sys
import threading
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import craft_bot  # noqa: E402
import frames  # noqa: E402
import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import window  # noqa: E402
from interact import craft, find  # noqa: E402

CEILING = 70000  # craft_bot.DEFAULT_MAX['water_filter']


def bot_on(region, ceiling, source):
    """A HideoutCraft wired for this one station and nothing else.

    object.__new__ rather than the real __init__, which wants a window, a monitor and a set of
    prefs, none of which is what this is about. _swap is the one behaviour replaced: the pass
    ends by moving to the next craft in the cycle, and there is no cycle here, so it records
    that it was reached and stays where it is.
    """
    runner = object.__new__(craft_bot.HideoutCraft)
    runner.region = region
    runner.stats = {key: 0 for key, _ in craft_bot.STAT_LABELS}
    runner._stop = threading.Event()
    runner.swapped = []
    runner._swap = lambda: runner.swapped.append(True)
    job = craft_bot.CraftJob(craft=craft.WATER_COLLECTOR,
                             max_prices={'water_filter': ceiling},
                             sources={'water_filter': source})
    return runner, job


def report(region):
    """What the panel says right now, without touching it. Returns the slot state."""
    box = find.find(craft.GET_ITEMS_TARGET, region)
    if box is None:
        print('  GET ITEMS   not on the panel')
    else:
        lit = craft.get_items_highlighted(box)
        print(f'  GET ITEMS   {"lit, so there is water to collect" if lit else "greyed, nothing finished"}')

    state = craft.water_filter_state(region)  # raises craft.Blind if it will not read
    print(f'  slot        {state}')
    if state == 'fitted':
        print('  -> producing already, so a real pass would collect and swap away')
        return state

    point = find.find_center(craft.WATER_FILTER_DROPDOWN_TARGET, region)
    print(f'  dropdown    {"at " + str(point) if point else "NOT on the panel, which would be Blind"}')
    print('  -> empty, so a real pass would open that dropdown, fit a filter if one is listed, '
          'and go to the flea if none is')
    return state


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--dry', action='store_true', help='read the panel and click nothing')
    p.add_argument('--max', type=int, default=CEILING, dest='ceiling',
                   help=f'most roubles to pay for a water filter (default {CEILING})')
    p.add_argument('--source', default='players', choices=('players', 'traders'))
    args = p.parse_args()

    find.VERBOSE = True  # the same narration a real craft run writes into the session log
    frames.start()  # every click leaves a before and after png, which is the evidence on a miss

    hwnd = window.handle()  # raises WindowError if Tarkov is missing or duplicated
    rect = window.position(hwnd) + window.size(hwnd)
    region = screen.overlap(rect, screen.current().rect) or rect
    print(f'window {region}, at {find.scale():.3f}x the 1080p the crops are stored at')

    # No navigation, so being on the wrong station is the caller's mistake and worth saying
    # plainly rather than discovering three reads later.
    if not craft.station_active(craft.WATER_COLLECTOR, region):
        sys.exit('FAILED: the water collector panel is not on screen. This test does no '
                 'navigating: open the station yourself and run it again.')
    print(f'on the {craft.WATER_COLLECTOR.station} panel')

    print('before:')
    state = report(region)

    if args.dry:
        print('\n--dry, so nothing was clicked. Run it without --dry to work the station.')
        raise SystemExit(0)

    runner, job = bot_on(region, args.ceiling, args.source)
    print(f'\nworking the station, ceiling {args.ceiling}, source {args.source}')
    runner.tend_water_collector(job)

    print('\nafter:')
    after = craft.water_filter_state(region)
    print(f'  slot        {after}')
    # The collector books no profit by design: PROFIT_PER_CRAFT has no figure for it, so
    # _book_profit adds 0 rather than a guess. Both counters are printed anyway, because 0 in
    # total_profit and 0 in this craft's own row are what "collected but unpriced" looks like,
    # and a non-zero here would mean somebody added a figure without measuring it.
    print(f'  profit      {runner.stats[f"profit:{craft.WATER_COLLECTOR.name}"]} for the '
          f'collector, {runner.stats["total_profit"]} total '
          f'(0 is right: the collector has no measured profit figure)')

    # Finishing where it started is half the contract: a pass that ends on the flea, or on some
    # other station, leaves the next one navigating from somewhere it does not expect.
    if not craft.station_active(craft.WATER_COLLECTOR, region):
        sys.exit('FAILED: the pass did not finish on the water collector panel. buy_water_filter '
                 'escapes the flea back to the station through craft.return_to_station, so this '
                 'is where to look if it went to the flea and stayed there.')
    print(f'  page        still the {craft.WATER_COLLECTOR.station} panel')

    assert runner.swapped, 'the pass never reached its swap, so it returned by some path that ' \
                           'skips the end of tend_water_collector'

    if state == 'empty' and after == 'fitted':
        print('\nok, an empty collector was filled and is producing')
    elif after == 'fitted':
        print('\nok, the collector has a filter in it and is producing')
    else:
        print(f'\nthe slot still reads {after!r}. That is a real outcome, not a crash: the '
              f'dropdown had nothing to fit and either no offer was under {args.ceiling} or the '
              f'buy did not land. The narration above says which, and a fresh pass tries again.')
