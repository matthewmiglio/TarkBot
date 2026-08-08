"""
This module is for selling items on the flea market.

Geometry self-check:  python -m interact.sell
"""
import random
import time

import numpy as np
import pyautogui
from PIL import Image

from interact import find, ocr
from narrate import log

# The buttons framing the inventory grid: (left edge, right and top edge, bottom edge)
EDGES = ('inventory_all_button', 'autoselect_similar', 'auto_sort')
SCAV_MARGIN = 0.15  # scav case boxes grow this much per side before their pixels are dropped
# Every colour an empty slot is known to take, read off screenshots showing nothing but empty
# slots. Drop another png in that folder to teach it more. ponytail: the images are the list.
DEAD_REFERENCE = 'dead_pixels'  # a folder under reference_images/, any number of pngs
DEAD_TOL = 5  # per-channel slack; this close to a known slot colour still counts as empty
MENU_DELAY = 0.3  # seconds for the right-click menu to draw before we go looking for it
WINDOW_DELAY = 1.0  # seconds for a window to finish appearing before we grab its title bar
# The scav case window is the one thing on screen that does not draw within WINDOW_DELAY: it
# loads its contents from the server, which took 2-4s every time it was measured. Waited for
# rather than slept through, so a fast open costs a poll and a slow one still works.
SCAV_WINDOW_TIMEOUT = 10.0  # seconds the scav case window gets to appear before we give up
SCAV_WINDOW_POLL = 0.25  # seconds between rechecks while waiting for it
SELECT_ATTEMPTS = 50  # clicks to try before admitting we cannot land on an item
# After a left click, before asking the offer panel what it did. Was MENU_DELAY / 2, which
# was under the panel's own redraw: the read landed on the *previous* attempt's panel, so a
# hit read as a miss (click on, one slot later) and a miss read as a hit (right click a gap,
# no filter by item, esc). Both of those look like the bot flailing. Nothing on screen says
# when the panel is done, so this is measured slack, not a signal.
SELECT_POLL_DELAY = 0.5  # after a click, before reading what it did
SELECT_WINDOW_DELAY = WINDOW_DELAY / 2  # after filter by item, for the flea panel to catch up
ADD_OFFER_TARGET = 'add_offer'  # the button that opens the offer creation window
OFFER_TARGET = 'offer_creation'  # reference images for the offer creation window
SCAV_WINDOW_TARGET = 'scav_case_window_title'  # reference images for the opened scav case window
CLOSE_BUTTON_TARGET = 'close_window_button'  # several are on screen at once, we want the leftmost
NO_SELECTION_TARGET = 'no_items_selected'  # the placeholder shown while nothing is picked
SELECTION_TARGET = 'item_is_selected'  # the panel shown once something is, the other half of the read
FLEA_ICON_TARGET = 'flea_icon'  # the taskbar entry, one folder holding both its states
FLEA_OPEN_BRIGHTNESS = 90  # mean channel value: measured 57 closed, 117 open
# The suggested price readout, as (left, top, right, bottom) fractions of the window.
# Measured at 1920x1080: left 1339, top 147, right 1498, bottom 186.
PRICE_FRACTIONS = (1339 / 1920, 147 / 1080, 1498 / 1920, 186 / 1080)
SCAV_TOP_PAD = 5  # px below the scav window title before its grid starts
SCAV_HEIGHT_FRACTION = 0.81  # of the monitor height
DRAG_SECONDS = 0.4  # fast, but not a teleport; an instant drag gets dropped by the UI
DRAG_REPEATS = 3  # dragged windows trail the cursor, so one drag stops short of the corner
LEFT_PAD = 10  # px right of the All button's right edge
RIGHT_PAD = 10  # px right of the autoselect similar button's right edge
TOP_PAD = 10  # px below the autoselect similar button
UNDERCUT_FRACTION = 0.90  # of the suggested price
UNDERCUT_FLAT = 2000  # roubles off the suggested price
PRICE_INPUT_TARGET = 'price_rubles_input'
PLACE_OFFER_TARGET = 'place_offer_button'
MORE_OFFERS_BRIGHTNESS = 190  # max channel in the add offer button: measured 255 lit, 123 greyed
OFFER_SLOT_POLL = 2.0  # seconds between rechecks while every offer slot is full
# Everything belonging to the flea's filter window shares a flea_filters_ prefix, so the
# reference_images listing groups them instead of scattering them through the alphabet.
# filter_by_item is deliberately not one of these: that is the inventory right-click menu.
FILTER_BUTTON_TARGET = 'flea_filters_button'  # opens the flea's filter window
FILTERS_WINDOW_TARGET = 'flea_filters_window_title'  # that window's title bar, for dragging it
CURRENCY_ANY_TARGET = 'flea_filters_currency_dropdown_any'  # currency, while it still says any
CURRENCY_RUBLES_OPTION = 'flea_filters_currency_dropdown_select_rubles'  # roubles, in the opened dropdown
CURRENCY_RUB_TARGET = 'flea_filters_currency_dropdown_rub'  # the dropdown once it reads roubles
OFFERS_FROM_ANY_TARGET = 'flea_filters_offers_from_any'  # offers-from, while it still says any
OFFERS_FROM_PLAYERS_OPTION = 'flea_filters_offers_from_select_players'  # players, in the opened dropdown
REMEMBER_ON_TARGET = 'flea_filters_remember_on'  # the remember-filters box, already ticked
REMEMBER_OFF_TARGET = 'flea_filters_remember_off'  # and the same box unticked
FILTERS_OK_TARGET = 'flea_filters_OK_button'  # applies the filters and closes the window
DROPDOWN_DELAY = 0.3  # seconds for the currency dropdown to unroll
OFFERS_FROM_DELAY = 0.33  # and for the offers-from one
# Goes at one dropdown before giving up on it. More than one because the usual failure is a
# click landing while the list is still unrolling, which the next attempt just repeats past.
DROPDOWN_ATTEMPTS = 3
CHECKMARK_TARGET = 'checkmark'  # the tick beside the autoselect similar button
CHECKMARK_MARGIN = 0.30  # that button's box grows this much per side before we look inside it
MY_OFFERS_TAB_TARGET = 'my_offers_tab_button'  # the flea tab listing what we have up for sale
# The browse tab, split into one folder per state. The tab draws differently depending on
# whether it is the active one, which is the only thing on screen that says which flea page we
# are on, so the two crops are a state read and not just something to click. Clicking it is
# clicking the unselected one: if the selected crop is what matched, we are already there.
BROWSE_SELECTED_TARGET = 'browse_button_selected'  # the browse tab while it is the active tab
BROWSE_UNSELECTED_TARGET = 'browse_button_unselected'  # and the same tab while it is not
TAB_ATTEMPTS = 3  # clicks at a tab before giving up, same reason the dropdowns get more than one
REMOVE_BUTTON_TARGET = 'remove_button'  # cancels one offer; several can be on screen at once
# The column of our own offers, walked top to bottom to expand each row. Fractions of the
# window rather than pixels, measured at 1920x1080: x 250, y 153 down to 380, every 20px.
STALE_X_FRACTION = 250 / 1920
STALE_TOP_FRACTION = 153 / 1080
STALE_BOTTOM_FRACTION = 380 / 1080
STALE_STEP_FRACTION = 20 / 1080
# After clicking a row, before looking for its remove buttons. Its own constant rather than
# the select loop's poll: that one is tuned for fifty cheap retries, and here a search that
# runs early just finds nothing and silently leaves the offer up.
STALE_ROW_DELAY = 1.5
STALE_CONFIRM_DELAY = 0.33  # seconds either side of the y that answers the are-you-sure dialog
STALE_SETTLE = 120  # seconds to let the flea catch up after cancelling, before selling again


