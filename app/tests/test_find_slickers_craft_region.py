"""Show craft.find_slickers_craft's band on a crafting screen.

Run:  python tests/test_find_slickers_craft_region.py                 (grab the live window)
      python tests/test_find_slickers_craft_region.py <frame.png ...>  (saved frames, no game)

Draws, to tests/output/slickers_region/<name>.png:
  - a yellow box around each OUTPUT slickers match (timer clock to its left)
  - a magenta box around every timer clock
  - a cyan box around the resulting band
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import window  # noqa: E402
from interact import craft, find  # noqa: E402

OUT = Path(__file__).parent / 'output' / 'slickers_region'
YELLOW, MAGENTA, CYAN = (255, 210, 0), (220, 0, 220), (0, 220, 220)
try:
    FONT = ImageFont.truetype('arialbd.ttf', 26)
except OSError:  # no truetype on this box, fall back to the tiny bitmap font
    FONT = ImageFont.load_default()


def outputs_in(image):
    """Output slickers and timer boxes in `image`, replaying craft.output_slickers on a haystack.

    Reuses craft's ROW_TOL and centre helper so the geometry is the module's, not a copy; only
    the find calls point at the frame instead of the screen.
    """
    tol = craft.ROW_TOL * find.scale()
    timers = find.find_all(craft.TIMER_TARGET, haystack=image)
    outs = []
    for slick in find.find_all(craft.SLICKERS_TARGET, haystack=image):
        sx, sy = craft._center(slick)
        if any(craft._center(t)[0] < sx and abs(craft._center(t)[1] - sy) <= tol for t in timers):
            outs.append(slick)
    return outs, timers


def band_from(boxes, left, width):
    if not boxes:
        return None
    top = min(b.top for b in boxes) - craft.SLICKERS_BAND_PAD + craft.SLICKERS_BAND_TOP_DROP
    bottom = max(b.top + b.height for b in boxes) + craft.SLICKERS_BAND_PAD
    return (left, top, width, bottom - top)


def annotate(image, name, outputs, timers, band):
    draw = ImageDraw.Draw(image)
    for b in timers:
        draw.rectangle((b.left, b.top, b.left + b.width, b.top + b.height), outline=MAGENTA, width=3)
    for b in outputs:
        draw.rectangle((b.left, b.top, b.left + b.width, b.top + b.height), outline=YELLOW, width=3)
    if band:
        l, t, w, h = band
        draw.rectangle((l, t, l + w, t + h), outline=CYAN, width=4)
        cx, cy = l + w // 2, t + h // 2
        # One label centred on each side, so the drop shows as a number, not just a moved line.
        for text, (x, y), anchor in ((f'top {t}', (cx, t + 6), 'ma'),
                                     (f'bottom {t + h}', (cx, t + h - 6), 'md'),
                                     (f'left {l}', (l + 6, cy), 'lm'),
                                     (f'right {l + w}', (l + w - 6, cy), 'rm')):
            draw.text((x, y), text, fill=CYAN, anchor=anchor, font=FONT)
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f'{name}.png')


if __name__ == '__main__':
    paths = sys.argv[1:]
    if paths:
        for path in paths:
            image = Image.open(path).convert('RGB')
            outputs, timers = outputs_in(image)
            band = band_from(outputs, 0, image.width)  # a frame's own left is 0
            annotate(image, Path(path).stem, outputs, timers, band)
            print(f'{Path(path).stem}: outputs={len(outputs)} band={band}')
    else:
        import pyautogui
        hwnd = window.handle()
        region = window.position(hwnd) + window.size(hwnd)
        print(f'live (screen coords): band={craft.find_slickers_craft(region)}')
        shot = pyautogui.screenshot(region=region)  # own 0-based coords, so boxes line up on it
        outputs, timers = outputs_in(shot)
        annotate(shot, 'live', outputs, timers, band_from(outputs, 0, shot.width))
    print(f'-> {OUT}')
