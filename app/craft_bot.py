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
MAX_HANDOVER_LOOPS = 3  # re-clicks of a handover button that will not go away, see _confirm_handover
HANDOVER_SETTLE = 2.0  # seconds between a handover click and the look that checks it landed
COLLECT_SETTLE = 2.0  # seconds after collecting for the row to flip back to ready
PARK_OFFSET = 100  # 1080p px to shove the cursor right after a click, so it stops covering the row

# The GUI's per-ingredient SOURCE picker. 'Players' or 'Traders' as shown; build() lowercases them
# into what sell.apply_flea_filters expects.
SOURCES = ('Players', 'Traders')
DEFAULT_SOURCE = 'Players'

# Per-ingredient defaults, used when the GUI has no saved value (or a junk one). The max is the most
# roubles to pay on the flea; the source is who to buy from. These match settings.DEFAULTS.
DEFAULT_MAX = {'crackers': 22000, 'alyonka': 22500, 'sewing_kit': 38500, 'ux_pro_beanie': 3500,
               'power_cord': 62000, 'pile_of_meds': 16600, 'purified_water': 140000,
               'sugar': 48900, 'sling_bag': 11000, 'green_gunpowder': 50000, 'matches': 20000,
               'water_filter': 70000}
# anything not listed defaults to players
DEFAULT_SOURCE_BY = {'ux_pro_beanie': 'traders', 'sling_bag': 'traders'}

# Estimated net roubles one finished craft is worth: the output's flea value less its inputs' cost.
# A single figure per craft, not a live read, so 'Est. profit' below is (crafts collected) * this.
# ponytail: constants, since input prices and output values drift; update them when they have, or
# read them off the market if this ever needs to be exact. Fleece's is a placeholder until measured.
PROFIT_PER_CRAFT = {'slickers': 12152, 'fleece': 24321, 'wires': 47235, 'ai2': 3521,
                    'moonshine': 32111, 'cordura': 27984, 'red_gunpowder': 40250}
# The water collector has no figure here on purpose: nothing was measured for it, and a
# guess would inflate 'Est. profit' rather than leave a gap. Collecting it books 0 until
# one is. Same as any craft the dict does not list, see collect_craft.

GET_ITEMS_SETTLE = 5.0  # seconds after clicking GET ITEMS; collecting can hang for a beat

# The crafts the GUI draws a STARTED and a PROFIT column against, in craft.CRAFTS' order so the
# stat keys and the GUI's rows name the same crafts.
CRAFT_NAMES = tuple(craft.CRAFTS)
# The counters. Two per craft (started, profit), plus the totals they foot into. Same flat
# {key: int} shape the other modes use, so the GUI's tick() fills every one of these by key with
# no crafts-specific code: 'started:<name>' rises on Start, 'profit:<name>' on collect, and the
# GUI reads them by the same craft names it draws rows for. TINT is the profit total, the working
# signal like the sell mode's money.
STAT_LABELS = (('total_started', 'Total started'), ('total_profit', 'Total profit'),
               *((f'started:{name}', name) for name in CRAFT_NAMES),
               *((f'profit:{name}', name) for name in CRAFT_NAMES))
TINT_STAT = 'total_profit'


def _book_profit(stats, name):
    """Add craft `name`'s estimated profit to its own counter and the total. Unlisted crafts
    (the water collector) book 0, same as they always did."""
    profit = PROFIT_PER_CRAFT.get(name, 0)
    stats[f'profit:{name}'] += profit
    stats['total_profit'] += profit

# One craft's config: the craft.Craft descriptor plus the per-ingredient ceilings and sources the
# GUI set, both keyed by ingredient name (craft.Ingredient.name).
CraftJob = namedtuple('CraftJob', 'craft max_prices sources')