def click_all_button(region=None):
    """Click the inventory's 'All' filter button. Returns the clicked (x, y), or None if not found."""
    point = find.find_center('inventory_all_button', region)
    if point:
        pyautogui.click(*point)
    return point


def _region_from(all_btn, similar, sort_btn):
    """The geometry half of infer_inventory_region, split out so it checks without a live screen."""
    left = int(all_btn.left + all_btn.width) + LEFT_PAD
    top = int(similar.top + similar.height) + TOP_PAD
    width = int(similar.left + similar.width) + RIGHT_PAD - left
    height = int(sort_btn.top + sort_btn.height) - top
    if width <= 0 or height <= 0:
        raise LookupError(f'degenerate inventory region {(left, top, width, height)}; did the layout change?')
    return left, top, width, height


def infer_inventory_region(region=None):
    """The inventory grid as (left, top, width, height) in screen coords.

    Derived from the buttons framing it: right of the All button, right of and below the
    autoselect similar button, down to the bottom of auto-sort. Raises LookupError if any
    of those is missing.
    """
    found = {name: find.find(name, region) for name in EDGES}
    missing = [n for n, box in found.items() if box is None]
    if missing:
        raise LookupError(f'cannot infer inventory region, not on screen: {", ".join(missing)}')
    inferred = _region_from(*(found[n] for n in EDGES))
    log(f'inventory grid inferred at {inferred} from {", ".join(EDGES)}', 1)
    return inferred


def find_flea_icon(region=None):
    """The flea market taskbar entry's bbox in whichever state it is in, or None."""
    return find.find(FLEA_ICON_TARGET, region)


def flea_icon_brightness(region=None):
    """Mean channel value of the flea icon, or None if the icon is not on screen.

    The entry inverts when the flea opens: light text on dark becomes dark text on a light
    highlight. That flip is far easier to read than matching two near-identical templates.
    """
    box = find_flea_icon(region)
    if not box:
        return None
    rect = (int(box.left), int(box.top), int(box.width), int(box.height))
    return float(np.asarray(pyautogui.screenshot(region=rect).convert('RGB')).mean())


def grab_price_region(region=None, fractions=PRICE_FRACTIONS):
    """The suggested price readout as (left, top, width, height), scaled off the window size.

    Fixed fractions rather than a template match: the box holds a number that changes every
    time, so there is nothing stable to match against. Scaling keeps it right at any
    resolution as long as the UI keeps its proportions.
    """
    left, top, width, height = region if region else (0, 0) + tuple(pyautogui.size())
    x0, y0, x1, y1 = fractions
    return (left + round(width * x0), top + round(height * y0),
            round(width * (x1 - x0)), round(height * (y1 - y0)))


def get_price(region=None):
    """The suggested price as an int, or None if nothing readable is in the box."""
    crop = grab_price_region(region)
    price = ocr.read_region(crop)
    log(f'read the suggested price box at {crop}: '
        + (f'{price}' if price is not None else 'no glyph matched, unreadable'), 1)
    return price


def undercut_price(price, fraction=UNDERCUT_FRACTION, flat=UNDERCUT_FLAT):
    """What to list at to sit just under the suggested price: the higher of the two cuts.

    Neither rule works alone. The percentage takes a painful bite out of an expensive item,
    the flat cut goes negative on anything cheaper than itself. Taking the higher of the two
    lets the flat cut win on big prices and the percentage win on small ones, so the undercut
    stays modest up top and stays positive down below. They cross at flat / (1 - fraction).
    """
    return max(round(price * fraction), price - flat)


def is_flea_open(region=None, threshold=FLEA_OPEN_BRIGHTNESS):
    """True when the flea market is open. False when closed, or when the icon is missing."""
    brightness = flea_icon_brightness(region)
    return brightness is not None and brightness >= threshold


def open_flea(region=None):
    """Make sure the flea market is open, clicking the taskbar entry if it is not.

    Returns True once it is open, False if the icon is missing or the click did not take.
    """
    brightness = flea_icon_brightness(region)
    if brightness is None:
        log('flea icon not on screen', 1)
        return False
    if brightness >= FLEA_OPEN_BRIGHTNESS:
        log(f'flea icon brightness {brightness:.0f} >= {FLEA_OPEN_BRIGHTNESS}, already open', 1)
        return True
    point = find.find_center(FLEA_ICON_TARGET, region)
    log(f'flea icon brightness {brightness:.0f} < {FLEA_OPEN_BRIGHTNESS}, clicking it at {point}', 1)
    pyautogui.click(*point)
    time.sleep(WINDOW_DELAY)
    opened = is_flea_open(region)
    log(f'flea {"open" if opened else "still shut after the click"}', 1)
    return opened


