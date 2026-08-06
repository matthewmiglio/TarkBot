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

from interact import find  # noqa: F401  (the stubs will all use it)
from narrate import log

# Reference image folders, all gym_ prefixed so they group in the reference_images listing the
# way flea_filters_ does. NONE OF THESE EXIST YET.
HIDEOUT_TAB_TARGET = 'gym_hideout_tab'  # the hideout entry on the main menu
GYM_STATION_TARGET = 'gym_station'  # the gym itself, in the hideout view
WORKOUT_BUTTON_TARGET = 'gym_workout_button'  # starts a session
GYM_WINDOW_TARGET = 'gym_window_title'  # the workout window's title bar, for orientating
REP_BAR_TARGET = 'gym_rep_bar'  # the timing bar the reps are hit against
REP_MARKER_TARGET = 'gym_rep_marker'  # the travelling marker on that bar
FATIGUE_TARGET = 'gym_fatigue_warning'  # shown once the character is too tired to continue

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
    # Nothing to assert yet: every function here is a stub and there is no derived geometry.
    # This block exists so the module answers `python -m interact.gym` the way sell.py does,
    # and so there is somewhere obvious to put the first real assertion.
    print('ok (skeleton: no geometry to check yet)')