class HideoutCraft:
    def __init__(self, jobs, stats=None, one_pass=False):
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
        self.one_pass = one_pass  # stop after every station has been visited once, see _swap
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
        """Move to the next craft in the cycle, navigating only if it is at another station.

        The jobs are grouped by station (see build), so the next craft is usually another one at
        the station already on screen, and navigating to a station we are stood in front of is
        worse than pointless: its tab is the selected one, so clicking it navigates back out.
        _ensure_on does the check, and the two lavatory crafts and the two workbench crafts get
        tended without a trip through the carousel between them.
        """
        if len(self.jobs) < 2:
            if self.one_pass:  # the sole craft is done; one pass is over
                log('one-pass: the only craft has been tended, stopping')
                raise Stopped()
            return  # only one craft; nothing to swap to
        next_index = (self.index + 1) % len(self.jobs)
        if self.one_pass and next_index == 0:  # about to wrap to the first station: pass complete
            log('one-pass: every station has been visited once, stopping')
            raise Stopped()
        self.index = next_index
        job = self.jobs[self.index]
        log(f'swapping to the {job.craft.name} craft')
        self._ensure_on(job)  # raises if it cannot get there

    def start_craft(self, job, read):
        """Start this craft: click the START the read already found, then confirm the handover.

        Two clicks, not one. START opens a handover dialog (it hands the ingredients over from
        the stash), and the craft only begins once that is confirmed. Returns the START point.

        `read` is this pass's CraftRead and the button comes out of it rather than being searched
        for again. It was matched moments ago and nothing has been clicked since, so the second
        search could only ever agree, while costing a find_all of the timer icon plus one of the
        output item. When it disagreed, which a flaky match does, the pass logged 'no START
        button in the row' and quietly did nothing, and the next lap did the same.
        """
        point = sell.jitter(pyautogui.center(read.start))
        log(f'starting the {job.craft.name} craft, clicking START at {point}', 1)
        pyautogui.click(*point)

        time.sleep(HANDOVER_DELAY)
        if not self._confirm_handover():
            log(f'START clicked but the {job.craft.name} handover was never confirmed, '
                f'so nothing was started', 1)
            self._park(point)
            return None
        self.stats[f'started:{job.craft.name}'] += 1
        self.stats['total_started'] += 1
        return point

    def _confirm_handover(self):
        """Click the handover dialog's confirm until it is gone. True once it is, False if it stays.

        START does not start anything on its own: it opens a dialog that hands the ingredients
        over from the stash, and the craft only runs once that is confirmed. A single click that
        misses leaves the craft un-started with nothing in the log to say so, which is how the
        wires craft bought a power cord and then sat there on 2026-08-30.

        So the dialog going away is the success test, not the click going out. Look, click, wait
        HANDOVER_SETTLE, look again, up to MAX_HANDOVER_LOOPS re-clicks. The cursor is parked off
        the button between looks, because the click's own hover highlight changes the very pixels
        the next look matches against.

    worse than saying so. Returning False rather than raising keeps that to a lost pass: the
        row is still ready, so the next lap tries again.

        No dialog at all is different, and is Blind. START was clicked, so the dialog is what
        comes next; never seeing one means the click did not land on the button we had just
        matched, or the dialog's crops do not match what the game drew. Either way the craft may
        or may not have begun, and the next pass's row read cannot tell those apart.
        """
        loops = 0
        while True:
            point = find.find_center(HANDOVER_TARGET, self.region)
            if point is None:
                if loops == 0:
                    raise craft.Blind(
                        'no handover dialog appeared after clicking START, so there is no way '
                        'to tell whether the craft began')
                return True
            if loops > MAX_HANDOVER_LOOPS:
                log(f'the handover button is still on screen after {loops} clicks', 1)
                return False
            point = sell.jitter(point)
            log(f'confirming the handover at {point} (click {loops + 1})', 1)
            pyautogui.click(*point)
            self._park(point)
            loops += 1
            time.sleep(HANDOVER_SETTLE)

    def collect_craft(self, job, read):
        """Collect a finished craft: click the GET ITEMS the read already found.

        Profit is booked here, not at Start: an estimate is only real once the craft is actually
        collected. The button comes out of `read` for the reason start_craft gives, and this one
        cost two searches rather than one, since craft_row_band went looking for the output all
        over again to frame a row the read had already framed.
        """
        point = sell.jitter(pyautogui.center(read.get_items))
        log(f'collecting the {job.craft.name} craft, clicking GET ITEMS at {point}', 1)
        pyautogui.click(*point)
        time.sleep(GET_ITEMS_SETTLE)  # collecting sometimes hangs; wait it out before moving on
        self._park(point)
        _book_profit(self.stats, job.craft.name)
        return point

    def buy_input(self, job, item, location):
        """Buy one missing ingredient off the flea at its ceiling, at a location already found on
        the craft row. True if it bought. No band read here: the caller read the whole row once."""
        # build() refuses to construct a job with a ceiling missing, so this cannot be absent
        # once a run is going: a KeyError here would mean the job was built by hand.
        ceiling = job.max_prices[item]
        if location is None:
            # read_craft raises before it can hand one of these over, so this is a guard rather
            # than a path anything takes. It stays because the alternative is a right click at
            # None.
            raise craft.Blind(f'no place to click for {item} on the {job.craft.name} row')
        source = job.sources.get(item, 'players')
        log(f'buying {item} at up to {ceiling} from {source}', 1)
        return craft.buy_craft_input_item(location, ceiling, self.region, source=source,
                                          craft=job.craft)

    def tend_water_collector(self, job):
        """The water collector's pass, which is not the state machine the other crafts use.

        There is no START here and no row of ingredients to fill: the station runs the moment a
        water filter is in its slot, so the whole job is collecting what is finished and keeping
        a filter in that slot.

          1. collect a lit GET ITEMS if there is one
          2. slot reads 'fitted'  -> it is producing, done
          3a. slot reads 'empty'  -> open the dropdown; if it lists any, fit one and check the
              slot reads 'fitted'
          3b. the dropdown lists none -> buy one off the flea, come back, open the dropdown
              again, fit one and check the slot reads 'fitted'

        The check at the end of 3a and 3b is the point of the rewrite. Fitting used to be judged
        on the click going out, with confirmation left to the next pass, so a click that missed
        read as a producing collector for a whole lap.

        A greyed GET ITEMS is left alone, the same rule read_craft uses: greyed means nothing has
        finished, and clicking it would book profit for a collection that did not happen.
        """
        box = find.find(craft.GET_ITEMS_TARGET, self.region)
        if box is not None and craft.get_items_highlighted(box):
            point = sell.jitter(pyautogui.center(box))
            log(f'collecting the water collector, clicking GET ITEMS at {point}', 1)
            pyautogui.click(*point)
            self._pause(GET_ITEMS_SETTLE)
            self._park(point)
            _book_profit(self.stats, job.craft.name)

        if craft.water_filter_state(self.region) == 'fitted':
            log('a water filter is in the collector, leaving it to produce', 1)
            self._swap()
            return

        listed = craft.open_filter_dropdown(self.region)
        if not listed:
            # 3b. Nothing in the stash to fit, so go and buy one, then come back and fit it in
            # this same pass rather than leaving the collector idle for a lap.
            ceiling = job.max_prices['water_filter']  # build() guarantees it
            source = job.sources.get('water_filter', 'players')
            log(f'no water filter in the stash, buying one at up to {ceiling} from {source}')
            if not craft.buy_water_filter(ceiling, self.region, source=source, craft=job.craft):
                log('no water filter bought this pass, leaving the collector empty', 1)
                self._swap()
                return
            listed = craft.open_filter_dropdown(self.region)
            if not listed:
                log('bought a water filter but the dropdown still lists none', 1)
                self._swap()
                return

        # 3a, and the tail of 3b: fit one and check the slot took it.
        if craft.fit_water_filter(listed, self.region):
            log('water filter fitted, the collector is producing')
            self._pause(START_SETTLE)
        self._swap()

    def step(self):
        """One pass of the state machine over the craft currently in front of us.

        One read of the row per pass, and everything after it acts on the boxes that read
        found. It used to search the same row four times: once for the state, twice inside
        craft_plan, and the whole of craft_plan again through validate_craftable after buying.
        On a 1440p screen that was 4.4 of a 7.1 second lap spent re-answering a settled
        question, since nothing is clicked between those looks.

        There is no re-read after buying either. The queue is bought and the pass ends; the next
        pass reads the row once and starts the craft if it is ready. That costs one lap of
        latency and removes a whole duplicate read, and the check it replaced was the thing
        printing 'still missing X after buying, will retry' once every seven seconds.
        """
        job = self.jobs[self.index]
        self._ensure_on(job)
        if job.craft.name == craft.WATER_COLLECTOR_NAME:  # no START, no ingredient row: its own pass
            self.tend_water_collector(job)
            return

        read = craft.read_craft(job.craft, self.region)

        if read.state == 'producing':  # nothing to do here; go tend another craft
            log(f'{job.craft.name} is producing, swapping to the next craft')
            self._pause()  # a Stop lands here; no wait, the swap's own navigation paces the loop
            self._swap()
            return
        if read.state == 'done':
            self.collect_craft(job, read)
            self._pause(COLLECT_SETTLE)  # let the row flip back to ready before the next look
            return
        if read.state == 'not started':  # greyed GET ITEMS: this loop cannot start it, move on
            log(f'{job.craft.name} is not started, swapping to the next craft')
            self._swap()
            return

        queue = [(name, location) for name, ready, location in read.inputs if not ready]
        if not queue:
            self.start_craft(job, read)
            self._pause(START_SETTLE)  # give the click time to flip the row to producing
            return

        log(f'{job.craft.name} missing {[name for name, _ in queue]}, buying each')
        for name, location in queue:
            self._pause()  # a Stop between buys lands here
            try:
                self.buy_input(job, name, location)
            except craft.Unbuyable as e:
                # Not worth staying on the flea for: too dear, locked behind a spent trader
                # limit, or outbid every try. buy_input already backed out to the station; leave
                # the rest of the queue and go tend another craft rather than overpaying or
                # waiting. e says which of the three it was, so a log reads back unambiguously.
                log(f'{name} {e}, swapping to the next craft', 1)
                self._swap()
                return
            except LookupError as e:
                # The game would not open a context menu on that slot, even after clearing an
                # Error dialog off it. Nothing was opened, the station is still up, and the
                # other crafts are unaffected, so this costs a pass rather than the run.
                #
                # craft.Blind is deliberately not caught here or anywhere else: it means a read
                # came back empty for something that is definitely drawn, which no amount of
                # swapping fixes. See craft.Blind.
                log(f'{name}: {e}, swapping to the next craft', 1)
                self._swap()
                return

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
                f"Crafts started {self.stats['total_started']}, "
                f"Est. profit {self.stats['total_profit']}")

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
    the runner buys against, keyed by the ingredient names read_craft returns.

    prefs['one_pass'] (set by the CLI's --one-pass, absent for a GUI run) makes the runner visit
    every station once and stop, rather than cycling forever. It rides in prefs so the GUI's and
    CLI's shared build(prefs, stats) call needs no craft-specific argument.
    """
    screen.use(prefs.get('monitor', screen.AUTO))  # before the runner, which clips to it
    jobs = []
    for craft_desc in craft.CRAFTS.values():
        if not prefs.get(f'{craft_desc.name}_enabled', True):  # only run the crafts ticked in the GUI
            continue
        max_prices, sources = {}, {}
        for ing in craft_desc.ingredients:
            if ing.name not in DEFAULT_MAX:
                # Here rather than mid-pass, because it is a hole in this file and not something
                # the screen did: a craft was added to interact.craft without a rouble ceiling,
                # and every pass that reaches its buying step would find None and skip the input
                # forever. Refusing to build says so once, before a run starts.
                raise ValueError(
                    f'{craft_desc.name} has an ingredient with no default ceiling: '
                    f'add {ing.name!r} to craft_bot.DEFAULT_MAX and '
                    f'{ing.name}_max to gui.settings.DEFAULTS')
            max_prices[ing.name] = _ceiling(prefs.get(f'{ing.name}_max'), DEFAULT_MAX[ing.name])
            sources[ing.name] = _source(prefs.get(f'{ing.name}_source'),
                                        DEFAULT_SOURCE_BY.get(ing.name, 'players'))
        jobs.append(CraftJob(craft_desc, max_prices, sources))
    # Group the cycle by station, so every craft at one station is tended before the carousel is
    # touched again: both lavatory crafts together, both workbench crafts together. Sorted by
    # where each station first appears rather than by name, so the cycle keeps craft.CRAFTS'
    # order and only the duplicates move. Navigation is the slowest and least reliable thing this
    # mode does, and ungrouped jobs paid for it twice a lap.
    order = {}
    for craft_desc in craft.CRAFTS.values():
        order.setdefault(craft_desc.station, len(order))
    jobs.sort(key=lambda job: order[job.craft.station])
    if not jobs:
        raise ValueError('No crafts are enabled. Tick at least one craft to run.')
    return HideoutCraft(jobs, stats=stats, one_pass=bool(prefs.get('one_pass', False)))