def add_offer_brightness(region=None):
    """Brightest channel value anywhere in the add offer button, or None if it is not on screen.

    Brightest rather than mean, unlike the flea icon: the button keeps its dark plate in both
    states and only the label and border light up, so an average is mostly background and
    barely moves. The single brightest pixel tracks the label directly.
    """
    box = find.find(ADD_OFFER_TARGET, region)
    if not box:
        return None
    rect = (int(box.left), int(box.top), int(box.width), int(box.height))
    return int(np.asarray(pyautogui.screenshot(region=rect).convert('RGB')).max())


def more_offers_available(region=None, threshold=MORE_OFFERS_BRIGHTNESS):
    """True while the add offer button is lit, ie there is still a free offer slot.

    False when it is greyed out, and false when the button is missing entirely: no button on
    screen is no slot to sell into either way.
    """
    brightness = add_offer_brightness(region)
    if brightness is None:
        log('add offer button not on screen, treating that as no free slot', 1)
        return False
    return brightness >= threshold


def _sleep(seconds, stop=None):
    """time.sleep, but cut short the moment stop is set. True if it was cut short."""
    if stop is None:
        time.sleep(seconds)
        return False
    return stop.wait(seconds)


def wait_for(target, region=None, timeout=SCAV_WINDOW_TIMEOUT, poll=SCAV_WINDOW_POLL):
    """Poll until `target` is on screen. Its Box, or None once timeout runs out.

    A fixed sleep is a guess at the slowest case that is still too short on a slower one.
    This returns the moment the thing is actually there, and only spends the whole timeout
    when it never arrives.
    """
    started = time.monotonic()
    while True:
        box = find.find(target, region)
        if box:
            log(f'{target} up after {time.monotonic() - started:.1f}s at '
                f'({int(box.left)}, {int(box.top)}) {int(box.width)}x{int(box.height)}', 1)
            return box
        if time.monotonic() - started >= timeout:
            log(f'{target} never appeared, gave up after {timeout:.0f}s', 1)
            return None
        time.sleep(poll)


def wait_for_offer_slot(region=None, poll=OFFER_SLOT_POLL, stop=None, timeout=None):
    """Block until the add offer button lights up. Returns the seconds spent waiting.

    A full offer board clears when something sells or expires, so by default there is no
    timeout: waiting is the only useful thing to do. Pass timeout to give up after that many
    seconds anyway, which is what lets the caller go and cancel the offers that never sold.
    Returning is not proof a slot opened, so a caller that passes timeout has to re-check
    more_offers_available itself. Pass a threading.Event as stop to abandon the wait the
    moment that is set; without one only Ctrl+C gets you out.
    """
    started = time.monotonic()
    announced = False
    while not more_offers_available(region):
        if timeout is not None and time.monotonic() - started >= timeout:
            log(f'still no free slot after {timeout / 60:.0f}m of waiting', 1)
            break
        if not announced:  # once, not every poll, or the log is nothing but this
            log(f'add offer button greyed out, every slot is full. Rechecking every '
                f'{poll:.0f}s for up to {timeout / 60:.0f}m'
                if timeout else f'add offer button greyed out, rechecking every {poll:.0f}s', 1)
            announced = True
        if _sleep(poll, stop):  # woken by stop rather than by the timeout
            break  # the caller checks the same flag and unwinds from there
    return time.monotonic() - started


def stale_offer_rows(region=None):
    """Screen (x, y) of every offer row to expand, top to bottom.

    A fixed column of points rather than a template match: the rows are a uniform grid and
    each one has to be clicked to reveal its remove button, so there is nothing to match
    against until after the click.
    """
    left, top, width, height = region or (0, 0, *pyautogui.size())
    x = left + round(width * STALE_X_FRACTION)
    first = top + round(height * STALE_TOP_FRACTION)
    last = top + round(height * STALE_BOTTOM_FRACTION)
    step = max(1, round(height * STALE_STEP_FRACTION))  # a 0 step would be an infinite range
    return [(x, y) for y in range(first, last + 1, step)]


def is_on_browse_page(region=None):
    """True when browse is the active flea tab, False when it is not, None when unreadable.

    Two reads that have to disagree with each other, the way is_item_selected wants three to
    agree: the selected crop present and the unselected one absent, or the other way round.
    Neither matching (or both) is not an answer, it is 'this is not a screen we recognise', so
    that comes back None rather than False. False means we are demonstrably on another tab;
    None means do not act on this read at all.
    """
    selected = find.find(BROWSE_SELECTED_TARGET, region)
    unselected = find.find(BROWSE_UNSELECTED_TARGET, region)
    if bool(selected) == bool(unselected):  # neither state matched, or both did
        log(f'browse tab read: selected={bool(selected)} unselected={bool(unselected)}, so it '
            f'matched neither state or both; cannot tell which page we are on', 1)
        return None
    if selected:
        log(f'browse tab reads selected at ({int(selected.left)}, {int(selected.top)}), '
            f'so we are on the browse page', 1)
        return True
    log(f'browse tab reads unselected at ({int(unselected.left)}, {int(unselected.top)}), '
        f'so we are on some other flea page', 1)
    return False


def _page_name(on_browse):
    """is_on_browse_page's tri-state as words, for the log lines that report where we are."""
    return {True: 'browse', False: 'not browse', None: 'unreadable'}[on_browse]


def return_to_browse(region=None, attempts=TAB_ATTEMPTS):
    """Click the browse tab until the flea reads as being on it. True once it does.

    Clicked in a loop rather than once, because the failure this exists to catch is a click
    that lands while the tab is mid redraw and does nothing. Already on browse is a no-op, not
    a click. An unreadable tab is not treated as a success: leaving the flea on my-offers is
    what makes the next selling pass read a screen full of somebody else's numbers.
    """
    for attempt in range(1, attempts + 1):
        if is_on_browse_page(region):
            log('browse tab confirmed active', 1)
            return True
        point = find.find_center(BROWSE_UNSELECTED_TARGET, region)
        if not point:
            log('browse tab not on screen to click', 1)
            return False
        log(f'attempt {attempt}/{attempts}: clicking the browse tab at {point}', 2)
        pyautogui.click(*point)
        time.sleep(WINDOW_DELAY)
    log(f'browse tab never went active in {attempts} attempts', 1)
    return False


