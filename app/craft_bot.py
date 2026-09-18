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
SCAV_CASE_MAX_COLLECTS = 6  # lit GET ITEMS clicked in one scav case pass before giving up. The panel
                            # holds five rows, so reaching this means a button that will not clear,
                            # and a bounded loop ends the pass instead of spinning on it.
PARK_OFFSET = 100  # 1080p px to shove the cursor right after a click, so it stops covering the row

# The GUI's per-ingredient SOURCE picker. 'Players' or 'Traders' as shown; build() lowercases them
# into what sell.apply_flea_filters expects.
SOURCES = ('Players', 'Traders')
DEFAULT_SOURCE = 'Players'

# Per-ingredient defaults, used when the GUI has no saved value (or a junk one). The max is the most
# roubles to pay on the flea; the source is who to buy from. These match settings.DEFAULTS.
# Set 2026-09-16 off tarkov-market 24h averages, each ~10% under its craft's break-even, so a buy
# at the ceiling still profits. Break-even is revenue / input cost, and the tightest crafts have
# almost none: moonshine ran 1.04x and ai2 0.73x, so their inputs (sugar, purified water, pile of
# meds) are deliberately left where a rising market stops the buy rather than funding a loss.
# ponytail: constants, and they drift. _price_scraper/item_price.py reprices them in ~2s.
DEFAULT_MAX = {'crackers': 23000, 'alyonka': 37000, 'sewing_kit': 38500, 'ux_pro_beanie': 3500,
               'power_cord': 79000, 'pile_of_meds': 16600, 'purified_water': 107000,
               'sugar': 48900, 'sling_bag': 11000, 'green_gunpowder': 62000, 'matches': 26000,
               'water_filter': 70000, 'moonshine': 230000}
