"""Read the numbers Tarkov prints in its UI.

Not OCR. The prices are a fixed bitmap font, so each digit is the same handful of pixels
every time: cut the crop into glyphs, match each against a reference, done. A real OCR
engine was tried first and read 999 as 666 and 777 as 7777, both at full confidence, which
is exactly the failure you cannot have on a number that decides a sale price.

Rebuild the references with tests/build_digit_templates.py, check with tests/test_price_corpus.py.
"""
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from PIL import Image

import screen
from interact import find  # for find.scale(), the one place the screen-vs-1080p ratio lives
from narrate import log

DIGITS = Path(__file__).parent / 'reference_images' / 'price_digits'
CANVAS = (16, 24)  # every glyph is padded into this box before comparing, width x height
MIN_AREA = 8  # lit pixels below this is a speck, not a glyph
MIN_SCORE = 0.85  # pixel agreement a match needs; below this the glyph is unrecognised

_templates = None


def _mask(image):
    """Bool array, True on the lit pixels. The threshold is per crop, they vary in brightness."""
    grey = np.asarray(image.convert('L'))
    return grey > (int(grey.min()) + int(grey.max())) // 2


def glyphs(image):
    """The digit-shaped blobs in image, left to right, each as its own tightly cropped Image.

    The currency symbol is dropped: it is taller than the digits, which all share one height
    and baseline. The keeper is the most common height, and the shorter one on a tie, which
    is what a single digit price gives you: one digit and one currency symbol, no majority.
    """
    mask = _mask(image)
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    blobs = [tuple(int(v) for v in row) for row in stats[1:] if row[4] >= MIN_AREA]
    if not blobs:
        return []
    heights = [blob[3] for blob in blobs]
    common = min(heights, key=lambda h: (-sum(abs(x - h) <= 2 for x in heights), h))
    digits = [b for b in blobs if abs(b[3] - common) <= 2]
    digits.sort(key=lambda b: b[0])
    return [Image.fromarray((mask[t:t + h, l:l + w] * 255).astype(np.uint8))
            for l, t, w, h, _ in digits]  # stats rows are left, top, width, height, area


def _canvas(glyph, size=CANVAS):
    """Centre a glyph in a fixed box so different widths still compare pixel to pixel."""
    box = Image.new('L', size, 0)
    glyph = glyph.crop(glyph.getbbox() or (0, 0, glyph.width, glyph.height))
    if glyph.width > size[0] or glyph.height > size[1]:
        glyph = glyph.resize((min(glyph.width, size[0]), min(glyph.height, size[1])))
    box.paste(glyph, ((size[0] - glyph.width) // 2, (size[1] - glyph.height) // 2))
    return np.asarray(box) > 127


def templates():
    """[(digit, mask)] from reference_images/price_digits, loaded once."""
    global _templates
    if _templates is None:
        _templates = [(path.stem.split('__')[0], _canvas(Image.open(path)))
                      for path in sorted(DIGITS.glob('*.png'))]
        if not _templates:
            raise FileNotFoundError(f'no digit references in {DIGITS}, '
                                    'run tests/build_digit_templates.py')
    return _templates


def match(glyph):
    """(digit, score) for the closest reference, or (None, score) if nothing is close enough."""
    target = _canvas(glyph)
    best, best_score = None, 0.0
    for digit, reference in templates():
        score = float((target == reference).mean())
        if score > best_score:
            best, best_score = digit, score
    return (best, best_score) if best_score >= MIN_SCORE else (None, best_score)


def read_digits(image):
    """[(digit, score)] for every glyph in image, left to right. digit is None if unrecognised."""
    return [match(glyph) for glyph in glyphs(image)]


def _number(read):
    """read_digits' output as an int, or None if it is empty or any glyph is unreadable.

    All or nothing on purpose: a partially read price is a wrong price, and a wrong price
    is worse than no price.
    """
    if not read or any(digit is None for digit, _ in read):
        return None
    return int(''.join(digit for digit, _ in read))


def read_number(image):
    """The number in image as an int, or None if any glyph in it is unreadable."""
    return _number(read_digits(image))


def read_region(rect):
    """Screenshot a (left, top, width, height) rect off the screen and read a number out of it.

    Brought back down to 1080p first on a bigger screen. The digit references are 1080p bitmaps
    and _canvas compares them pixel to pixel inside a fixed 16x24 box, so a 1440p glyph is too
    big for that box and gets squashed out of shape rather than matched. Shrinking the crop by
    the same factor find.py grows its needles by puts the digits back at the size they were cut
    at. A 1080p screen is left alone.
    """
    image = screen.grab(rect)
    factor = find.scale()
    if factor != 1.0:
        image = image.resize((max(1, round(image.width / factor)),
                              max(1, round(image.height / factor))), Image.LANCZOS)
    read = read_digits(image)
    # Every glyph and how well it matched, because 'unreadable' on its own says nothing about
    # whether the crop was empty, cut in the wrong place, or holding a digit at 0.84 that only
    # just missed MIN_SCORE. Written here rather than in the caller so the scores survive the
    # all-or-nothing rule that is about to throw them away.
    log(f'price crop {rect} read at {factor:.3f}x as {image.width}x{image.height}: '
        + (', '.join(f'{digit if digit is not None else "?"} {score:.2f}' for digit, score in read)
           if read else f'no glyphs at all, nothing above {MIN_AREA}px lit'), 2)
    return _number(read)


if __name__ == '__main__':
    import sys

    for path in sys.argv[1:] or sys.exit('usage: python -m interact.ocr <image>...'):
        image = Image.open(path)
        read = read_digits(image)
        print(f'{path}  {image.size}  {len(read)} glyphs')
        for digit, score in read:
            print(f'  {digit or "?"}  {score:.3f}')
        print(f'  -> {read_number(image)}')
