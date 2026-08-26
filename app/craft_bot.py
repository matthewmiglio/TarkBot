"""Hideout Craft mode: keep the nutrition unit's slickers craft running, buying what it needs.

The loop is a small state machine over interact/craft.get_slickers_craft_state:
  - producing         -> wait, the craft is already running
  - ready, ingredients in the stash    -> click START
  - ready, ingredients missing         -> buy each missing one off the flea, then look again
Anything else (a finished craft waiting to be collected, or one not started) is left alone for
now and just waited through; collecting is not this mode's job yet.

Navigation to the nutrition unit is done once at Start through craft.get_to_nutrition_unit, which
clicks the hideout tab if needed and swipes the module carousel across to it. Same runner shape
as gym_bot.py and the two flea modes: a stats dict the GUI also owns, a _pause checkpoint every
wait goes through so Stop lands mid loop, and build(prefs, stats).
"""
import threading
import time

import pyautogui

import screen
import window
from interact import craft, find, sell
from narrate import log
from sell_bot import Stopped  # shared runner plumbing, see the _pause note below

PRODUCING_WAIT = 10.0  # seconds to wait while the craft is running before looking again
IDLE_WAIT = 5.0  # seconds to wait in a state this loop does nothing with (done / not started)
HANDOVER_TARGET = 'handover_button'  # the confirm button the START click brings up
HANDOVER_DELAY = 1.0  # seconds after START for the handover confirm button to appear
COLLECT_SETTLE = 2.0  # seconds after collecting for the row to flip back to ready
PARK_OFFSET = 100  # 1080p px to shove the cursor right after a click, so it stops covering the row

# The most roubles to pay for one of each ingredient on the flea before buy_craft_input_item
# backs out. The GUI types these into a digits-only field (settings stores the string); build()
# below reads them back as ints. Defaults are what a slickers input is worth today; change them
# to whatever it is worth to you.
DEFAULT_CRACKERS_MAX = 22000
DEFAULT_ALYONKA_MAX = 17500

# Estimated net roubles one finished slickers craft is worth: the output's flea value less what
# its inputs cost. A single figure, not a live read, so 'Est. profit' below is crafts * this.
# ponytail: a constant, since input prices and the output value both drift; update it when they
# have, or read it off the market if this ever needs to be exact rather than an estimate.
PROFIT_PER_CRAFT = 12152

# The counters, in the order the GUI lists them. Same shape as sell_bot.STAT_LABELS.
STAT_LABELS = (('crafts', 'Crafts started'), ('bought', 'Inputs bought'),
               ('profit', 'Est. profit'))
TINT_STAT = 'profit'  # the row that goes green: estimated profit is the working signal, like money


