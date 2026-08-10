"""Clicks land off centre, but never off the button.

Run:  python tests/test_click_jitter.py

No game needed, nothing is clicked. jitter() is called directly, and the seven wired-up call
sites are driven with find faked so the offset actually reaches pyautogui.

Two failure modes are worth catching and they pull opposite ways. Too little spread and the
jitter is decoration: a thousand clicks on one pixel with a 1px wobble is still a column. Too
much and it walks off the control, which shows up as the bot pressing nothing at all and then
reporting something misleading further down.

The bound checked here is the smallest reference crop for each target, since find() returns
whichever crop matched and the smallest one gives the least room. Staying inside that box keeps
every click inside the tightest view of the control that exists.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import Image  # noqa: E402

from interact import find, sell  # noqa: E402

REFS = Path(__file__).resolve().parent.parent / 'interact' / 'reference_images'
DRAWS = 400
CENTRE = (1000, 500)

# (label, the call, the target folder its box comes from, expected x spread, expected y spread)
SITES = (
    ('click_add_offer', lambda: sell.click_add_offer(), 'add_offer', sell.CLICK_JITTER, sell.CLICK_JITTER),
    ('enter_price', lambda: sell.enter_price(1), 'price_rubles_input', sell.CLICK_JITTER, sell.CLICK_JITTER),
    ('click_place_offer', lambda: sell.click_place_offer(), 'place_offer_button', sell.CLICK_JITTER, sell.CLICK_JITTER),
)
# The gear and the OK button are jittered inside apply_flea_filters, which needs a whole filter
# window faked to reach them. Their offsets are the same call, so jitter()'s own checks cover
# the maths and this only has to prove the wiring on the three that stand alone.


def smallest(name):
    """(width, height) of the tightest crop in `name`, the least room any match can give."""
    sizes = [Image.open(p).size for p in (REFS / name).glob('*.png')]
    return min(s[0] for s in sizes), min(s[1] for s in sizes)


def spread(call, draws=DRAWS):
    """Run `call` `draws` times with the screen faked. Returns the clicked points."""
    clicked = []
    originals = (find.find_center, find.find, pyautogui.click, pyautogui.hotkey,
                 pyautogui.typewrite, sell.time.sleep)
    find.find_center = lambda *a, **kw: pyautogui.Point(*CENTRE)
    find.find = lambda *a, **kw: 'a box'
    pyautogui.click = lambda x, y=None, **kw: clicked.append((x, y))
    pyautogui.hotkey = lambda *a, **kw: None
    pyautogui.typewrite = lambda *a, **kw: None
    sell.time.sleep = lambda *a: None
    try:
        for _ in range(draws):
            call()
        return clicked
    finally:
        (find.find_center, find.find, pyautogui.click, pyautogui.hotkey,
         pyautogui.typewrite, sell.time.sleep) = originals


if __name__ == '__main__':
    print('jitter() itself:')
    assert sell.jitter(None) is None, 'a missing point has to survive being jittered'
    for x, y in ((3, 3), (2, 2), (3, 0)):
        points = [sell.jitter(CENTRE, x, y) for _ in range(DRAWS)]
        dx = {p[0] - CENTRE[0] for p in points}
        dy = {p[1] - CENTRE[1] for p in points}
        assert dx == set(range(-x, x + 1)), f'x={x} produced offsets {sorted(dx)}'
        assert dy == set(range(-y, y + 1)), f'y={y} produced offsets {sorted(dy)}'
        print(f'  ok  x +-{x} y +-{y}: every offset in range appears, and none outside it')
    assert all(p[1] == CENTRE[1] for p in (sell.jitter(CENTRE, 3, 0) for _ in range(DRAWS))), \
        'y=0 still moved the point, so the menu rows are being clicked off their text'
    print('  ok  y=0 pins the row exactly, for the 6px menu crops')

    print('wired up, and inside the smallest crop of each control:')
    for label, call, target, want_x, want_y in SITES:
        points = spread(call)
        assert len(points) == DRAWS, f'{label}: clicked {len(points)} times, wanted {DRAWS}'
        dx = sorted({p[0] - CENTRE[0] for p in points})
        dy = sorted({p[1] - CENTRE[1] for p in points})
        assert dx == list(range(-want_x, want_x + 1)), f'{label}: x offsets {dx}'
        assert dy == list(range(-want_y, want_y + 1)), f'{label}: y offsets {dy}'
        width, height = smallest(target)
        assert max(map(abs, dx)) < width / 2, f'{label}: x {max(dx)} escapes a {width}px crop'
        assert max(map(abs, dy)) < height / 2, f'{label}: y {max(dy)} escapes a {height}px crop'
        common = Counter(points).most_common(1)[0][1]
        assert common < DRAWS / 4, f'{label}: {common}/{DRAWS} clicks landed on one pixel'
        print(f'  ok  {label:20} x{dx[0]}..{dx[-1]} y{dy[0]}..{dy[-1]}, '
              f'inside the {width}x{height} crop')

    print('ok, every click is off centre and every click is on the button')
