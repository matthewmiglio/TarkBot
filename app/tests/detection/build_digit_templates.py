"""Cut every price fixture into glyphs and file them under the digit each one is.

App layer: rebuilds the digit templates interact/ocr.py matches against. It calls ocr.glyphs to
segment each fixture in tests/fixtures/prices/ and writes the results into
interact/reference_images/price_digits/, the answer-key folder ocr.read_number compares to.

Run:  python tests/detection/build_digit_templates.py

NO GAME needed: a pure fixture-to-fixture rebuild, reading pngs off disk and writing pngs. The
fixture filename is the answer key: 43998.png segments into five glyphs left to right, so they
are a 4, a 3, a 9, a 9 and an 8. Writes them to
interact/reference_images/price_digits/<digit>__<n>.png, which is what ocr.py matches against.
Rerun it whenever the corpus grows; it rebuilds the folder from scratch.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image  # noqa: E402

from interact import ocr  # noqa: E402

PRICES = Path(__file__).resolve().parents[1] / 'fixtures' / 'prices'
DIGITS = Path(__file__).resolve().parents[2] / 'interact' / 'reference_images' / 'price_digits'

if __name__ == '__main__':
    fixtures = sorted(PRICES.glob('*.png'))
    if not fixtures:
        sys.exit(f'no fixtures in {PRICES}')

    DIGITS.mkdir(parents=True, exist_ok=True)
    for stale in DIGITS.glob('*.png'):
        stale.unlink()

    counts, skipped = {}, []
    for path in fixtures:
        answer = path.stem.split('__')[0]
        image = Image.open(path)
        glyphs = ocr.glyphs(image)
        if len(glyphs) != len(answer):
            skipped.append(f'{path.name}: {len(glyphs)} glyphs for {len(answer)} digits')
            continue
        for digit, glyph in zip(answer, glyphs):
            counts[digit] = counts.get(digit, 0) + 1
            glyph.save(DIGITS / f'{digit}__{counts[digit]}.png')

    for note in skipped:
        print(f'skipped {note}')
    print(f'\n{sum(counts.values())} glyphs from {len(fixtures) - len(skipped)} fixtures')
    for digit in '0123456789':
        print(f'  {digit}: {counts.get(digit, 0)}{"  <-- MISSING" if digit not in counts else ""}')
