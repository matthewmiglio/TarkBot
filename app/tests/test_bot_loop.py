"""Run the bot's main loop against the live game, once or until you stop it.

Run:  python tests/test_bot_loop.py             (one pass, stash only)
      python tests/test_bot_loop.py --loop      (pass after pass until ctrl+c)
      python tests/test_bot_loop.py --scav      (scav cases SCAV_CHANCE of the time)
      python tests/test_bot_loop.py --scav-only (every pass takes the scav path)
      python tests/test_bot_loop.py --dry       (report what it would find, click nothing)

Flags combine, so --loop --scav-only is the long running scav test.

The real run drives your mouse: it opens the flea if closed, clicks add offer, drags the
offer window to the corner, picks an item, reads the price, undercuts it and lists it.
Writes tests/output/bot_loop.png afterwards. Exits non-zero if a step failed.

--loop calls stop() from the main thread while the bot runs on another, which is exactly
what the GUI's Stop button and window X do, so it tests that path and not just the loop.
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import sell_bot as bot_module  # noqa: E402
import tarkov_window  # noqa: E402
from sell_bot import Tarkbot  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the clicks land nowhere useful otherwise
STOP_TIMEOUT = 30  # seconds to let the bot unwind after ctrl+c before we call it wedged


def report(region, scav):
    """What each step of the loop would find right now, without touching anything."""
    print(f'flea open:      {sell.is_flea_open(region)}')
    print(f'add offer:      {find.find(sell.ADD_OFFER_TARGET, region) or "not on screen"}')
    print(f'offer window:   {find.find(sell.OFFER_TARGET, region) or "not on screen"}')
    print(f'item selected:  {sell.is_item_selected(region)}')
    price = sell.get_price(region)
    print(f'price:          {price}' + (f' -> would list at {sell.undercut_price(price)}'
                                        if price is not None else ' (unreadable)'))
    print(f'roubles field:  {find.find(sell.PRICE_INPUT_TARGET, region) or "not on screen"}')
    print(f'place offer:    {find.find(sell.PLACE_OFFER_TARGET, region) or "not on screen"}')
    try:
        print(f'stash region:   {sell.infer_inventory_region(region)}')
    except LookupError as e:
        print(f'stash region:   {e}')
    if scav:
        print(f'scav cases:     {len(find.find_all("scav_case", region))} on screen '
              f'({bot_module.SCAV_CHANCE:.0%} of runs would use one)')


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    only = '--scav-only' in sys.argv
    scav = only or '--scav' in sys.argv
    if only:
        bot_module.SCAV_CHANCE = 1.0  # select_item reads this at call time, so patching it here works
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    print(f'window {region}, target_scav_cases={scav}')

    if dry:
        report(region, scav)
        sys.exit(0)

    for n in range(DELAY, 0, -1):
        print(f'starting in {n}...')
        time.sleep(1)

    started = time.monotonic()
    tarkbot = Tarkbot(target_scav_cases=scav)
    failure = None
    if '--loop' in sys.argv:
        worker = threading.Thread(target=tarkbot.start, daemon=True)
        worker.start()
        print('looping, ctrl+c to stop')
        try:
            while worker.is_alive():
                worker.join(0.5)  # a bare join swallows ctrl+c on Windows, so poll it
            failure = RuntimeError('the loop ended on its own, see the traceback above')
        except KeyboardInterrupt:
            print('\nstop requested, letting the current pass unwind')
            stopped_at = time.monotonic()
            tarkbot.stop()
            worker.join(timeout=STOP_TIMEOUT)
            print(f'stopped after {time.monotonic() - stopped_at:.1f}s')
            if worker.is_alive():
                failure = RuntimeError(f'still running {STOP_TIMEOUT}s after stop()')
    else:
        try:
            tarkbot.sell_one()  # one pass; start() would never return
        except (RuntimeError, LookupError) as e:  # the steps raise these when a screen is wrong
            failure = e

    OUT.mkdir(exist_ok=True)
    path = OUT / 'bot_loop.png'
    pyautogui.screenshot(region=region).save(path)
    print(f'took {time.monotonic() - started:.1f}s, wrote {path}')
    if failure:
        sys.exit(f'FAILED: {failure}')
    print('loop completed')
