"""Show interact/craft.py's ingredient-checkmark read on a crafting screen.

App layer under test: interact/craft.py's craft_plan / validate_craftable (here through the
slickers wrapper validate_slickers_craftable), the READ that decides which ingredients are in the
stash. It reads the whole row once and calls an ingredient ready when a checkmark (CHECK_TARGET)
sits beneath its icon (_mark_beneath), not ready on an X, nothing, or an off-screen icon. The
check is scoped to the slickers craft's own row: it finds the band around the output slickers
first (craft.find_slickers_craft) and only reads ingredients and marks inside it. Not navigation,
not buying.

What it verifies: the (all_ready, missing) verdict, printed, plus a picture of exactly which
icons and marks it saw.

Live game OR no game: bare, it grabs the live window (needs the game, crafting screen open); hand
it saved frame paths and it needs no game.

Run:  python tests/hideout_craft_reads/test_slickers_requisites_check.py                 (grab the live window)
      python tests/hideout_craft_reads/test_slickers_requisites_check.py <frame.png ...>  (saved frames, no game)

Draws, to tests/output/slickers/<name>.png:
  - a cyan box around the band
  - a box around crackers and alyonka (yellow)
  - a box around every checkmark (green) and X (red) inside the band
and prints the (all_ready, missing) verdict.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import window  # noqa: E402
from interact import craft, find  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'slickers'
FONT = ImageFont.truetype('arialbd.ttf', 16)
YELLOW, GREEN, RED, CYAN = (255, 210, 0), (0, 220, 0), (220, 0, 0), (0, 220, 220)


def band_of(image):
    """The output-slickers band in this frame's own 0-based coords, or None."""
    tol = craft.ROW_TOL * find.scale()
    timers = find.find_all(craft.TIMER_TARGET, haystack=image)
    outs = [s for s in find.find_all(craft.SLICKERS_TARGET, haystack=image)
            if any(craft._center(t)[0] < craft._center(s)[0]
                   and abs(craft._center(t)[1] - craft._center(s)[1]) <= tol for t in timers)]
    if not outs:
        return None
    top = min(b.top for b in outs) - craft.SLICKERS_BAND_PAD
    bottom = max(b.top + b.height for b in outs) + craft.SLICKERS_BAND_PAD
    return (0, top, image.width, bottom - top)


def in_band(target, image, band):
    """find_all for `target` restricted to `band`, on a frame, boxes back in image coords."""
    l, t, w, h = band
    crop = image.crop((l, t, l + w, t + h))
    from pyscreeze import Box
    return [Box(b.left + l, b.top + t, b.width, b.height)
            for b in find.find_all(target, haystack=crop)]


def annotate(image, name, band):
    draw = ImageDraw.Draw(image)
    if band:
        l, t, w, h = band
        draw.rectangle((l, t, l + w, t + h), outline=CYAN, width=4)
        for target, color, label in ((craft.CRACKERS_TARGET, YELLOW, 'crackers'),
                                      (craft.ALYONKA_TARGET, YELLOW, 'alyonka'),
                                      (craft.CHECK_TARGET, GREEN, 'check'),
                                      (craft.X_TARGET, RED, 'X')):
            for b in in_band(target, image, band):
                draw.rectangle((b.left, b.top, b.left + b.width, b.top + b.height),
                               outline=color, width=3)
                draw.text((b.left, b.top - 17), label, font=FONT, fill=color)
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f'{name}.png')


def verdict_on(image, band):
    """The module's verdict replayed against a frame's band."""
    if band is None:
        return (False, ['crackers', 'alyonka'])
    checks = in_band(craft.CHECK_TARGET, image, band)
    alyonkas = in_band(craft.ALYONKA_TARGET, image, band)
    crackers_all = in_band(craft.CRACKERS_TARGET, image, band)
    alyonka = min(alyonkas, key=lambda b: b.top) if alyonkas else None
    crackers = crackers_all[0] if crackers_all else None
    missing = [n for n, icon in (('crackers', crackers), ('alyonka', alyonka))
               if icon is None or craft._mark_beneath(icon, checks) is None]
    return (not missing, missing)


if __name__ == '__main__':
    paths = sys.argv[1:]
    if paths:
        for path in paths:
            image = Image.open(path).convert('RGB')
            band = band_of(image)
            print(f'{Path(path).stem}: {verdict_on(image, band)}')
            annotate(image, Path(path).stem, band)
    else:
        import pyautogui
        hwnd = window.handle()
        region = window.position(hwnd) + window.size(hwnd)
        print(f'live: {craft.validate_slickers_craftable(region)}')
        shot = pyautogui.screenshot(region=region)  # own 0-based coords, so boxes line up on it
        annotate(shot, 'live', band_of(shot))
    print(f'-> {OUT}')
