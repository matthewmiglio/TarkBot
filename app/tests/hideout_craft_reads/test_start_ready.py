"""Outline every START button on a crafting screen: green when ready, red when greyed out.

App layer under test: interact/craft.py's START-button brightness READ, the brightest-channel
threshold craft.START_READY_BRIGHTNESS that get_craft_state uses to tell a lit (ready) START plate
from a greyed one. This reads brightness straight off the image it is annotating and compares to
craft.START_READY_BRIGHTNESS, so the box colour is the real decision, not a re-implementation of
it. Not navigation, not buying.

What it verifies: which START buttons read as ready, printed as the brightest channel per button
and drawn as a green (ready) or red (not ready) box.

Live game OR no game: bare, it grabs the live window (needs the game, crafting screen open); hand
it saved frame paths and it needs no game.

Run:  python tests/hideout_craft_reads/test_start_ready.py                 (grab the live window)
      python tests/hideout_craft_reads/test_start_ready.py <frame.png ...>  (saved frames, no game needed)

Writes tests/output/start_ready/<name>.png and prints the brightest channel per button.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import window  # noqa: E402
from interact import craft, find  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'start_ready'
GREEN = (0, 220, 0)
RED = (220, 0, 0)


def brightest(image, box):
    crop = image.crop((box.left, box.top, box.left + box.width, box.top + box.height))
    return int(np.asarray(crop.convert('RGB')).max())


def annotate(image, name):
    """Box every START button on `image`, ready green and not-ready red. Returns any found."""
    boxes = sorted(craft.start_buttons() if image is None else
                   find.find_all(craft.START_TARGET, haystack=image), key=lambda b: b.top)
    draw = ImageDraw.Draw(image)
    for i, box in enumerate(boxes):
        bright = brightest(image, box)
        ready = bright >= craft.START_READY_BRIGHTNESS
        xy = (box.left, box.top, box.left + box.width, box.top + box.height)
        draw.rectangle(xy, outline=GREEN if ready else RED, width=3)
        print(f'  {name} [{i}] top={box.top:5d} brightest={bright:3d} '
              f'-> {"READY" if ready else "not ready"}')
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f'{name}.png')
    return boxes


def frame(path):
    return Image.open(path).convert('RGB')


def live():
    import pyautogui
    hwnd = window.handle()
    return pyautogui.screenshot(region=window.position(hwnd) + window.size(hwnd))


if __name__ == '__main__':
    paths = sys.argv[1:]
    if paths:
        for path in paths:
            annotate(frame(path), Path(path).stem)
    else:
        annotate(live(), 'live')
    print(f'-> {OUT}')
