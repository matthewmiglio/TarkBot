"""How fast can the flea filter step be driven before the game stops keeping up?

sell.apply_flea_filters paces itself with a handful of sleeps (see SCALED below), each picked
to be comfortably longer than the UI needs. This runs the real thing against the real game,
dividing every one of those sleeps by a speed that climbs each round, and reports the first
speed at which it breaks. Three failing speeds in a row ends it.

One attempt is three steps:

  1. open the flea, at normal speed
  2. open the filter window, park it, set the filters, OK out - all of which is one call to
     apply_flea_filters, and the only step the speed applies to
  3. escape back off the flea

Only step 2 is hurried, which is the point: step 1 is not what is being measured, and a flea
that would not open at speed says nothing about whether the filters can be set at it. The
earlier version of this hurried step 1 too and spent its whole run failing to open the flea.

Three scenarios per speed, the three shapes production actually calls it in, so a speed only
passes if all three do:

  1. flea sell     - no reset, players, condition 100. sell_bot's call, the seller's pass over a
                     board it is about to undercut.
  2. snipe         - reset first, players, condition 100. snipe_bot's call, where a filter left
                     on by someone else is a board the sniper is not reading all of.
  3. craft input   - no reset, traders, no condition. craft.buy_craft_input_item buying a
                     trader-sourced ingredient, the only shape that skips the condition box and
                     the only one that touches the traders option.

Needs the game running, on the hideout or stash, NOT on the flea: the loop opens and closes it
itself and starts every attempt from a shut flea. If the flea is already up when this starts it
is closed first.

It drives the real mouse for as long as it runs, so do not touch the machine while it does.

Run: python tests/speed_test_apply_filters.py
     python tests/speed_test_apply_filters.py --max 5.0 --step 1.0
"""
import argparse
import os
import sys
import time
from collections import namedtuple
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pyautogui

import screen
import window
from interact import find, sell
from narrate import log

# The sleeps that make up the pace of a filter pass. Every one is a flat wait for the UI to
# catch up, so dividing them all by the speed is what "faster" means here. Timeouts are
# deliberately not in this list: FILTERS_WINDOW_TIMEOUT and friends are a maximum wait on a
# poll that already returns as soon as it sees the thing, so they cost nothing at 1x and
# shrinking them would only fail the run for a reason that has nothing to do with pace.
#
# DRAG_SECONDS is in it even though it is a gesture rather than a wait, because its comment
# ('an instant drag gets dropped by the UI') says it is exactly the kind of thing that breaks
# when hurried, and the filter window is dragged on every single pass.
# FILTER_* are the filter pass's own waits and are the ones that matter here; the general
# MENU_DELAY and WINDOW_DELAY are still in the list because open_filters and the drag under it
# read those. Scaling a constant the pass never reads would measure nothing, and missing one it
# does read would report a speed the pass never actually ran at.
SCALED = ('FILTER_MENU_DELAY', 'FILTER_DROPDOWN_DELAY', 'FILTER_OFFERS_FROM_DELAY',
          'MENU_DELAY', 'WINDOW_DELAY', 'DRAG_SECONDS', 'RECOVER_DELAY', 'SELECT_WINDOW_DELAY')

START_SPEED = 1.0
SPEED_STEP = 0.1
FAILS_TO_STOP = 3  # consecutive failing speeds that end the run
MAX_SPEED = 6.0  # a backstop, so a game that never fails cannot loop forever
CLOSE_ATTEMPTS = 4  # escapes to spend getting off the flea before giving up
CLOSE_SETTLE = 1.0  # seconds after an escape before reading whether the flea went
SETTLE_BETWEEN = 1.0  # seconds between attempts, at normal speed, so one cannot bleed into the next

Scenario = namedtuple('Scenario', 'name kwargs')
SCENARIOS = (
    Scenario('flea sell', dict(reset=False, source='players', set_condition=True)),
    Scenario('snipe', dict(reset=True, source='players', set_condition=True)),
    Scenario('craft input', dict(reset=False, source='traders', set_condition=False)),
)


@contextmanager
def sped_up(factor):
    """Divide every pacing sleep in sell by factor for the duration of the block.

    Module globals rather than arguments, because that is how the functions under test read
    them: apply_flea_filters looks DROPDOWN_DELAY and OFFERS_FROM_DELAY up at call time and
    hands them down, and everything else below it reads MENU_DELAY and WINDOW_DELAY the same
    way. Restored in a finally so a failed attempt cannot leave the next one running fast.
    """
    original = {name: getattr(sell, name) for name in SCALED}
    try:
        for name, value in original.items():
            setattr(sell, name, value / factor)
        yield
    finally:
        for name, value in original.items():
            setattr(sell, name, value)


def close_flea(region):
    """Escape until the flea is shut. True once it is, False if it will not go.

    Every attempt starts from a closed flea, so a pass cannot inherit a window the last one
    left open and quietly skip the opening it was meant to be timing.
    """
    for attempt in range(CLOSE_ATTEMPTS):
        if not sell.is_flea_open(region):
            return True
        log(f'flea still open, escaping it (attempt {attempt + 1})', 1)
        pyautogui.press('esc')
        time.sleep(CLOSE_SETTLE)
    return not sell.is_flea_open(region)


