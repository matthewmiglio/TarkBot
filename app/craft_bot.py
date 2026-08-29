"""Hideout Craft mode: keep several hideout crafts running, buying what each one needs.

There is more than one craft now (slickers at the nutrition unit, fleece at the lavatory), each
at its own station. The loop cycles between them: it works the craft in front of it, and the
moment that craft is only producing (nothing to do but wait) it swaps to the next station and
works that one, round and round. So while one craft runs its timer the bot is off tending the
other, and it never sits idle staring at a progress bar.

Per craft the state machine over interact/craft.get_craft_state is:
  - producing         -> wait a beat, then swap to the next craft's station
  - done              -> collect the finished items (GET ITEMS), then look again
  - ready, ingredients in the stash    -> click START, confirm the handover
  - ready, ingredients missing         -> buy each missing one off the flea, then look again
  - not started (greyed GET ITEMS)     -> nothing to do here, swap to the next craft
An output the reader cannot find on screen is none of those: get_craft_state raises LookupError
and the run ends, rather than the loop guessing a state for a row it cannot see. See its note.

Each craft carries its own rouble ceilings and offer sources (players/traders) per ingredient,
filled in from the GUI. Same runner shape as gym_bot.py and the two flea modes: a stats dict the
GUI also owns, a _pause checkpoint every wait goes through so Stop lands mid loop, and
build(prefs, stats).
"""
import threading
import time
from collections import namedtuple

import pyautogui

import screen
import window
from interact import craft, find, sell
from narrate import log
from sell_bot import Stopped  # shared runner plumbing, see the _pause note below

START_SETTLE = 3.0  # seconds after START for the row to flip to producing before the next look
HANDOVER_TARGET = 'hideout/handover_button'  # the confirm button the START click brings up
HANDOVER_DELAY = 1.0  # seconds after START for the handover confirm button to appear
COLLECT_SETTLE = 2.0  # seconds after collecting for the row to flip back to ready
PARK_OFFSET = 100  # 1080p px to shove the cursor right after a click, so it stops covering the row

# The GUI's per-ingredient SOURCE picker. 'Players' or 'Traders' as shown; build() lowercases them
# into what sell.apply_flea_filters expects.
SOURCES = ('Players', 'Traders')
DEFAULT_SOURCE = 'Players'

# Per-ingredient defaults, used when the GUI has no saved value (or a junk one). The max is the most
# roubles to pay on the flea; the source is who to buy from. These match settings.DEFAULTS.
DEFAULT_MAX = {'crackers': 22000, 'alyonka': 17500, 'sewing_kit': 38500, 'ux_pro_beanie': 3500,
               'power_cord': 62000, 'pile_of_meds': 16600}
DEFAULT_SOURCE_BY = {'ux_pro_beanie': 'traders'}  # anything not listed defaults to players

# Estimated net roubles one finished craft is worth: the output's flea value less its inputs' cost.
# A single figure per craft, not a live read, so 'Est. profit' below is (crafts collected) * this.
# ponytail: constants, since input prices and output values drift; update them when they have, or
# read them off the market if this ever needs to be exact. Fleece's is a placeholder until measured.
PROFIT_PER_CRAFT = {'slickers': 12152, 'fleece': 24321, 'wires': 47235, 'ai2': 3521}

GET_ITEMS_SETTLE = 5.0  # seconds after clicking GET ITEMS; collecting can hang for a beat

# The counters, in the order the GUI lists them. Same shape as sell_bot.STAT_LABELS.
STAT_LABELS = (('crafts', 'Crafts started'), ('profit', 'Est. profit'))
TINT_STAT = 'profit'  # the row that goes green: estimated profit is the working signal, like money

# One craft's config: the craft.Craft descriptor plus the per-ingredient ceilings and sources the
# GUI set, both keyed by ingredient name (craft.Ingredient.name).
CraftJob = namedtuple('CraftJob', 'craft max_prices sources')


