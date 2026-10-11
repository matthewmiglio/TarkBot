"""One snipe pass over one random watchlist item, live: open, search, click, read, maybe buy.

App layer under test: snipe_bot.FleaSniper.check_one, the whole per-item pass, behind
interact/snipe.open_clean_board and snipe.apply_flea_filters. Needs the LIVE game and SPENDS
REAL ROUBLES: a top offer at least MARGIN under trader value is bought.

Run:  python tests/flea_snipe/test_snipe_one_item_live.py              one random item
      python tests/flea_snipe/test_snipe_one_item_live.py 5            five, a fresh random item each
      python tests/flea_snipe/test_snipe_one_item_live.py 5 --margin 2000

Each loop: open the flea (open_clean_board), pick a random row off snipe_targets.csv, then
check_one types its name, clicks the suggestion, waits for the board, reads the top offer's
price, and buys it when trader price - asking >= margin. The filters go on after each open, as
sweep_once does after its own: without them the top row is whatever the board is sorted by.

Exits non-zero if any loop raised. A dear offer, a locked item or an unreadable price is not a
failure; each is printed and the loop moves on.
"""
import argparse
import random
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import screen  # noqa: E402,F401  patches pyautogui.screenshot, so import it before grabbing

import snipe_bot  # noqa: E402
from interact import snipe  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument('loops', nargs='?', type=int, default=1)
parser.add_argument('--margin', type=int, default=snipe_bot.MARGINS[snipe_bot.DEFAULT_MARGIN])
args = parser.parse_args()

sniper = snipe_bot.FleaSniper(margin=args.margin)
failures = 0
for i in range(1, args.loops + 1):
    name, trader, trader_price = random.choice(sniper.watchlist)
    print(f'\n== loop {i}/{args.loops}: {name} ({trader} pays {trader_price:,}, '
          f'buying at {trader_price - args.margin:,} or under)')
    try:
        if not snipe.open_clean_board(sniper.region):
            raise RuntimeError('the flea did not open')
        # ponytail: every loop, since a reopened flea is not known to keep them; hoist it out
        # of the loop once that is checked, it is ~15s a pass
        if not snipe.apply_flea_filters(sniper.region):
            raise RuntimeError('the flea filters would not go on')
        print('BOUGHT' if sniper.check_one(name, trader, trader_price) else 'not bought')
    except Exception:  # noqa: BLE001  one bad loop is a result to print, not the end of the run
        failures += 1
        traceback.print_exc()

print('\n' + ', '.join(f'{label} {sniper.stats[key]}' for key, label in snipe_bot.STAT_LABELS))
print(f'{failures} of {args.loops} loops raised')
sys.exit(1 if failures else 0)
