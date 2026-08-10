"""Where gym.read_lines thinks the two lines are, drawn back onto the crop it read them from.

The numbers on their own do not say whether a reading is right; a line drawn down the middle of
the line it found does. Every fixture comes out as a picture in tests/output/gym_line_reads/,
green down the target and red down the closing ring, so a bad read is seen rather than argued
about.

The fixtures are ROI crops, not whole frames: cut with gym.rep_region out of the recording in
_recorder/recordings/gym-1, which is where more come from if this corpus needs widening.

Run:  python tests/gym/test_line_reads.py                      every fixture
      python tests/gym/test_line_reads.py path/to/crop.png     one crop
      python tests/gym/test_line_reads.py path/to/folder       every crop in a folder

Exits non-zero if any fixture reads as no lines at all, or reads its ring left of its target.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw  # noqa: E402

from interact import gym  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'gym' / 'line_reads'
OUTPUT = Path(__file__).resolve().parents[1] / 'output' / 'gym_line_reads'
TARGET_COLOUR = (0, 255, 0)  # the fixed inner hexagon's edge
MOVING_COLOUR = (255, 0, 0)  # the ring closing on it
ZOOM = 3  # the crops are 201x58, which is too small to judge a one pixel error by eye


def annotate(image, lines):
    """`image` blown up, with a vertical line down each centre gym.read_lines found."""
    big = image.convert('RGB').resize((image.width * ZOOM, image.height * ZOOM), Image.NEAREST)
    if lines is None:
        return big
    draw = ImageDraw.Draw(big)
    # Drawn moving first, so an overlap shows the target's green on top rather than under: the
    # question at a gap of zero is where the target is, and a red line hiding it is no answer.
    for centre, color in ((lines.moving, MOVING_COLOUR), (lines.target, TARGET_COLOUR)):
        x = round(centre * ZOOM + ZOOM / 2)  # the middle of the zoomed pixel, not its left edge
        # ZOOM wide, so the mark is exactly one crop pixel. A hairline over the target's white
        # band cannot be seen, which for a test whose whole output is a picture is no use.
        draw.line((x, 0, x, big.height), fill=color, width=ZOOM)
    return big


if __name__ == '__main__':
    where = Path(sys.argv[1]) if len(sys.argv) > 1 else FIXTURES
    crops = sorted(where.glob('*.png')) if where.is_dir() else [where]
    if not crops:
        sys.exit(f'no crops in {where}')

    OUTPUT.mkdir(parents=True, exist_ok=True)
    failures = []
    for path in crops:
        image = Image.open(path)
        lines = gym.read_lines(image)
        annotate(image, lines).save(OUTPUT / path.name)

        if lines is None:
            print(f'{path.name}  no lines')
            failures.append(f'{path.name}: nothing bright enough to be a line')
            continue
        print(f'{path.name}  target {lines.target:6.2f}  moving {lines.moving:6.2f}  '
              f'gap {lines.gap:6.2f}' + ('  OVERLAP' if lines.gap == 0 else ''))
        if lines.moving < lines.target:
            failures.append(f'{path.name}: ring at {lines.moving:.2f} is left of the target '
                            f'at {lines.target:.2f}')
        if not 0 <= lines.target <= image.width or not 0 <= lines.moving <= image.width:
            failures.append(f'{path.name}: a centre is outside the {image.width} px crop')

    print(f'\n{len(crops)} crops, pictures in {OUTPUT}')
    if failures:
        print('\n'.join(failures))
        sys.exit(f'{len(failures)} of {len(crops)} failed')
    print('ok')
