import random
import threading
import time
from collections import namedtuple

import pyautogui

import tarkov_window
from interact import sell
from narrate import log

SCAV_CHANCE = 0.5  # how often to sell out of a scav case instead of the stash, when enabled
# Where the bot takes items from. key -> (label, target_scav_cases, scav_chance). The GUI
# lists these in order and the CLI flags map onto them, so there is one definition of a mode.
MODES = {'inventory': ('INVENTORY ONLY', False, 0.0),
         'both': ('INVENTORY + SCAV', True, SCAV_CHANCE),
         'scav': ('SCAV CASES ONLY', True, 1.0)}
# How long a full offer board is allowed to sit before we cancel what has not sold. GUI label
# -> minutes, so the dropdown, the saved setting and the wait all read off one definition.
STALE_THRESHOLDS = {'5m': 5, '10m': 10, '30m': 30}
DEFAULT_STALE = '10m'
# How far under the suggested price to list. GUI label -> (fraction, flat) for
# sell.undercut_price, which takes the higher of the two cuts. The percentage is the same 85%
# throughout; only the flat cut changes, so picking a bigger one only moves the price above
# which the flat cut takes over: 13333, 20000, 33333 roubles.
UNDERCUTS = {'2k rubles | 85%': (0.85, 2000),
             '3k rubles | 85%': (0.85, 3000),
             '5k rubles | 85%': (0.85, 5000)}
DEFAULT_UNDERCUT = '2k rubles | 85%'
REFRESH_DELAY = 1.0  # seconds either side of the f5 that refreshes the flea after an offer
PRICE_DELAY = 2.0  # seconds to let the suggested price populate before reading it
# How many escapes it takes to get back to a clean screen from wherever a pass gave up.
INVENTORY_ESCAPES = 1  # the offer creation window
SCAV_ESCAPES = 2  # that, plus the scav case window sat on top of it
PRICE_ESCAPES = 1  # an unreadable price leaves only the offer window open

# The counters Tarkbot keeps, in the order the GUI lists them. Keys are also stats dict keys,
# and posted_<source> has to match the source names Selection carries.
STAT_LABELS = (('selected', 'Items found'),
               ('select_failed', 'Find failures'),
               ('price_found', 'Prices read'),
               ('price_missing', 'Prices unreadable'),
               ('posted', 'Items posted'),
               ('posted_scav', '  from scav cases'),
               ('posted_inventory', '  from inventory'),
               ('money', 'Total money'),
               ('stale_removed', 'Stale offers removed'))
MONEY_STAT = 'money'  # the one row the GUI tints, so both ends read off one name
TINT_STAT = MONEY_STAT  # what the GUI tints for this mode; gym.py names its own

# What select_item picked, where it came from, and how many escapes back out of that screen.
Selection = namedtuple('Selection', 'point escapes source')


class Stopped(Exception):
    """Raised at the first checkpoint after stop(), to unwind out of a half finished pass."""


class Retry(Exception):
    """Raised to abandon this pass and start a fresh one, rather than to stop the bot.

    For the things that go wrong often enough that quitting over them would be silly: a price
    that never populates, a stash where fifty clicks all landed on nothing.
    """