def remove_stale_offers(region=None, stop=None, settle=STALE_SETTLE):
    """Cancel every offer that is still sitting on the my-offers tab, then go back to browse.

    Returns how many remove buttons were clicked, which is what the GUI counts. 0 means
    either a clean board or a tab button that was not on screen; both mean nothing was
    cancelled, so neither is worth distinguishing.

    Bottom up at both levels, the rows and the remove buttons within a row: cancelling an
    offer closes its gap and everything *below* it slides up, so working upwards means every
    point still to be clicked is one the removal could not have moved. Top down, each removal
    invalidates the rest of the sweep. Each removal takes a y to confirm, and until that lands
    the dialog is modal, so the next click would go nowhere.
    """
    log(f'stale offer sweep starting, region {region}, settle {settle:.0f}s')
    log(f'flea page before the tab click: {_page_name(is_on_browse_page(region))}', 1)
    point = find.find_center(MY_OFFERS_TAB_TARGET, region)
    if not point:
        log('no my offers tab on screen, leaving the offers alone', 1)
        return 0
    log(f'opening the my offers tab at {point}, then {WINDOW_DELAY:.1f}s for it to draw', 1)
    pyautogui.click(*point)
    time.sleep(WINDOW_DELAY)
    if is_on_browse_page(region):  # the click missed and browse is still the active tab
        log('still on the browse tab, so that click missed; not walking the rows here', 1)
        return 0  # the rows below are fixed points, and on browse they are somebody else's offers

    removed = 0
    rows = stale_offer_rows(region)
    log(f'on the my offers tab, walking {len(rows)} offer rows from the bottom up, '
        f'{rows[-1]} up to {rows[0]}', 1)
    for index, row in enumerate(reversed(rows), start=1):  # lowest row first, see above
        log(f'row {index}/{len(rows)} at {row}: clicking to expand it', 1)
        pyautogui.click(*row)
        time.sleep(STALE_ROW_DELAY)
        found = find.find_all(REMOVE_BUTTON_TARGET, region)
        log(f'{len(found)} remove buttons on screen after expanding it', 2)
        for box in sorted(found, key=lambda b: b.top, reverse=True):  # and lowest button first
            point = pyautogui.center(box)
            log(f'clicking remove at ({int(point[0])}, {int(point[1])}), then y to confirm', 2)
            pyautogui.click(*point)
            time.sleep(STALE_CONFIRM_DELAY)
            pyautogui.press('y')  # the are-you-sure dialog; nothing is cancelled without it
            time.sleep(STALE_CONFIRM_DELAY)
            removed += 1
            log(f'cancelled, {removed} so far', 2)
        if stop is not None and stop.is_set():
            log('stop asked for mid sweep, backing out', 2)
            break  # mid sweep, the caller unwinds; the tab click below still runs

    log(f'removed {removed} stale offers, settling for {settle:.0f}s', 1)
    _sleep(settle, stop)
    log('settled, heading back to the browse tab', 1)
    if not return_to_browse(region):
        log('could not get back to the browse tab; the next pass will be reading my-offers', 1)
    log(f'sweep done, {removed} offers cancelled, flea page now '
        f'{_page_name(is_on_browse_page(region))}')
    return removed


def click_add_offer(region=None):
    """Click the add offer button. Returns the clicked (x, y), or None if not found."""
    point = find.find_center(ADD_OFFER_TARGET, region)
    log(f'clicking add offer at {point}' if point else 'no add offer button on screen', 1)
    if point:
        pyautogui.click(*point)
    return point


def enter_price(value, region=None):
    """Click the roubles field and type value into it. Returns the clicked (x, y), or None.

    Select all first: the field arrives holding the suggested price, and typing into it
    without clearing appends, which turns 99000 into something like 10000099000.
    """
    point = find.find_center(PRICE_INPUT_TARGET, region)
    if not point:
        log('no roubles price field on screen', 1)
        return None
    log(f'typing {value} into the roubles field at {point}', 1)
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(str(value))
    return point


def click_place_offer(region=None):
    """Click the place offer button. Returns the clicked (x, y), or None if not found."""
    point = find.find_center(PLACE_OFFER_TARGET, region)
    log(f'clicking place offer at {point}' if point else 'no place offer button on screen', 1)
    if point:
        pyautogui.click(*point)
    return point


def is_item_selected(region=None):
    """True only when all three reads agree that something is really selected.

    Absence of the placeholder used to be the whole answer, which made every failed match read
    as a hit: a hover highlight or a mid-animation frame is indistinguishable from a real
    selection, and a pass that believed one went on to price an item that was never picked.
    Three independent targets now have to fail the same way at the same moment to fool this:
    the currency rows and the place offer button both present, the placeholder absent.

    Ordered cheapest-to-be-wrong first, and short-circuiting, so a miss usually costs one
    template scan instead of three. Most attempts are misses; they land between items.
    """
    return (find.find(SELECTION_TARGET, region) is not None
            and find.find(PLACE_OFFER_TARGET, region) is not None
            and find.find(NO_SELECTION_TARGET, region) is None)


def _crop_to(ltrb, size):
    """An expanded (left, top, right, bottom) clipped to a screen, as (left, top, width, height)."""
    left, top, right, bottom = ltrb
    return (max(0, left), max(0, top),
            min(size[0], right) - max(0, left), min(size[1], bottom) - max(0, top))


def autoselect_similar_region(region=None, margin=CHECKMARK_MARGIN):
    """The autoselect similar button's box grown by margin per side, as (left, top, width, height).

    Raises LookupError if the button is not on screen, which means the screen is not the one
    we think it is, not that the box is empty.
    """
    box = find.find('autoselect_similar', region)
    if not box:
        raise LookupError('autoselect similar button not on screen')
    return _crop_to(_expand(box, margin), pyautogui.size())  # the grown box can run off an edge


def is_autoselect_similar_ticked(region=None, margin=CHECKMARK_MARGIN):
    """True when the checkmark is showing beside the autoselect similar button.

    The tick sits just outside the button's own artwork, hence the widened crop: search the
    whole screen for a checkmark and you find every other one in the UI.
    """
    return find.find(CHECKMARK_TARGET, autoselect_similar_region(region, margin)) is not None


