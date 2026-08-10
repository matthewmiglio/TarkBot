"""
This module is for the hideout gym: everything gym mode does to a screen.

The same job for the gym that sell.py does for the flea, and a separate module on purpose.
The two share find.py and narrate.py and nothing else: a gym pass never opens the flea and a
selling pass never leaves it, so folding these together would put two unrelated screens behind
one import and one set of module constants.

Geometry self-check, no game needed:  python -m interact.gym

SKELETON. Every function that touches the screen raises NotImplementedError, deliberately.
A stub that returns None or False instead would let gym mode "run" and quietly do nothing,
which is exactly the failure class the flea filters just had to be rewritten to kill. Loud
beats silent while this is being built out.

None of the reference image folders named below exist yet. Cut the crops, then check each one
matches with:  python tests/test_find.py gym_<name>
"""
import time
from collections import namedtuple

import numpy as np

import screen
from interact import find  # noqa: F401  (the stubs will all use it)
from narrate import log

# Reference image folders, all gym_ prefixed so they group in the reference_images listing the
# way flea_filters_ does. Only gym_rep_hexagon exists so far.
HIDEOUT_TAB_TARGET = 'gym_hideout_tab'  # the hideout entry on the main menu
GYM_STATION_TARGET = 'gym_station'  # the gym itself, in the hideout view
WORKOUT_BUTTON_TARGET = 'gym_workout_button'  # starts a session
GYM_WINDOW_TARGET = 'gym_window_title'  # the workout window's title bar, for orientating
# The small fixed hexagon with the mouse icon in it, at the centre of the skill check. Present
# means a rep is still being asked for, absent means the set is over, so this is what the loop
# runs until rather than a rep count.
REP_HEXAGON_TARGET = 'gym_rep_hexagon'
FATIGUE_TARGET = 'gym_fatigue_warning'  # shown once the character is too tired to continue

# The corridor the closing hexagon travels down, as fractions of the game window, measured off
# _recorder/recordings/gym-1 at 1920x1080: x 1000-1201, y 783-830. Fractions rather than pixels
# for the same reason as sell.PRICE_FRACTIONS: the same UI on a 1440p screen is the same
# proportion of it, and every reference image in this repo is already scaled that way.
# It deliberately does not enclose the whole hexagon. It is a horizontal strip off the right
# side, at the height where both hexagons' edges are vertical, so a horizontal scan crosses
# them square on and reads as two bright runs whose gap closes to nothing at the overlap. A box
# lower down was tried first and read almost nothing: there the edges are diagonal, so they
# slide sideways out of the box as the ring comes in.
# The top of that box has been cut back twice, a tenth at a time (772 -> 778 -> 783): it is
# where the hexagons' corners start to lean in, and a leaning edge is a diagonal smear across
# several columns rather than a line. Only the top moves. The bottom is already at the widest
# part of both hexagons, where their edges are as close to vertical as they ever get.
REP_ROI_FRACTIONS = (1000 / 1920, 783 / 1080, 1201 / 1920, 830 / 1080)

# Where to look for the hexagon icon, same idea and same units. Measured over the recording:
# the match lands in (932, 776)-(993, 848) and moves by a single pixel across 54 frames, so
# this is that box with about 40px of slack on every side.
# It exists because the icon is checked before every single look, and a match over the whole
# 1920x1080 window costs 335ms against 46ms for the strip read: at roughly 8 columns of ring
# travel per 100ms, searching the whole window would put a quarter of the ring's journey
# between seeing the screen and clicking it. Searching a box a hundredth of the size does not.
ICON_ROI_FRACTIONS = (890 / 1920, 735 / 1080, 1035 / 1920, 890 / 1080)