class Tarkbot:
    def __init__(self, target_scav_cases=False, scav_chance=SCAV_CHANCE,
                 stale_minutes=STALE_THRESHOLDS[DEFAULT_STALE],
                 undercut=UNDERCUTS[DEFAULT_UNDERCUT], stats=None):
        log('Initalizing Tarkbot')
        self.hwnd = tarkov_window.handle()  # raises WindowError if missing or duplicated
        self.position = tarkov_window.position(self.hwnd)
        self.size = tarkov_window.size(self.hwnd)
        self.region = self.position + self.size  # (left, top, width, height) to search in
        self.target_scav_cases = target_scav_cases  # sell out of scav cases too, not just the stash
        self.scav_chance = scav_chance  # how often, when the above is on. 1.0 is scav cases only
        self.stale_minutes = stale_minutes  # how long a full board waits before we cancel offers
        self.undercut = undercut  # (fraction, flat), straight into sell.undercut_price
        log(f'Tarkov window {self.hwnd} at {self.position} size {self.size}')
        log(f'scav cases {"on" if target_scav_cases else "off"} '
            f'(chance {scav_chance:.0%}), stale threshold {stale_minutes}m, '
            f'undercut {undercut[0]:.1%} or {undercut[1]} roubles', 1)
        # The GUI hands in its own dict, which outlives any one Tarkbot, so the counters carry
        # across stop/start and only reset when the app does. Nothing passed, count from zero.
        self.stats = {key: 0 for key, _ in STAT_LABELS} if stats is None else stats
        self._stop = threading.Event()  # set from whichever thread owns the stop button

    def _pause(self, seconds=0):
        """Wait, or abandon the pass right now if stop() has been called.

        Every wait and every step boundary goes through here rather than time.sleep, so a
        stop lands within one sell.* call instead of at the end of the pass. It cannot
        interrupt a drag or a right-click already in flight, so worst case is a second or
        two, not a whole listing.
        """
        if self._stop.wait(seconds):  # wait(0) is just a check, no sleep
            raise Stopped()

    def _await_offer_slot(self):
        """Block until there is a slot to sell into, cancelling stale offers to make one.

        The board only frees up when something sells or expires, so waiting is usually the
        whole job. Past stale_minutes though, waiting longer is just betting on offers that
        have already proved they will not sell, so those get cancelled and the wait restarts.
        Loops rather than doing it once, since a sweep that removes nothing leaves us right
        back where we started and the next threshold is the only thing left to try.
        """
        timeout = self.stale_minutes * 60
        while True:
            log('waiting for a free offer slot')
            waited = sell.wait_for_offer_slot(self.region, stop=self._stop, timeout=timeout)
            self._pause()  # a stop during the wait unwinds here, before any clicking
            log(f'waited {waited:.1f}s for an offer slot', 1)
            if sell.more_offers_available(self.region):  # returning is not proof one opened
                log('a slot is free', 1)
                return
            log(f'no slot after {self.stale_minutes}m, clearing out the offers that never sold')
            removed = sell.remove_stale_offers(self.region, stop=self._stop)
            self.stats['stale_removed'] += removed
            log(f'{removed} cancelled, {self.stats["stale_removed"]} this session', 1)
            self._pause()

    def open_offer_creation(self):
        """Get from wherever we are to an offer creation window sat in the top left corner."""
        log('opening the flea market')
        if not sell.open_flea(self.region):
            raise RuntimeError('could not open the flea market')
        self._pause()
        self._await_offer_slot()  # can block for hours, minus the odd stale-offer sweep
        log('applying the flea filters')
        if not sell.apply_flea_filters(self.region):
            raise RuntimeError('could not apply the flea filters')
        self._pause()
        log('opening the offer creation window')
        if not sell.click_add_offer(self.region):
            raise RuntimeError('no add offer button on screen')
        self._pause(sell.WINDOW_DELAY)  # the window has to exist before there is a title bar to grab
        if not sell.disable_autoselect_similar(self.region):
            raise RuntimeError('could not switch off autoselect similar')
        self._pause()
        if not sell.orientate_offer_creation(self.region):
            raise RuntimeError('offer creation window never appeared')
        log('offer creation ready')

    def select_item(self):
        """Pick something to sell, from a scav case now and then if that is switched on.

        Opening the case is part of the scav path: open_scav_case right-clicks one, hits
        open, and orientates the window. The stash is the fallback whenever that fails.

        Returns a Selection. Its escapes count is decided when the case opens, not when the
        pick succeeds: a case that opened and then would not read still leaves its window on
        screen even though the item ends up coming from the stash. Its source is where the
        item actually came from, which is what the posted_* counters want, so those two
        deliberately disagree on that fallback path.
        """
        escapes = INVENTORY_ESCAPES
        if self.target_scav_cases and random.random() < self.scav_chance:
            log('picking an item, trying a scav case first')
            if not sell.open_scav_case(self.region):
                log('no scav case to open, falling back to the stash', 1)
            else:
                escapes = SCAV_ESCAPES  # open now, and open whatever happens next
                try:
                    point = sell.select_item_from_random_scav_case(self.region)
                    return Selection(point, escapes, 'scav')
                except LookupError as e:  # opened, but the window never became readable
                    log(f'scav case window not readable ({e}), falling back to the stash', 1)
        else:
            log('picking an item out of the stash')
        return Selection(sell.select_item_from_inventory(self.region), escapes, 'inventory')

    def _escape(self, presses):
        """Back out of whatever is on screen, so the next pass starts somewhere known."""
        log(f'escaping {presses}x back to a clean screen', 1)
        for _ in range(presses):
            pyautogui.press('esc')
            time.sleep(sell.MENU_DELAY)

    def sell_one(self):
        """One full pass: open the offer window, pick something, price it, list it, refresh."""
        started = time.monotonic()
        self.open_offer_creation()
        picked = self.select_item()
        if not picked.point:
            self.stats['select_failed'] += 1
            self._escape(picked.escapes)
            raise Retry('nothing selectable after every attempt')
        self.stats['selected'] += 1
        log(f'selected item at {picked.point} ({picked.source})')
        self._pause()

        log(f'waiting {PRICE_DELAY:.0f}s for the suggested price to populate')
        self._pause(PRICE_DELAY)  # the suggested price arrives from the server, not instantly
        price = sell.get_price(self.region)
        if price is None:  # never guess at it, a half read price is worse than no sale
            self.stats['price_missing'] += 1
            self._escape(PRICE_ESCAPES)
            raise Retry('could not read the suggested price')
        self.stats['price_found'] += 1
        listing = sell.undercut_price(price, *self.undercut)
        log(f'suggested {price}, undercutting to {listing} ({price - listing} off)')
        self._pause()

        log('placing the offer')
        if not sell.enter_price(listing, self.region):
            raise RuntimeError('no roubles price field on screen')
        if not sell.click_place_offer(self.region):
            raise RuntimeError('no place offer button on screen')
        self.stats['posted'] += 1
        self.stats[f'posted_{picked.source}'] += 1
        # What we asked for, not what we got: nothing on screen says whether an offer ever sold.
        self.stats[MONEY_STAT] += listing
        log(f'offer placed, {self.stats["posted"]} so far, {self.stats[MONEY_STAT]} asked for '
            f'in total. Pass took {time.monotonic() - started:.1f}s')

        log(f'refreshing the flea (f5), {REFRESH_DELAY:.0f}s either side', 1)
        self._pause(REFRESH_DELAY)  # let the offer land before asking the flea to redraw
        pyautogui.press('f5')
        self._pause(REFRESH_DELAY)  # and let the redraw finish before the next pass reads the screen

    def start(self):
        """Sell one item after another until stop() is called. Blocks, so give it a thread."""
        log('Starting Tarkbot')
        self._stop.clear()
        passes = 0
        try:
            while not self._stop.is_set():
                passes += 1
                log(f'===== pass {passes} =====')
                try:
                    self.sell_one()
                except Retry as e:  # recoverable, the screen has already been backed out of
                    log(f'{e}, starting a fresh pass')
        except Stopped:
            log('stopped part way through a pass')
        log(f'Tarkbot finished after {passes} passes. '
            + ', '.join(f'{label.strip()} {self.stats[key]}' for key, label in STAT_LABELS))

    def stop(self):
        """Ask the loop to quit. Safe from any thread, and safe to call twice."""
        log('Stopping Tarkbot')
        self._stop.set()


def build(prefs, stats):
    """A Tarkbot configured from the GUI's saved preferences.

    Here rather than in the GUI so the mapping from a settings key to a constructor argument
    sits beside the constants those keys index into. gym.build() is the same function for the
    other mode, and the GUI calls whichever the active tab names.
    """
    _, scav, chance = MODES.get(prefs.get('mode'), MODES['inventory'])
    stale = STALE_THRESHOLDS.get(prefs.get('stale'), STALE_THRESHOLDS[DEFAULT_STALE])
    undercut = UNDERCUTS.get(prefs.get('undercut'), UNDERCUTS[DEFAULT_UNDERCUT])
    return Tarkbot(target_scav_cases=scav, scav_chance=chance, stale_minutes=stale,
                   undercut=undercut, stats=stats)