class HideoutCraft:
    def __init__(self, jobs, stats=None):
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
        self.jobs = list(jobs)  # the crafts to cycle between, in order
        self.index = 0  # which job we are working right now
        self.stats = {key: 0 for key, _ in STAT_LABELS} if stats is None else stats
        self._stop = threading.Event()
        log(f'Tarkov window {self.hwnd} at {self.position} size {self.size}', 1)
        log(f'monitor {self.monitor.label} at {self.monitor.rect}, searching {self.region}', 1)
        for job in self.jobs:
            log(f'{job.craft.name}: ceilings {job.max_prices}, sources {job.sources}', 1)

    def _park(self, point):
        """Move the cursor right of a just-clicked button so it stops covering the next read.
        The click's own hover keeps a highlight/tooltip over the button that the state and
        find calls then misread; parking clears it. point is an (x, y) pair (sell.jitter's tuple)."""
        x, y = point
        pyautogui.moveTo(x + round(PARK_OFFSET * find.scale()), y)

    def _pause(self, seconds=0):
        """Wait, or drop out of the loop now if stop() was called. A copy of FleaSeller._pause;
        hoist all three modes' copies into a Runner when one of them needs to diverge."""
        if self._stop.wait(seconds):  # wait(0) is just a check, no sleep
            raise Stopped()

    def _ensure_on(self, job):
        """Get to this craft's station if we are not already looking at it."""
        if craft.station_active(job.craft, self.region):
            log(f'already on the {job.craft.station}', 1)
            return
        log(f'not on the {job.craft.station}, navigating there', 1)
        craft.get_to_station(job.craft, self.region)  # raises LookupError if it cannot get there

    def _swap(self):
        """Move to the next craft in the cycle and navigate to its station."""
        if len(self.jobs) < 2:
            return  # only one craft; nothing to swap to
        self.index = (self.index + 1) % len(self.jobs)
        job = self.jobs[self.index]
        log(f'swapping to the {job.craft.name} craft')
        craft.get_to_station(job.craft, self.region)  # raises if it cannot get there

    def start_craft(self, job):
        """Start this craft: click START, then confirm on the handover button.

        Two clicks, not one. START opens a handover dialog (it hands the ingredients over from the
        stash), and the craft only begins once that is confirmed. Returns the START point clicked,
        or None if there was no START button to click.
        """
        band = craft.find_craft(job.craft, self.region)
        if band is None:
            log(f'no {job.craft.name} craft on screen to start', 1)
            return None
        point = find.find_center(craft.START_TARGET, band)
        if point is None:
            log(f'no START button in the {job.craft.name} row', 1)
            return None
        point = sell.jitter(point)
        log(f'starting the {job.craft.name} craft, clicking START at {point}', 1)
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

    def collect_craft(self, job):
        """Collect a finished craft: click its GET ITEMS button. Returns the point, or None.

        The row has no timer in the done state, so the band comes from craft_row_band (which works
        in any state) rather than find_craft. Profit is booked here, not at Start: an estimate is
        only real once the craft is actually collected.
        """
        band = craft.craft_row_band(job.craft, self.region)
        if band is None:
            log(f'no {job.craft.name} craft on screen to collect', 1)
            return None
        point = find.find_center(craft.GET_ITEMS_TARGET, band)
        if point is None:
            log(f'no GET ITEMS button in the {job.craft.name} row', 1)
            return None
        point = sell.jitter(point)
        log(f'collecting the {job.craft.name} craft, clicking GET ITEMS at {point}', 1)
        pyautogui.click(*point)
        time.sleep(GET_ITEMS_SETTLE)  # collecting sometimes hangs; wait it out before moving on
        self._park(point)
        self.stats['profit'] += PROFIT_PER_CRAFT.get(job.craft.name, 0)
        return point

    def buy_input(self, job, item, location):
        """Buy one missing ingredient off the flea at its ceiling, at a location already found on
        the craft row. True if it bought. No band read here: the caller read the whole row once."""
        ceiling = job.max_prices.get(item)
        if ceiling is None:
            log(f'no price ceiling set for {item}, skipping it this pass', 1)
            return False
        if location is None:
            log(f'could not find {item} on the craft row to buy it', 1)
            return False
        source = job.sources.get(item, 'players')
        log(f'buying {item} at up to {ceiling} from {source}', 1)
        return craft.buy_craft_input_item(location, ceiling, self.region, source=source,
                                          craft=job.craft)

    def step(self):
        """One pass of the state machine over the craft currently in front of us."""
        job = self.jobs[self.index]
        self._ensure_on(job)
        state = craft.get_craft_state(job.craft, self.region)

        if state == 'producing':  # nothing to do here; go straight to tending the other craft
            log(f'{job.craft.name} is producing, swapping to the next craft')
            self._pause()  # a Stop lands here; no wait, the swap's own navigation paces the loop
            self._swap()
            return
        if state == 'done':
            self.collect_craft(job)
            self._pause(COLLECT_SETTLE)  # let the row flip back to ready before the next look
            return
        if state == 'not started':  # greyed GET ITEMS: this loop cannot start it, move on
            log(f'{job.craft.name} is not started, swapping to the next craft')
            self._swap()
            return

        # Read the whole row once into a to-buy queue (name + where it sits), buy the queue in a
        # row, then read the row again to confirm it is ready before starting. One band read for
        # the plan, not one per ingredient.
        plan = craft.craft_plan(job.craft, self.region)
        queue = [(name, location) for name, ready, location in plan if not ready]
        if not queue:
            self.start_craft(job)
            self._pause(START_SETTLE)  # give the click time to flip the row to producing
            return

        log(f'{job.craft.name} missing {[name for name, _ in queue]}, buying each')
        for name, location in queue:
            self._pause()  # a Stop between buys lands here
            try:
                self.buy_input(job, name, location)
            except craft.PriceTooHigh as e:
                # Too dear right now. buy_input already backed out to the station; leave the rest
                # of the queue and go tend the other craft rather than overpaying or waiting.
                log(f'{name} {e}, swapping to the next craft', 1)
                self._swap()
                return
            except LookupError as e:
                # The game would not open a context menu on that slot, so this input cannot be
                # bought this pass. Same shape as too dear: nothing was opened, the station is
                # still up, and the other crafts are unaffected. Swapping costs a pass; raising
                # here used to cost the whole run.
                log(f'{name}: {e}, swapping to the next craft', 1)
                self._swap()
                return

        ready, still_missing = craft.validate_craftable(job.craft, self.region)
        if ready:
            self.start_craft(job)
            self._pause(START_SETTLE)
        else:
            log(f'{job.craft.name} still missing {still_missing} after buying, will retry', 1)

    def start(self):
        """Navigate to the first craft's station, then run the craft cycle until stop(). Blocks."""
        log('Starting Hideout Craft')
        self._stop.clear()
        started = time.perf_counter()
        # Craft mode leans hardest on detection (tab, station carousel, panel headers, ingredient
        # marks), and it is the mode whose misses we are still chasing, so narrate every match and,
        # on a miss, how close it came. Scoped to this run and restored after, so the flea loop that
        # would drown in it is untouched. See find.VERBOSE and find.best_score.
        was_verbose = find.VERBOSE
        find.VERBOSE = True
        try:
            self._ensure_on(self.jobs[self.index])
            while not self._stop.is_set():
                self.step()
        except Stopped:
            log('stopped between steps')
        finally:
            find.VERBOSE = was_verbose
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