class HideoutCraft:
    def __init__(self, max_prices=None, stats=None):
        log('Initalizing Hideout Craft')
        self.hwnd = window.handle()  # raises WindowError if missing or duplicated
        self.position = window.position(self.hwnd)
        self.size = window.size(self.hwnd)
        self.monitor = screen.current()
        self.region = screen.overlap(self.position + self.size, self.monitor.rect)
        if self.region is None:  # same rule as FleaSeller and HideoutGym
            raise window.WindowError(
                f'Tarkov is at {self.position + self.size}, which is not on monitor '
                f'{self.monitor.label} at {self.monitor.rect}. Pick the other monitor, or move '
                f'the game onto this one.')
        # Per-ingredient rouble ceilings, keyed by the same names validate returns ('crackers',
        # 'alyonka'). The GUI fills this in; an ingredient with no ceiling here is not bought,
        # since buying with a made-up price is the one mistake that spends real money.
        self.max_prices = dict(max_prices or {})
        self.stats = {key: 0 for key, _ in STAT_LABELS} if stats is None else stats
        self._stop = threading.Event()
        log(f'Tarkov window {self.hwnd} at {self.position} size {self.size}', 1)
        log(f'monitor {self.monitor.label} at {self.monitor.rect}, searching {self.region}', 1)
        log(f'input price ceilings: {self.max_prices or "none set"}', 1)

    def _park(self, point):
        """Move the cursor right of a just-clicked button so it stops covering the next read.
        The click's own hover keeps a highlight/tooltip over the button that the state and
        find calls then misread; parking clears it."""
        pyautogui.moveTo(point.x + round(PARK_OFFSET * find.scale()), point.y)

    def _pause(self, seconds=0):
        """Wait, or drop out of the loop now if stop() was called. A copy of FleaSeller._pause;
        hoist all three modes' copies into a Runner when one of them needs to diverge."""
        if self._stop.wait(seconds):  # wait(0) is just a check, no sleep
            raise Stopped()

    def _ensure_on_nutrition_unit(self):
        """Steps 1-2: get to the nutrition unit if we are not already looking at it."""
        if craft.check_if_nutrition_unit_active(self.region):
            log('already on the nutrition unit', 1)
            return
        log('not on the nutrition unit, navigating there', 1)
        craft.get_to_nutrition_unit(self.region)  # raises LookupError if it cannot get there

    def start_craft(self):
        """Start the slickers craft: click START, then confirm on the handover button.

        Two clicks, not one. START opens a handover dialog (it hands the ingredients over from the
        stash), and the craft only begins once that is confirmed. Returns the START point clicked,
        or None if there was no START button to click.
        """
        band = craft.find_slickers_craft(self.region)
        if band is None:
            log('no slickers craft on screen to start', 1)
            return None
        point = find.find_center(craft.START_TARGET, band)
        if point is None:
            log('no START button in the slickers row', 1)
            return None
        point = sell.jitter(point)
        log(f'starting the craft, clicking START at {point}', 1)
        pyautogui.click(*point)

        time.sleep(HANDOVER_DELAY)
        confirm = find.find_center(HANDOVER_TARGET, self.region)
        if confirm is None:
            log('START clicked but no handover button appeared to confirm it', 1)
            self._park(point)
            return point  # the click went out; the counter below still reflects the attempt
        confirm = sell.jitter(confirm)
        log(f'confirming the handover at {confirm}', 1)
        pyautogui.click(*confirm)
        self._park(confirm)
        self.stats['crafts'] += 1
        return point

    def collect_craft(self):
        """Collect a finished craft: click its GET ITEMS button. Returns the point, or None.

        The row has no timer in the done state, so the band comes from slickers_row_band (which
        works in any state) rather than find_slickers_craft. Profit is booked here, not at Start:
        an estimate is only real once the craft is actually collected.
        """
        band = craft.slickers_row_band(self.region)
        if band is None:
            log('no slickers craft on screen to collect', 1)
            return None
        point = find.find_center(craft.GET_ITEMS_TARGET, band)
        if point is None:
            log('no GET ITEMS button in the slickers row', 1)
            return None
        point = sell.jitter(point)
        log(f'collecting the craft, clicking GET ITEMS at {point}', 1)
        pyautogui.click(*point)
        self._park(point)
        self.stats['profit'] += PROFIT_PER_CRAFT
        return point

    def buy_missing(self, item):
        """Buy one missing ingredient off the flea, at its configured ceiling. True if it bought."""
        ceiling = self.max_prices.get(item)
        if ceiling is None:
            log(f'no price ceiling set for {item}, skipping it this pass', 1)
            return False
        band = craft.find_slickers_craft(self.region)
        if band is None:
            log('lost the slickers craft before buying, skipping', 1)
            return False
        location = find.find_center(f'crafting/{item}', band)
        if location is None:
            log(f'could not find {item} on the craft row to buy it', 1)
            return False
        log(f'buying {item} at up to {ceiling}', 1)
        bought = craft.buy_craft_input_item(location, ceiling, self.region)
        if bought:
            self.stats['bought'] += 1
        return bought

    def step(self):
        """One pass of the state machine (step 3)."""
        state = craft.get_slickers_craft_state(self.region)
        if state == 'producing':
            log(f'craft is producing, waiting {PRODUCING_WAIT}s')
            self._pause(PRODUCING_WAIT)
            return
        if state == 'done':
            self.collect_craft()
            self._pause(COLLECT_SETTLE)  # let the row flip back to ready before the next look
            return
        if state != 'ready':  # 'not started': nothing this loop does yet
            log(f'craft state is {state!r}, nothing to do, waiting {IDLE_WAIT}s')
            self._pause(IDLE_WAIT)
            return

        ready, missing = craft.validate_slickers_craftable(self.region)
        if ready:
            self.start_craft()
            self._pause(PRODUCING_WAIT)  # give the click time to flip the row to producing
            return

        log(f'missing {missing}, buying each')
        for item in missing:
            self._pause()  # a Stop between buys lands here
            self.buy_missing(item)

    def start(self):
        """Navigate to the nutrition unit, then run the craft loop until stop(). Blocks."""
        log('Starting Hideout Craft')
        self._stop.clear()
        started = time.perf_counter()
        try:
            self._ensure_on_nutrition_unit()
            while not self._stop.is_set():
                self.step()
        except Stopped:
            log('stopped between steps')
        finally:
            log(f'Hideout Craft finished after {time.perf_counter() - started:.0f}s. '
                + ', '.join(f'{label} {self.stats[key]}' for key, label in STAT_LABELS))

    def stop(self):
        """Ask the loop to quit. Safe from any thread, and safe to call twice."""
        log('Stopping Hideout Craft')
        self._stop.set()


def _ceiling(value, default):
    """A settings string parsed to roubles, falling back to default if it is blank or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build(prefs, stats):
    """A HideoutCraft configured from the GUI's saved preferences.

    The GUI stores each ceiling as a typed rouble string (crackers_max, alyonka_max); parse the
    two into the {item: roubles} dict the runner buys against, keyed by the names
    validate_slickers_craftable returns.
    """
    screen.use(prefs.get('monitor', screen.AUTO))  # before the runner, which clips to it
    max_prices = {
        'crackers': _ceiling(prefs.get('crackers_max'), DEFAULT_CRACKERS_MAX),
        'alyonka': _ceiling(prefs.get('alyonka_max'), DEFAULT_ALYONKA_MAX),
    }
    return HideoutCraft(max_prices=max_prices, stats=stats)
