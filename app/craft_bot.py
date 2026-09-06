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
HANDOVER_APPEAR_TIMEOUT = 10.0  # poll up to this long after START for the handover dialog to draw. It
                                # stages the stash items it hands over, so it can be slow; a single
                                # look a fixed beat after START used to miss a slow one and end the
                                # run (a false Blind that also wedged the dialog over the next
                                # navigation, see _craft_mode_run_debugging). See _confirm_handover.
HANDOVER_OPTIONAL_WAIT = 1.5  # required=False (scav case): a brief look only, no handover expected there
HANDOVER_POLL = 0.5  # seconds between looks while waiting for the handover dialog to appear
MAX_HANDOVER_LOOPS = 3  # re-clicks of a handover button that will not go away, see _confirm_handover
HANDOVER_SETTLE = 2.0  # seconds between a handover click and the look that checks it landed
RECEIVE_TARGET = 'hideout/recieve_items_button'  # the scav case's LOOT FROM SCAVS reveal confirm button
RECEIVE_APPEAR_TIMEOUT = 10.0  # poll up to this long after GET ITEMS for the scav case RECEIVE button
RECEIVE_POLL = 0.5  # seconds between looks while waiting for the RECEIVE button to appear
COLLECT_SETTLE = 2.0  # seconds after collecting for the row to flip back to ready
PARK_OFFSET = 100  # 1080p px to shove the cursor right after a click, so it stops covering the row

# The GUI's per-ingredient SOURCE picker. 'Players' or 'Traders' as shown; build() lowercases them
# into what sell.apply_flea_filters expects.
SOURCES = ('Players', 'Traders')
DEFAULT_SOURCE = 'Players'

