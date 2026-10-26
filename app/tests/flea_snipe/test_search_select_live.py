"""Search one item the way the sniper does, step by step, and picture every step.

App layer under test: the search half of snipe_bot.FleaSniper.check_one: interact/snipe.search_for
(type, wait_for_suggestion, click suggestion_point, clear_search) and then purchase_buttons +
read_price on the top offer. Nothing is bought.

Each item: 1. type the name; 2. wait for the suggestion to show (the shipping poll); 3. click it,
let the board reload and check the board is one item; 4. read the top offer's price. Pictures
per step: <n>-<item>-1-typed / -2-waited (the patch the poll watches, yellow) / -3-board (name
strips green or red) / -4-price (the price box read, cyan). An item passes when the board is one
item and the price reads.

Run:  python tests/flea_snipe/test_search_select_live.py                      3 random Therapist items
      python tests/flea_snipe/test_search_select_live.py 10                   10 of them
      python tests/flea_snipe/test_search_select_live.py "RAM stick" "Can of Dr. Lupo's coffee beans"
      python tests/flea_snipe/test_search_select_live.py --frame tests/fixtures/snipe/mixed_board_1080p_1.png

The one-item check is every offer row naming the same thing: the item-name strip on
each row (NAME_LEFT/TOP/WIDTH/HEIGHT off that row's PURCHASE button) is cut to its lit text pixels
and compared with the top row's, allowing a few pixels of vertical slack because the PURCHASE
crops land a few pixels apart. A board filtered to one item names it on every row; the default
board after a missed click (the whole Barter items category) does not.

Tuned on the nine 1080p laptop boards in tests/fixtures/snipe/ (2026-10-26): four mixed_board_*
and five single_item_board_*. Rows naming the same item as the top row differ by at most 5.2% of
their text pixels (the ASh-12 rifle board), rows naming another item by at least 11.1%
(mixed_board_1080p_2), so SAME_ITEM sits at the midpoint, 8.15%. Same-item rows drift up the
further down the board they are and then level off, so a board that creeps toward the cutoff
wants each row compared with the one above it rather than with the top row.

What this cannot say on its own is that it is the *right* item: there is no text reader for
names, which is what the pictures in tests/output/search_select/ are for. A board that has not
moved at all since before the search is called out too: that is a click landing on the category
tree instead of the suggestion.

--frame runs only the step 3 check on a saved full-screen frame, no game and no clicks:
fixtures/snipe/mixed_board_* must come back MIXED and single_item_board_* ONE ITEM.

Game (live) or with a frame (no-game). Exits non-zero if any item fails.
"""
import argparse
import random
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing

from interact import find, snipe  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'search_select'

SAME_ITEM = snipe.SAME_ITEM  # the bot's own cutoff; tuned against these fixtures, see snipe.py


def check_board(image):
    """(one_item, rects, scores) for a board image, through the bot's snipe.name_disagreements."""
    buttons = sorted(find.find_all(snipe.PURCHASE_TARGET, haystack=image), key=lambda b: b.top)
    if not buttons:
        return False, [], []
    rects, scores = snipe.name_disagreements(image, buttons)
    return all(s <= SAME_ITEM for s in scores), rects, scores


def draw(image, rects, scores, path):
    shot = image.convert('RGB')
    pen = ImageDraw.Draw(shot)
    for (l, t, w, h), s in zip(rects, scores):
        colour = 'lime' if s <= SAME_ITEM else 'red'
        pen.rectangle((l, t, l + w, t + h), outline=colour, width=2)
        pen.text((l + w + 6, t + 4), f'{s:.1%}', fill=colour)
    shot.save(path)


def report(one_item, scores):
    rows = ', '.join(f'{s:.1%}' for s in scores) or 'no PURCHASE buttons found'
    print(f'  {"ONE ITEM" if one_item else "MIXED"}: {len(scores)} rows, '
          f'disagreement with the top row: {rows}')


parser = argparse.ArgumentParser()
parser.add_argument('names', nargs='*', help='item names to search; a bare number is a count of '
                                             'random Therapist items (default 3)')
parser.add_argument('--frame', help='check this saved full-screen frame only; no game, no clicks')
args = parser.parse_args()
OUT.mkdir(parents=True, exist_ok=True)