# Grey level a column has to reach to count as part of a line. Measured across 25 crops in
# tests/fixtures/gym/line_reads: the gym floor behind the hexagons reads 18-22, a line at full
# brightness peaks at 203-206 and the thin moving one at 170-185. 100 sits in the empty middle.
# It also excludes the fade in, which peaks around 110 as the prompt draws itself: those frames
# have no meaningful gap to measure yet, so reading nothing from them is the right answer.
LINE_BRIGHT = 100
MIN_LINE_WIDTH = 2  # columns. A single lit column is compression noise, not a line

# Narrate every strip read that has anything bright in it: the runs, their peaks, and a picture
# of the whole profile. On while the click is being tuned, because the only way to tell a real
# skill check from something else bright in the gym is to see what the strip actually held.
# Reads with nothing in them stay quiet, or the idle poll alone would write ten lines a second.
VERBOSE = True
# Grey levels, darkest to brightest, for the profile drawing. ASCII on purpose: this goes into
# a session log that gets read in Notepad and mailed around.
RAMP = ' .:-=+*#%@'
RAMP_WIDTH = 50  # characters the strip is drawn as, whatever its real width

# target is the fixed inner hexagon's edge, moving is the closing ring, both as sub-pixel
# column positions inside the ROI. gap is the distance between those centres.
# touch is the gap at which the two stop being separate lines and become one: half of each
# line's width added together, since that is when their edges meet. It is the moment the ring
# lands on the target rather than the moment their middles line up, and it is what to aim at,
# roughly 4 to 8 columns before gap reaches 0. Zero when there is only one line left, because
# by then the touching has already happened.
Lines = namedtuple('Lines', 'target moving gap touch')

# Seconds. Measured values go here with the measurement in the comment, same as sell.py.
# These are placeholders: nothing below has been timed against the real game yet.
WINDOW_TIMEOUT = 10.0  # the hideout and gym windows both load from the server, like the scav case
WINDOW_POLL = 0.25
MENU_DELAY = 0.3  # for a menu to draw before we look for what is in it
REP_POLL = 0.05  # how often the rep bar is re-read mid swing; fast, it is a timing minigame


def wait_for(target, region=None, timeout=WINDOW_TIMEOUT, poll=WINDOW_POLL):
    """Poll until `target` is on screen. Its Box, or None once timeout runs out.

    ponytail: the same helper as sell.wait_for. Left as a copy rather than shared, because the
    two modules are meant to be independent and this is nine lines. Hoist it into find.py the
    moment a third caller wants it.
    """
    started = time.monotonic()
    while True:
        box = find.find(target, region)
        if box:
            log(f'{target} up after {time.monotonic() - started:.1f}s', 1)
            return box
        if time.monotonic() - started >= timeout:
            log(f'{target} never appeared, gave up after {timeout:.0f}s', 1)
            return None
        time.sleep(poll)


def _slice(region, fractions):
    """`fractions` of `region` as (left, top, width, height), in the same screen coordinates.

    ponytail: the same four lines as sell.grab_price_region, copied rather than shared for the
    same reason wait_for is. Hoist both into a geometry helper if a third module wants them.
    """
    left, top, width, height = region if region else screen.rect()
    x0, y0, x1, y1 = fractions
    return (left + round(width * x0), top + round(height * y0),
            round(width * (x1 - x0)), round(height * (y1 - y0)))


def rep_region(region=None, fractions=REP_ROI_FRACTIONS):
    """The skill check corridor as (left, top, width, height), scaled off the window size."""
    return _slice(region, fractions)


def icon_region(region=None, fractions=ICON_ROI_FRACTIONS):
    """Where to look for the hexagon icon, as (left, top, width, height)."""
    return _slice(region, fractions)


def look_region(region=None):
    """One box holding both the icon box and the strip, so a look needs a single screenshot.

    screen.grab photographs the whole virtual desktop and crops out whatever it was asked for,
    so a grab costs about 45ms regardless of how small the region is, and asking twice pays it
    twice. The ring covers 8 to 22 columns in 45ms depending on the rep, so that second grab
    was a large part of why a click landed anywhere between the lines first touching and the
    overlap nearly being over.
    """
    icon, strip = icon_region(region), rep_region(region)
    left, top = min(icon[0], strip[0]), min(icon[1], strip[1])
    right = max(icon[0] + icon[2], strip[0] + strip[2])
    bottom = max(icon[1] + icon[3], strip[1] + strip[3])
    return (left, top, right - left, bottom - top)