def disable_autoselect_similar(region=None):
    """Untick autoselect similar if it is ticked. Returns True once it is off.

    Left on, picking one item pulls in every matching one, so the offer is not the single
    item the price was read for. Already off is a no-op, not a click, because clicking it
    then would switch it on.
    """
    if not is_autoselect_similar_ticked(region):
        log('autoselect similar already off', 1)
        return True
    point = find.find_center('autoselect_similar', region)
    if not point:
        log('autoselect similar is ticked but its button vanished', 1)
        return False
    log(f'autoselect similar is ticked, unticking it at {point}', 1)
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    off = not is_autoselect_similar_ticked(region)  # confirm the click took, do not assume
    log(f'autoselect similar now {"off" if off else "STILL ON, the click did not take"}', 1)
    return off


def _scav_region_from(title, close_btn, screen_height):
    """The geometry half of infer_scav_case_region, split out so it checks without a live screen."""
    left = int(title.left)
    top = int(title.top + title.height) + SCAV_TOP_PAD
    width = int(close_btn.left + close_btn.width) - left
    height = round(screen_height * SCAV_HEIGHT_FRACTION)
    if width <= 0 or height <= 0:
        raise LookupError(f'degenerate scav case region {(left, top, width, height)}')
    return left, top, width, height


def infer_scav_case_region(region=None):
    """The opened scav case grid as (left, top, width, height) in screen coords.

    Runs from the title bar's left edge to the right edge of the *leftmost* close button;
    there is a second close button further right belonging to another window, and taking it
    would swallow half the screen. Raises LookupError if either piece is missing.
    """
    title = find.find(SCAV_WINDOW_TARGET, region)
    closes = find.find_all(CLOSE_BUTTON_TARGET, region)
    missing = ([SCAV_WINDOW_TARGET] if not title else []) + ([CLOSE_BUTTON_TARGET] if not closes else [])
    if missing:
        raise LookupError(f'cannot infer scav case region, not on screen: {", ".join(missing)}')
    screen_height = region[3] if region else pyautogui.size()[1]
    inferred = _scav_region_from(title, min(closes, key=lambda b: b.left), screen_height)
    log(f'scav case grid inferred at {inferred} from the title bar and '
        f'the leftmost of {len(closes)} close buttons', 1)
    return inferred


def _expand(box, margin=SCAV_MARGIN):
    """Grow a Box by margin of its own size on each side, as (left, top, right, bottom)."""
    dx, dy = round(box.width * margin), round(box.height * margin)
    return (int(box.left) - dx, int(box.top) - dy,
            int(box.left + box.width) + dx, int(box.top + box.height) + dy)


def scav_case_regions(region=None, margin=SCAV_MARGIN):
    """(left, top, right, bottom) of every scav case on screen, each grown by margin. [] if none."""
    return [_expand(box, margin) for box in find.find_all('scav_case', region)]


