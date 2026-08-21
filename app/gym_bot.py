"""Hideout Gym mode: hit the workout skill check, over and over, until told to stop.

The skill check is one thin hexagon shrinking onto a fixed smaller one, and the rep lands if
the click goes in while they overlap. interact/gym.py turns that into two numbers by reading a
thin strip off the right of both hexagons (see REP_ROI_FRACTIONS): the fixed one's edge and the
closing one's, as columns. The gap between them is all this module needs.

It does not navigate anywhere. Start it with the workout already running and it clicks reps;
Stop ends it. Getting to the hideout, opening the gym and reading fatigue are still stubs in
interact/gym.py, so nothing here presses anything but the mouse button.

The icon comes first, every single look, and the strip is only read once it has matched. The
strip on its own cannot tell a skill check from anything else: an early version read it first
and looked for the icon only when it came back empty, on the grounds that a template match
costs time the closing ring does not have. It clicked fifteen times at a character standing
still, because a bright scene fills the whole strip and one run spanning all 201 columns is
indistinguishable from two lines that have met. The icon is the only thing on screen that says
a rep is being asked for, so nothing is read or clicked until it says so.
"""
import threading
import time
from collections import deque

import pyautogui

# Every clock reading in this module is time.perf_counter(), never time.monotonic(). On Windows
# monotonic() ticks about every 15.6ms, which is why a look was only ever logged as 47ms or
# 62ms: those are three and four ticks. The predictor divides a change in gap by a change in
# time, so a 15ms error in the divisor is a 30% error in the ring's speed and therefore in
# where the press lands. perf_counter() is the sub-microsecond one.

import screen
import window
from gui.settings import APP_DIR
from interact import find, gym
from narrate import log
from sell_bot import Stopped  # shared runner plumbing, see the note on _pause below

# Every strip that got clicked, saved while gym.VERBOSE is on, beside the logs and the frames.
# The log says what the numbers were; these say what the screen was, which is the only way to
# tell a real skill check apart from something else in the gym that happened to be bright.
# ponytail: no cap on how many pile up. They are about 5KB each. Add one if that stops being
# true, or delete the folder.
STRIP_DIR = APP_DIR / 'gym'

