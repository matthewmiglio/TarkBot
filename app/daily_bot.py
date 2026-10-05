"""
DailyReset: the fifth mode, rerolling Ragman's operational 'Find and transfer' task with REPLACE
until it asks for WD-40 (100ml), then stopping on its own.

Start it on TRADERS > TASKS with Ragman selected. Accepting the task is left to the player.
Grew out of _sudak_daily_resetter/daily_resetter.py, which is where the thresholds were measured.
"""
import threading

import pyautogui

import screen
from interact import find
from narrate import log
from sell_bot import Stopped

OFFER = 'tasks/find_and_transfer_daily_offer'
REPLACE = 'tasks/replace_daily_button'
WD_40 = 'tasks/wd_40_100ml'

# Where the objective line sits, as fractions of the screen (left, top, width, height). Measured off
# _sudak_daily_resetter/fixtures/wd_40_100ml_example_offer_daily_frame.png (2560x1440).
OBJECTIVE_FRACTIONS = (0.251, 0.550, 0.745, 0.106)
# The crop is '(100ml)' alone: a crop of the whole objective line is mostly text every offer
# shares, which let 'Ripstop fabric' (0.836) and then 'WD-40 (400ml)' (0.987) through. '(100ml)'
# reads 0.991 on 100ml, 0.872 on 400ml and 0.566 on Ripstop, and 0.95 sits in that gap. It has no
# center subcrops on purpose: a smaller crop is mostly the '00ml' that 400ml shares.
WD_40_CONFIDENCE = 0.95

SETTLE = 0.5  # after clicking the offer, before reading its objective. ponytail: a guess, worked
REPLACE_SETTLE = 1.0  # after confirming REPLACE with 'y'

STAT_LABELS = (('replaced', 'Quests replaced'),)
TINT_STAT = 'replaced'


class DailyReset:
    def __init__(self, stats=None):
        self.stats = stats if stats is not None else {key: 0 for key, _ in STAT_LABELS}
        self._stop = threading.Event()

    def _pause(self, seconds=0):
        if self._stop.wait(seconds):
            raise Stopped()

    def _find_or_raise(self, name):
        point = find.find_center(name, region=screen.rect())
        if point is None:
            raise LookupError(f'{name} is not on screen')
        return point

    def objective_region(self):
        left, top, width, height = screen.rect()
        fl, ft, fw, fh = OBJECTIVE_FRACTIONS
        return (left + round(width * fl), top + round(height * ft),
                round(width * fw), round(height * fh))

    def is_wd_40_100ml_offer(self):
        return find.find(WD_40, region=self.objective_region(),
                         confidence=WD_40_CONFIDENCE) is not None

    def click_daily_offer(self):
        pyautogui.click(*self._find_or_raise(OFFER))
        self._pause(SETTLE)

    def replace_daily_task(self):
        """Replace the task, then reopen it: the panel keeps showing the old offer until clicked."""
        pyautogui.click(*self._find_or_raise(REPLACE))
        pyautogui.press('y')
        self._pause(REPLACE_SETTLE)
        self.click_daily_offer()

    def start(self):
        """Replace until WD-40 (100ml) is up or stop() is called. Blocks, so give it a thread."""
        log('Starting Daily Reset')
        self._stop.clear()
        try:
            self.click_daily_offer()
            while not self.is_wd_40_100ml_offer():
                self.replace_daily_task()
                self.stats['replaced'] += 1
                log(f'replaced ({self.stats["replaced"]})', 1)
            log(f'WD-40 (100ml) offer up after {self.stats["replaced"]} replacements')
        except Stopped:
            log('stopped between replacements')

    def stop(self):
        log('Stopping Daily Reset')
        self._stop.set()


def build(prefs, stats):
    """A DailyReset on the GUI's chosen monitor. Nothing else to configure."""
    screen.use(prefs.get('monitor', screen.AUTO))
    return DailyReset(stats=stats)
