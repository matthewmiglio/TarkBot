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
from game_client import tarkov  # for NeedsLogin, which must miss the restart tuple in start()
from interact import craft, find, sell
from narrate import log
from sell_bot import GameRestarts, Stopped, auto_restart_from  # shared runner plumbing, see _pause

START_SETTLE = 3.0  # seconds after START for the row to flip to producing before the next look
PANEL_LEAVE_SETTLE = 3.0  # seconds to let a station panel settle before navigating away from it.
                          # Navigation's first act is clicking that panel's close X, and this used
                          # to happen with no gap at all. See the 'producing' branch of step().
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
COLLECT_SETTLE = 3.0  # seconds after collecting for the row to flip back to ready. Was 2.0; raised
                      # 2026-09-17 because a GET ITEMS click makes the whole client lag, sometimes
                      # close to a freeze, and the next thing the loop does is read the row again.
                      # Note this is on top of GET_ITEMS_SETTLE, so a collect now has ~8s before
                      # anything reads that row, and the 12:54 Blind that prompted the change came
                      # off the failed-handover path (START_SETTLE, already 3.0s) rather than off a
                      # collect, so this hardens the lag but is not proven to be that fix.
SCAV_CASE_MAX_ROUNDS = 8  # read-and-act rounds over the scav case rolls in one visit. The longest
                          # honest path is five (collect, START, buy, START, read producing). Was
                          # six; on 2026-10-15 a collect that hid the other row cost two rounds and
                          # the visit ran out one read short of counting a folder's start, so two
                          # rounds of slack. Reaching eight means a roll that will not settle.
PARK_OFFSET = 100  # 1080p px to shove the cursor right after a click, so it stops covering the row

# The GUI's per-ingredient SOURCE picker. 'Players' or 'Traders' as shown; build() lowercases them
# into what sell.apply_flea_filters expects.
SOURCES = ('Players', 'Traders')
DEFAULT_SOURCE = 'Players'

# Per-ingredient defaults, used when the GUI has no saved value (or a junk one). The max is the most
# roubles to pay on the flea; the source is who to buy from. These match settings.DEFAULTS.
# Set 2026-10-07 off tarkov-market 24h averages by /scrape-craft-prices: each is the price at which
# its craft makes exactly 7%, a craft's inputs scaled together. Exactly, not under: a ceiling below
# the market never buys. Moonshine (0% today) and ai2 (-17%) have 7% ceilings under the market, so
# their inputs (sugar, purified water, pile of meds) buy only when prices fall that far.
# sewing_kit, ux_pro_beanie, sling_bag, water_filter, moonshine and intelligence are not priced
# by that skill.
# ponytail: constants, and they drift. Rerun /scrape-craft-prices to reprice them.
DEFAULT_MAX = {'crackers': 29700, 'alyonka': 38290, 'sewing_kit': 38500, 'ux_pro_beanie': 3500,
               'power_cord': 84291, 'pile_of_meds': 19208, 'purified_water': 73390,
               'sugar': 66941, 'sling_bag': 11000, 'green_gunpowder': 75400, 'matches': 31186,
               'water_filter': 70000, 'moonshine': 230000,
               'intelligence': 400000}
# anything not listed defaults to players
# crackers was 'traders' for part of 2026-09-17 and is back on players: a trader source caps volume
# at the restock limit, and the overnight soak hit that cap 5 times in 4.5 hours. See the ledger.
DEFAULT_SOURCE_BY = {'ux_pro_beanie': 'traders', 'sling_bag': 'traders'}

# Estimated net roubles one finished craft is worth: the output's flea value less its inputs' cost.
# A single figure per craft, not a live read, so 'Est. profit' below is (crafts collected) * this.
# ponytail: constants, since input prices and output values drift; update them when they have, or
# read them off the market if this ever needs to be exact. Fleece's is a placeholder until measured.
PROFIT_PER_CRAFT = {'slickers': 12152, 'fleece': 24321, 'wires': 47235, 'ai2': 3521,
                    'moonshine': 32111, 'cordura': 27984, 'red_gunpowder': 40250,
                    # Gross rather than net, and correctly so: the farm consumes nothing per
                    # collect, so one physical bitcoin's flea value is the whole of it.
                    'bitcoin': 532000}
