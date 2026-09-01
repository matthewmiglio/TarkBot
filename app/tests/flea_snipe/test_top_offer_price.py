"""The top offer's price, read the way the moonshine craft reads a purified water offer.

App layer under test: interact/snipe.py's price read on the topmost offer row
(snipe.read_price, price_region, currency_region and the PRICE_LEFT/TOP/WIDTH/HEIGHT offsets
from the PURCHASE button), reached through craft._top_offer. This is the same read the flea
BUYER decides a purchase on. Needs the LIVE game: it grabs the window and polls the board.

Run:  python tests/flea_snipe/test_top_offer_price.py           with a filtered flea board on screen
      python tests/flea_snipe/test_top_offer_price.py 140000    and say what the ceiling is

Assumes you are already on the flea, on an item search page with results. It does not open the
flea, does not search and does not buy: it only reads.

This is the tail of craft.buy_craft_input_item, on its own. That function right clicks the
ingredient slot, picks 'filter by item', lets the board load, applies the flea filters, and only
then does the two calls this test makes: craft._top_offer for the topmost PURCHASE button and
snipe.read_price for the number beside it. Those two are where a purified water offer either
gets bought or gets skipped, and the numbers that decide it (snipe.PRICE_LEFT, PRICE_TOP,
PRICE_WIDTH, PRICE_HEIGHT) are offsets from the button, so a board whose rows sit anywhere else
reads the wrong rectangle and the printed price is the only warning you get.

Writes tests/output/top_offer_price/window.png with the boxes drawn on it, and crop.png with the
price rectangle at 4x:

  yellow  the topmost PURCHASE button, which everything else is measured from
  green   snipe.price_region, the rectangle the digits are read out of
  blue    snipe.currency_region, the wider box the dollars icon is looked for in
  red     snipe.PRICE_GUTTER, the strip at the left that has to stay empty

Look at the pictures, not just the number. The gutter strip is the whole reason a clipped price
comes back None instead of coming back as its last three digits, and a price that reads fine on
a five figure offer can be cut on a six figure one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw  # noqa: E402

import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import window  # noqa: E402
from interact import craft, find, snipe  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'top_offer_price'
ZOOM = 4
CEILING = 140000  # craft_bot.DEFAULT_MAX['purified_water'], overridable on the command line


def draw(shot, region, button):
    """The window with the button and its three price rectangles on it, plus the crop."""
    ox, oy = region[0], region[1]  # a live window does not start at (0, 0)

    def rect(box, colour, width=2):
        left, top, w, h = box
        ImageDraw.Draw(marked).rectangle((left - ox, top - oy, left - ox + w - 1,
                                          top - oy + h - 1), outline=colour, width=width)

    price = snipe.price_region(button)
    gutter = (price[0], price[1], max(1, round(snipe.PRICE_GUTTER * find.scale())), price[3])
    marked = shot.copy()
    rect((button.left, button.top, button.width, button.height), '#e0c040')
    rect(snipe.currency_region(button), '#4080e0')
    rect(price, '#40c060')
    rect(gutter, '#e04040', width=1)

    OUT.mkdir(parents=True, exist_ok=True)
    marked.save(OUT / 'window.png')
    crop = shot.crop((price[0] - ox, price[1] - oy,
                      price[0] - ox + price[2], price[1] - oy + price[3]))
    crop.resize((crop.width * ZOOM, crop.height * ZOOM), Image.NEAREST).save(OUT / 'crop.png')
    return price


if __name__ == '__main__':
    ceiling = int(sys.argv[1]) if len(sys.argv) > 1 else CEILING
    find.VERBOSE = True  # the same narration a real craft pass writes into the session log

    hwnd = window.handle()  # raises WindowError if Tarkov is missing or duplicated
    rect = window.position(hwnd) + window.size(hwnd)
    region = screen.overlap(rect, screen.current().rect) or rect
    shot = screen.grab(region)
    print(f'window {region}, at {find.scale():.3f}x the 1080p the reference crops are stored at')

    # 1. The topmost PURCHASE button. This polls for up to craft.OFFER_WAIT, because a board
    # that has just been filtered or refreshed does not draw all its offers at once.
    top = craft._top_offer(region)
    if top is None:
        sys.exit(f'FAILED: no PURCHASE button anywhere on the board after '
                 f'{craft.OFFER_WAIT:.0f}s. An empty board and a board of LOCKED trader offers '
                 f'both look like this, and buy_craft_input_item raises Unbuyable on both.')
    print(f'top offer button at ({top.left}, {top.top}) {top.width}x{top.height}')

    # 2. And its price. read_price grabs the screen again itself, so draw the boxes first:
    # nothing has moved between the two grabs, and this way a crash below still leaves pictures.
    price_box = draw(shot, region, top)
    print(f'price region {price_box}')

    # The measurement PRICE_GUTTER is compared against, printed whether or not it refuses the
    # price. This is the number that was wrong on 2026-08-31: a whole 138 888 starting 6.8px
    # into its box, refused by a gutter of 8. See tests/test_price_gutter.py.
    edge = snipe.first_lit_column(screen.grab(price_box))
    print(f'leftmost lit column {edge if edge is None else round(edge, 1)} px into the box at '
          f'1080p, against a gutter of {snipe.PRICE_GUTTER}')

    price = snipe.read_price(top)

    if price is None:
        print('PRICE: unreadable')
        print('  Three things read as None and the narration above says which: a dollars icon '
              'beside the number, no glyph matching the price font, or something lit in the '
              'gutter strip meaning the number is wider than its box.')
    else:
        verdict = 'at or under' if price <= ceiling else 'OVER'
        print(f'PRICE: {price:,} roubles, {verdict} the {ceiling:,} ceiling')
        if price > ceiling:
            print(f'  A real craft pass would wait {craft.DEAR_DELAY:.0f}s and press '
                  f'{craft.REFRESH_KEY.upper()}, up to {craft.DEAR_REFRESHES} times, before '
                  f'giving up on this ingredient.')

    print(f'boxes drawn on the window: {OUT / "window.png"}')
    print(f'the price rectangle at {ZOOM}x: {OUT / "crop.png"}')
    print('The green box should hold the whole number with the red gutter strip empty beside '
          'it. If it does not, the offsets to edit are snipe.PRICE_LEFT and friends.')