# Per-ingredient defaults, used when the GUI has no saved value (or a junk one). The max is the most
# roubles to pay on the flea; the source is who to buy from. These match settings.DEFAULTS.
DEFAULT_MAX = {'crackers': 22000, 'alyonka': 24000, 'sewing_kit': 38500, 'ux_pro_beanie': 3500,
               'power_cord': 62000, 'pile_of_meds': 16600, 'purified_water': 140000,
               'sugar': 48900, 'sling_bag': 11000, 'green_gunpowder': 50000, 'matches': 20000,
               'water_filter': 70000, 'moonshine': 230000}
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

        if not self._confirm_handover():
            log(f'START clicked but the {job.craft.name} handover was never confirmed, '
                f'so nothing was started', 1)
            self._park(point)
            return None
        self.stats[f'started:{job.craft.name}'] += 1
        self.stats['total_started'] += 1
        return point

    def _confirm_handover(self, required=True):
        """Wait for the handover dialog, then click its confirm until it is gone. True once it is
        (or it never appeared and was optional), False if it appeared but would not clear.

        START does not start anything on its own: it opens a dialog that hands the ingredients
        over from the stash, and the craft only runs once that is confirmed. That dialog stages
        the stash items it will hand over, so it can take a moment to draw; a single look a fixed
        beat after START used to miss a slow one and end the run (a false Blind that also left the
        dialog wedged over the next navigation, see _craft_mode_run_debugging). So poll for it to
        appear up to HANDOVER_APPEAR_TIMEOUT, acting the instant it shows.

        Once it is up, the dialog going away is the success test, not the click going out: look,
        click, wait HANDOVER_SETTLE, look again, up to MAX_HANDOVER_LOOPS re-clicks. The cursor is
        parked off the button between looks, because the click's own hover highlight changes the
        very pixels the next look matches against. Returning False rather than raising keeps a
        won't-clear dialog to a lost pass: the row is still ready, so the next lap tries again.

        No dialog within the window is Blind when required=True. START was clicked, so the dialog
        is what comes next; never seeing one means the click did not land on the button we had just
        matched, or the dialog's crops do not match what the game drew. required=False turns that
        off: the scav case may raise no handover at all, so a brief look (HANDOVER_OPTIONAL_WAIT)
        that finds nothing just means 'nothing to confirm here' and returns True. Its caller judges
        the start by re-reading the row rather than by the dialog.
        """
        deadline = time.monotonic() + (HANDOVER_APPEAR_TIMEOUT if required else HANDOVER_OPTIONAL_WAIT)
        while True:
            point = find.find_center(HANDOVER_TARGET, self.region)
            if point is not None:
                break
            if time.monotonic() >= deadline:
                if required:
                    raise craft.Blind(
                        f'no handover dialog appeared within {HANDOVER_APPEAR_TIMEOUT:.0f}s of '
                        'clicking START, so there is no way to tell whether the craft began')
                return True  # optional: nothing came up, nothing to confirm
            time.sleep(HANDOVER_POLL)

        loops = 0
        while point is not None:
            if loops > MAX_HANDOVER_LOOPS:
                log(f'the handover button is still on screen after {loops} clicks', 1)
                return False
            clicked = sell.jitter(point)
            log(f'confirming the handover at {clicked} (click {loops + 1})', 1)
            pyautogui.click(*clicked)
            self._park(clicked)
            loops += 1
            time.sleep(HANDOVER_SETTLE)
            point = find.find_center(HANDOVER_TARGET, self.region)
        return True

    def _confirm_receive(self):
        """Confirm the scav case's LOOT FROM SCAVS reveal, which GET ITEMS opens for a scav case.

        A scav case collect is two steps, unlike every other craft: GET ITEMS opens a 'LOOT FROM
        SCAVS' reveal listing what the scavs brought, and the loot only lands in the stash once its
        RECEIVE button is clicked. The list takes a moment to populate, so poll up to
        RECEIVE_APPEAR_TIMEOUT for the button, then click its centre and break. Blind if it never
        appears: the loot is then stuck behind a modal that dims everything and wedges the next
        navigation (see _craft_mode_run_debugging), so guessing is worse than stopping.
        """
        deadline = time.monotonic() + RECEIVE_APPEAR_TIMEOUT
        while True:
            point = find.find_center(RECEIVE_TARGET, self.region)
            if point is not None:
                clicked = sell.jitter(point)
                log(f'scav case loot reveal is up; clicking RECEIVE at {clicked}', 1)
                pyautogui.click(*clicked)
                self._park(clicked)
                return
            if time.monotonic() >= deadline:
                raise craft.Blind(
                    f'the scav case RECEIVE button never appeared within {RECEIVE_APPEAR_TIMEOUT:.0f}s '
                    'of GET ITEMS, so the loot reveal is stuck open')
            time.sleep(RECEIVE_POLL)

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
        # Collected output has to land in the stash; a full one makes Tarkov refuse it with the
        # stash-full dialog. Nothing a craft run can do about that, so stop rather than book profit
        # for items that never arrived.
        craft.check_stash_full(self.region)
        _book_profit(self.stats, job.craft.name)
        return point

    def buy_input(self, job, item, location, band):
        """Buy a missing ingredient off the flea at its ceiling, at a location already found on the
        craft row. Buys as many as the row's have/need fraction says are still short (see
        craft.quantity_to_buy), all in one flea trip. True if it bought them all. The only read
        here beyond the caller's is that fraction, off the still-open panel before the flea opens."""
        # build() refuses to construct a job with a ceiling missing, so this cannot be absent
        # once a run is going: a KeyError here would mean the job was built by hand.
        ceiling = job.max_prices[item]
        if location is None:
            # read_craft raises before it can hand one of these over, so this is a guard rather
            # than a path anything takes. It stays because the alternative is a right click at
            # None.
            raise craft.Blind(f'no place to click for {item} on the {job.craft.name} row')
        source = job.sources.get(item, 'players')
        quantity = craft.quantity_to_buy(location, band, self.region)
        log(f'buying {quantity} {item} at up to {ceiling} from {source}', 1)
        # _pause is the checkpoint: it waits interruptibly and raises Stopped the instant Stop was
        # pressed, so a Stop lands mid-buy (before/after the filters, between purchase attempts)
        # rather than waiting out the whole ~20s flea trip.
        return craft.buy_craft_input_item(location, ceiling, self.region, source=source,
                                          craft=job.craft, checkpoint=self._pause, quantity=quantity)

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
            craft.check_stash_full(self.region)  # collected water has to fit; stop if it cannot
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
            if not craft.buy_water_filter(ceiling, self.region, source=source, craft=job.craft,
                                          checkpoint=self._pause):
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

    def tend_scav_case(self, job):
        """The scav case's pass: tend the moonshine roll, then the 95k roll, then leave.

        Both rolls live on the one panel and neither fits the normal ready/producing state
        machine, for the same reason: every reward variant outputs the same '?' box, so a row is
        named only by its input item and carries no per-input tick. The panel opens scrolled to
        the moonshine roll at the top, so that one is tended first off the visible row; the 95k
        roll sits below it and is scrolled to (see _tend_scav_case_95k). Both are done before the
        single swap away, so one visit works both rolls rather than one roll per visit.
        """
        self._tend_scav_case_moonshine(job)
        self._tend_scav_case_95k(job)
        self._swap()  # leave the scav case; both rolls have been tended

    def _tend_scav_case_moonshine(self, job):
        """Tend the moonshine roll on the visible (top) scav case row. Does not swap.

        The row is named only by its input, so read_craft anchors on the moonshine bottle rather
        than an output (see craft.SCAV_CASE), and there is no per-input tick, so 'ready' cannot be
        split into have-the-input and need-to-buy the way read_craft does for other crafts: the
        bottle is always drawn on the row, ticked or not. So readiness is judged after the fact:

          producing -> nothing to do, leave it running
          done      -> collect
          ready     -> click START, read the row back. Producing now means it started (count it).
                       Still ready means the click did nothing, which for a scav case means the
                       moonshine bottle was not in the stash, so buy one and let the next lap start.

        START may or may not raise a handover dialog. The other crafts always get one and treat a
        missing one as Blind; this one was never confirmed to, so _confirm_handover(required=False)
        clears one if it shows and shrugs if it does not. The start is judged by the row read, not
        by the dialog.

        ponytail: the re-read is the only 'did it start' signal there is, since the row carries no
        tick. Its blind spot is a START that opens an insert dialog even when the bottle IS in the
        stash: that dialog shows the moonshine, so the re-read could match the bottle in the dialog
        and read 'producing' falsely. Not seen in practice (the handover is believed not to appear
        at all), and the fix if it ever does is a crop of the 'Collecting' state or the insert
        dialog to disambiguate, rather than trusting the bottle match alone.
        """
        read = craft.read_craft(job.craft, self.region)

        if read.state == 'producing':  # running; leave it, move on to the 95k roll
            log('scav case moonshine roll is producing')
            self._pause()
            return
        if read.state == 'done':
            # A scav case collect is two steps, not one: GET ITEMS opens a LOOT FROM SCAVS reveal
            # that only deposits the loot once its RECEIVE is clicked (collect_craft's single GET
            # ITEMS is enough for every other craft but not here). Click GET ITEMS, then confirm
            # the reveal, or the modal is left wedging the next navigation.
            point = sell.jitter(pyautogui.center(read.get_items))
            log(f'collecting the scav case moonshine roll, clicking GET ITEMS at {point}', 1)
            pyautogui.click(*point)
            self._park(point)
            self._confirm_receive()
            self._pause(COLLECT_SETTLE)
            return
        if read.state == 'not started':  # a greyed GET ITEMS; nothing this loop can do
            log('scav case moonshine roll is not started')
            return

        # ready: START is on the row. Click it, let any handover confirm, then read the row back.
        point = sell.jitter(pyautogui.center(read.start))
        log(f'starting the scav case moonshine craft, clicking START at {point}', 1)
        pyautogui.click(*point)
        self._confirm_handover(required=False)  # confirm one if it shows; fine if it does not
        self._park(point)
        self._pause(START_SETTLE)  # give the click time to flip the row to producing

        if craft.read_craft(job.craft, self.region).state == 'producing':
            log('scav case moonshine roll started')
            self.stats['started:scav_case'] += 1
            self.stats['total_started'] += 1
            return

        # Still ready: the START did nothing, so the moonshine bottle is not in the stash. Buy one
        # (the row's sole input) at its ceiling and let the next lap start the craft. location is
        # the bottle on the row, from read.inputs; quantity 1, since a scav case takes one.
        name, _, location = read.inputs[0]
        ceiling = job.max_prices[name]  # build() guarantees it
        source = job.sources.get(name, 'players')
        log(f'scav case did not start, so the {name} input is missing; buying one at up to '
            f'{ceiling} from {source}')
        try:
            craft.buy_craft_input_item(location, ceiling, self.region, source=source,
                                       craft=job.craft, checkpoint=self._pause, quantity=1)
        except craft.Unbuyable as e:
            log(f'{name} {e}, moving on', 1)
        except LookupError as e:
            log(f'{name}: {e}, moving on', 1)

    def _tend_scav_case_95k(self, job):
        """Tend the 95,000-rouble scav case roll, scrolled to below the moonshine roll. No swap.

        Same shape as the moonshine roll (no timer tick, state read off the row's buttons), read
        through craft.read_scav_case_95k, which scrolls down to the roll and reads its buttons off
        the 95k exception band. The one difference is the missing-input path: the roll's input is a
        stack of roubles, which cannot be bought off the flea, so a START that does not take means
        the stash is short of roubles (the user's to top up), not an ingredient to go and buy.
        """
        read = craft.read_scav_case_95k(self.region)
        if read is None:
            log('the 95k scav case roll never scrolled into view, skipping it', 1)
            return
        if read.state == 'producing':
            log('the 95k scav case roll is producing')
            return
        if read.state == 'done':
            point = sell.jitter(pyautogui.center(read.get_items))
            log(f'collecting the 95k scav case roll, clicking GET ITEMS at {point}', 1)
            pyautogui.click(*point)
            self._park(point)
            self._confirm_receive()
            self._pause(COLLECT_SETTLE)
            return
        if read.state == 'not started':
            log('the 95k scav case roll is not started')
            return

        # ready: click START, confirm any handover, read the row back to judge if it took.
        point = sell.jitter(pyautogui.center(read.start))
        log(f'starting the 95k scav case roll, clicking START at {point}', 1)
        pyautogui.click(*point)
        self._confirm_handover(required=False)
        self._park(point)
        self._pause(START_SETTLE)

        again = craft.read_scav_case_95k(self.region)
        if again and again.state == 'producing':
            log('the 95k scav case roll started')
            self.stats['started:scav_case'] += 1
            self.stats['total_started'] += 1
        else:
            log('the 95k scav case roll did not start, so the stash is short of roubles; '
                'moving on', 1)

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
        if job.craft.name == craft.SCAV_CASE_NAME:  # anchored on its input, no tick: its own pass
            self.tend_scav_case(job)
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
                self.buy_input(job, name, location, read.band)
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
        except craft.StashFull as e:
            # A run-ender the runner can name: no craft can buy inputs or collect output into a
            # full stash, so there is nothing to swap to. Clear the dialog off the game and stop
            # cleanly rather than crash. The user has to empty the stash before a run is any use.
            craft.dismiss_stash_full(self.region)
            log(f'{e}; stopping the run, empty the stash and start again')
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
