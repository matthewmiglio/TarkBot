import random
import threading
import time
from collections import namedtuple

import pyautogui

import screen
import window
from interact import sell, snipe
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
# sell.undercut_price, which takes the higher of the two cuts. The percentage is the same 90%
# throughout; only the flat cut changes, so picking a bigger one only moves the price above
# which the flat cut takes over: 20000, 30000, 50000 roubles.
UNDERCUTS = {'2k rubles | 90%': (0.90, 2000),
             '3k rubles | 90%': (0.90, 3000),
             '5k rubles | 90%': (0.90, 5000)}
DEFAULT_UNDERCUT = '2k rubles | 90%'
# Whether the offer creation window's autoselect similar checkbox ends up ticked. GUI label ->
# the state to leave it in, so the dropdown, the saved setting and the click read off one
# definition. On lists every matching item as one offer, which is a stack sold at the price
# read for a single one, so off is the default and on is a deliberate choice.
AUTOSELECT = {'OFF': False, 'ON': True}
DEFAULT_AUTOSELECT = 'OFF'
REFRESH_DELAY = 1.0  # seconds either side of the f5 that refreshes the flea after an offer
PRICE_DELAY = 2.0  # seconds to let the suggested price populate before reading it
# How many escapes it takes to get back to a clean screen from wherever a pass gave up. What is
# open depends on where the item came from and not on what went wrong, so every path out of
# sell_one counts off the Selection it was handed rather than off a constant of its own.
INVENTORY_ESCAPES = 1  # the offer creation window
SCAV_ESCAPES = 2  # that, plus the scav case window sat on top of it
# The below-market-value confirmation, on top of whatever the pass already had open. Added to
# the pass's own count rather than written out per mode, so it stays 2 from the stash and 3 with
# a scav case open without a second place to keep those numbers in step.
CHEAP_POPUP_ESCAPES = 1
# Escape-and-look rounds Start gets to clear the screen. Generous because it only ever runs
# once, and the alternative to one more round is a failed run.
RECOVER_ROUNDS = 10
# The pause between rounds is sell.RECOVER_DELAY, the same one the sweep waits after each click
# and each escape. There is no separate number for it on purpose.

# The counters FleaSeller keeps, in the order the GUI lists them. Keys are also stats dict keys,
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
TINT_STAT = MONEY_STAT  # what the GUI tints for this mode; gym_bot.py names its own

# What select_item picked, where it came from, and how many escapes back out of that screen.
Selection = namedtuple('Selection', 'point escapes source')


class Stopped(Exception):
    """Raised at the first checkpoint after stop(), to unwind out of a half finished pass."""


class Retry(Exception):
    """Raised to abandon this pass and start a fresh one, rather than to stop the bot.

    For the things that go wrong often enough that quitting over them would be silly: a price
    that never populates, a stash where every click of the select loop landed on nothing.
    """


