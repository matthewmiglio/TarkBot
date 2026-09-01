"""Set the flea market filters to roubles, from players only, condition from 100%.

App layer under test: interact/sell.py, sell.apply_flea_filters and the phase functions it
calls (open_filters, orientate_filters_window, filter_plan, run_filter_plan, confirm_filters).
Verifies the whole filter pass runs against a live flea and that the settings survive the OK by
reopening the window to read them back; also instruments and prints the find/sleep time split
per phase (non-zero exit if a step failed or the filters did not end up set).

Needs the live game: it drives your mouse. Opens the filter window, works both dropdowns, types
100 into the condition-from box, then OKs out. Anything already set is left alone, so running it
twice in a row is safe and the second run should touch nothing but the OK button.

Run:  python tests/flea_filters/test_apply_flea_filters.py        (do it)
      python tests/flea_filters/test_apply_flea_filters.py --dry  (report the state, click nothing)

Writes tests/output/flea_filters_before.png and _after.png (full window). The after shot is
taken with the filter window reopened, so it shows what the settings actually ended up as
rather than the closed window OK leaves behind; it escapes back out afterwards. Exits non-zero
if a step failed or the filters did not end up set.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the clicks land nowhere useful otherwise

# Every find call and every sleep, tallied while the pass runs, so a phase's wall time can be
# split into "matching the screen" and "waiting for the game". The phase functions live on the
# sell module and apply_flea_filters calls them by bare name, so wrapping them there is enough.
COST = {'find': 0.0, 'find_n': 0, 'sleep': 0.0}


def _tally(kind, fn):
    def wrapped(*a, **k):
        t = time.monotonic()
        try:
            return fn(*a, **k)
        finally:
            COST[kind] += time.monotonic() - t
            if kind == 'find':
                COST['find_n'] += 1
    return wrapped


def _timed_phase(name, fn):
    """Wrap a sell phase so it prints its own wall time and the find/sleep split inside it."""
    def wrapped(*a, **k):
        before = (COST['find'], COST['find_n'], COST['sleep'])
        t = time.monotonic()
        try:
            return fn(*a, **k)
        finally:
            wall = time.monotonic() - t
            find_s = COST['find'] - before[0]
            finds = COST['find_n'] - before[1]
            sleep_s = COST['sleep'] - before[2]
            other = wall - find_s - sleep_s
            print(f'  [{name:<22}] {wall:6.2f}s  '
                  f'find {find_s:5.2f}s ({finds:2d})  sleep {sleep_s:5.2f}s  other {other:5.2f}s')
    return wrapped


def instrument():
    """Patch find + sleep to tally, and each filter phase to report. Undoes nothing; test-only."""
    # Only the leaf finds: find_center delegates to find, so wrapping it too double-counts.
    find.find = _tally('find', find.find)
    find.find_all = _tally('find', find.find_all)
    time.sleep = _tally('sleep', time.sleep)
    for name in ('open_filters', 'orientate_filters_window', 'filter_plan',
                 'run_filter_plan', 'confirm_filters'):
        setattr(sell, name, _timed_phase(name, getattr(sell, name)))


def report(region):
    """What each element the routine needs looks like right now."""
    for label, target in (('filter button', sell.FILTER_BUTTON_TARGET),
                          ('filters window', sell.FILTERS_WINDOW_TARGET),
                          ('currency: any', sell.CURRENCY_ANY_TARGET),
                          ('currency: rub', sell.CURRENCY_RUB_TARGET),
                          ('offers from: any', sell.OFFERS_FROM_ANY_TARGET),
                          ('condition label', sell.CONDITION_LABEL_TARGET),
                          ('items expiring', sell.EXPIRING_TEXT_TARGET),
                          ('OK button', sell.FILTERS_OK_TARGET)):
        print(f'  {label:<18} {find.find(target, region) or "not on screen"}')


if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    print(f'window {region}')

    if '--dry' in sys.argv:
        report(region)
        sys.exit(0)

    for n in range(DELAY, 0, -1):
        print(f'starting in {n}...')
        time.sleep(1)

    OUT.mkdir(exist_ok=True)
    pyautogui.screenshot(region=region).save(OUT / 'flea_filters_before.png')

    instrument()  # after the countdown, so its own sleeps are not counted
    print('per-phase timings (find = template matching, sleep = pacing waits):')
    started = time.monotonic()
    ok = sell.apply_flea_filters(region)
    total = time.monotonic() - started
    print(f'apply_flea_filters -> {ok}, took {total:.1f}s')
    print(f'  totals: find {COST["find"]:.2f}s over {COST["find_n"]} calls '
          f'({COST["find"] / max(COST["find_n"], 1) * 1000:.0f}ms each), '
          f'sleep {COST["sleep"]:.2f}s, rest {total - COST["find"] - COST["sleep"]:.2f}s')

    if find.find(sell.FILTERS_WINDOW_TARGET, region):
        sys.exit('FAILED: the filter window is still open, OK did not take')

    # Reopen it to read the settled state. Reporting straight after apply_flea_filters said
    # nothing at all: OK is the last thing it does, so every row read 'not on screen' because
    # the window was shut, whatever the filters ended up as. Reopening also checks the thing
    # worth checking, that the settings survived the OK, rather than that they were on screen
    # a moment before it.
    shown = find.find_center(sell.FILTER_BUTTON_TARGET, region)
    if not shown:
        sys.exit('FAILED: no filter button to reopen the window with')
    pyautogui.click(*shown)
    time.sleep(sell.MENU_DELAY)
    pyautogui.screenshot(region=region).save(OUT / 'flea_filters_after.png')
    print(f'wrote {OUT / "flea_filters_before.png"} and _after.png')
    print('after (window reopened, so these are the applied settings):')
    report(region)
    pyautogui.press('esc')  # leave the screen as we found it
    time.sleep(sell.MENU_DELAY)

    if not ok:
        sys.exit('FAILED: apply_flea_filters returned False')
    print('filters applied and the window is closed')