def inside(outer, inner):
    """`inner` as a PIL crop box (left, top, right, bottom) in `outer`'s own pixels."""
    left, top = inner[0] - outer[0], inner[1] - outer[1]
    return (left, top, left + inner[2], top + inner[3])


def _runs(lit, minimum=MIN_LINE_WIDTH):
    """(first, last) column of every run of `minimum` or more True values in `lit`."""
    found, start = [], None
    for i, on in enumerate(lit):
        if on and start is None:
            start = i
        elif not on and start is not None:
            found.append((start, i - 1))
            start = None
    if start is not None:
        found.append((start, len(lit) - 1))
    return [(a, b) for a, b in found if b - a + 1 >= minimum]


def _centre(profile, first, last, threshold):
    """The brightness-weighted centre of one run, as a float column.

    Weighted rather than the midpoint of the run, because the run's ends move a whole pixel at
    a time as the line's edge crosses the threshold while its centre has moved a fraction of
    one. The ring travels about 8 px a frame at 10 fps, so a pixel of jitter in the reading is
    a tenth of a frame of error in the click, and this is four lines to not have it.
    """
    columns = np.arange(first, last + 1)
    weights = profile[first:last + 1] - threshold  # only the part above the floor should pull
    return float((columns * weights).sum() / weights.sum())


def drawn(profile, width=RAMP_WIDTH):
    """`profile` as one line of ASCII, brightest pixel in each bucket. For the log.

    The columns are bucketed by max rather than by mean, to match how the profile itself was
    built: a line three columns wide inside a five column bucket must still show up as a line.
    """
    step = len(profile) / width
    out = []
    for i in range(width):
        first = int(i * step)
        chunk = profile[first:max(int((i + 1) * step), first + 1)]
        out.append(RAMP[min(len(RAMP) - 1, int(chunk.max() / 256 * len(RAMP)))])
    return ''.join(out)


def read_lines(image, threshold=LINE_BRIGHT):
    """The two lines in a rep_region crop, as a Lines, or None if there are none to read.

    Both hexagons cross this strip as near vertical edges, so the whole 2D problem collapses to
    one number per column: the brightest pixel in it. A line is then a run of bright columns,
    the leftmost run is the fixed target and the rightmost is the ring coming in. No template
    matching, because the ring is a different size in every single frame.

    max down each column rather than mean, because the ring only crosses part of the strip's
    height in some frames and a mean would dilute it towards the floor.

    One run means the two have met and the answer is a gap of zero. That is not a failure, it
    is the state the whole thing is waiting for.
    """
    profile = np.asarray(image.convert('L'), dtype=float).max(axis=0)
    runs = _runs(profile > threshold)
    if not runs:
        return None
    centres = [_centre(profile, first, last, threshold) for first, last in runs]
    # Half of the first line's width plus half of the last one's: the centre distance at which
    # their edges meet. Measured per frame rather than assumed, because the target band is
    # drawn thicker on some reps than others.
    touch = 0.0 if len(runs) == 1 else ((runs[0][1] - runs[0][0] + 1)
                                        + (runs[-1][1] - runs[-1][0] + 1)) / 2
    lines = Lines(centres[0], centres[-1], centres[-1] - centres[0], touch)
    if VERBOSE:
        log(f'strip [{drawn(profile)}] floor {np.median(profile):.0f}', 2)
        log(f'{len(runs)} run(s): ' + ', '.join(
            f'{first}-{last} peak {profile[first:last + 1].max():.0f} centre {centre:.1f}'
            for (first, last), centre in zip(runs, centres))
            + f'  ->  target {lines.target:.1f} moving {lines.moving:.1f} '
              f'gap {lines.gap:.1f} touch {lines.touch:.1f}', 2)
    return lines


