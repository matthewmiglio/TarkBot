"""Where sell.grab_first_offer_region lands, drawn on the screen it was cut from.

App layer under test: interact/sell.py's grab_first_offer_region and FIRST_OFFER_FRACTIONS, the
box around the topmost comparable offer row that the flea BUYER's currency check reads from.
This is that box's tuning loop.

Run:  python tests/flea_snipe/test_first_offer_region.py              against the live game
      python tests/flea_snipe/test_first_offer_region.py frame.png    against a saved full-window screenshot

No game needed if you pass a saved frame; bare it grabs the live window.

Writes two pictures to tests/output/first_offer_region/: the whole window with the box drawn on
it in yellow, and the crop itself at 2x. Look at both, the way test_ruble_region.py wants you
to: a box in the wrong place and an empty board look identical in a summary.

The tuning loop for sell.FIRST_OFFER_FRACTIONS: run it, look, edit the four numbers at the top
of interact/sell.py, run it again. No game needed if you pass a saved frame, and
%APPDATA%/tarkbot/frames/ is full of them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw  # noqa: E402

import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import window  # noqa: E402
from interact import sell  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'first_offer_region'
ZOOM = 2


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
    box = sell.grab_first_offer_region(region)
    print(f'{what}: window {region}')
    print(f'fractions {sell.FIRST_OFFER_FRACTIONS} -> region {box}')

    # Back into the picture's own coordinates, since a live window does not start at (0, 0).
    left, top = box[0] - region[0], box[1] - region[1]
    right, bottom = left + box[2], top + box[3]
    if right > shot.width or bottom > shot.height:
        sys.exit(f'FAILED: the region runs off a {shot.width}x{shot.height} screenshot')

    OUT.mkdir(parents=True, exist_ok=True)
    marked = shot.copy()
    ImageDraw.Draw(marked).rectangle((left, top, right - 1, bottom - 1), outline='#e0c040', width=3)
    marked.save(OUT / 'window.png')

    crop = shot.crop((left, top, right, bottom))
    crop.resize((crop.width * ZOOM, crop.height * ZOOM), Image.NEAREST).save(OUT / 'crop.png')
    print(f'crop is {crop.width}x{crop.height}, written {ZOOM}x to {OUT / "crop.png"}')
    print(f'the whole window with the box on it is {OUT / "window.png"}')
    print('the topmost offer row should sit inside the box. If it does not, edit '
          'FIRST_OFFER_FRACTIONS in interact/sell.py and run this again.')
