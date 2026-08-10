"""Cut the skill check ROI out of a saved frame and write it out, so the numbers can be seen.

The frame is a still from a recording rather than a live grab, so this runs with no game open
and reads the same every time. That is what makes it the place to check a change to
gym.REP_ROI_FRACTIONS: crop, look, adjust, crop again.

Run:  python tests/gym/test_generate_roi.py                     the committed fixture
      python tests/gym/test_generate_roi.py path/to/frame.png   any frame, e.g. from _recorder

Writes two pictures into tests/output/:
    gym_roi.png          the crop itself, which is what the detector will actually see
    gym_roi_context.png  the whole frame with the ROI boxed on it, which is what says whether
                         the box is in the right place at all

Exits non-zero if the crop is not where the fractions say it should be.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw  # noqa: E402

from interact import gym  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'gym' / 'rep_prompt.png'
OUTPUT = Path(__file__).resolve().parents[1] / 'output'
BOX_COLOUR = (0, 255, 0)
BOX_WIDTH = 3


def crop_roi(image):
    """(the ROI crop, the (left, top, width, height) it was taken from) for a whole-window frame.

    The image is the game window, so its own top left is the window's: the region comes back in
    coordinates that are already the crop box, with no screen offset to subtract.
    """
    region = gym.rep_region((0, 0) + image.size)
    left, top, width, height = region
    return image.crop((left, top, left + width, top + height)), region


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else FIXTURE
    if not path.exists():
        sys.exit(f'no such frame: {path}')

    frame = Image.open(path).convert('RGB')
    roi, region = crop_roi(frame)
    left, top, width, height = region
    print(f'{path.name}  {frame.width}x{frame.height}')
    print(f'roi {region}  ->  ltrb ({left}, {top}, {left + width}, {top + height})')

    OUTPUT.mkdir(parents=True, exist_ok=True)
    roi.save(OUTPUT / 'gym_roi.png')
    context = frame.copy()
    ImageDraw.Draw(context).rectangle((left, top, left + width, top + height),
                                      outline=BOX_COLOUR, width=BOX_WIDTH)
    context.save(OUTPUT / 'gym_roi_context.png')
    print(f'wrote {OUTPUT / "gym_roi.png"} and {OUTPUT / "gym_roi_context.png"}')

    x0, y0, x1, y1 = gym.REP_ROI_FRACTIONS
    assert roi.size == (width, height), f'crop {roi.size} is not the region {region}'
    assert 0 < width < frame.width and 0 < height < frame.height, f'roi {region} is not a slice'
    assert left + width <= frame.width and top + height <= frame.height, \
        f'roi {region} runs off a {frame.width}x{frame.height} frame'
    # The fractions are what makes this survive a 1440p screen, so check the crop really did
    # come from them rather than from anything hard coded to this fixture's size.
    assert abs(left / frame.width - x0) < 0.001 and abs(top / frame.height - y0) < 0.001, \
        f'{region} does not sit at fractions {gym.REP_ROI_FRACTIONS} of {frame.size}'
    print('ok')