def open_hideout(region=None):
    """Get from wherever we are to the hideout view. True once it is up."""
    raise NotImplementedError('capture gym_hideout_tab, then click it and wait for the hideout')


def open_gym(region=None):
    """From the hideout view, open the gym station. True once the workout window is up.

    Wait for GYM_WINDOW_TARGET rather than sleeping a guess: the scav case window taught us
    that a flat delay is always wrong on a slow load.
    """
    raise NotImplementedError('capture gym_station and gym_window_title')


def is_fatigued(region=None):
    """True when the character is too tired to train, so the pass should stop rather than retry.

    Wants two agreeing reads before it returns True, the way sell.is_item_selected does. One
    template that fails for its own reasons must not read as "keep going" here: the cost of
    getting it wrong is a run that grinds a character who cannot lift.
    """
    raise NotImplementedError('capture gym_fatigue_warning')


def do_one_rep(region=None):
    """Hit one rep on the timing bar. True if it landed, False if it was missed.

    This is the only part of the gym that is a reflex rather than a click: the marker travels
    and the click has to land inside the window. Read REP_MARKER_TARGET against REP_BAR_TARGET
    every REP_POLL and click when it is inside.

    Returns rather than raises on a miss. A missed rep is normal and the set carries on; only
    a bar that never appears is a real failure.
    """
    raise NotImplementedError('capture gym_rep_bar and gym_rep_marker, then time the marker')


def finish_workout(region=None):
    """Close the workout window and get back to a known screen. True once it is shut."""
    raise NotImplementedError('decide what "done" looks like on screen first')


