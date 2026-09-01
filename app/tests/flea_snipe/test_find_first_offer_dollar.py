"""Is the topmost comparable offer priced in dollars, and where exactly did the glyph land.

App layer under test: the flea BUYER's currency check on the topmost comparable offer,
interact/snipe.py's DOLLARS_TARGET crops matched inside interact/sell.py's
grab_first_item_price_region (FIRST_ITEM_PRICE_FRACTIONS). This is that region's tuning loop
and the bridge between snipe's dollars crops and sell's first-offer box.

Run:  python tests/flea_snipe/test_find_first_offer_dollar.py              against the live game
      python tests/flea_snipe/test_find_first_offer_dollar.py frame.png    against a saved full-window shot

No game needed if you pass a saved frame; bare it grabs the live window.

Writes tests/output/first_offer_dollar/window.png: the whole frame, sell's price region boxed
in yellow, the whole offer row boxed dim behind it for context, and the dollars icon boxed in
red when one was found. Look at it. A miss because the offer is in roubles and a miss because
the yellow box is in the wrong place read identically in a one-line summary, and only one of
them is good news, so this is also the tuning loop for FIRST_ITEM_PRICE_FRACTIONS.

%APPDATA%/tarkbot/frames/ is full of saved frames to point this at, so no game is needed.

Note on where this belongs. Nothing in the sell path reads currency yet: sell.get_price refuses
a pack offer (first_offer_is_a_pack) and reads the number otherwise, whatever currency it is
quoted in. The dollars crops live in interact/snipe.py, aimed at a purchase button's own row
rather than at a fixed region. This script is the bridge: snipe's crops against sell's
grab_first_item_price_region, which is what a currency check in sell mode would have to do.

Exits non-zero only if the region runs off the picture. A rouble offer is a pass, not a fail.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw  # noqa: E402

import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import window  # noqa: E402
from interact import find, sell  # noqa: E402
from interact.snipe import DOLLARS_TARGET  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'first_offer_dollar'
REGION_COLOR = '#e0c040'   # the price region, the one being tuned
ROW_COLOR = '#4a5a6a'      # the whole offer row, drawn only for context
GLYPH_COLOR = '#e04040'    # the dollars icon, when one is found


def from_file(path):
    """A saved screenshot, treated as the whole window sitting at the origin."""
    shot = Image.open(path).convert('RGB')
    return shot, (0, 0, shot.width, shot.height), path.name


def from_game():
    """The live Tarkov window, clipped to the chosen monitor the way every mode does it."""
    hwnd = window.handle()  # raises WindowError if Tarkov is missing or duplicated
    rect = window.position(hwnd) + window.size(hwnd)
    region = screen.overlap(rect, screen.current().rect) or rect
    return screen.grab(region), region, 'the live window'


if __name__ == '__main__':
    shot, region, what = (from_file(Path(sys.argv[1])) if len(sys.argv) > 1 else from_game())
    box = sell.grab_first_item_price_region(region)
    row = sell.grab_first_offer_region(region)
    print(f'{what}: window {region}')
    print(f'price region  {box}  from {sell.FIRST_ITEM_PRICE_FRACTIONS}')
    print(f'offer row     {row}  (context only, what first_offer_is_a_pack reads)')

    # Back into the picture's own coordinates, since a live window does not start at (0, 0).
    left, top = box[0] - region[0], box[1] - region[1]
    right, bottom = left + box[2], top + box[3]
    if right > shot.width or bottom > shot.height:
        sys.exit(f'FAILED: the region runs off a {shot.width}x{shot.height} screenshot')

    # A saved frame carries its own resolution, and find.scale() reads the live screen, so a
    # 1440p frame opened on a 1080p desktop would be matched with needles sized for the desktop.
    find.scale = lambda height=shot.height: height / find.REFERENCE_HEIGHT
    crop = shot.crop((left, top, right, bottom))
    glyph = find.find(DOLLARS_TARGET, haystack=crop)  # crop coords, so shifted back below

    marked = shot.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle((row[0] - region[0], row[1] - region[1],
                    row[0] - region[0] + row[2] - 1, row[1] - region[1] + row[3] - 1),
                   outline=ROW_COLOR, width=2)
    draw.rectangle((left, top, right - 1, bottom - 1), outline=REGION_COLOR, width=3)
    if glyph:
        at = (left + int(glyph.left), top + int(glyph.top))
        draw.rectangle((at[0] - 2, at[1] - 2,
                        at[0] + int(glyph.width) + 1, at[1] + int(glyph.height) + 1),
                       outline=GLYPH_COLOR, width=2)
        print(f'DOLLARS: found {DOLLARS_TARGET} at {at} in the frame, '
              f'{int(glyph.width)}x{int(glyph.height)}, '
              f'({int(glyph.left)}, {int(glyph.top)}) inside the region')
    else:
        print(f'ROUBLES: no {DOLLARS_TARGET} anywhere in the first offer region '
              f'({len(find.images(DOLLARS_TARGET))} reference crop(s) tried at confidence '
              f'{find.confidence_for(DOLLARS_TARGET)})')

    OUT.mkdir(parents=True, exist_ok=True)
    marked.save(OUT / 'window.png')
    print(f'wrote {OUT / "window.png"}: yellow is the price region, grey is the whole offer '
          f'row, red is the dollars icon')
    print('the price and its currency glyph should sit inside the yellow box, with nothing '
          'from the rows either side. If they do not, edit FIRST_ITEM_PRICE_FRACTIONS in '
          'interact/sell.py and run this again.')