IDLE_POLL = 0.1  # seconds between looks while there is no skill check on screen
# ROI columns between the two lines that counts as lined up. 0 means "not until they touch",
# which assumes reading, deciding and clicking take no time at all. They do not, so this is the
# number to raise once a real run says how late the clicks land: every 1 here is one column of
# ring travel, and the ring covers about 8 of them per 100ms.
CLICK_GAP = 0.0
# The two trim knobs, and they are not interchangeable. Which one to reach for is decided by
# whether the reps that miss are the fast ones or all of them.
#
# Columns short of the centres lining up to aim at. 0 aims at the centres themselves. Raising
# it presses earlier by that many columns at every speed, so this is the knob for a miss that
# looks the same on the first rep of a set and the fifteenth. Aiming at Lines.touch, 4 to 8
# columns, was tried and pressed too early on every rep.
AIM_COLUMNS = 0.0
# Seconds to shift the press. Positive presses earlier, negative presses later. A fixed time
# error costs more columns the faster the ring is going, so this is the knob for reps that land
# early in a set and miss late in it, when the only thing that has changed is speed.
#
# 15ms, and this is the knob for it rather than AIM_COLUMNS because what is being cancelled is
# a delay: the press is sent, and Windows and the game between them take a while to act on it.
# A delay costs more columns the faster the ring goes, which is exactly what a lead in seconds
# corrects and a spatial offset does not.
#
# It was 0, on the strength of three sessions that found a lead worse in both directions. Those
# predate two changes that make them unreadable: the loop now reads through screen.fast_grab,
# and a reading is anchored to when its pixels were grabbed rather than to when the look began,
# which on its own was pressing a whole grab early. Scored properly against the green and red
# flash the game gives each rep, over reps 11 to 15 of four recorded sets, 20 presses:
#     press landed under 0ms early    0 of 2 landed
#                        0 to 5ms     2 of 4
#                        5 to 10ms    3 of 7
#                        10 to 15ms   3 of 4
#                        15 to 20ms   3 of 3
#                        20 to 35ms   4 of 5
# So the aim point is not the two centres lining up, it is a good 20ms before that, and pressing
# at the centres is the one thing that reliably misses. That is the lopsided measurement the
# note here used to ask for. Aiming dead on scored 11 of 15; the run before it, which pressed
# early by accident, scored 14. Nothing yet says where too early starts: on the fastest reps,
# every press 18ms or more ahead has landed.
CLICK_LEAD = 0.020
# How many readings the ring's speed is measured across, oldest to newest. Two is the fewest
# that works and the noisiest: each gap is good to about half a column, so a short baseline
# turns that half column into a large fraction of the speed. Measuring across a longer span
# averages it out, and matters more the faster the loop reads, since faster reads mean less
# travel between them and a worse ratio.
#
# 12, which at the loop's ~15ms look is most of a rep. It was 4, and 4 is not enough now that
# the aim has to be good to a column: a gap is good to about half a column, so 4 samples spanning
# 50ms measure a 350 column/second ring to within about 6%, and 12 spanning 150ms to within 2%.
# The ring's speed inside one rep is dead constant (measured: steps of 11 11 11 11 10 11 10 11
# columns), so a longer baseline costs nothing and there is still no curve to fit.
SPEED_SAMPLES = 12
# ponytail: a look is now one screenshot sliced in two, about 50ms, and 45 of those 50 are the
# grab. Pillow photographs the whole virtual desktop however small the region asked for, and
# passing it a bbox does not help, it crops internally. A ctypes BitBlt of just the look box
# measures 17ms, but its pixels come back 1 to 2 levels per channel off Pillow's, and
# screen.grab also feeds ocr.py's digit templates and sell.py's dead pixel colors at ±5 a
# channel. Not worth a second capture path with a color difference nobody has explained.
# Seconds after a click before another one can land. The lines stay overlapped for a moment
# after a rep, and without this one rep would read as several clicks. Guessed, not measured.
REP_COOLDOWN = 0.5

# The counters gym mode keeps, in the order the GUI lists them. Same shape as
# sell_bot.STAT_LABELS so the GUI can draw either from one code path.
STAT_LABELS = (('reps', 'Reps clicked'),)
# The row the GUI tints green once it is non-zero. sell_bot.py names 'money'; here the "it is
# actually working" signal is clicks that went in.
TINT_STAT = 'reps'


