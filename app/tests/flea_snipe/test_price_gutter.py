"""A six figure price is read, and a price whose leading digits are outside its box is refused.

App layer under test: interact/snipe.py's clipped-price guard, first_lit_column, _clipped and
PRICE_GUTTER, the check that refuses a price whose leading digit fell outside its box so the
flea BUYER never reads a truncated (and so falsely cheap) number.

Run:  python tests/flea_snipe/test_price_gutter.py

No game needed: the crops are drawn here from measurements off a real 1440p board, so this is
about where snipe.PRICE_GUTTER sits rather than about matching anything.

Why this exists. On 2026-08-31 the moonshine craft would not buy purified water. The board was
showing 138 888 roubles, the whole number was inside the price box, and read_price answered
None: the gutter was 8 px at 1080p and the leading digit of a six figure price starts 6.8 px in,
so the check was sat on top of a price it was meant to pass. Every craft ingredient ceiling is
five or six figures, so the whole feature was one digit away from never working.

The check itself is right and stays. Tarkov right-aligns the price against its currency glyph,
so a seven figure price is pushed a digit and a group separator further left than a six figure
one, its leading digit falls outside the box, and the crop opens part way into the second digit.
1 234 567 read as 234 567 is a bargain that is not there, and it is money that gets spent on it.

The two numbers below are measured, not guessed, and they are what the threshold sits between:
a six figure price's first lit column is 6.8 px into the box and a seven figure one's is 0.75.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image  # noqa: E402

from interact import find, snipe  # noqa: E402

# Measured off a live 2560x1440 flea board, in the 1080p pixels snipe.py's constants use.
SIX_FIGURE_EDGE = 6.8   # 138 888: whole, inside the box, and must be read
SEVEN_FIGURE_EDGE = 0.75  # 1 234 567: leading digit outside the box, and must be refused
BACKGROUND = 25  # brightest channel of the empty box, measured
GLYPH = 180      # and of the digits themselves


def board_crop(edge_1080p):
    """A price box whose leftmost lit column sits `edge_1080p` px in, at the current scale.

    Everything right of that is lit too, which is enough: nothing here reads the digits, only
    where they start.
    """
    width, height = round(snipe.PRICE_WIDTH * find.scale()), round(snipe.PRICE_HEIGHT * find.scale())
    crop = Image.new('RGB', (width, height), (BACKGROUND,) * 3)
    left = round(edge_1080p * find.scale())
    crop.paste((GLYPH,) * 3, (left, 4, width, height - 4))
    return crop


if __name__ == '__main__':
    scale = find.scale()
    print(f'this screen is {scale:.3f}x the 1080p the constants are written in')

    # The measurement is reported, not just acted on, and it comes back in 1080p px whatever the
    # screen is: that is the only way the two numbers above mean anything on another machine.
    for edge in (SIX_FIGURE_EDGE, SEVEN_FIGURE_EDGE):
        got = snipe.first_lit_column(board_crop(edge))
        assert abs(got - edge) <= 1 / scale, f'asked for {edge}, measured {got}'
    assert snipe.first_lit_column(Image.new('RGB', (40, 20), (BACKGROUND,) * 3)) is None, \
        'an empty box has no lit column, and None is not a distance of 0'
    print('  ok  measurement      first_lit_column reports 1080p px, and None for a blank box')

    # The regression. A six figure price is what the craft mode buys its ingredients at.
    assert not snipe._clipped(board_crop(SIX_FIGURE_EDGE)), (
        f'a six figure price starting {SIX_FIGURE_EDGE}px into its box was refused: '
        f'PRICE_GUTTER is {snipe.PRICE_GUTTER} and has to be under that')
    print(f'  ok  six figures      starts {SIX_FIGURE_EDGE}px in, read rather than refused')

    # And the reason the check is there at all.
    assert snipe._clipped(board_crop(SEVEN_FIGURE_EDGE)), (
        f'a price whose leading digit is outside the box was accepted: PRICE_GUTTER is '
        f'{snipe.PRICE_GUTTER} and has to be over {SEVEN_FIGURE_EDGE}')
    print(f'  ok  clipped price    starts {SEVEN_FIGURE_EDGE}px in, refused')

    # The threshold is between the two rather than on either, so neither case is decided by a
    # pixel of anti-aliasing.
    assert SEVEN_FIGURE_EDGE < snipe.PRICE_GUTTER < SIX_FIGURE_EDGE, snipe.PRICE_GUTTER
    room = min(snipe.PRICE_GUTTER - SEVEN_FIGURE_EDGE, SIX_FIGURE_EDGE - snipe.PRICE_GUTTER)
    print(f'  ok  headroom         gutter {snipe.PRICE_GUTTER}, {room:.2f}px clear of the '
          f'nearer case at 1080p ({room * scale:.1f}px here)')

    print('ok, six figure prices read and clipped ones are still refused')