# The water collector has no figure here on purpose: nothing was measured for it, and a
# guess would inflate 'Est. profit' rather than leave a gap. Collecting it books 0 until
# one is. Same as any craft the dict does not list, see collect_craft.

GET_ITEMS_SETTLE = 5.0  # seconds after clicking GET ITEMS; collecting can hang for a beat
GET_ITEMS_ATTEMPTS = 3  # clicks of a GET ITEMS that will not clear before giving the pass up. Same
                        # shape and same reason as MAX_HANDOVER_LOOPS above: on 2026-09-17 a red
                        # gunpowder collect was watched going out with the game frozen for a beat,
                        # the click landing nowhere, and the row left with its loot on it. See
                        # collect_craft.

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


class HideoutCraft(GameRestarts):
    def __init__(self, jobs, stats=None, one_pass=False, restart_as=None):
        log('Initalizing Hideout Craft')
        self.restart_as = restart_as  # a tarkov.Character to relaunch as, or None to never restart
        # The window clipped to the chosen monitor, or hwnd None for start() to boot the game when
        # it is shut and auto restart is on. See GameRestarts._measure_or_defer.
        self._measure_or_defer()
        self.jobs = list(jobs)  # the crafts to cycle between, in order
        self.index = 0  # which job we are working right now
        self.one_pass = one_pass  # stop after every station has been visited once, see _swap
        self.stats = {key: 0 for key, _ in STAT_LABELS} if stats is None else stats
        self._stop = threading.Event()
        log(f'auto restart {restart_as.name.lower() if restart_as else "off"}', 1)
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

    def _receive_point(self, timeout=RECEIVE_APPEAR_TIMEOUT):
        """Poll up to `timeout` for the scav case's LOOT FROM SCAVS reveal. Its centre, or None.

        Split out from the click because it has a second job: it is the proof that a scav case GET
        ITEMS click landed. On that panel the button cannot be the proof the way it is for every
        other craft, because clicking it opens a modal that covers the button rather than removing
        it, so 'the button is gone' reads true for a click that collected nothing. The reveal
        opening is the thing only a registered click produces.
        """
        deadline = time.monotonic() + timeout
        while True:
            point = find.find_center(RECEIVE_TARGET, self.region)
            if point is not None:
                return point
            if time.monotonic() >= deadline:
                return None
            time.sleep(RECEIVE_POLL)

    def _confirm_receive(self):
        """Confirm the scav case's LOOT FROM SCAVS reveal, which GET ITEMS opens for a scav case.

        A scav case collect is two steps, unlike every other craft: GET ITEMS opens a 'LOOT FROM
        SCAVS' reveal listing what the scavs brought, and the loot only lands in the stash once its
        RECEIVE button is clicked. The list takes a moment to populate, so _receive_point polls up
        to RECEIVE_APPEAR_TIMEOUT for the button, then this clicks its centre. Blind if it never
        appears: the loot is then stuck behind a modal that dims everything and wedges the next
        navigation (see _craft_mode_run_debugging), so guessing is worse than stopping.

        Callers that have already waited for the reveal as their proof that the GET ITEMS click
        landed find it up immediately, so the second look costs one match.
        """
        point = self._receive_point()
        if point is None:
            raise craft.Blind(
                f'the scav case RECEIVE button never appeared within {RECEIVE_APPEAR_TIMEOUT:.0f}s '
                'of GET ITEMS, so the loot reveal is stuck open')
        clicked = sell.jitter(point)
        log(f'scav case loot reveal is up; clicking RECEIVE at {clicked}', 1)
        pyautogui.click(*clicked)
        self._park(clicked)

    def _click_until_taken(self, what, box, landed, settle=GET_ITEMS_SETTLE):
        """Click `box` until `landed()` says the game took it. The point clicked, or None.

        The click going out is never the success test, because a click Tarkov ignores leaves the
        screen exactly as it was. Watched on 2026-09-17: a red gunpowder GET ITEMS click went
        nowhere with the game frozen for a beat, and the pass carried on as though it had
        collected, booking the profit for loot still sat on the row. Nothing downstream could have
        noticed, which is why the proof has to be taken here. Same shape and same reason as
        _confirm_handover, which learned this about START.

        Every attempt clicks, parks the cursor off the button, waits `settle`, then asks `landed`.
        The park is not cosmetic: the click's own hover highlight changes the very pixels the next
        look matches against, which is why every clicked button in this file is parked off before
        it is re-read. The point is re-jittered per attempt, so a click that missed by a hair is
        not repeated identically. Bounded at GET_ITEMS_ATTEMPTS.

        `landed` is the caller's proof, and the two callers need different ones:

          collect_craft              the button itself goes away (craft.get_items_cleared). A
                                     normal craft collects instantly, so a cleared button is the
                                     whole of the evidence.
          _collect_scav_case_roll    the LOOT FROM SCAVS reveal opens (_receive_point). A scav
                                     case click opens a modal that *covers* its button instead of
                                     removing it, so a cleared button would read true for a click
                                     that collected nothing.

        `settle` exists for that second caller: _receive_point polls for up to ten seconds by
        itself, so waiting the full GET_ITEMS_SETTLE first would only add dead time.
        """
        for attempt in range(1, GET_ITEMS_ATTEMPTS + 1):
            point = sell.jitter(pyautogui.center(box))
            log(f'clicking GET ITEMS for {what} at {point} '
                f'(attempt {attempt}/{GET_ITEMS_ATTEMPTS})', 1)
            pyautogui.click(*point)
            self._park(point)  # off the button before the look; its hover changes those pixels
            if settle:
                time.sleep(settle)  # collecting sometimes hangs; wait it out before looking
            if landed():
                return point
            log(f'the GET ITEMS click for {what} did not register', 2)
        log(f'GET ITEMS for {what} would not take after {GET_ITEMS_ATTEMPTS} clicks', 1)
        return None

    def collect_craft(self, job, read):
        """Collect a finished craft: click GET ITEMS until the button actually goes away.

        The clearing of the button is the proof, not the click going out; _click_until_taken holds
        the why and the loop. This is the instant kind of collect, the one every craft but the scav
        case has: no reveal, no second confirm, the loot simply lands.

        Profit is booked only once the button has cleared, and that is the substance of this rather
        than the retry: booking on the click counted loot that never arrived, and every total
        downstream inherited it. Still lit after the last attempt is a lost pass rather than a
        raise, exactly like the handover: the row is still 'done', so the next lap collects it.

        Profit is booked here and not at Start for the same reason: an estimate is only real once
        the craft is actually collected. The button comes out of `read` for the reason start_craft
        gives, and this one cost two searches rather than one, since craft_row_band went looking
        for the output all over again to frame a row the read had already framed.

        Returns the point clicked, or None when the button never cleared.
        """
        point = self._click_until_taken(
            f'the {job.craft.name} craft', read.get_items,
            lambda: craft.get_items_cleared(read.get_items, read.band))
        if point is None:
            log(f'nothing was collected for {job.craft.name} and no profit is booked; the row is '
                'still done, so the next lap will try again', 1)
            return None
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

    def _collect_if_lit(self, job):
        """Click the one GET ITEMS button on this station's panel if it is lit, and book the craft's
        profit if it was. True if something was collected.

        For the two stations that have no craft row to read: the water collector and the bitcoin
        farm. Both have a single production on the panel and no START, so the button's own
        brightness is the whole state read, which is why this does not go through read_craft or
        collect_craft's _click_until_taken proof.

        Nothing is clicked unless the button is both there and lit. The collector greys its button;
        the bitcoin farm removes it entirely and puts a timer back on the row (measured on
        2026-09-21, straight after a collect). Either way nothing has finished, and clicking would
        book profit for a collection that did not happen.
        """
        box = find.find(craft.GET_ITEMS_TARGET, self.region)
        if box is None or not craft.get_items_highlighted(box):
            return False
        point = sell.jitter(pyautogui.center(box))
        log(f'collecting the {job.craft.station}, clicking GET ITEMS at {point}', 1)
        pyautogui.click(*point)
        self._pause(GET_ITEMS_SETTLE)
        self._park(point)
        craft.check_stash_full(self.region)  # the loot has to fit the stash; stop if it cannot
        _book_profit(self.stats, job.craft.name)
        return True

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
        self._collect_if_lit(job)

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
        """The scav case's pass: scroll once, then read both rolls and act until both are running.

          1. wheel the list to the bottom once (craft.scroll_scav_case_list), which puts every roll
             the bot runs on screen together
          2. read each roll's row and do the one thing it needs (_tend_scav_case_roll): collect a
             finished roll, START a ready one, buy the input of one whose START did nothing
          3. repeat 2 until every roll is producing, or has nothing more this visit can do, and
             leave

        No reopening the panel, and no scrolling after the first wheel except straight after a buy
        or a collect: the trip to the flea and back resets the list to the top, and a collect's
        loot reveal shifts it, each of which on 2026-10-15 left a row off screen ("not on screen,
        skipping it this visit"). So _buy_scav_case_input and _collect_scav_case_roll each wheel
        again on their way back. Otherwise every round is plain reads. This replaced a per-roll hunt (look, scroll, look again,
        for each roll in turn) and a second collect-only sweep behind a panel reopen. That sweep
        existed because a running or finished roll was believed to stop drawing its input icon; on
        2026-10-13 a finished moonshine roll still showed its bottle and a running intelligence roll
        its folder, so the anchored read names a row in every state.

        Bounded by SCAV_CASE_MAX_ROUNDS: a roll that never reaches producing ends the visit rather
        than spinning on it. Every scav case job (craft.SCAV_CASE_NAMES) is tended in this one
        visit; build() keeps them adjacent, so the index jumps to the last of them before the swap.
        """
        rolls = [j for j in self.jobs if j.craft.name in craft.SCAV_CASE_NAMES]
        craft.scroll_scav_case_list(self.region)
        progress = {j.craft.name: {'starts': 0, 'bought': False, 'counted': False} for j in rolls}
        for _ in range(SCAV_CASE_MAX_ROUNDS):
            self._pause()
            # A list, not a generator: every roll gets its action this round, rather than all()
            # stopping at the first one that is still busy.
            if all([self._tend_scav_case_roll(j, progress[j.craft.name]) for j in rolls]):
                log('every scav case roll is running or has nothing more to do, leaving')
                break
        else:
            log(f'gave up on the scav case after {SCAV_CASE_MAX_ROUNDS} rounds; the next lap '
                'tries again', 1)
        self.index = max(self.jobs.index(r) for r in rolls)
        self._swap()

    def _tend_scav_case_roll(self, job, progress):
        """Read one scav case roll and do the one thing it needs. True when it needs nothing more
        this visit: producing, or stuck in a way only a later lap can fix.

        `progress` is this roll's own record across the rounds of one visit: START clicks made,
        whether its input was bought, whether its start has been counted.

        A ready row is not split into have-the-input and need-to-buy by its tick. On a 1080p panel
        wheeled to the bottom the lowest row's tick is cut off by the panel's edge, and reading a
        cut-off tick as 'missing' would buy a 400k folder that was already in the stash. So START
        is clicked first and the next round's read says whether it took: still ready means the
        input is not there, so buy one and START again. One buy per roll per visit, so a START that
        fails for some other reason cannot buy input after input.
        """
        name = job.craft.ingredients[0].name  # 'moonshine' / 'intelligence', for the log
        if not find.find(job.craft.output_target, self.region):
            log(f'the {name} scav case roll is not on screen, skipping it this visit', 1)
            return True
        read = craft.read_craft(job.craft, self.region)
        if read.state == 'producing':
            if progress['starts'] and not progress['counted']:
                progress['counted'] = True
                log(f'scav case {name} roll started')
                self.stats[f'started:{job.craft.name}'] += 1
                self.stats['total_started'] += 1
            return True
        if read.state == 'done':
            return not self._collect_scav_case_roll(name, job, read)
        if read.state != 'ready':  # 'not started', a greyed GET ITEMS: nothing a click can do
            log(f'scav case {name} roll is {read.state}, nothing to do', 1)
            return True
        if progress['starts'] == 0 or (progress['bought'] and progress['starts'] == 1):
            self._click_scav_start(name, read)
            progress['starts'] += 1
            return False
        if progress['bought']:
            log(f'the {name} roll still did not start after buying its input; the next lap tries '
                'again', 1)
            return True
        progress['bought'] = True
        return not self._buy_scav_case_input(job, read)

    def _collect_scav_case_roll(self, name, job, read):
        """Collect a finished roll through its LOOT FROM SCAVS reveal. True if the loot landed.

        The same verified click every collect gets, with this panel's own proof: the reveal
        opening. A scav case collect is two steps, not one, and the click that opens the reveal is
        the one the game can swallow. settle=0 because _receive_point polls for the reveal itself.
        """
        point = self._click_until_taken(f'the finished {name} scav case roll', read.get_items,
                                        lambda: self._receive_point() is not None, settle=0)
        if point is None:
            log(f'the finished {name} roll would not open its loot reveal after '
                f'{GET_ITEMS_ATTEMPTS} clicks; the next lap tries again', 1)
            return False
        self._confirm_receive()  # the loot only lands once RECEIVE is clicked
        self._pause(COLLECT_SETTLE)
        # The loot has to land. A full stash makes Tarkov refuse it, which is the user's to clear,
        # so stop rather than keep clicking collects that cannot arrive.
        craft.check_stash_full(self.region)
        _book_profit(self.stats, job.craft.name)  # 0 until the scav case rolls have a figure
        # The reveal closing shifts the list, which on 2026-10-15 pushed the intelligence row off
        # screen for two rounds after a moonshine collect. Wheel back to the bottom, as after a buy.
        craft.scroll_scav_case_list(self.region)
        return True

    def _buy_scav_case_input(self, job, read):
        """Buy this roll's one input off the flea at its ceiling. True if bought.

        Called when a START did nothing, which for a scav case means the input is not in the stash.
        location is the input on the row, from read.inputs; quantity 1, since a roll takes one. The
        buy escapes the flea back to this panel (return_to_station) whether it bought or not, and
        the next round's read picks the roll up from there. That return lands the list scrolled to
        the top, so it is wheeled to the bottom again here, bought or not (an unbuyable roll's
        neighbour still needs its row on screen). Not after a LookupError: that one may not have
        made it back to the panel, and the wheel clicks the panel's dead space first.
        """
        name, _, location = read.inputs[0]
        ceiling = job.max_prices[name]  # build() guarantees it
        source = job.sources.get(name, 'players')
        log(f'scav case did not start, so the {name} input is missing; buying one at up to '
            f'{ceiling} from {source}')
        try:
            # Filters off for moonshine only: a bottle is always 100% condition and only ever
            # sold by players, so every control in that window would be set to what the board
            # already shows. Skipping it saves ~15s of clicks on every moonshine buy, and that
            # roll is the most frequent buyer in the cycle (53 trips to this board in one 3h
            # soak). The intelligence folder keeps them: nobody has checked its board for trader
            # barter offers, which the roubles and source filters are what keep out.
            craft.buy_craft_input_item(location, ceiling, self.region, source=source,
                                       craft=job.craft, checkpoint=self._pause, quantity=1,
                                       filters=name != 'moonshine')
        except craft.Unbuyable as e:
            log(f'{name} {e}, moving on', 1)
            bought = False
        except LookupError as e:
            log(f'{name}: {e}, moving on', 1)
            return False
        else:
            bought = True
        craft.scroll_scav_case_list(self.region)  # the flea trip reset the list to the top
        return bought

    def _click_scav_start(self, name, read):
        """Click a roll's START and give the row time to flip. Whether it took is the next round's
        read, not this click's business.

        START may or may not raise a handover dialog. The other crafts always get one and treat a
        missing one as Blind; this one was never confirmed to, so _confirm_handover(required=False)
        clears one if it shows and shrugs if it does not.
        """
        point = sell.jitter(pyautogui.center(read.start))
        log(f'starting the scav case {name} roll, clicking START at {point}', 1)
        pyautogui.click(*point)
        self._confirm_handover(required=False)  # confirm one if it shows; fine if it does not
        self._park(point)
        self._pause(START_SETTLE)  # give the click time to flip the row to producing

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
        if job.craft.name in craft.SCAV_CASE_NAMES:  # anchored on its input, no tick: its own pass
            self.tend_scav_case(job)
            return
        if job.craft.name == craft.BITCOIN_NAME:
            # The whole pass. The farm mines on its own with nothing to start and nothing to buy,
            # so a lit GET ITEMS is the only thing that can be acted on, and no button at all
            # (the farm's resting state) means come back later. No swap-less branch and no
            # settle: there is nothing to wait for.
            if not self._collect_if_lit(job):
                log('no bitcoin ready at the farm, swapping to the next craft')
            self._swap()
            return

        read = craft.read_craft(job.craft, self.region)

        if read.state == 'producing':  # nothing to do here; go tend another craft
            log(f'{job.craft.name} is producing, swapping to the next craft')
            # A Stop lands here. This waited nothing, on the grounds that the swap's own navigation
            # paces the loop. It does not: navigation's FIRST act is closing this station's panel,
            # and there is no gap at all between confirming the row is producing and clicking that
            # X. The 2026-09-17 soak had the workbench panel swallow its first close click 35 times
            # in 57, nine of them all the way to ending the run, while the other six stations closed
            # first time across ~400 attempts. Every one of those nine came through this branch.
            # So give the panel a beat to settle before navigation starts clicking at it.
            self._pause(PANEL_LEAVE_SETTLE)
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
            if self.hwnd is None:  # built with the game shut, and auto restart says open it
                self._boot_game()
            # No navigation up here: step() opens with _ensure_on, and inside the loop a failed
            # first navigation is covered by auto restart like any other.
            while not self._stop.is_set():
                try:
                    self.step()
                except (RuntimeError, LookupError, craft.Blind, window.WindowError) as e:
                    # Every fatal in a step funnels here; StashFull and Stopped are not in the
                    # tuple and fall through to the handlers below. Off, a bare re-raise. On, a
                    # fresh client, unless a full stash is what really broke the step under some
                    # other name (2026-09-02 saw one surface as Blind): check_stash_full raises
                    # StashFull then, which ends the run rather than restarting into the same wall.
                    if not self.restart_as:
                        raise
                    craft.check_stash_full(self.region)
                    self._restart_game(f'the run hit {type(e).__name__}: {e}')
        except Stopped:
            log('stopped between steps')
        except craft.StashFull as e:
            # A run-ender the runner can name: no craft can buy inputs or collect output into a
            # full stash, so there is nothing to swap to. Clear the dialog off the game and stop
            # cleanly rather than crash. The user has to empty the stash before a run is any use.
            craft.dismiss_stash_full(self.region)
            log(f'{e}; stopping the run, empty the stash and start again')
        except tarkov.NeedsLogin as e:
            # The other run-ender a person has to clear, and the reason NeedsLogin inherits from
            # Exception rather than RuntimeError: restarting is exactly the wrong answer here, and
            # the RuntimeError branch above would do precisely that, closing and relaunching the
            # client into the same sign-in dialog for the whole run while logging a restart each
            # time and never naming the cause. Nothing to dismiss on the way out either, since the
            # launcher is its own window and the game never started.
            log(f'{e}')
        finally:
            # finally, like the other modes: these used to run only after a full stash, so any
            # other ending left find.VERBOSE on and the totals unlogged.
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
    return HideoutCraft(jobs, stats=stats, one_pass=bool(prefs.get('one_pass', False)),
                        restart_as=auto_restart_from(prefs))
