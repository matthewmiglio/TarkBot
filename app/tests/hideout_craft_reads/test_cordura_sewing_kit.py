"""Draw the cordura row, the sewing_kit found inside it, and the confidence it matched at.

App layer under test: interact/craft.py's ingredient READ for the cordura craft, exactly as the
bot does it: craft.find_craft(CRAFTS['cordura']) frames the row into a band, then the sewing_kit
input icon is searched for *inside that band*. This is the read that failed the 2026-09-02 run
("sewing_kit icon is not on the cordura row"): it draws the band, boxes the best sewing_kit match
within it, and paints on the frame the grey peak confidence it reached against the 0.9 default, so
you can see at a glance whether the icon is undetectable there or just under threshold.

The real module functions do the work (craft.find_craft, find.best_score, find.find), so the band
and the score are the bot's, not a copy. In frame mode the screen module is pointed at the loaded
frame so find_craft runs unchanged.

Live game OR no game: bare, it grabs the live window (game, on the cordura/lavatory craft screen);
hand it one or more saved frame paths and it needs no game.

Run:  python tests/hideout_craft_reads/test_cordura_sewing_kit.py                  (grab the live window)
      python tests/hideout_craft_reads/test_cordura_sewing_kit.py <frame.png ...>   (saved frames, no game)

Draws, to tests/output/cordura_sewing_kit/<name>.png:
  - a cyan box around the cordura row band (output_box + _row_band, the region read_craft uses),
    now the row output_box anchors by its ingredient signature (sewing_kit + sling_bag)
  - a magenta box around the cordura output that anchored the row
  - each ingredient boxed green (or red if it misses its threshold) with its grey peak confidence
  - the sewing_kit peak, the default it is judged at, and PASS/FAIL, painted on the frame
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import screen  # noqa: E402
from interact import craft, find  # noqa: E402

TARGET = 'crafting/sewing_kit'
CRAFT = craft.CRAFTS['cordura']
OUT = Path(__file__).resolve().parents[1] / 'output' / 'cordura_sewing_kit'
CYAN, YELLOW, RED, INK = (0, 220, 220), (255, 210, 0), (235, 60, 60), (240, 240, 240)
GREEN, MAGENTA = (60, 220, 90), (220, 0, 220)
try:
    FONT, BIG = ImageFont.truetype('arialbd.ttf', 26), ImageFont.truetype('arialbd.ttf', 34)
except OSError:  # no truetype on this box, fall back to the tiny bitmap font
    FONT = BIG = ImageFont.load_default()


def _use_frame(image):
    """Point the screen module at `image` so craft.find_craft / find run against it unchanged."""
    w, h = image.width, image.height
    screen.grab = lambda region=None: image.crop((region[0], region[1], region[0] + region[2],
                                                   region[1] + region[3])) if region else image
    screen.rect = lambda: (0, 0, w, h)
    screen.size = lambda: (w, h)


def _boxed(target, band):
    """(peak grey score, best box just under it) for `target` inside `band`; box is None if unlit."""
    peak, _ = find.best_score(target, region=band)
    box = find.find(target, region=band, confidence=max(0.05, peak - 0.02))
    return peak, box


def analyse(image, name):
    """Draw the anchored cordura row, its output and every ingredient on it, with each confidence.

    output_box now picks the cordura row by its ingredient signature (sewing_kit + sling_bag), so
    this frames that row and shows the whole anchor: the output (magenta), each ingredient boxed
    green/red with its peak, and sewing_kit as the headline pass/fail against the 0.9 default.
    """
    region = screen.rect()
    draw = ImageDraw.Draw(image)

    # The exact row read_craft reads: output_box's anchored output, padded into _row_band.
    output = craft.output_box(CRAFT, region)
    band = craft._row_band(output, region) if output else None
    if band is None:
        summary = 'no cordura row: output_box found no cordura output on screen'
        draw.rectangle((30, 30, 30 + int(BIG.getlength(summary)) + 24, 84), fill=(0, 0, 0))
        draw.text((42, 38), summary, fill=RED, font=BIG)
        OUT.mkdir(parents=True, exist_ok=True)
        image.save(OUT / f'{name}.png')
        print(f'{name}: band=None  no output')
        return False

    l, t, w, h = band
    draw.rectangle((l, t, l + w, t + h), outline=CYAN, width=4)
    draw.text((l + 8, t + 8), 'cordura row (anchored by ingredients)', fill=CYAN, font=FONT)
    draw.rectangle((output.left, output.top, output.left + output.width, output.top + output.height),
                   outline=MAGENTA, width=4)
    draw.text((output.left, output.top - 30), 'cordura output', fill=MAGENTA, font=FONT)

    headline_peak = 0.0
    for ing in CRAFT.ingredients:
        default = find.confidence_for(ing.target)
        peak, box = _boxed(ing.target, band)
        if ing.target == TARGET:
            headline_peak = peak
        colour = GREEN if peak >= default else RED
        if box:
            draw.rectangle((box.left, box.top, box.left + box.width, box.top + box.height),
                           outline=colour, width=4)
            draw.text((box.left, box.top - 30), f'{ing.name} {peak:.3f}', fill=colour, font=FONT)
        print(f'  {ing.name:12} peak {peak:.4f}  vs {default:.2f}  {"ok" if peak >= default else "MISS"}')

    passed = headline_peak >= find.confidence_for(TARGET)
    verdict = 'PASS' if passed else 'FAIL'
    summary = (f'cordura row anchored;  sewing_kit peak {headline_peak:.3f}'
               f'  vs default {find.confidence_for(TARGET):.2f}  ->  {verdict}')
    draw.rectangle((30, 30, 30 + int(BIG.getlength(summary)) + 24, 84), fill=(0, 0, 0))
    draw.text((42, 38), summary, fill=(INK if passed else RED), font=BIG)

    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f'{name}.png')
    print(f'{name}: band={band}  sewing_kit peak={headline_peak:.4f}  {verdict}')
    return passed


if __name__ == '__main__':
    paths = sys.argv[1:]
    if paths:
        ok = True
        for path in paths:
            image = Image.open(path).convert('RGB')
            _use_frame(image)
            ok &= analyse(image, Path(path).stem)
        print(f'\n-> {OUT}')
        sys.exit(0)  # a diagnostic: FAIL is a finding, not a broken test
    else:
        import window
        hwnd = window.handle()
        wx, wy = window.position(hwnd)
        # Work on the monitor the game is on, so find.scale matches the live read.
        mons = screen.monitors()
        for mon in mons:
            bx, by, bw, bh = mons[mon] if isinstance(mons, dict) else (0, 0, 0, 0)
            if bx <= wx < bx + bw and by <= wy < by + bh:
                screen.use(mon)
                break
        shot = screen.grab().convert('RGB')  # the used monitor's pixels
        _use_frame(shot)  # re-point screen at the shot so every box lands in its 0-based coords
        analyse(shot, 'live')
        print(f'\n-> {OUT}')