if __name__ == '__main__':  # geometry, checked without needing Tarkov open
    # The ROI against the resolution it was measured at: the numbers straight back out.
    assert rep_region((0, 0, 1920, 1080)) == (1000, 783, 201, 47), rep_region((0, 0, 1920, 1080))

    # And against a bigger screen, which is the whole point of holding it as fractions. Same
    # proportion of the window, so a 4/3 taller screen puts every edge 4/3 further out.
    big = rep_region((0, 0, 2560, 1440))
    assert big == (1333, 1044, 268, 63), big
    for a, b in zip(big, rep_region((0, 0, 1920, 1080))):
        assert abs(a / b - 4 / 3) < 0.01, f'{big} is not 1440p sized, {a} vs {b}'

    # A window that does not start at (0, 0), which is every monitor left of the primary and
    # every windowed game. The offset moves the region and must not stretch it.
    offset = rep_region((-1920, 100, 1920, 1080))
    assert offset == (1000 - 1920, 783 + 100, 201, 47), offset

    # The icon box has to hold every place the icon was seen in the recording, (932, 776) to
    # (993, 848), or the gate it feeds would say "no skill check" in the middle of one.
    icon = icon_region((0, 0, 1920, 1080))
    assert icon == (890, 735, 145, 155), icon
    assert icon[0] <= 932 and icon[1] <= 776, f'{icon} starts inside the measured match'
    assert icon[0] + icon[2] >= 993 and icon[1] + icon[3] >= 848, f'{icon} cuts the match off'
    # And it must stay smaller than the strip search it replaced is worth: the whole point is
    # area, and a box more than a twentieth of the window would not have been worth the change.
    assert icon[2] * icon[3] < 1920 * 1080 / 20, f'{icon} is not much of a saving'

    # One grab has to hold both, and the crop boxes taken out of it have to land back on the
    # regions they came from, or the strip would be read off the wrong pixels entirely.
    window = (0, 0, 1920, 1080)
    look = look_region(window)
    assert look == (890, 735, 311, 155), look
    for part in (icon_region(window), rep_region(window)):
        assert look[0] <= part[0] and look[1] <= part[1], f'{look} does not hold {part}'
        assert look[0] + look[2] >= part[0] + part[2], f'{look} cuts {part} off'
        assert look[1] + look[3] >= part[1] + part[3], f'{look} cuts {part} off'
        box = inside(look, part)
        assert box[2] - box[0] == part[2] and box[3] - box[1] == part[3], f'{box} vs {part}'
        assert (box[0] + look[0], box[1] + look[1]) == part[:2], f'{box} lands wrong'
    # And it still holds on a window that does not start at the origin, which is where an
    # offset bug would otherwise hide until someone ran it on a second monitor.
    moved = (-1920, 100, 1920, 1080)
    assert inside(look_region(moved), rep_region(moved)) == inside(look, rep_region(window))

    # read_lines against drawn strips rather than a real crop, so the maths is checked here and
    # the real frames are checked in tests/gym/test_line_reads.py where they can be looked at.
    from PIL import Image, ImageDraw

    def strip(bars):
        """A dark 201x58 strip with a white bar over each (first, last) column."""
        image = Image.new('RGB', (201, 47), (20, 20, 20))  # 20 is what the gym floor reads
        for first, last in bars:
            ImageDraw.Draw(image).rectangle((first, 0, last, 46), fill=(204, 204, 204))
        return image

    lines = read_lines(strip([(20, 30), (100, 104)]))
    assert abs(lines.target - 25) < 0.01, lines  # centre of 20..30
    assert abs(lines.moving - 102) < 0.01, lines
    assert abs(lines.gap - 77) < 0.01, lines
    # An 11 wide band and a 5 wide line meet when their centres are 8 apart.
    assert abs(lines.touch - 8) < 0.01, lines

    # The log drawing, which has to be a fixed width or two lines under each other stop lining
    # up, which is the only reason it is drawn at all.
    import numpy as np

    for columns in (10, 201, 999):
        picture = drawn(np.linspace(0, 255, columns))
        assert len(picture) == RAMP_WIDTH, f'{columns} columns drew {len(picture)} chars'
    assert drawn(np.zeros(201)) == ' ' * RAMP_WIDTH, 'a black strip draws as blank'
    assert drawn(np.full(201, 255.0)) == RAMP[-1] * RAMP_WIDTH, 'a white one draws as full'

    assert read_lines(strip([])) is None, 'an empty strip reads as nothing, not as a gap of 0'
    assert read_lines(strip([(20, 20)])) is None, 'one lit column is noise, not a line'

    merged = read_lines(strip([(20, 30)]))
    assert merged.gap == 0 and merged.target == merged.moving == 25, merged
    assert merged.touch == 0, f'one line has already touched, {merged}'

    # touch is what the two lines are, not a constant: a thinner band meets its ring later.
    thin = read_lines(strip([(24, 26), (100, 104)]))
    assert abs(thin.touch - 4) < 0.01, thin
    # And two separate runs are always further apart than their touching distance, which is
    # what makes "gap <= touch" a safe way to say "they have already met".
    for shape in ((20, 30), (24, 26), (10, 40)):
        pair = read_lines(strip([shape, (100, 104)]))
        assert pair.gap > pair.touch, pair

    # Three runs, which is what a hexagon corner clipping the strip looks like. The outermost
    # two are still the answer; anything between them is not a line either of us cares about.
    three = read_lines(strip([(20, 30), (60, 62), (100, 104)]))
    assert abs(three.target - 25) < 0.01 and abs(three.moving - 102) < 0.01, three

    # Sub-pixel: a bar with one dim edge column sits off the run's midpoint, towards the bright
    # end. The midpoint would say 25 for both of these and the ring would be read a frame late.
    lopsided = Image.new('RGB', (201, 47), (20, 20, 20))
    ImageDraw.Draw(lopsided).rectangle((21, 0, 30, 46), fill=(204, 204, 204))
    ImageDraw.Draw(lopsided).rectangle((20, 0, 20, 46), fill=(120, 120, 120))  # dim leading edge
    off = read_lines(lopsided)
    assert 25 < off.target < 25.6, f'the dim edge should barely pull the centre left, {off}'

    print('ok')
