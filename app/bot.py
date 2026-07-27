import random
import threading
import time
from collections import namedtuple

import pyautogui

import tarkov_window
from interact import sell

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
               ('stale_removed', 'Stale offers removed'))

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
                 stale_minutes=STALE_THRESHOLDS[DEFAULT_STALE]):
        print('Initalizing Tarkbot')
        self.hwnd = tarkov_window.handle()  # raises WindowError if missing or duplicated
        self.position = tarkov_window.position(self.hwnd)
        self.size = tarkov_window.size(self.hwnd)
        self.region = self.position + self.size  # (left, top, width, height) to search in
        self.target_scav_cases = target_scav_cases  # sell out of scav cases too, not just the stash
        self.scav_chance = scav_chance  # how often, when the above is on. 1.0 is scav cases only
        self.stale_minutes = stale_minutes  # how long a full board waits before we cancel offers
        print(f'Tarkov window {self.hwnd} at {self.position} size {self.size}')
        self.stats = {key: 0 for key, _ in STAT_LABELS}  # ponytail: GUI polls this dict
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
            waited = sell.wait_for_offer_slot(self.region, stop=self._stop, timeout=timeout)
            self._pause()  # a stop during the wait unwinds here, before any clicking
            if waited:
                print(f'waited {waited:.0f}s for an offer slot')
            if sell.more_offers_available(self.region):  # returning is not proof one opened
                return
            print(f'no slot after {self.stale_minutes}m, clearing out the offers that never sold')
            self.stats['stale_removed'] += sell.remove_stale_offers(self.region, stop=self._stop)
            self._pause()

    def open_offer_creation(self):
        """Get from wherever we are to an offer creation window sat in the top left corner."""
        if not sell.open_flea(self.region):
            raise RuntimeError('could not open the flea market')
        self._pause()
        self._await_offer_slot()  # can block for hours, minus the odd stale-offer sweep
        if not sell.apply_flea_filters(self.region):
            raise RuntimeError('could not apply the flea filters')
        self._pause()
        if not sell.click_add_offer(self.region):
            raise RuntimeError('no add offer button on screen')
        self._pause(sell.WINDOW_DELAY)  # the window has to exist before there is a title bar to grab
        if not sell.disable_autoselect_similar(self.region):
            raise RuntimeError('could not switch off autoselect similar')
        self._pause()
        if not sell.orientate_offer_creation(self.region):
            raise RuntimeError('offer creation window never appeared')
        print('offer creation ready')

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
            if not sell.open_scav_case(self.region):
                print('no scav case to open, falling back to the stash')
            else:
                escapes = SCAV_ESCAPES  # open now, and open whatever happens next
                try:
                    point = sell.select_item_from_random_scav_case(self.region)
                    return Selection(point, escapes, 'scav')
                except LookupError:  # opened, but the window never became readable
                    print('scav case window not readable, falling back to the stash')
        return Selection(sell.select_item_from_inventory(self.region), escapes, 'inventory')

    def _escape(self, presses):
        """Back out of whatever is on screen, so the next pass starts somewhere known."""
        for _ in range(presses):
            pyautogui.press('esc')
            time.sleep(sell.MENU_DELAY)

    def sell_one(self):
        """One full pass: open the offer window, pick something, price it, list it, refresh."""
        self.open_offer_creation()
        picked = self.select_item()
        if not picked.point:
            self.stats['select_failed'] += 1
            self._escape(picked.escapes)
            raise Retry('nothing selectable after every attempt')
        self.stats['selected'] += 1
        print(f'selected item at {picked.point} ({picked.source})')
        self._pause()

        self._pause(PRICE_DELAY)  # the suggested price arrives from the server, not instantly
        price = sell.get_price(self.region)
        if price is None:  # never guess at it, a half read price is worse than no sale
            self.stats['price_missing'] += 1
            self._escape(PRICE_ESCAPES)
            raise Retry('could not read the suggested price')
        self.stats['price_found'] += 1
        listing = sell.undercut_price(price)
        print(f'suggested {price}, listing at {listing}')
        self._pause()

        if not sell.enter_price(listing, self.region):
            raise RuntimeError('no roubles price field on screen')
        if not sell.click_place_offer(self.region):
            raise RuntimeError('no place offer button on screen')
        self.stats['posted'] += 1
        self.stats[f'posted_{picked.source}'] += 1
        print(f'offer placed, {self.stats["posted"]} so far')

        self._pause(REFRESH_DELAY)  # let the offer land before asking the flea to redraw
        pyautogui.press('f5')
        self._pause(REFRESH_DELAY)  # and let the redraw finish before the next pass reads the screen

    def start(self):
        """Sell one item after another until stop() is called. Blocks, so give it a thread."""
        print('Starting Tarkbot')
        self._stop.clear()
        try:
            while not self._stop.is_set():
                try:
                    self.sell_one()
                except Retry as e:  # recoverable, the screen has already been backed out of
                    print(f'{e}, starting a fresh pass')
        except Stopped:
            print('stopped part way through a pass')
        print('Tarkbot finished. ' + ', '.join(f'{label.strip()} {self.stats[key]}'
                                               for key, label in STAT_LABELS))

    def stop(self):
        """Ask the loop to quit. Safe from any thread, and safe to call twice."""
        print('Stopping Tarkbot')
        self._stop.set()
