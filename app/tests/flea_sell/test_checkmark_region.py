"""Where the tick is looked for, and whether it is found there, over saved frames.

Exercises the checkmark-region geometry behind interact/sell.py's is_autoselect_similar_ticked:
_checkmark_region_from (which autoselect_similar_region wraps) matches the autoselect similar
button, takes its right half (the checkbox sits at that end of every reference crop of it),
grows that by CHECKMARK_MARGIN per side, and searches for the checkmark inside. The regression
it guards is a region grown too small to hold the checkmark needle, which makes pyscreeze raise
rather than miss, and which only happens on a screen that is not 1080p.

Every frame is run twice, once at its own size and once resized to 1920x1080, because the
references are 1080p crops. The 1080p pass is a stand-in, not a real 1080p screen: the frame
recorder writes what the monitor is, and there are no 1080p frames to hand. Point this at one
when there is. Writes an annotated png (and a zoom) per frame per size into
tests/flea_sell/output/checkmark_region/: the matched button in blue, the searched region in
yellow, the checkmark in green when found. Look at those before believing a 'no tick here' line,
since a region drawn in the wrong place and a box that genuinely has no tick read identically in
the summary.

A no-game test: it works off recorded frames (the frame recorder's folder by default, or the
paths named), never a live screen, so nothing is clicked and no window is needed.

Run:  python tests/flea_sell/test_checkmark_region.py                  # every frame the recorder has
      python tests/flea_sell/test_checkmark_region.py some/frame.png    # or the ones named
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image, ImageDraw

import interact.find as find
import interact.sell as sell

FRAMES = Path(os.environ.get('APPDATA', '')) / 'tarkbot' / 'frames'
OUTPUT = Path(__file__).parents[1] / 'output' / 'checkmark_region'
SIZES = [None, (1920, 1080)]  # None means the frame at its own size


def _needle_size(path):
    """How big that reference is once grown for this screen. needle() hands back a path at 1080p."""
    grown = find.needle(path)
    return Image.open(grown).size if isinstance(grown, str) else grown.size


def look(frame, size):
    """Find the button, work out the region, look for a tick in it. One annotated png out."""
    image = Image.open(frame).convert('RGB')
    if size:
        image = image.resize(size, Image.LANCZOS)
    find.scale = lambda: image.height / find.REFERENCE_HEIGHT  # what this frame's screen reports

    button = find.find(sell.AUTOSELECT_TARGET, haystack=image)
    label = f'{frame.name} @ {image.width}x{image.height}'
    if not button:
        _draw(image, frame, size, None, None, None)
        return label, 'NO BUTTON', '', ''

    region = sell._checkmark_region_from(button, (0, 0, image.width, image.height))
    crop = image.crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))
    biggest = max(_needle_size(p) for p in find.images(sell.CHECKMARK_TARGET))
    fits = biggest[0] <= region[2] and biggest[1] <= region[3]
    tick = find.find(sell.CHECKMARK_TARGET, haystack=crop) if fits else None
    _draw(image, frame, size, button, region, tick)
    return (label, f'button {button.width}x{button.height}',
            f'region {region[2]}x{region[3]} vs needle {biggest[0]}x{biggest[1]} '
            f'{"fits" if fits else "TOO SMALL"}',
            'TICKED' if tick else ('unticked' if fits else 'not looked for'))


def _draw(image, frame, size, button, region, tick):
    """The picture half: the button, the region and the tick drawn on the frame it came from."""
    canvas = image.copy()
    pen = ImageDraw.Draw(canvas)
    if button:
        pen.rectangle([button.left, button.top, button.left + button.width,
                       button.top + button.height], outline=(80, 160, 255), width=2)
    if region:
        pen.rectangle([region[0], region[1], region[0] + region[2], region[1] + region[3]],
                      outline=(255, 210, 0), width=2)
        if tick:
            pen.rectangle([region[0] + tick.left, region[1] + tick.top,
                           region[0] + tick.left + tick.width, region[1] + tick.top + tick.height],
                          outline=(0, 255, 90), width=2)
    tag = f'{image.width}x{image.height}'
    OUTPUT.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT / f'{frame.stem}-{tag}.png')
    if not button:
        return
    # And the same thing close up. The tick is 20 pixels across on a 1440p frame, which is not
    # something anyone can judge from a whole screen shrunk to fit on one, and judging it by eye
    # is the entire point of these.
    pad = 40
    near = canvas.crop((max(0, button.left - pad), max(0, button.top - pad),
                        min(canvas.width, button.left + button.width + pad),
                        min(canvas.height, button.top + button.height + pad)))
    near = near.resize((near.width * 4, near.height * 4), Image.NEAREST)
    near.save(OUTPUT / f'{frame.stem}-{tag}-zoom.png')


if __name__ == '__main__':
    named = [Path(a) for a in sys.argv[1:]]
    frames = named or sorted(FRAMES.glob('*.png'))
    if not frames:
        sys.exit(f'no frames to look at, and none under {FRAMES}')

    rows, found = [], 0
    for frame in frames:
        for size in SIZES:
            row = look(frame, size)
            if row[1] == 'NO BUTTON':  # the button is not in every frame, only note the ones
                continue               # where it is; a frame of the stash is not a failure
            rows.append(row)
            found += 1
    for label, button, region, verdict in rows:
        print(f'{label:44} {button:20} {region:52} {verdict}')

    if not found:
        sys.exit(f'the autoselect similar button was in none of the {len(frames)} frame(s)')
    small = [r for r in rows if 'TOO SMALL' in r[2]]
    print(f'\n{found} look(s) at {len(frames)} frame(s), {len(small)} with a region too small '
          f'for the checkmark. Pictures in {OUTPUT}')
    assert not small, f'{len(small)} region(s) too small to hold the checkmark needle'
