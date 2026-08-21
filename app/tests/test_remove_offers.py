"""Run the whole stale-offer sweep on the live screen: my offers, cancel everything, back to browse.

Run:  python tests/test_remove_offers.py
      python tests/test_remove_offers.py --settle 5    (skip most of the 2 minute wait)
      python tests/test_remove_offers.py --quiet       (drop the per-reference-image lines)

Assumes the flea market is already open, on any tab. This one really does cancel offers, so
there is a countdown before it starts and Ctrl+C during it costs nothing. Writes
tests/output/remove_offers_before.png, _rows.png and _after.png. Exits non-zero if it never
found the my-offers tab, or if it did not end up back on the browse tab.

Narrates loudly on purpose: find.VERBOSE puts a timestamped line under every reference image
tried, matched or not, so a failed sweep says which crop stopped matching rather than only
that something did.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import frames  # noqa: E402
import session_log  # noqa: E402
import window  # noqa: E402
from interact import find, sell  # noqa: E402
from narrate import log  # noqa: E402

OUT = Path(__file__).parent / 'output'
COUNTDOWN = 5  # seconds to alt-tab into Tarkov, or to change your mind
# Every target this sweep reads, so the run opens with proof each one has reference images on
# disk. A missing folder raises here, before anything is clicked, rather than as a silent None
# halfway through a sweep that has already cancelled offers.
TARGETS = (sell.MY_OFFERS_TAB_TARGET, sell.BROWSE_SELECTED_TARGET, sell.BROWSE_UNSELECTED_TARGET,
           sell.REMOVE_BUTTON_TARGET, sell.ADD_OFFER_TARGET, sell.FLEA_ICON_TARGET)

if __name__ == '__main__':
    settle = sell.STALE_SETTLE
    if '--settle' in sys.argv:
        settle = float(sys.argv[sys.argv.index('--settle') + 1])
    find.VERBOSE = '--quiet' not in sys.argv
    session_log.start()  # the console scrolls past; the file is what gets read afterwards
    frames.start()  # a screenshot either side of every click this sweep makes

    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    OUT.mkdir(exist_ok=True)
    log(f'tarkov window hwnd {hwnd}, region {region}, screen {tuple(pyautogui.size())}, '
        f'reference scale {find.scale():.3f}x')

    log('reference images this sweep depends on:')
    for target in TARGETS:
        names = [p.name for p in find.images(target)]  # raises if the folder is missing or empty
        log(f'{target}: {len(names)} png(s) in {find.REFS / target}', 1)

    if not sell.is_flea_open(region):
        sys.exit('FAILED: the flea market is not open. Open it and run this again.')
    log('flea market is open')
    log(f'flea page right now: {sell._page_name(sell.is_on_browse_page(region))}', 1)

    rows = sell.stale_offer_rows(region)
    log(f'{len(rows)} offer rows to walk, {rows[0]} down to {rows[-1]}, '
        f'{rows[1][1] - rows[0][1]}px apart, settle {settle:.0f}s')

    # The click points drawn over the screen, numbered in the order they get clicked, so both
    # a wrong offset and a flipped sweep direction are obvious in the picture rather than only
    # in the clicking. 1 has to be the bottom one: removing an offer slides everything below
    # it upwards, so anything already clicked must sit below anything still to come.
    shot = pyautogui.screenshot(region=region)
    draw = ImageDraw.Draw(shot)
    for order, (x, y) in enumerate(reversed(rows), start=1):
        local = (x - region[0], y - region[1])
        draw.ellipse((local[0] - 5, local[1] - 5, local[0] + 5, local[1] + 5), outline='red', width=2)
        draw.text((local[0] + 10, local[1] - 6), str(order), fill='red')
    shot.save(OUT / 'remove_offers_rows.png')
    pyautogui.screenshot(region=region).save(OUT / 'remove_offers_before.png')
    log(f'wrote {OUT / "remove_offers_rows.png"} (click column, numbered in click order)', 1)
    log(f'wrote {OUT / "remove_offers_before.png"} (the screen as found)', 1)

    log(f'THIS CANCELS REAL OFFERS. Starting in {COUNTDOWN}s, Ctrl+C to bail.')
    for left in range(COUNTDOWN, 0, -1):
        log(f'{left}...', 1)
        time.sleep(1)

    started = time.monotonic()
    removed = sell.remove_stale_offers(region, settle=settle)
    elapsed = time.monotonic() - started

    pyautogui.screenshot(region=region).save(OUT / 'remove_offers_after.png')
    log(f'removed {removed} offers in {elapsed:.0f}s, wrote {OUT / "remove_offers_after.png"}')

    # Ending back on browse is the half the bot depends on: the next pass looks for the add
    # offer button and finds nothing if we were left sat on my-offers. The reference images
    # only capture each tab in one state, so which of them still matches is not a reliable
    # read of where we are; the add offer button is, and it only exists on the browse tab.
    log('checking where the sweep left the flea')
    if not find.find(sell.MY_OFFERS_TAB_TARGET, region):
        sys.exit('FAILED: no my-offers tab on screen, so the flea is not where we left it. '
                 'Check remove_offers_after.png')
    log('my-offers tab still on screen, so this is still the flea', 1)
    brightness = sell.add_offer_brightness(region)
    if brightness is None:
        sys.exit('FAILED: no add offer button, so we never got back to the browse tab. '
                 'Check remove_offers_after.png')
    log(f'add offer button found, brightest channel {brightness} '
        f'({"a slot is free" if brightness >= sell.MORE_OFFERS_BRIGHTNESS else "greyed out"})', 1)
    log(f'PASSED: back on the browse flea tab, {removed} offers removed in {elapsed:.0f}s')
