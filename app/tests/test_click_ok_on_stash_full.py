"""Where the stash-full dialog's OK click would land, drawn on every crop of it.

App layer: the same arithmetic sell.dismiss_error_popup uses for the Error/0 dialog (box middle
in x, a fraction down in y), previewed for the new errors/stash_full crops so the fraction can be
eyeballed before it is wired into a real click. Marks 50% across and 75% down each crop with a red
X, stitches the crops into one labelled column, and writes it to tests/output/.

No game, nothing clicked: it only reads the reference pngs and draws on them. Look at the result
before trusting a fraction; an X in the dialog's empty middle is a click that reports success and
leaves the run stuck.

Run:  python tests/test_click_ok_on_stash_full.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

X_FRACTION = 0.50   # across
Y_FRACTION = 0.68   # down
CROPS = Path('interact/reference_images/errors/stash_full')
OUT = Path(__file__).resolve().parents[1] / 'tests' / 'output' / 'click_ok_on_stash_full.png'

ARM = 7        # half-length of the red X's strokes, px
LABEL_H = 22   # strip under each crop for its caption
GAP = 8        # space between stacked crops
PAD = 10       # border around the whole column
RED = (220, 30, 30)


def mark(img):
    """Draw the red X at (50% w, 75% h) and return the crop with its point."""
    im = img.convert('RGB')
    w, h = im.size
    x, y = round(w * X_FRACTION), round(h * Y_FRACTION)
    d = ImageDraw.Draw(im)
    d.line((x - ARM, y - ARM, x + ARM, y + ARM), fill=RED, width=2)
    d.line((x - ARM, y + ARM, x + ARM, y - ARM), fill=RED, width=2)
    return im, (x, y)


def main():
    pngs = sorted(CROPS.glob('*.png'))
    assert pngs, f'no crops in {CROPS}'
    font = ImageFont.load_default()

    marked = [(p.name, *mark(Image.open(p))) for p in pngs]
    width = max(im.width for _, im, _ in marked)
    row_h = [im.height + LABEL_H for _, im, _ in marked]

    canvas = Image.new('RGB', (width + 2 * PAD,
                               sum(row_h) + GAP * (len(marked) - 1) + 2 * PAD),
                        (245, 245, 245))
    d = ImageDraw.Draw(canvas)
    y = PAD
    for (name, im, (px, py)), rh in zip(marked, row_h):
        canvas.paste(im, (PAD, y))
        d.text((PAD, y + im.height + 4),
               f'{name}  {im.width}x{im.height}  X at ({px}, {py})  '
               f'= {X_FRACTION:.0%} x, {Y_FRACTION:.0%} y',
               fill=(20, 20, 20), font=font)
        print(f'{name}: {im.width}x{im.height}, X at ({px}, {py})')
        y += rh + GAP

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT)
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