def verify(scenario, region):
    """Reopen the filter window and read back what the pass actually set. True if it took.

    An independent check rather than trusting the return value. apply_flea_filters reads its
    own dropdowns as it sets them, so its True already means something, but it reads them in
    the same breath as the click that set them: a control that reverts a moment later, which is
    exactly what being hurried would look like, reads as set and then is not. Reopening the
    window and looking again is the only way to catch that.

    Always at normal speed, whatever the attempt ran at, so a failure is the filters not
    sticking rather than the check itself being rushed.

    ponytail: the two dropdowns only, not the condition box. Reading a typed 100 back needs OCR
    over a field with no reference crop, and a condition that did not take fails
    _set_condition_from inside the pass anyway. Add it here if a speed ever passes this check
    with the condition visibly wrong.
    """
    if not sell.open_filters(region):
        log('could not reopen the filter window to verify', 1)
        return False
    _option, settled = sell.OFFERS_FROM[scenario.kwargs['source']]
    currency = find.find(sell.CURRENCY_RUB_TARGET, region) is not None
    offers = find.find(settled, region) is not None
    log(f'verify: currency reads roubles {currency}, offers-from reads '
        f'{scenario.kwargs["source"]} {offers}', 1)
    pyautogui.press('esc')  # leave the window as we found it, shut
    time.sleep(sell.MENU_DELAY)
    return currency and offers


@contextmanager
def no_failsafe():
    """Hold pyautogui's corner fail-safe off, and let go of the mouse on the way out.

    Both halves are needed and the first run proved it. orientate_filters_window drags the
    filter window to the top left, which walks the cursor to (0, 0) and is exactly what the
    fail-safe watches for. sell turns it off for the drag itself, but the raise came from
    elsewhere in the pass, and a drag abandoned mid-gesture leaves the left button held down:
    every read after it was against a screen with a button stuck on it, so three speeds
    "failed" that were never measured at all.

    ponytail: off for the whole attempt rather than chasing which call trips it. The fail-safe
    is a human's way out of a runaway script, and this script already stops on its own.
    """
    was = pyautogui.FAILSAFE
    pyautogui.FAILSAFE = False
    try:
        yield
    finally:
        pyautogui.mouseUp()  # a drag cut short otherwise leaves the button down for the next one
        pyautogui.FAILSAFE = was


def attempt(scenario, speed, region):
    """One scenario at one speed. True if the filters went on and stuck.

    The three steps of the loop, and only the middle one is sped up. See the module docstring.
    """
    with no_failsafe():
        # 1. open the flea, at normal speed
        if not close_flea(region):
            log('could not get off the flea to start this attempt', 1)
            return False
        if not sell.open_flea(region):
            log('the flea would not open', 1)
            return False

        # 2. the step being timed: filter window open, parked, set, OK'd
        with sped_up(speed):
            applied = sell.apply_flea_filters(region, **scenario.kwargs)
        ok = applied and verify(scenario, region)
        if not applied:
            log('apply_flea_filters said no', 1)

        # 3. back off the flea, so the next attempt starts where this one did
        pyautogui.press('esc')
        time.sleep(CLOSE_SETTLE)
        return ok


def game_region():
    """The search region for the Tarkov window, the same clip every runner uses."""
    hwnd = window.handle()
    position, size = window.position(hwnd), window.size(hwnd)
    monitor = screen.current()
    region = screen.overlap(position + size, monitor.rect)
    if region is None:
        raise window.WindowError(
            f'Tarkov is at {position + size}, which is not on monitor {monitor.label} at '
            f'{monitor.rect}. Move the game onto this one.')
    return region


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max', type=float, default=MAX_SPEED,
                        help=f'stop at this speed even if nothing has failed (default {MAX_SPEED})')
    parser.add_argument('--step', type=float, default=SPEED_STEP,
                        help=f'how much to speed up between rounds (default {SPEED_STEP})')
    parser.add_argument('--start', type=float, default=START_SPEED,
                        help=f'speed to begin at (default {START_SPEED})')
    args = parser.parse_args()
    if args.step <= 0:
        parser.error('--step has to be positive, or the speed never climbs')

    region = game_region()
    print(f'searching {region}')
    print(f'pacing sleeps at 1x: ' + ', '.join(f'{n}={getattr(sell, n)}' for n in SCALED))
    print('starting from a shut flea; do not touch the mouse while this runs\n')

    rows = []
    speed, consecutive = args.start, 0
    while consecutive < FAILS_TO_STOP and speed <= args.max + 1e-9:
        failed = []
        for scenario in SCENARIOS:
            log(f'=== {speed:g}x, {scenario.name} ===')
            try:
                ok = attempt(scenario, speed, region)
            except Exception as e:  # a raise at speed is a failure at speed, not a crashed run
                log(f'{scenario.name} raised: {e!r}', 1)
                ok = False
            if not ok:
                failed.append(scenario.name)
            time.sleep(SETTLE_BETWEEN)
        rows.append((speed, not failed, failed))
        consecutive = consecutive + 1 if failed else 0
        print(f'{speed:g}x | {"pass" if not failed else "fail"}'
              + (f' | {", ".join(failed)}' if failed else ''))
        speed = round(speed + args.step, 3)

    close_flea(region)
    print('\nSpeed | success?')
    for value, passed, failed in rows:
        print(f'{value:g}x | {"pass" if passed else "fail"}'
              + (f' | failed: {", ".join(failed)}' if failed else ''))
    fastest = max((value for value, passed, _ in rows if passed), default=None)
    print(f'\nfastest speed all three scenarios passed at: '
          + (f'{fastest:g}x' if fastest else 'none, it failed at the current pace'))


if __name__ == '__main__':
    main()