class HideoutGym:
    def __init__(self, gap=CLICK_GAP, stats=None):
        log('Initalizing Hideout Gym')
        self.hwnd = window.handle()  # raises WindowError if missing or duplicated
        self.position = window.position(self.hwnd)
        self.size = window.size(self.hwnd)
        self.monitor = screen.current()
        self.region = screen.overlap(self.position + self.size, self.monitor.rect)
        if self.region is None:  # same rule as FleaSeller, see the note there
            raise window.WindowError(
                f'Tarkov is at {self.position + self.size}, which is not on monitor '
                f'{self.monitor.label} at {self.monitor.rect}. Pick the other monitor, or move '
                f'the game onto this one.')
        self.roi = gym.rep_region(self.region)
        self.icon_roi = gym.icon_region(self.region)
        # One screenshot per look, sliced into the two parts. See gym.look_region.
        self.look_roi = gym.look_region(self.region)
        self._icon_at = gym.inside(self.look_roi, self.icon_roi)
        self._strip_at = gym.inside(self.look_roi, self.roi)
        self.gap = gap
        log(f'Tarkov window {self.hwnd} at {self.position} size {self.size}')
        log(f'monitor {self.monitor.label} ({self.monitor.name}) at {self.monitor.rect}, '
            f'searching {self.region}', 1)
        log(f'skill check strip {self.roi}, icon searched in {self.icon_roi}, '
            f'clicking at a gap of {self.gap:.1f} or less', 1)
        # The GUI hands in its own dict so the counters span the session, exactly as FleaSeller does.
        self.stats = {key: 0 for key, _ in STAT_LABELS} if stats is None else stats
        self._stop = threading.Event()
        self._idle = False  # whether the last look found no icon, so waiting logs once
        self._last = deque(maxlen=SPEED_SAMPLES)  # (capture time, gap) readings of this rep
        self._due = None  # when this rep's press is aimed for, once a speed has been measured

    def _pause(self, seconds=0):
        """Wait, or drop out of the loop right now if stop() has been called.

        ponytail: a copy of FleaSeller._pause, not a shared base class. Two runners is not enough
        to justify one. Hoist _pause, _stop and stop() into a Runner the moment a third mode
        turns up, or the moment these two stop agreeing.
        """
        if self._stop.wait(seconds):  # wait(0) is just a check, no sleep
            raise Stopped()

    def _save_strip(self, strip):
        """Keep the strip that was just clicked on, named for the millisecond. Its path, or None.

        Named the same way frames.py names its frames, so a saved strip lines up against the
        log line printed beside it.
        """
        if not gym.VERBOSE:
            return None
        STRIP_DIR.mkdir(parents=True, exist_ok=True)
        path = STRIP_DIR / f'{int(time.time() * 1000)}-rep.png'
        strip.save(path)
        return path

    def click_rep(self):
        """Left click the middle of the strip. Returns the point clicked.

        Deliberately not pyautogui.click: frames.py wraps that to save a screenshot *before*
        the input goes out, about 100ms, and this is the one click in the app where 100ms is
        the difference between a rep and a miss. mouseDown/mouseUp are not wrapped. To see what
        a rep actually looked like, record it with _recorder/ rather than reaching for the
        frames folder.
        """
        left, top, width, height = self.roi
        point = (left + width // 2, top + height // 2)
        pyautogui.mouseDown(*point)
        pyautogui.mouseUp(*point)
        return point

    def _wait(self):
        """No skill check on screen: say so once, then wait IDLE_POLL before looking again."""
        if not self._idle:
            self._idle = True
            log('no skill check on screen, waiting')
        self._pause(IDLE_POLL)

    def do_one_rep(self):
        """One look at the screen. True if that look ended in a click.

        The icon first, always. A missing reference folder raises out of find, and is meant to:
        with no icon to match, this loop would wait forever and look like a bot that runs and
        does nothing, which is worse than one that stops and says why.

        Returns without sleeping while the ring is still closing, on purpose: that is the phase
        where every millisecond not spent looking is ring travel gone unseen.
        """
        started = time.perf_counter()
        shot = screen.fast_grab(self.look_roi)  # not screen.grab, see the note on fast_grab
        grabbed = time.perf_counter()
        if not find.find(gym.REP_HEXAGON_TARGET, haystack=shot.crop(self._icon_at)):
            # Whatever was closing has gone; do not carry its speed or its aim into the next rep
            self._forget()
            self._wait()
            return False
        self._idle = False
        found = time.perf_counter()

        strip = shot.crop(self._strip_at)
        lines = gym.read_lines(strip)
        if gym.VERBOSE:
            # How long one look costs, which is exactly the lag CLICK_GAP has to make up for:
            # the ring has already moved this much further in by the time the click goes out.
            log(f'look took {(time.perf_counter() - started) * 1000:.0f}ms '
                f'(grab {(grabbed - started) * 1000:.0f}ms, '
                f'icon {(found - grabbed) * 1000:.0f}ms)', 2)
        if lines is None:
            self._forget()
            return False  # icon up but nothing readable yet, which is the prompt still fading in
        if lines.gap > AIM_COLUMNS + self.gap:
            # grabbed, not started. This is when the pixels being read are from, and the whole
            # aim hangs off it: a reading anchored to the wrong moment is extrapolated forward
            # from the wrong place, and the press lands early by however long the grab took.
            # Which of the two it is was measured rather than assumed. The ring closes at a dead
            # constant speed inside one rep, so the right clock is the one that makes gap against
            # time straightest. Over 15 reps and 453 looks of recording_06, the residual about a
            # straight line was 0.62 columns against grabbed and 0.72 against started, and the
            # grab is not a fixed cost (8 to 22ms), which is what lets the two be told apart at
            # all. Anchoring to started was therefore pressing a whole grab early: 12ms on
            # average, which is 4 columns at the 313 columns a second rep 15 closes at, into a
            # window about 2.5 columns wide.
            return self._predict(grabbed, lines, strip)

        # The lines met before any look could commit to a moment. If an earlier look in this
        # rep worked one out, honour it: the aimed moment can legitimately be *after* the two
        # lines merge, since the ring keeps travelling once its edge is inside the band, and a
        # CLICK_LEAD that presses late puts it there on purpose. Pressing on sight here would
        # quietly throw that away and cap how late the loop can ever be aimed.
        due = self._due
        self._forget()
        wait = 0.0 if due is None else due - time.perf_counter()
        if wait > 0:
            self._sleep(wait)
        return self._click(f'met at column {lines.target:.1f}, held {wait * 1000:.0f}ms'
                           if wait > 0 else f'met at column {lines.target:.1f}', strip)

    def _forget(self):
        """Drop this rep's readings and its aim, so the next one is measured from scratch.

        Speeds are per rep and rise through a set, so carrying a reading across a gap in the
        skill check would aim the next rep with the last one's pace.
        """
        self._last.clear()
        self._due = None

    def _sleep(self, seconds):
        """Wait `seconds` accurately, noticing a Stop either side of it.

        Not _pause, which waits on the Event so Stop can land mid wait: on Windows that wait
        rounds up to the 15.6ms timer tick, measured at 45ms for a 31ms ask. Rounding a press
        up by 15ms is a third of a look, and at 240 columns a second it is 4 columns past where
        it was aimed. time.sleep is the accurate one. The cost is that a Stop pressed during
        this wait lands when it finishes, and it is never longer than one look.
        """
        self._pause()  # a Stop that already happened must not be slept through first
        time.sleep(seconds)
        self._pause()

    def _predict(self, captured, lines, strip):
        """Two readings give the ring's speed. If the overlap lands before the next look could
        see it, sleep until it and press. True if that happened.

        Aiming at a predicted moment rather than an observed one is the whole trick. A look
        costs about 48ms and the pixels are already ~45ms old when it finishes, while the ring
        closes at anywhere from 75 to 235 columns a second depending on how far into a set it
        is. Waiting to see the lines meet therefore means pressing between 7 and 25 columns
        past them, which is why reps 1-9 of a set used to land and 10 onwards did not. Speed
        measured per rep needs no such constant, and it tracks the ring speeding up as the set
        goes on.

        The commit test is against the measured look period rather than a tuned threshold: if
        the overlap will happen sooner than the next look could report it, this is the last
        chance to aim, so take it. Otherwise loop again and get a better estimate from a
        shorter extrapolation.
        """
        self._last.append((captured, lines.gap))
        if len(self._last) < 2:
            return False  # first reading of this rep, nothing to measure a speed against
        # Oldest against newest, rather than the last two: the same half a column of reading
        # error spread over three times the travel is a third of the speed error. Endpoints
        # rather than a fitted line because the ring's speed inside one rep is dead constant
        # (measured: steps of 11 11 11 11 10 11 10 11 columns), so there is no curve to fit.
        (first, far), (recent, near) = self._last[0], self._last[-1]
        period = captured - self._last[-2][0]  # one look, which is what the commit test needs
        speed = (far - near) / (recent - first) if recent > first else 0
        if speed <= 0:
            return False  # standing still or drifting apart: not a ring closing in

        # Aimed at the centres lining up, less whatever AIM_COLUMNS and CLICK_LEAD trim off.
        # Aiming at Lines.touch instead, where the two lines first meet, was tried on the
        # strength of every fallback press having landed there, and pressed too early on every
        # rep at every speed. The touch is still logged, as the width of the window being
        # aimed into.
        due = captured + (lines.gap - AIM_COLUMNS) / speed - CLICK_LEAD
        self._due = due  # kept for the merged branch, in case no look gets to commit
        wait = due - time.perf_counter()
        # Commit on the last look that can still see two lines, not on the last look before the
        # press is due. Those are not the same moment and the difference is the whole reason the
        # end of a set used to miss: the two runs stop being separate once their edges meet,
        # which is Lines.touch columns before their centres line up. On rep 15, touch is 3
        # columns and the ring covers 5 in a look, so the merge lands inside the same look period
        # the old test was waiting for. The predictor therefore never got to commit, read_lines
        # came back with one run, and the press fell through to the merged branch, which fires
        # the moment the edges touch and is early by exactly that much. Measured over a scored
        # 15 rep set: 13 of 15 presses went through that fallback and every one was early, by
        # +1.9 columns on average, and the two that missed were the two where the window had
        # shrunk to less than that.
        # Two reasons to stop deferring, and it commits on whichever comes first. The lines are
        # about to merge, so this is the last look that can measure anything; or the press is
        # about to fall due, so waiting for another look would miss it. Deferring needs both to
        # agree there is time.
        # The second one is back because the aim point is no longer the merge. With CLICK_LEAD
        # at 15ms and a rep 14 ring at 313 columns a second, the press is due about 5 columns
        # before the centres line up, which is sooner than the two lines stop being separate.
        # Waiting for the merge look there meant the aim point had already gone by, so the press
        # went out the instant it could and delivered 8.6ms of the 15ms it was asked for. That
        # rep missed and the one before it, which got its full lead, landed.
        if (lines.gap - lines.touch) / speed > period and wait > period:
            return False  # another look is affordable, and it will know better
        if wait > 0:
            self._sleep(wait)
        self._forget()
        return self._click(f'predicted at {speed:.0f} col/s from a gap of {lines.gap:.1f} '
                           f'and a touch of {lines.touch:.1f}, '
                           f'waited {max(wait, 0) * 1000:.0f}ms', strip)

    def _click(self, why, strip):
        """Press, count it, keep the strip, and sit out the cooldown. Always True."""
        point = self.click_rep()
        self.stats['reps'] += 1
        saved = self._save_strip(strip)
        log(f'rep {self.stats["reps"]}: {why}, clicked {point}'
            + (f', strip {saved.name}' if saved else ''))
        self._pause(REP_COOLDOWN)  # or the same overlap reads as several reps
        return True

    def start(self):
        """Hit reps until stop() is called. Blocks, so give it a thread."""
        log('Starting Hideout Gym')
        self._stop.clear()
        self._idle = False
        self._forget()
        started = time.perf_counter()
        try:
            while not self._stop.is_set():
                self.do_one_rep()
        except Stopped:
            log('stopped between reps')
        finally:
            # finally, for the same reason as sell_bot.start(): an error out of a look is not
            # caught here, and the totals are worth more on a crashed run than on a clean one.
            log(f'Hideout Gym finished after {time.perf_counter() - started:.0f}s. '
                + ', '.join(f'{label} {self.stats[key]}' for key, label in STAT_LABELS))

    def stop(self):
        """Ask the loop to quit. Safe from any thread, and safe to call twice."""
        log('Stopping Hideout Gym')
        self._stop.set()


def build(prefs, stats):
    """A HideoutGym configured from the GUI's saved preferences.

    Gym mode has nothing to configure yet beyond the monitor, which every mode shares, so this
    is thinner than sell_bot.build(). It exists because the GUI calls build() on whichever tab
    is active and does not know one mode from another.
    """
    screen.use(prefs.get('monitor', screen.AUTO))  # before the runner, which clips to it
    return HideoutGym(stats=stats)
