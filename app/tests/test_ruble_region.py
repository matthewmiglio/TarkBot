"""Where snipe.ruble_region lands, drawn on the screen it was cut from.

Run:  python tests/test_ruble_region.py              against the live game
      python tests/test_ruble_region.py frame.png    against a saved full-window screenshot

Writes two pictures to tests/output/ruble_region/: the whole window with the box drawn on it in
yellow, and the crop itself at 4x. Look at both. A box in the wrong place and a balance that
simply is not there look identical in a summary and completely different in a picture.

This is the tuning loop for snipe.RUBLE_ROI_FRACTIONS: run it, look, edit the four numbers at
the top of interact/snipe.py, run it again. No game needed if you pass a saved frame, and
%APPDATA%/tarkbot/frames/ is full of them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw  # noqa: E402

import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import tarkov_window  # noqa: E402
from interact import snipe  # noqa: E402

OUT = Path(__file__).resolve().parent / 'output' / 'ruble_region'
ZOOM = 4


def from_file(path):
    """A saved screenshot, treated as the whole window sitting at the origin."""
    shot = Image.open(path).convert('RGB')
    return shot, (0, 0, shot.width, shot.height), path.name


def from_game():
    """The live Tarkov window, clipped to the chosen monitor the way every mode does it."""
    hwnd = tarkov_window.handle()  # raises WindowError if Tarkov is missing or duplicated
    window = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    region = screen.overlap(window, screen.current().rect) or window
    return screen.grab(region), region, 'the live window'


if __name__ == '__main__':
    shot, region, what = (from_file(Path(sys.argv[1])) if len(sys.argv) > 1 else from_game())
    box = snipe.ruble_region(region)
    print(f'{what}: window {region}')
    print(f'fractions {snipe.RUBLE_ROI_FRACTIONS} -> region {box}')

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
    print('the balance should sit inside the box with a little room around it. If it does not, '
          'edit RUBLE_ROI_FRACTIONS in interact/snipe.py and run this again.')
