"""Print craft.get_slickers_craft_state for a crafting screen.

Run:  python tests/test_get_slickers_craft_state.py                 (grab the live window)
      python tests/test_get_slickers_craft_state.py <frame.png ...>  (saved frames, no game)

Prints one of: not started / done / ready / producing. On a saved frame the same logic is
replayed against the image so the reported state is the module's, with the four targets and the
GET ITEMS brightness threshold coming straight from craft.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import window  # noqa: E402
from interact import craft, find  # noqa: E402


def output_box(image):
    """The output slickers bar in a frame, timer-anchored then rightmost, mirroring craft."""
    tol = craft.ROW_TOL * find.scale()
    timers = find.find_all(craft.TIMER_TARGET, haystack=image)
    slicks = find.find_all(craft.SLICKERS_TARGET, haystack=image)
    timed = [s for s in slicks
             if any(craft._center(t)[0] < craft._center(s)[0]
                    and abs(craft._center(t)[1] - craft._center(s)[1]) <= tol for t in timers)]
    pool = timed or slicks
    return max(pool, key=lambda b: b.left) if pool else None


def find_in_row(target, image, output):
    """find for `target` within the output row's full-width band, boxes in image coords."""
    top = max(0, output.top - craft.SLICKERS_BAND_PAD)
    height = output.height + 2 * craft.SLICKERS_BAND_PAD
    crop = image.crop((0, top, image.width, top + height))
    from pyscreeze import Box
    box = find.find(target, haystack=crop)
    return Box(box.left, box.top + top, box.width, box.height) if box else None


def bright(image, box):
    c = image.crop((box.left, box.top, box.left + box.width, box.top + box.height))
    return int(np.asarray(c.convert('RGB')).max())


def state_of(image):
    output = output_box(image)
    if output is None:
        return 'producing'
    gi = find_in_row(craft.GET_ITEMS_TARGET, image, output)
    if gi:
        return 'done' if bright(image, gi) >= craft.GET_ITEMS_HIGHLIGHT_BRIGHTNESS else 'not started'
    return 'ready' if find_in_row(craft.START_TARGET, image, output) else 'producing'


if __name__ == '__main__':
    paths = sys.argv[1:]
    if paths:
        for path in paths:
            print(f'{Path(path).stem}: {state_of(Image.open(path).convert("RGB"))}')
    else:
        hwnd = window.handle()
        region = window.position(hwnd) + window.size(hwnd)
        print(f'live: {craft.get_slickers_craft_state(region)}')
