"""Set the flea market filters to roubles, from players only, condition from 100%.

Run:  python tests/test_apply_flea_filters.py        (do it)
      python tests/test_apply_flea_filters.py --dry  (report the state, click nothing)

Drives your mouse: opens the filter window, works both dropdowns, types 100 into the
condition-from box, then OKs out. Anything already set is left alone, so running it twice in a row is safe and
the second run should touch nothing but the OK button.

Writes tests/output/flea_filters_before.png and _after.png (full window). The after shot is
taken with the filter window reopened, so it shows what the settings actually ended up as
rather than the closed window OK leaves behind; it escapes back out afterwards. Exits non-zero
if a step failed or the filters did not end up set.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the clicks land nowhere useful otherwise


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
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    print(f'window {region}')

    if '--dry' in sys.argv:
        report(region)
        sys.exit(0)

    for n in range(DELAY, 0, -1):
        print(f'starting in {n}...')
        time.sleep(1)

    OUT.mkdir(exist_ok=True)
    pyautogui.screenshot(region=region).save(OUT / 'flea_filters_before.png')

    started = time.monotonic()
    ok = sell.apply_flea_filters(region)
    print(f'apply_flea_filters -> {ok}, took {time.monotonic() - started:.1f}s')

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
