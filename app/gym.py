"""Hideout Gym mode: train the character at the hideout gym instead of selling anything.

Nothing to do with the flea. It shares the window handle, the template matcher and the stop
protocol with Tarkbot and that is the whole overlap, so it lives in its own module rather than
as a branch inside bot.py.

SKELETON. train_once() calls into interact/gym.py, every function of which raises
NotImplementedError until its reference images exist. Starting this mode today fails loudly on
the first step and the GUI turns the lamp red, which is the intended state for a skeleton: it
is obviously unfinished rather than quietly doing nothing.
"""
import threading
import time

import tarkov_window
from bot import Retry, Stopped  # shared runner plumbing, see the note on _pause below
from interact import gym
from narrate import log

# What a session looks like. Placeholders: none of this has been checked against the game.
# GUI label -> reps per set, so the dropdown, the saved setting and the loop read one definition,
# the way STALE_THRESHOLDS does for the flea.
ROUTINES = {'light': ('LIGHT', 5), 'normal': ('NORMAL', 10), 'heavy': ('HEAVY', 20)}
DEFAULT_ROUTINE = 'normal'
REST_SECONDS = 60.0  # between sets, so the character is not spammed. Untimed against the game.
SET_ESCAPES = 1  # escapes it takes to get out of the workout window from a half finished set

# The counters gym mode keeps, in the order the GUI lists them. Same shape as bot.STAT_LABELS
# so the GUI can draw either from one code path.
STAT_LABELS = (('sets', 'Sets completed'),
               ('reps', 'Reps hit'),
               ('reps_missed', 'Reps missed'),
               ('fatigued', 'Stopped for fatigue'))
# The row the GUI tints green once it is non-zero, or None for no tint. bot.py names 'money';
# here the equivalent "it is actually working" signal is reps landed.
TINT_STAT = 'reps'


class HideoutGym:
    def __init__(self, reps_per_set=ROUTINES[DEFAULT_ROUTINE][1], rest=REST_SECONDS, stats=None):
        log('Initalizing Hideout Gym')
        self.hwnd = tarkov_window.handle()  # raises WindowError if missing or duplicated
        self.position = tarkov_window.position(self.hwnd)
        self.size = tarkov_window.size(self.hwnd)
        self.region = self.position + self.size  # (left, top, width, height) to search in
        self.reps_per_set = reps_per_set
        self.rest = rest
        log(f'Tarkov window {self.hwnd} at {self.position} size {self.size}')
        log(f'{reps_per_set} reps per set, {rest:.0f}s rest between sets', 1)
        # The GUI hands in its own dict so the counters span the session, exactly as Tarkbot does.
        self.stats = {key: 0 for key, _ in STAT_LABELS} if stats is None else stats
        self._stop = threading.Event()

    def _pause(self, seconds=0):
        """Wait, or abandon the set right now if stop() has been called.

        ponytail: a copy of Tarkbot._pause, not a shared base class. Two runners is not enough
        to justify one, and the gym's real loop is not written yet, so a base class now would be
        guessing at what the two have in common. Hoist _pause, _stop and stop() into a Runner
        the moment a third mode turns up, or the moment these two stop agreeing.
        """
        if self._stop.wait(seconds):  # wait(0) is just a check, no sleep
            raise Stopped()

    def _escape(self, presses):
        """Back out of whatever is on screen, so the next set starts somewhere known."""
        import pyautogui

        log(f'escaping {presses}x back to a clean screen', 1)
        for _ in range(presses):
            pyautogui.press('esc')
            time.sleep(gym.MENU_DELAY)

    def train_once(self):
        """One full set: get to the gym, work through the reps, close out and rest.

        Raises Retry to abandon this set and start a fresh one, the same contract sell_one()
        uses, so a bad screen costs one set rather than the run.
        """
        started = time.monotonic()
        log('opening the hideout')
        if not gym.open_hideout(self.region):
            raise RuntimeError('could not get to the hideout')
        self._pause()

        log('opening the gym')
        if not gym.open_gym(self.region):
            raise RuntimeError('could not open the gym')
        self._pause()

        # Checked before the set rather than after a failed rep: a fatigued character reads as
        # a string of missed reps, and grinding through those looks like the bot working.
        if gym.is_fatigued(self.region):
            self.stats['fatigued'] += 1
            log('character is too fatigued to train')
            self._escape(SET_ESCAPES)
            raise Retry('fatigued')

        for rep in range(1, self.reps_per_set + 1):
            self._pause()
            if gym.do_one_rep(self.region):
                self.stats['reps'] += 1
                log(f'rep {rep}/{self.reps_per_set} landed', 2)
            else:
                self.stats['reps_missed'] += 1
                log(f'rep {rep}/{self.reps_per_set} missed', 2)

        if not gym.finish_workout(self.region):
            raise RuntimeError('could not close the workout window')
        self.stats['sets'] += 1
        log(f'set done, {self.stats["sets"]} so far, {self.stats["reps"]} reps landed. '
            f'Set took {time.monotonic() - started:.1f}s')

        log(f'resting {self.rest:.0f}s before the next set')
        self._pause(self.rest)

    def start(self):
        """Train set after set until stop() is called. Blocks, so give it a thread."""
        log('Starting Hideout Gym')
        self._stop.clear()
        sets = 0
        try:
            while not self._stop.is_set():
                sets += 1
                log(f'===== set {sets} =====')
                try:
                    self.train_once()
                except Retry as e:  # recoverable, the screen has already been backed out of
                    log(f'{e}, starting a fresh set')
                    self._pause(self.rest)  # a fatigued character needs the rest more, not less
        except Stopped:
            log('stopped part way through a set')
        log(f'Hideout Gym finished after {sets} sets. '
            + ', '.join(f'{label} {self.stats[key]}' for key, label in STAT_LABELS))

    def stop(self):
        """Ask the loop to quit. Safe from any thread, and safe to call twice."""
        log('Stopping Hideout Gym')
        self._stop.set()


def build(prefs, stats):
    """A HideoutGym configured from the GUI's saved preferences.

    Here rather than in the GUI so the mapping from a settings key to a constructor argument
    sits beside the constants those keys index into. bot.build() is the same function for the
    flea, and the GUI calls whichever the active tab names.
    """
    _, reps = ROUTINES.get(prefs.get('routine'), ROUTINES[DEFAULT_ROUTINE])
    return HideoutGym(reps_per_set=reps, stats=stats)