class FleaSeller:
    def __init__(self, target_scav_cases=False, scav_chance=SCAV_CHANCE,
                 stale_minutes=STALE_THRESHOLDS[DEFAULT_STALE],
                 undercut=UNDERCUTS[DEFAULT_UNDERCUT],
                 autoselect=AUTOSELECT[DEFAULT_AUTOSELECT], stats=None):
        log('Initalizing Flea Seller')
        self.hwnd = window.handle()  # raises WindowError if missing or duplicated
        self.position = window.position(self.hwnd)
        self.size = window.size(self.hwnd)
        self.monitor = screen.current()
        # What gets searched is the window clipped to the chosen monitor. The window alone is
        # wrong when the user has picked a screen the game is not on, and the monitor alone is
        # wrong when the game is windowed; the part they share is right either way.
        self.region = screen.overlap(self.position + self.size, self.monitor.rect)
        if self.region is None:
            raise window.WindowError(
                f'Tarkov is at {self.position + self.size}, which is not on monitor '
                f'{self.monitor.label} at {self.monitor.rect}. Pick the other monitor, or move '
                f'the game onto this one.')
        self.target_scav_cases = target_scav_cases  # sell out of scav cases too, not just the stash
        self.scav_chance = scav_chance  # how often, when the above is on. 1.0 is scav cases only
        self.stale_minutes = stale_minutes  # how long a full board waits before we cancel offers
        self.undercut = undercut  # (fraction, flat), straight into sell.undercut_price
        self.autoselect = autoselect  # leave autoselect similar ticked, so an offer is the stack
        log(f'Tarkov window {self.hwnd} at {self.position} size {self.size}')
        log(f'monitor {self.monitor.label} ({self.monitor.name}) at {self.monitor.rect}, '
            f'searching {self.region}', 1)
        log(f'scav cases {"on" if target_scav_cases else "off"} '
            f'(chance {scav_chance:.0%}), stale threshold {stale_minutes}m, '
            f'undercut {undercut[0]:.1%} or {undercut[1]} roubles, '
            f'autoselect similar {"on" if autoselect else "off"}', 1)
        # The GUI hands in its own dict, which outlives any one FleaSeller, so the counters carry
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
            # Stopped unwinds past every frame between here and start(), where it is caught and
            # the traceback thrown away, so without this the log just stops mid pass. The line
            # above this one is the step it was interrupted at.
            log(f'stop seen at the {seconds:.1f}s checkpoint, unwinding this pass', 1)
            raise Stopped()

    def _past_error_dialog(self, step, failed):
        """Run `step`; if it fails, clear a Tarkov Error dialog and run it once more.

        Returns whatever the step returned, so a step that answers with something useful can be
        wrapped as readily as one that answers True or False.

        Tarkov's "Error / 0 / OK" dialog breaks every step of a pass the same two ways, which
        is why one wrapper covers all of them rather than each step growing its own check. It
        is modal, so a click lands on it instead of on whatever was aimed at, and it dims the
        whole screen behind it, so template matches and brightness reads come back under
        threshold. Any step that just failed is therefore worth one look at whether the dialog
        is the reason, and one more go once it is gone.

        The dialog is the game's to raise whenever it likes, usually a moment after some
        request it did not like, so there is no one step to guard: the run of 2026-08-22 died
        opening the flea, the run of 2026-08-23 died applying the filters, and both screens had
        the OK button sat on them unclicked.

        Failing means either coming back false or raising LookupError, and the two are the same
        event seen from different sides. The region inferences raise it when the window they
        measure themselves against is not on screen, and a dialog is one of the things that
        takes a window off the screen, so a raise deserves the same second look as a false. The
        LookupError's own text is carried into the message, since it names which anchors went
        missing and that is the part worth reading.

        One retry, and only when the dialog was really there. A step that fails on a clean
        screen has a real problem and raises exactly the message it always did; a step that
        fails again with the dialog cleared says so in its message, so the log never blames the
        dialog for something that was never about the dialog. Every step passed in here has to
        be safe to run twice, which they are: each one gives up on a target it could not find,
        so a failed attempt has typed and clicked nothing.
        """
        try:
            result = step()
            if result:
                return result
            why = failed
        except LookupError as e:
            why = f'{failed}: {e}'
        if not sell.dismiss_error_popup(self.region):
            raise RuntimeError(why)
        log(f'{why}: trying once more now the error dialog is gone', 1)
        try:
            result = step()
        except LookupError as e:
            raise RuntimeError(f'{failed}: {e} after clearing the error dialog')
        if not result:
            raise RuntimeError(f'{failed} after clearing the error dialog')
        return result

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
            # Not _past_error_dialog: the loop is already the retry. The dialog dims the add
            # offer button along with everything else, so a slot that is genuinely free reads
            # as full and the wait above times out with nothing actually wrong. Left there,
            # this is the worst of the dialog's hiding places, because it never raises: the
            # sweep below cannot cancel anything through a modal that eats every click, so the
            # loop waits stale_minutes, removes nothing, and goes round again until Stop.
            if sell.dismiss_error_popup(self.region):
                log('the wait was behind an error dialog, not a full board, so waiting again', 1)
                continue
            log(f'no slot after {self.stale_minutes}m, clearing out the offers that never sold')
            removed = sell.remove_stale_offers(self.region, stop=self._stop)
            self.stats['stale_removed'] += removed
            log(f'{removed} cancelled, {self.stats["stale_removed"]} this session', 1)
            self._pause()

    def open_offer_creation(self):
        """Get from wherever we are to an offer creation window sat in the bottom left corner."""
        log('opening the flea market')
        # snipe's opening, not sell.open_flea: open, escape, open again, then clear a
        # leftover filter-by-item chip. A stash item filtered by last pass survives into
        # this one and narrows the board the offer window reads.
        #
        # Through _past_error_dialog, like every screen-reading step below it. This is the step
        # the dialog hides itself from best: the dimmed screen drops the flea taskbar icon's
        # mean brightness below FLEA_OPEN_BRIGHTNESS, so an open flea reads as shut, and the
        # click that would fix a shut flea lands on the modal that eats it, so the second read
        # says shut too. The run of 2026-08-22 ended here, 27 passes in.
        self._past_error_dialog(lambda: snipe.open_clean_board(self.region),
                                'could not open the flea market')
        self._pause()
        self._await_offer_slot()  # can block for hours, minus the odd stale-offer sweep
        log('opening the offer creation window')
        # The last thing between here and a click, and the only one that asks Windows rather
        # than the screen. self.region was measured once at Start and every grab since has been
        # of that rectangle, so a game closed mid-run is invisible to template matching: it
        # photographs whatever is behind it now and reports the add offer button missing, which
        # points at the flea instead of at the game being gone. handle() raises WindowError.
        window.handle()

        def add_offer_window():
            """The click and the window it raises, retried as one rather than separately.

            A dialog that ate the click leaves nothing for a second wait to find, so retrying
            only the wait would time out again for a reason that had already been fixed. The
            cost is that the two no longer raise separately, and 'no add offer button on
            screen' is now a log line inside click_add_offer rather than its own message.

            Waited for, not slept through. Everything below assumes this window is up: the
            autoselect tick and the drag both live on it, and a flat WINDOW_DELAY that lands
            early turns into 'could not switch autoselect similar off', which points at the
            wrong thing entirely.
            """
            if not sell.click_add_offer(self.region):
                return False
            self._pause()
            return sell.wait_for(sell.OFFER_TARGET, self.region)

        self._past_error_dialog(add_offer_window, 'offer creation window never opened')
        want = 'on' if self.autoselect else 'off'
        self._past_error_dialog(lambda: sell.set_autoselect_similar(self.autoselect, self.region),
                                f'could not switch autoselect similar {want}')
        self._pause()
        self._past_error_dialog(lambda: sell.orientate_offer_creation(self.region),
                                'offer creation window never appeared')
        log('offer creation ready')

    def select_item(self):
        """Pick something to sell, from a scav case now and then if that is switched on.

        Opening the case is part of the scav path: open_scav_case right-clicks one, hits
        open, and orientates the window. The stash is the fallback whenever that fails, but
        only in a mode that wanted the stash at all. SCAV CASES ONLY means only: a pass with
        no case to open gives up with an empty Selection, which sell_one escapes out of and
        retries, rather than quietly listing whatever the stash happens to hold. That
        fallback is what a user saw on 2026-08-20 as "scav case only ... selling random shit".

        Returns a Selection. Its escapes count is decided when the case opens, not when the
        pick succeeds: a case that opened and then would not read still leaves its window on
        screen even though the item ends up coming from the stash. Its source is where the
        item actually came from, which is what the posted_* counters want, so those two
        deliberately disagree on that fallback path.
        """
        escapes = INVENTORY_ESCAPES
        stash_allowed = self.scav_chance < 1.0  # SCAV CASES ONLY is the only mode without it
        if self.target_scav_cases and random.random() < self.scav_chance:
            log('picking an item, trying a scav case first')
            if not sell.open_scav_case(self.region):
                if not stash_allowed:
                    log('no scav case to open and the stash is off, ending this pass', 1)
                    return Selection(None, escapes, 'scav')
                log('no scav case to open, falling back to the stash', 1)
            else:
                escapes = SCAV_ESCAPES  # open now, and open whatever happens next
                try:
                    point = sell.select_item_from_random_scav_case(self.region, stop=self._stop)
                    return Selection(point, escapes, 'scav')
                except LookupError as e:  # opened, but the window never became readable
                    if not stash_allowed:
                        log(f'scav case window not readable ({e}) and the stash is off, '
                            f'ending this pass', 1)
                        return Selection(None, escapes, 'scav')
                    log(f'scav case window not readable ({e}), falling back to the stash', 1)
        else:
            log('picking an item out of the stash')
        return Selection(sell.select_item_from_inventory(self.region, stop=self._stop),
                         escapes, 'inventory')

    def _park_windows(self, picked, offer_corner, scav_corner, scav_first):
        """Move whatever this pass has open into the named corners.

        Called twice: once to clear the left of the board for the filter window, and once to
        put everything back where the rest of the pass expects it. Whether there is a scav case
        window to move is read off picked.escapes rather than picked.source, since the fallback
        path leaves the case open while taking its item from the stash.

        scav_first is the whole subtlety. The case window is drawn on top of the offer creation
        window and runs a good 1100px down and across from its own title bar, so whichever side
        it is parked on, it covers the offer window's title bar on that side and find() has
        nothing to grab. Both windows travel together, so on each leg the one that has to move
        first is the one currently sat over the other:

          going right  scav_first=True   the case is on the left, over the offer title bar
          coming back  scav_first=False  the case is on the right, over it again

        Both halves of that were watched failing on 2026-08-22. Offer first on the way out left
        it where it opened; case first on the way back logged 'offer_creation_window_title not
        on screen' and left it parked on the right, where the fixed price region does not read
        the price box.

        Neither drag is fatal here. A window that would not grab costs a covered control at
        worst, and the filter step checks its own window and says so in better words.
        """
        moves = [(sell.orientate_offer_creation, offer_corner)]
        if picked.escapes == SCAV_ESCAPES:
            moves.insert(0 if scav_first else 1, (sell.orientate_scav_box, scav_corner))
        for move, corner in moves:
            move(self.region, corner)

    def _escape(self, presses):
        """Back out of whatever is on screen, so the next pass starts somewhere known."""
        log(f'escaping {presses}x back to a clean screen', 1)
        for _ in range(presses):
            pyautogui.press('esc')
            time.sleep(sell.MENU_DELAY)

    def sell_one(self):
        """One full pass, in order:

        1. open the flea and wait for a free offer slot
        2. click add offer
        3. drag the offer creation window to the bottom left
        4. pick a source, and on the scav path open a case and drag it to the top left
        5. click an item and check something actually got selected
        6. swing both windows over to the right, clear of the filter window
        7. set the flea filters
        8. put both windows back on the left, then price it, list it and refresh
        """
        started = time.monotonic()
        self.open_offer_creation()
        # Wrapped for the LookupError, not for the return: a Selection is truthy even when its
        # point is None, and 'nothing selectable' is already a Retry further down. What this
        # catches is infer_inventory_region giving up on all three of its anchors at once, which
        # is what a window closing under it looks like. The run of 2026-08-24 03:26 ended here
        # with the dialog on screen at 0.961 against a 0.9 threshold: it closed the scav case
        # window, select_item caught that one and fell back to the stash, and the stash's own
        # infer then raised into a screen nobody had looked at. One dismiss covers both, because
        # the retry starts the pick over from the top.
        picked = self._past_error_dialog(self.select_item, 'could not pick an item to sell')
        # Before the no-item accounting below, because the select loop also returns None when
        # it was stopped part way. Without this a Stop read as 'nothing selectable', which
        # counted a find failure that never happened and pressed escape on the way out.
        self._pause()
        if not picked.point:
            self.stats['select_failed'] += 1
            self._escape(picked.escapes)
            raise Retry('nothing selectable after every attempt')
        self.stats['selected'] += 1
        log(f'selected item at {picked.point} ({picked.source})')
        self._pause()

        # The filters go on after the item, not before the offer window. The board the filters
        # narrow is the one the suggested price is read off, so the only thing that has to be
        # true is that they are set before that read. Doing it here means the offer window is
        # already up and can be swung out of the way, where doing it first meant setting them on
        # a board that the filter-by-item chip then re-filtered anyway.
        log('moving the open windows off the left of the board for the filter window')
        self._park_windows(picked, sell.FILTERING_OFFER_CORNER, sell.FILTERING_SCAV_CORNER,
                           scav_first=True)  # the case is on the left, over the offer title bar
        self._pause()
        log('applying the flea filters')
        # Where the run of 2026-08-23 died, 154 passes in. The dialog arrived during the drag
        # just above that swings the offer window off the board, so the gear click half a
        # second later landed on the modal and the filter window never came up. Safe to run
        # twice: it only touches a dropdown while that dropdown still says 'any', so a board
        # already filtered gets the window opened and OK'd straight back out.
        self._past_error_dialog(lambda: sell.apply_flea_filters(self.region),
                                'could not apply the flea filters')
        self._pause()
        log('putting the open windows back')
        self._park_windows(picked, sell.OFFER_CORNER, sell.SCAV_CORNER,
                           scav_first=False)  # now it is on the right, over it again
        self._pause()

        log(f'waiting {PRICE_DELAY:.0f}s for the suggested price to populate')
        self._pause(PRICE_DELAY)  # the suggested price arrives from the server, not instantly
        price = sell.get_price(self.region)
        if price is None:  # never guess at it, a half read price is worse than no sale
            self.stats['price_missing'] += 1
            # picked.escapes, not a flat 1. An unreadable price says nothing about how many
            # windows are open: the item still came from wherever it came from, and a scav case
            # pass has the case window under the offer window either way. This was the one path
            # out of sell_one still escaping a fixed number of times, and on 2026-08-20 it ended
            # a run. A scav case item that could not be listed put an error banner over the
            # price box; the single escape closed the banner, the offer creation window stayed
            # up, and it covers the flea taskbar icon, so the next pass could not find the flea
            # and raised. 132 passes in, then 5h36m sat idle.
            # ponytail: still one press per window we know about, so a banner on top of a scav
            # pass leaves the case window open. Harmless today, since the case window does not
            # reach the taskbar. Loop on close_leftover_windows here if that stops being true.
            self._escape(picked.escapes)
            raise Retry('could not read the suggested price')
        self.stats['price_found'] += 1
        listing = sell.undercut_price(price, *self.undercut)
        log(f'suggested {price}, undercutting to {listing} ({price - listing} off)')
        self._pause()

        log('placing the offer')
        # enter_price selects all before it types, so even a retry that somehow ran on top of a
        # field it had already filled replaces the number rather than appending to it.
        self._past_error_dialog(lambda: sell.enter_price(listing, self.region),
                                'no roubles price field on screen')
        self._past_error_dialog(lambda: sell.click_place_offer(self.region),
                                'no place offer button on screen')

        # Some items get a "below market value, are you sure" confirmation instead of being
        # listed. Everything below this point assumes the offer went up, so it is checked before
        # a single counter moves: the popup means no sale, and treating it as one inflates both
        # the posted count and the money asked for by an offer that never existed.
        self._pause(sell.CHEAP_OFFER_POPUP_DELAY)
        if sell.cheap_offer_popup(self.region):
            self.stats['price_missing'] += 1  # the price is what it rejected, so it counts here
            self._escape(picked.escapes + CHEAP_POPUP_ESCAPES)
            raise Retry('the offer was refused as below market value')

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

    def _recover(self):
        """Get to the flea from whatever the last session left on screen.

        Runs once, on Start. Every screen a pass meets afterwards is one the bot opened itself,
        so this is the only point where the state is genuinely unknown: the user may have hit
        Start with a scav case open, or over the wreckage of a run that was stopped mid pass.

        Loops rather than escaping once, because the windows stack. A scav case run that was
        interrupted leaves the case window with an offer creation window on top of it, and one
        pass of close_leftover_windows closes the top one and then reports the flea tab still
        missing, which is exactly what it was asked to fix. Each round escapes what it can see
        and then looks again, so a stack unwinds a layer at a time.

        The flea tab being visible is the finish line, not the number of escapes. It is the
        thing the first pass actually needs, and it is the only signal that says the screen is
        clear rather than merely that this round found nothing it recognised.

        Nothing here is fatal. If the flea will not open, the first pass raises about it with
        the message that has always meant that, rather than a second one from up here.
        """
        log('checking for anything left open from last time')
        for round_number in range(1, RECOVER_ROUNDS + 1):
            # Checked here rather than through _pause: _recover runs before start()'s try, so a
            # Stopped raised in here would leave start() as an unhandled crash in the GUI.
            if self._stop.is_set():
                log('stopped during recovery, before the first pass', 1)
                return
            escaped = sell.close_leftover_windows(self.region)
            if sell.find_flea_icon(self.region):
                log(f'the flea tab is visible, recovery done in {round_number} round(s)', 1)
                break
            log(f'round {round_number}/{RECOVER_ROUNDS}: {escaped} escape(s) and the flea tab '
                f'is still hidden, looking again', 2)
            time.sleep(sell.RECOVER_DELAY)
        else:
            log(f'the flea tab never appeared in {RECOVER_ROUNDS} rounds; something is on '
                f'screen that recovery does not recognise', 1)
        if not sell.open_flea(self.region):
            log('the flea did not open during recovery, leaving it to the first pass', 1)

    def start(self):
        """Sell one item after another until stop() is called. Blocks, so give it a thread."""
        log('Starting Flea Seller')
        self._stop.clear()
        self._recover()
        passes = 0
        try:
            while not self._stop.is_set():
                passes += 1
                log(f'===== pass {passes} =====')
                try:
                    self.sell_one()
                except Retry as e:  # recoverable, the screen has already been backed out of
                    log(f'{e}, starting a fresh pass')
                    # Here rather than in sell_one, because a pass has many ways to fail and the
                    # Error dialog is the one that fails all of them at once. Costs one match on
                    # a pass that was already lost, and a run stuck behind that dialog would
                    # otherwise lose every pass after it until Stop.
                    sell.dismiss_error_popup(self.region)
        except Stopped:
            log('stopped part way through a pass')
        finally:
            # finally, not after the try: a RuntimeError from a pass is not caught here, and
            # without this the totals line is skipped on exactly the runs worth reading back.
            # The GUI logs the exception itself, so this only has to survive it, not report it.
            log(f'Flea Seller finished after {passes} passes. '
                + ', '.join(f'{label.strip()} {self.stats[key]}' for key, label in STAT_LABELS))

    def stop(self):
        """Ask the loop to quit. Safe from any thread, and safe to call twice."""
        log('Stopping Flea Seller')
        self._stop.set()


def build(prefs, stats):
    """A FleaSeller configured from the GUI's saved preferences.

    Here rather than in the GUI so the mapping from a settings key to a constructor argument
    sits beside the constants those keys index into. gym_bot.build() is the same function for the
    other mode, and the GUI calls whichever the active tab names.
    """
    screen.use(prefs.get('monitor', screen.AUTO))  # before the FleaSeller, which clips to it
    _, scav, chance = MODES.get(prefs.get('mode'), MODES['inventory'])
    stale = STALE_THRESHOLDS.get(prefs.get('stale'), STALE_THRESHOLDS[DEFAULT_STALE])
    undercut = UNDERCUTS.get(prefs.get('undercut'), UNDERCUTS[DEFAULT_UNDERCUT])
    autoselect = AUTOSELECT.get(prefs.get('autoselect'), AUTOSELECT[DEFAULT_AUTOSELECT])
    return FleaSeller(target_scav_cases=scav, scav_chance=chance, stale_minutes=stale,
                   undercut=undercut, autoselect=autoselect, stats=stats)
