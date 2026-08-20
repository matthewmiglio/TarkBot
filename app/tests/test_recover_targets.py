"""The real recovery, the real FleaSeller, against the real Tarkov window. Nothing is faked.

Run:  python tests/test_recover_targets.py          report what is on screen, press nothing
      python tests/test_recover_targets.py --run    run the real recovery, clicks and all

Needs the game up, with whatever you want checked already on screen. The default reads only, so
it is safe to point at a scav case with an offer creation window over it, which is the state
worth pointing it at.

This is the half test_recover_loop.py cannot cover. That one fakes find() so it can pass with no
game open, which makes it airtight about the loop's logic and silent about whether any crop
matches the actual game. Every window could stop matching tomorrow and it would still pass.

So nothing here is stubbed. It builds a real FleaSeller, which finds the window, picks the monitor
and works out the search region exactly as the Start button does, and --run then calls that
bot's own _recover. No copy of the region maths, no copy of the loop: if this passes, that is
the shipping code path passing.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sell_bot  # noqa: E402
from interact import find, sell  # noqa: E402

# The three reads the recovery loop is built out of, in the order it does them.
TARGETS = ((sell.OFFER_TARGET, 'offer creation window', 'escape, first because it sits on top'),
           (sell.SCAV_WINDOW_TARGET, 'scav case window', 'escape'),
           (sell.FILTERS_WINDOW_TARGET, 'flea filter window', 'escape'),
           (sell.FLEA_ICON_TARGET, 'flea tab', 'the finish line, what recovery is aiming at'))
REFS = Path(__file__).resolve().parent.parent / 'interact' / 'reference_images'


def report(region):
    """Print what each target matches right now. Returns {target: box or None}."""
    seen = {}
    for target, what, why in TARGETS:
        crops = len(list((REFS / target).glob('*.png')))
        box = find.find(target, region)
        seen[target] = box
        where = f'at ({int(box.left)}, {int(box.top)})' if box else ''
        print(f'  {"FOUND   " if box else "no match"}  {what:22} {target:28} '
              f'{crops} crop(s)  {where}')
        print(f'            -> {why}')
    return seen


if __name__ == '__main__':
    # The real thing: finds the window, picks the monitor, works out the region. Raises
    # WindowError if Tarkov is not up, which is the correct way for this to fail.
    bot = sell_bot.FleaSeller()
    print(f'\nreal FleaSeller on monitor {bot.monitor.label}, searching {bot.region}\n')

    if '--run' in sys.argv:
        print(f'running the bot\'s own _recover: real clicks, real waits, up to '
              f'{sell_bot.RECOVER_ROUNDS} rounds of '
              f'{sell.RECOVER_DELAY}s. Hands off the mouse.\n')
        started = time.monotonic()
        bot._recover()
        elapsed = time.monotonic() - started
        print(f'\n{elapsed:.1f}s on the clock. That is the stopwatch, not an assertion.\n')

    seen = report(bot.region)
    still_open = [what for target, what, _ in TARGETS[:3] if seen[target]]
    print()
    if seen[sell.FLEA_ICON_TARGET] and not still_open:
        print('the flea tab is visible and nothing is left open. Recovery has nothing to do. OK')
        sys.exit(0)
    if still_open:
        print(f'still open: {", ".join(still_open)}')
        print('run again with --run to have the real recovery clear them.' if '--run' not in
              sys.argv else 'recovery ran and these are STILL up, so escape is not closing them.')
    elif not seen[sell.FLEA_ICON_TARGET]:
        print('nothing above matched and the flea tab is not visible either, so whatever is on '
              'screen has no crops. Recovery would burn all its rounds and give up.')
    sys.exit(1)