if args.frame:
    frame = Image.open(args.frame)
    find.scale = lambda: frame.height / find.REFERENCE_HEIGHT  # the frame's screen, not this one
    one_item, rects, scores = check_board(frame)
    report(one_item, scores)
    draw(frame, rects, scores, OUT / f'{Path(args.frame).stem}-checked.png')
    print(f'  picture: {OUT / (Path(args.frame).stem + "-checked.png")}')
    sys.exit(0 if one_item else 1)

import pyautogui  # noqa: E402  only the live path clicks
import snipe_bot  # noqa: E402  only the live path needs a Tarkov window
from interact import sell  # noqa: E402

watchlist = snipe_bot.for_trader(snipe_bot.targets(), 'Therapist')
if len(args.names) == 1 and args.names[0].isdigit():
    names = [row[0] for row in random.sample(watchlist, int(args.names[0]))]
else:
    names = args.names or [row[0] for row in random.sample(watchlist, 3)]

sniper = snipe_bot.FleaSniper(watchlist=watchlist)
region = sniper.region
if not snipe.open_clean_board(region):
    sys.exit('the flea did not open')

def local(rect):
    """A screen rect moved into the coordinates of a grab of `region`."""
    return (rect[0] - region[0], rect[1] - region[1], rect[2], rect[3])


def boxed(image, rect, colour, label, path):
    shot = image.convert('RGB')
    l, t, w, h = local(rect)
    pen = ImageDraw.Draw(shot)
    pen.rectangle((l, t, l + w, t + h), outline=colour, width=3)
    pen.text((l, t + h + 4), label, fill=colour)
    shot.save(path)


failures, box = 0, None
for i, name in enumerate(names, 1):
    print(f'\n== {i}/{len(names)}: {name}')
    stem = OUT / f'{i:02d}-{"".join(c if c.isalnum() else "_" for c in name)[:40]}'
    before = screen.grab(region)
    box = snipe.find_search_box(region, box)

    # 1. type the name. The same clicks and keys as snipe.search_for, split out so each step
    # gets its own picture; keep the two in step if search_for changes.
    pyautogui.click(*sell.jitter(pyautogui.center(box)))
    time.sleep(sell.MENU_DELAY)
    pyautogui.hotkey('ctrl', 'a')
    row = snipe.suggestion_row(region)
    unchanged = screen.grab(row)  # what the poll compares against, as search_for takes it
    pyautogui.typewrite(name)
    screen.grab(region).save(f'{stem}-1-typed.png')

    # 2. wait for the suggestion, through the shipping poll. The yellow box is the patch it
    # watches; on a working search it holds the suggestion when the poll returns.
    waited = snipe.wait_for_suggestion(region, unchanged)
    boxed(screen.grab(region), row, 'yellow', f'waited {waited}s', f'{stem}-2-waited.png')
    print(f'  2. suggestion poll returned after {waited}s'
          + (' (instantly: lit before anything could have been drawn?)' if waited == 0 else ''))
    if snipe.is_locked(region):
        snipe.clear_search(box)
        print('  locked, so nothing was clicked; not counted either way')
        continue

    # 3. click the suggestion, empty the box, let the board reload, then check it is one item.
    point = snipe.suggestion_point(box)
    pyautogui.click(*point)
    time.sleep(sell.MENU_DELAY)
    snipe.clear_search(box)
    time.sleep(snipe.BOARD_DELAY)
    board = screen.grab(region)
    one_item, rects, scores = check_board(board)
    print(f'  3. clicked the suggestion at {point}')
    report(one_item, scores)
    moved = np.abs(np.asarray(before.convert('L'), int) - np.asarray(board.convert('L'), int)).mean()
    if moved < 1:
        print(f'     the board did not change ({moved:.2f} mean grey difference): '
              'the click did not pick a suggestion')
    draw(board, rects, scores, f'{stem}-3-board.png')

    # 4. read the top offer's price, as check_one does.
    buttons = snipe.purchase_buttons(region)
    price = snipe.read_price(buttons[0]) if buttons else None
    if buttons:
        boxed(board, snipe.price_region(buttons[0]), 'cyan', f'read {price}', f'{stem}-4-price.png')
    print(f'  4. top offer price: {price if price is not None else "unreadable / no offers"}')
    print(f'  pictures: {stem}-[1-typed|2-waited|3-board|4-price].png')
    failures += not (one_item and price is not None)

print(f'\n{failures} of {len(names)} searches did not land on a single item')
sys.exit(1 if failures else 0)