def _source(label, default='players'):
    """A SOURCE label ('Players'/'Traders') as the 'players'/'traders' apply_flea_filters wants,
    falling back to default for anything an edited settings file might hold."""
    source = str(label).lower()
    return source if source in ('players', 'traders') else default


def build(prefs, stats):
    """A HideoutCraft configured from the GUI's saved preferences.

    One CraftJob per craft in craft.CRAFTS. Each ingredient stores <name>_max (a typed rouble
    string) and <name>_source (a SOURCES label) in prefs; parse them into the {name: value} dicts
    the runner buys against, keyed by the ingredient names validate_craftable returns.
    """
    screen.use(prefs.get('monitor', screen.AUTO))  # before the runner, which clips to it
    jobs = []
    for craft_desc in craft.CRAFTS.values():
        if not prefs.get(f'{craft_desc.name}_enabled', True):  # only run the crafts ticked in the GUI
            continue
        max_prices, sources = {}, {}
        for ing in craft_desc.ingredients:
            max_prices[ing.name] = _ceiling(prefs.get(f'{ing.name}_max'), DEFAULT_MAX[ing.name])
            sources[ing.name] = _source(prefs.get(f'{ing.name}_source'),
                                        DEFAULT_SOURCE_BY.get(ing.name, 'players'))
        jobs.append(CraftJob(craft_desc, max_prices, sources))
    if not jobs:
        raise ValueError('No crafts are enabled. Tick at least one craft to run.')
    return HideoutCraft(jobs, stats=stats)