# anything not listed defaults to players
# crackers was 'traders' for part of 2026-09-17 and is back on players: a trader source caps volume
# at the restock limit, and the overnight soak hit that cap 5 times in 4.5 hours. See the ledger.
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
          _collect_scav_case_rolls   the LOOT FROM SCAVS reveal opens (_receive_point). A scav
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
        """The scav case's pass: start what can be started, then collect what has finished.

        Two phases with a panel reopen between them, because they want opposite things from the
        panel and cannot share one sweep of its list:

          starts   a startable roll still draws its input icon, so it can be named: the moonshine
                   bottle, or the 95k rouble count. Each roll is hunted by its own anchor
                   (craft.find_scav_case_row), in whichever scroll direction it lies.
          collect  a roll that is running or finished stops drawing its input icon, so a lit GET
                   ITEMS cannot be attributed to a row at all. It does not need to be: every roll
                   pays out the same '?' boxes, so every lit GET ITEMS is collected wherever it
                   sits (craft.lit_get_items).

        That second point is the bug this shape exists to fix. Collecting used to go through the
        same anchor-then-band read a start does, so a finished roll whose input label had dimmed
        was invisible to it and its loot was never taken. The screenshot of 2026-09-17 has a lit
        GET ITEMS sat on a row with no input icon drawn on it at all.

        Before that, this tended moonshine off 'the visible top row' and scrolled only for the 95k
        roll below it, which had the panel exactly backwards: the moonshine read found nothing,
        raised Blind into the restart path, and took the 95k roll queued behind it down with it, so
        neither roll was ever tended once. A roll that cannot be found is skipped with a log line.

        The reopen between the phases is what lets the collect sweep start from a known place: the
        starts phase leaves the list wherever hunting its two anchors stopped.
        """
        self._start_scav_case_moonshine(job)
        self._start_scav_case_95k(job)
        self._reopen_scav_case(job)
        self._collect_scav_case_rolls()
        self._swap()  # leave the scav case; both phases are done

    def _reopen_scav_case(self, job):
        """Close the scav case panel and open it again, putting its list back at the top.

        Reopening rather than scrolling back: the starts phase leaves the list wherever its anchor
        hunt stopped, and 'wheel up until it stops moving' is more wheeling and more trust than
        letting the panel redraw itself. get_to_station re-enters through the module carousel,
        which does not touch the production list's own scroll at all.

        A panel that will not close raises LookupError out of close_open_station_panel, which is in
        this mode's restart tuple, and that is the right answer: the collect phase cannot read a
        list it cannot see, and a wedged panel is the thing a restart fixes.
        """
        log('reopening the scav case panel to put its list back at the top', 1)
        craft.close_open_station_panel(self.region)
        craft.get_to_station(job.craft, self.region)

    def _collect_scav_case_rolls(self):
        """Click every lit GET ITEMS on the scav case panel, whichever row each one sits on.

        Sweeps the whole list (craft.scav_case_scroll_positions), because a finished roll can sit
        below the fold, and re-looks after every collect rather than walking a list of boxes taken
        up front: the loot reveal and the row flipping back both redraw the panel, so a box found
        before a click is stale after it.

        Bounded by SCAV_CASE_MAX_COLLECTS, for the reason every loop in this file is bounded: a
        button that will not clear has to end the pass rather than spin on it.
        """
        collected, stuck = 0, False
        for _ in craft.scav_case_scroll_positions():
            while not stuck and collected < SCAV_CASE_MAX_COLLECTS:
                boxes = craft.lit_get_items(self.region)
                if not boxes:
                    break
                # The same verified click every collect gets, with this panel's own proof: the
                # LOOT FROM SCAVS reveal opening. A scav case collect is two steps, not one, and
                # the click that opens the reveal is the one the game can swallow. settle=0 because
                # _receive_point polls for the reveal by itself.
                point = self._click_until_taken('a finished scav case roll', boxes[0],
                                                lambda: self._receive_point() is not None,
                                                settle=0)
                if point is None:
                    stuck = True
                    break
                self._confirm_receive()  # the loot only lands once RECEIVE is clicked
                self._pause(COLLECT_SETTLE)
                # The loot has to land. A full stash makes Tarkov refuse it, which is the user's to
                # clear, so stop rather than keep clicking collects that cannot arrive.
                craft.check_stash_full(self.region)
                _book_profit(self.stats, craft.SCAV_CASE_NAME)  # 0 until scav_case has a figure
                collected += 1
            if stuck or collected >= SCAV_CASE_MAX_COLLECTS:
                break
        if stuck:
            log(f'a finished scav case roll would not open its loot reveal after '
                f'{GET_ITEMS_ATTEMPTS} clicks, so the rest of the sweep is left for the next lap', 1)
        elif collected >= SCAV_CASE_MAX_COLLECTS:
            log(f'stopped after {SCAV_CASE_MAX_COLLECTS} collects, which a five-row panel '
                'should never reach', 1)
        log(f'collected {collected} finished scav case roll(s)' if collected
            else 'no finished scav case rolls to collect')

    def _start_scav_case_moonshine(self, job):
        """Start the moonshine roll if it is ready. Collecting is _collect_scav_case_rolls' job.

        The row is named only by its input, so read_craft anchors on the moonshine bottle rather
        than an output (see craft.SCAV_CASE), and there is no per-input tick, so 'ready' cannot be
        split into have-the-input and need-to-buy the way read_craft does for other crafts: the
        bottle is always drawn on a startable row, ticked or not. So readiness is judged after the
        fact: click START, then read the row back. Producing now means it started (count it). Still
        ready means the click did nothing, which for a scav case means the moonshine bottle was not
        in the stash, so buy one and let the next lap start it.

        Every state but 'ready' is somebody else's business now, 'done' included: the collect phase
        takes a finished roll, and it needs no anchor and no row to do it.

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
        # Scroll to it first. read_craft searches for the bottle across the whole region and
        # raises Blind when it is not drawn, and Blind restarts the game, so a roll sitting below
        # the panel's fold has to be brought into view before the read rather than after it.
        if craft.find_scav_case_row(craft.MOONSHINE_TARGET, self.region) is None:
            log('the moonshine scav case roll is not startable right now, skipping its start', 1)
            return

        read = craft.read_craft(job.craft, self.region)
        if read.state != 'ready':
            log(f'scav case moonshine roll is {read.state}, nothing to start')
            self._pause()  # a Stop still lands here, as it did in the old producing branch
            return

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

    def _start_scav_case_95k(self, job):
        """Start the 95,000-rouble roll if it is ready. Collecting is the collect phase's job.

        Same shape as the moonshine roll (no tick, state read off the row's buttons), read through
        craft.read_scav_case_95k, which scrolls to the roll and reads its buttons off the 95k
        exception band. The one difference is the missing-input path: this roll's input is a stack
        of roubles, which cannot be bought off the flea, so a START that does not take means the
        stash is short of roubles (the user's to top up), not an ingredient to go and buy.
        """
        read = craft.read_scav_case_95k(self.region)
        if read is None:
            log('the 95k scav case roll is not startable right now, skipping its start', 1)
            return
        if read.state != 'ready':
            log(f'the 95k scav case roll is {read.state}, nothing to start')
            self._pause()
            return

        point = sell.jitter(pyautogui.center(read.start))
        log(f'starting the 95k scav case roll, clicking START at {point}', 1)
        pyautogui.click(*point)
        self._confirm_handover(required=False)
        self._park(point)
        self._pause(START_SETTLE)

        # Judge it off the START button in the row we already found, not a re-read. read_scav_case_95k
        # re-anchors on the '95000/95000' count text, and a roll that started has *consumed* those
        # roubles, so the anchor is gone and a genuine start read back as 'did not start'. START
        # disappearing from the stored band is the roll producing; START still there is the handover
        # that could not complete, i.e. the stash short of roubles (the user's to top up).
        if find.find_all(craft.START_TARGET, read.band):
            log('the 95k scav case roll did not start, so the stash is short of roubles; '
                'moving on', 1)
        else:
            log('the 95k scav case roll started')
            self.stats['started:scav_case'] += 1
            self.stats['total_started'] += 1

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