def _pack(rgb):
    """Squash the last axis of an RGB array into one int per pixel, so colours compare as scalars."""
    rgb = np.asarray(rgb).astype(np.uint32)
    return (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def _load_dead_colours(name=DEAD_REFERENCE):
    """Every distinct colour across every reference image of empty slots, packed and sorted.

    Transparent pixels are skipped, so a screenshot can be masked down to just its empty slots.
    """
    seen = []
    for path in find.images(name):
        pixels = np.asarray(Image.open(path).convert('RGBA')).reshape(-1, 4)
        seen.append(_pack(pixels[pixels[:, 3] > 0][:, :3]))
    return np.unique(np.concatenate(seen))


def _dead_cube(colours, tol=DEAD_TOL):
    """A 256^3 lookup, True for any colour within tol of a known one on every channel.

    ponytail: 16MB of bools built once at import, so the per-pixel test is a plain array
    index. Widening every known colour beats comparing 500k pixels against 1500 colours.
    """
    cube = np.zeros((256, 256, 256), dtype=bool)
    rgb = np.stack([(colours >> 16) & 255, (colours >> 8) & 255, colours & 255], axis=1)
    span = range(-tol, tol + 1)
    offsets = np.array([(r, g, b) for r in span for g in span for b in span], dtype=np.int16)
    near = np.clip(rgb[:, None, :].astype(np.int16) + offsets, 0, 255).reshape(-1, 3)
    cube[near[:, 0], near[:, 1], near[:, 2]] = True
    return cube


DEAD_COLOURS = _load_dead_colours()
DEAD_CUBE = _dead_cube(DEAD_COLOURS)


def calculate_dead_pixel(pixel, cube=None):
    """True where the colour is within DEAD_TOL of one an empty slot takes.

    Takes one (r, g, b) or a whole HxWx3 array. Not a brightness threshold: a dark blue is
    dark but is nowhere near a slot colour, so it stays alive.
    """
    rgb = np.asarray(pixel)
    lookup = DEAD_CUBE if cube is None else cube
    return lookup[rgb[..., 0], rgb[..., 1], rgb[..., 2]]


def _live_mask(pixels, origin, exclude=()):
    """Bool HxW: True where a pixel is not dead and not inside an excluded rect.

    exclude: (left, top, right, bottom) rects in screen coords; origin is the crop's top-left.
    """
    mask = ~calculate_dead_pixel(pixels)
    for left, top, right, bottom in exclude:  # clamped, a rect may hang off the crop
        mask[max(0, top - origin[1]):max(0, bottom - origin[1]),
             max(0, left - origin[0]):max(0, right - origin[0])] = False
    return mask


def _live_points(pixels, origin, exclude=()):
    """Screen coords of every pixel in an HxWx3 array that isn't dead."""
    ys, xs = np.nonzero(_live_mask(pixels, origin, exclude))
    return list(zip((xs + origin[0]).tolist(), (ys + origin[1]).tolist()))


def _pixels_in(rect, exclude=()):
    """Screen (x, y) of every live pixel inside rect, itself a (left, top, width, height)."""
    shot = np.asarray(pyautogui.screenshot(region=rect).convert('RGB'))
    ys, xs = np.nonzero(_live_mask(shot, rect[:2], exclude))
    return list(zip((xs + rect[0]).tolist(), (ys + rect[1]).tolist()))


def find_sell_pixels(region=None):
    """Screen (x, y) of every pixel inside the inventory region that isn't an empty slot.

    Pixels inside a scav case (grown by SCAV_MARGIN) are dropped, since those items
    are not ours to sell. Handles any number of cases.

    ponytail: returns raw pixels; grouping them into clickable items is still open,
    see docs/pixel_clustering_ideas.md.
    """
    inventory = infer_inventory_region(region)
    return _pixels_in(inventory, scav_case_regions(inventory))


def find_scav_case_pixels(region=None):
    """Screen (x, y) of every pixel in the open scav case that isn't an empty slot.

    No scav exclusion here: inside the case, those items are the point.
    """
    return _pixels_in(infer_scav_case_region(region))


def select_item_from_inventory(region=None, attempts=SELECT_ATTEMPTS):
    """Grab a random item from the inventory screen and filter by it on the flea.

    Left-clicks a random sellable pixel and asks the offer panel whether that actually
    selected anything. A live pixel is not always a clickable item (icon overhang, a tooltip,
    a stack counter), so a miss just means try again somewhere else: the pixels are re-found
    and a new one drawn each attempt. Only once something is selected does it bother with the
    right-click menu and 'filter by item'. Returns the clicked (x, y), or None if every
    attempt missed.

    Checking the cheap thing first is the point: a miss now costs one left click instead of a
    right click, a menu wait and a menu search.

    ponytail: re-screenshots per attempt as asked, so each retry costs a fraction of a second.
    """
    for attempt in range(1, attempts + 1):
        points = find_sell_pixels(region)
        if not points:
            log('no sellable pixels in the inventory, the stash looks empty', 1)
            return None  # nothing to sell, retrying will not conjure an item
        chosen = random.choice(points)
        log(f'attempt {attempt}/{attempts}: {len(points)} live pixels, clicking {chosen}', 2)
        pyautogui.click(*chosen)
        time.sleep(SELECT_POLL_DELAY)
        if not is_item_selected(region):
            # Get the pointer off the grid before the next attempt re-reads the screen. A click
            # leaves it where it landed, and one resting in the top rows puts a hover state or a
            # tooltip over the buttons the region is inferred from, which sit just above the
            # grid. No reference image has a cursor under it, so the match fails at 0.9 and the
            # infer raises. A hit never hit this: it right clicks and moves to the menu, which
            # takes the pointer away on its own.
            _park_cursor()
            log('nothing selected, that was a gap between items', 2)
            continue  # landed on a gap, the placeholder is still showing
        log('item selected, right clicking for the menu', 2)
        pyautogui.rightClick(*chosen)
        time.sleep(MENU_DELAY)  # the menu's own draw time, not the shorter poll wait
        box = find.find('filter_by_item', region)
        if not box:
            log('no filter by item in the menu, escaping out', 2)
            pyautogui.press('esc')  # shut whatever did open, or the next find hits a stale menu
            continue
        point = pyautogui.center(box)
        log(f'clicking filter by item at {point}', 2)
        pyautogui.click(*point)
        time.sleep(SELECT_WINDOW_DELAY)  # the flea panel has to catch up before we read it
        return point
    log(f'all {attempts} attempts missed', 1)
    return None


def _park_cursor():
    """Move the pointer to the middle of the screen and return where it went.

    Somewhere it cannot hover a button we are about to look for. Mid screen rather than a
    corner because every corner is one of pyautogui's panic points.
    """
    width, height = pyautogui.size()
    point = (width // 2, height // 2)
    pyautogui.moveTo(*point)
    return point


def _corner_point(corner, size):
    """Where a named corner sits on a screen of (width, height).

    The bottom row is height - 1: height itself is one past the last pixel and the drag would
    land off screen.
    """
    width, height = size
    try:
        return {'top left': (0, 0), 'bottom left': (0, height - 1)}[corner]
    except KeyError:
        raise ValueError(f"unknown corner {corner!r}, want 'top left' or 'bottom left'") from None


def _drag_to_corner(target, corner='top left', region=None, duration=DRAG_SECONDS,
                    repeats=DRAG_REPEATS):
    """Grab the centre of target's bbox and drag it into a corner. Last point grabbed, or None.

    Dragged repeats times over: the window trails the cursor, so one pass stops short and each
    following pass re-finds it wherever it settled. Stops early if it goes missing, which is
    also how a single failed find still returns None.

    Parks the cursor mid screen afterwards. Every screen corner is one of pyautogui's panic
    points, so the fail-safe comes off for the drag and only goes back on once the cursor is
    clear of it. Leaving it parked in a corner trips the next call instead, which is a crash
    a long way from its cause.
    """
    width, height = pyautogui.size()
    destination = _corner_point(corner, (width, height))
    grabbed = None
    failsafe = pyautogui.FAILSAFE
    pyautogui.FAILSAFE = False
    try:
        for _ in range(repeats):
            point = find.find_center(target, region)
            if not point:
                break
            grabbed = point
            pyautogui.moveTo(*point)
            pyautogui.dragTo(*destination, duration=duration, button='left')
        pyautogui.moveTo(width // 2, height // 2)  # must happen before the fail-safe is back on
    finally:
        pyautogui.FAILSAFE = failsafe
    return grabbed


def orientate_offer_creation(region=None, duration=DRAG_SECONDS, repeats=DRAG_REPEATS):
    """Drag the offer creation window to the bottom left of the monitor, into a known place.

    Grabs it by the centre of its bbox, repeats times over like the scav box. Returns the last
    point it grabbed, or None if not found.
    """
    point = _drag_to_corner(OFFER_TARGET, 'bottom left', region, duration, repeats)
    log(f'dragged the offer window to the bottom left by {point}' if point
        else 'offer creation window not on screen to drag', 1)
    return point


def _dropdown_arrow(box):
    """Middle of a box's right edge, where a dropdown's arrow sits. Inside it, not one past."""
    return int(box.left + box.width) - 1, int(box.top + box.height // 2)


def _set_dropdown(any_target, option_target, settled_target, region=None, delay=DROPDOWN_DELAY):
    """Get a dropdown off 'any' and onto its setting, and only return once that is seen.

    Nothing here trusts a click. The old version returned True the moment it had clicked the
    option, and treated a missing any_target as 'already set to something', so a dropdown
    still reading Any because its reference image simply did not match came back as
    configured. That is silent: the run browses the wrong offers for the rest of the session
    and the log says the filter was applied.

    Every attempt now ends by re-reading the closed dropdown. Only settled_target present with
    any_target gone counts as done; anything else is retried, because the usual cause is a
    click that landed while the list was still unrolling.

    Returns True once the dropdown is read as settled, False if it never is.
    """
    for attempt in range(1, DROPDOWN_ATTEMPTS + 1):
        settled = find.find(settled_target, region)
        any_box = find.find(any_target, region)
        if settled and not any_box:
            log(f'{settled_target} confirmed on screen, the dropdown is set', 1)
            return True
        if settled and any_box:  # both at once means one of the two reference sets is too loose
            log(f'ambiguous read: {any_target} and {settled_target} both matched', 1)
            return False
        if not any_box:
            # Neither state matched, so there is no arrow to click and nothing to confirm.
            # Calling this success is the exact bug this rewrite exists for.
            log(f'dropdown matched neither {any_target} nor {settled_target}, so its state is '
                f'unknown; not assuming it is set. Add reference crops for whichever it reads', 1)
            return False
        log(f'attempt {attempt}/{DROPDOWN_ATTEMPTS}: {any_target} still reads any, opening it', 2)
        pyautogui.click(*_dropdown_arrow(any_box))
        time.sleep(delay)
        point = find.find_center(option_target, region)
        if not point:
            log(f'{option_target} not in the opened {any_target} dropdown', 2)
            pyautogui.press('esc')  # shut the list, or the next attempt clicks inside it
            time.sleep(MENU_DELAY)
            continue
        log(f'picking {option_target} at {point}', 2)
        pyautogui.click(*point)
        time.sleep(MENU_DELAY)  # let it close before the top of the loop reads it back
    log(f'{any_target} never settled on {settled_target} in {DROPDOWN_ATTEMPTS} attempts', 1)
    return False


def apply_flea_filters(region=None):
    """Open the flea's filter window, tick remember, set roubles and players only, then OK out.

    Returns True once everything reads the right thing and the window is closed. Nothing that
    is already set gets clicked: the dropdowns are only touched while they still say 'any',
    and the remember box only while it is off, so running this against an already filtered
    board opens the window and OKs straight back out rather than undoing the settings.
    """
    point = find.find_center(FILTER_BUTTON_TARGET, region)
    if not point:
        log('no filter button on screen', 1)
        return False
    log(f'opening the filter window at {point}', 1)
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)

    # Off, or the window never opened at all: either way the 'off' image has to be there next
    if not find.find(REMEMBER_ON_TARGET, region):
        toggle = find.find_center(REMEMBER_OFF_TARGET, region)
        if not toggle:
            log('remember selected filters checkbox not on screen, did the window open?', 1)
            return False
        log(f'ticking remember selected filters at {toggle}', 1)
        pyautogui.click(*toggle)
        time.sleep(MENU_DELAY)
        if not find.find(REMEMBER_ON_TARGET, region):  # confirm the click took, same as the dropdowns
            log('remember selected filters STILL OFF, the click did not take', 1)
            return False
        log('remember selected filters now ticked', 1)
    else:
        log('remember selected filters already ticked', 1)

    # The confirm-it-took read used to live here, for the currency dropdown only. It is inside
    # _set_dropdown now, so offers-from gets the same treatment instead of being taken on trust.
    if not _set_dropdown(CURRENCY_ANY_TARGET, CURRENCY_RUBLES_OPTION, CURRENCY_RUB_TARGET,
                         region, DROPDOWN_DELAY):
        return False

    # Settled state and menu option read out of the same folder, unlike currency, which has a
    # separate flea_filters_currency_dropdown_rub. find() tries every png in a folder, so crops of the open
    # list row and of the closed field can sit side by side there and either one matching means
    # the dropdown says players.
    if not _set_dropdown(OFFERS_FROM_ANY_TARGET, OFFERS_FROM_PLAYERS_OPTION,
                         OFFERS_FROM_PLAYERS_OPTION, region, OFFERS_FROM_DELAY):
        return False

    point = find.find_center(FILTERS_OK_TARGET, region)  # applies them and shuts the window
    if not point:
        log('no OK button on the flea filter window', 1)
        return False
    log(f'OK out of the filter window at {point}', 1)
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    return True


def orientate_scav_box(region=None, duration=DRAG_SECONDS, repeats=DRAG_REPEATS):
    """Drag the opened scav case window to the top left of the monitor, by its title bar.

    Returns the last point it grabbed, or None if the title bar was never found.
    """
    return _drag_to_corner(SCAV_WINDOW_TARGET, 'top left', region, duration, repeats)


def open_scav_case(region=None):
    """Right-click a random scav case and choose open from the menu that appears.

    Returns the clicked (x, y) of the open entry, or None if there was no case on screen
    or the menu never showed up.

    The window is waited for rather than slept through. A flat WINDOW_DELAY used to land
    before the case had finished loading, so orientate_scav_box found no title bar to grab,
    infer_scav_case_region then had nothing to measure from, and the pass fell back to the
    stash reporting a case that was on screen the whole time, just late.
    """
    cases = find.find_all('scav_case', region)
    log(f'scav cases on screen: {len(cases)}', 1)
    if not cases:
        return None
    case = pyautogui.center(random.choice(cases))
    log(f'right click a scav case at {case}', 1)
    pyautogui.rightClick(*case)
    time.sleep(MENU_DELAY)
    box = find.find('open_scav_case', region)
    if not box:
        log('no open entry in the right click menu', 1)
        return None
    point = pyautogui.center(box)
    log(f'click open at {point}, waiting up to {SCAV_WINDOW_TIMEOUT:.0f}s for the window', 1)
    pyautogui.click(*point)
    if wait_for(SCAV_WINDOW_TARGET, region) is None:
        # Still the clicked point, not None: the caller uses a truthy return to decide how
        # many escapes it takes to back out, and a window that appears a moment after we
        # stopped looking still has to be escaped past.
        return point
    grabbed = orientate_scav_box(region)
    log(f'dragged the scav window to the top left by {grabbed}' if grabbed
        else 'scav window up but its title bar would not grab', 1)
    return point


def select_item_from_random_scav_case(region=None, attempts=SELECT_ATTEMPTS):
    """Grab a random item from the open scav case and filter by it on the flea.

    Assumes the case is already open and orientated. Same flow as
    select_item_from_inventory, just over the scav case grid instead of the stash: left click,
    ask the offer panel whether anything got selected, and only then go for the right-click
    menu. Returns the clicked (x, y), or None if every attempt missed.
    """
    for attempt in range(1, attempts + 1):
        points = find_scav_case_pixels(region)
        if not points:
            log('no live pixels in the scav case, it is empty', 1)
            return None  # an empty case will not fill itself on a retry
        chosen = random.choice(points)
        log(f'attempt {attempt}/{attempts}: {len(points)} live pixels, clicking {chosen}', 2)
        pyautogui.click(*chosen)
        time.sleep(SELECT_POLL_DELAY)
        if not is_item_selected(region):
            # Get the pointer off the grid before the next attempt re-reads the screen. A click
            # leaves it where it landed, and one resting in the top rows puts a hover state or a
            # tooltip over the buttons the region is inferred from, which sit just above the
            # grid. No reference image has a cursor under it, so the match fails at 0.9 and the
            # infer raises. A hit never hit this: it right clicks and moves to the menu, which
            # takes the pointer away on its own.
            _park_cursor()
            log('nothing selected, that was a gap between items', 2)
            continue  # landed on a gap, the placeholder is still showing
        log('item selected, right clicking for the menu', 2)
        pyautogui.rightClick(*chosen)
        time.sleep(MENU_DELAY)  # the menu's own draw time, not the shorter poll wait
        box = find.find('filter_by_item', region)
        if not box:
            log('no filter by item in the menu, escaping out', 2)
            pyautogui.press('esc')  # same as the inventory path: a left open menu eats the next click
            continue
        point = pyautogui.center(box)
        log(f'clicking filter by item at {point}', 2)
        pyautogui.click(*point)
        time.sleep(SELECT_WINDOW_DELAY)  # the flea panel has to catch up before we read it
        return point
    log(f'all {attempts} attempts missed', 1)
    return None


if __name__ == '__main__':  # the geometry, checked without needing Tarkov open
    from pyscreeze import Box
    assert _region_from(Box(1232, 82, 26, 24), Box(1600, 60, 20, 20), Box(1200, 900, 30, 20)) == (1268, 90, 362, 830)
    try:  # autoselect similar left of the grid's left edge would invert it
        _region_from(Box(1232, 82, 26, 24), Box(100, 60, 20, 20), Box(1200, 900, 30, 20))
        raise AssertionError('expected LookupError')
    except LookupError:
        pass

    assert len(DEAD_COLOURS) > 100, f'{DEAD_REFERENCE}/ gave only {len(DEAD_COLOURS)} colours'
    one = _dead_cube(np.array([_pack(np.array([100, 100, 100]))]), tol=5)  # tolerance, on its own
    assert one[100, 100, 100] and one[105, 100, 95], 'within 5 on every channel is dead'
    assert not one[106, 100, 100], '6 off on any channel is alive'
    assert calculate_dead_pixel((23, 24, 24)) and not calculate_dead_pixel((200, 0, 0))
    img = np.full((3, 4, 3), (23, 24, 24), dtype=np.uint8)  # 3 rows, 4 cols of empty slot
    img[0, 0] = (24, 25, 25)  # another slot colour, still empty
    img[1, 2] = (200, 0, 0)  # an item, at row 1 col 2
    img[2, 3] = (0, 200, 0)  # another item, at row 2 col 3
    assert _live_points(img, (100, 200)) == [(102, 201), (103, 202)], 'x/y swapped?'
    assert _live_points(img, (100, 200), exclude=[(102, 201, 103, 202)]) == [(103, 202)]
    assert _live_points(img, (100, 200), exclude=[(0, 0, 50, 50)]) == [(102, 201), (103, 202)]  # off the crop
    assert _expand(Box(100, 200, 20, 40), 0.10) == (98, 196, 122, 244)
    assert _crop_to((98, 196, 122, 244), (1920, 1080)) == (98, 196, 24, 48)  # well inside the screen
    assert _crop_to((-6, -4, 30, 40), (1920, 1080)) == (0, 0, 30, 40)  # grown off the top left
    assert _crop_to((1900, 1060, 1950, 1100), (1920, 1080)) == (1900, 1060, 20, 20)  # off the bottom right
    assert _dropdown_arrow(Box(100, 200, 20, 40)) == (119, 220), 'right edge, vertical middle'
    assert _corner_point('top left', (1920, 1080)) == (0, 0)
    assert _corner_point('bottom left', (1920, 1080)) == (0, 1079), 'last row, not one past it'
    try:
        _corner_point('middle', (1920, 1080))
        raise AssertionError('expected ValueError')
    except ValueError:
        pass

    # Derived from the constants, not hardcoded, so retuning the undercut does not break this
    crossover = UNDERCUT_FLAT / (1 - UNDERCUT_FRACTION)  # the price where both rules agree
    cheap, dear = round(crossover / 2), round(crossover * 2)
    assert undercut_price(cheap) == round(cheap * UNDERCUT_FRACTION), 'below it the percentage wins'
    assert undercut_price(dear) == dear - UNDERCUT_FLAT, 'above it the flat cut wins'
    assert undercut_price(1) == 1, 'never negative, never free'

    assert grab_price_region((0, 0, 1920, 1080)) == (1339, 147, 159, 39)  # where it was measured
    assert grab_price_region((0, 0, 3840, 2160)) == (2678, 294, 318, 78)  # scales with the window

    rows = stale_offer_rows((0, 0, 1920, 1080))  # where the column was measured
    assert rows[0] == (250, 153) and rows[-1] == (250, 373), rows[:1] + rows[-1:]
    assert rows[1][1] - rows[0][1] == 20, 'the 20px step'
    assert all(x == 250 for x, _ in rows), 'one fixed column'
    big = stale_offer_rows((0, 0, 3840, 2160))
    assert big[0] == (500, 306) and len(big) == len(rows), 'scales, same number of rows'
    assert stale_offer_rows((100, 40, 1920, 1080))[0] == (350, 193), 'offset by the window origin'
    assert _scav_region_from(Box(100, 50, 200, 20), Box(500, 50, 20, 20), 1080) == (100, 75, 420, 875)
    try:  # a close button left of the title would invert it
        _scav_region_from(Box(100, 50, 200, 20), Box(10, 50, 20, 20), 1080)
        raise AssertionError('expected LookupError')
    except LookupError:
        pass
    print('ok')
