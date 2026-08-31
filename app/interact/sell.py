"""
This module is for selling items on the flea market.

Geometry self-check:  python -m interact.sell
"""
import random
import time
from collections import namedtuple
from collections import namedtuple

import numpy as np
import pyautogui
from PIL import Image

import screen
from interact import find, ocr
from narrate import log

ALL_BUTTON_TARGET = 'inventory_all_button'  # the ALL tab over the inventory grid
AUTOSELECT_TARGET = 'autoselect_similar'  # the autoselect similar checkbox, on the offer window
# The buttons framing the inventory grid: (left edge, right and top edge, bottom edge)
EDGES = (ALL_BUTTON_TARGET, AUTOSELECT_TARGET, 'auto_sort')
SCAV_MARGIN = 0.15  # scav case boxes grow this much per side before their pixels are dropped
# Every color an empty slot is known to take, read off screenshots showing nothing but empty
# slots. Drop another png in that folder to teach it more. ponytail: the images are the list.
DEAD_REFERENCE = 'dead_pixels'  # a folder under reference_images/, any number of pngs
DEAD_TOL = 5  # per-channel slack; this close to a known slot color still counts as empty
MENU_DELAY = 0.3  # seconds for the right-click menu to draw before we go looking for it
WINDOW_DELAY = 1.0  # seconds for a window to finish appearing before we grab its title bar
# The scav case window is the one thing on screen that does not draw within WINDOW_DELAY: it
# loads its contents from the server, which took 2-4s every time it was measured. Waited for
# rather than slept through, so a fast open costs a poll and a slow one still works.
SCAV_WINDOW_TIMEOUT = 10.0  # seconds the scav case window gets to appear before we give up
# Seconds the filter window gets. Shorter than the scav case's: that one waits on the game
# loading a container, this one on a panel that is either drawn straight away or blocked.
FILTERS_WINDOW_TIMEOUT = 3.0
SCAV_WINDOW_POLL = 0.25  # seconds between rechecks while waiting for it
# Clicks to try before admitting we cannot land on an item. Was 50, which took a minute or two
# to burn through at roughly 1.5s a miss, all of it clicking gaps in a grid the pass had already
# read once. Ten misses is enough to say this screen is not giving up an item; starting a fresh
# pass re-reads the inventory region and costs less than the forty attempts it replaces.
SELECT_ATTEMPTS = 10
# After a left click, before asking the offer panel what it did. Was MENU_DELAY / 2, which
# was under the panel's own redraw: the read landed on the *previous* attempt's panel, so a
# hit read as a miss (click on, one slot later) and a miss read as a hit (right click a gap,
# no filter by item, esc). Both of those look like the bot flailing. Nothing on screen says
# when the panel is done, so this is measured slack, not a signal.
SELECT_POLL_DELAY = 0.5  # after a click, before reading what it did
SELECT_WINDOW_DELAY = WINDOW_DELAY / 2  # after filter by item, for the flea panel to catch up
ADD_OFFER_TARGET = 'add_offer'  # the button that opens the offer creation window
OFFER_TARGET = 'offer_creation_window_title'  # that window's title bar, for dragging and for
# spotting one left open. Named to match scav_case_window_title and flea_filters/window_title:
# the three things recovery escapes are all matched on their title bars, for the same reason.
SCAV_WINDOW_TARGET = 'scav_case_window_title'  # reference images for the opened scav case window
CLOSE_BUTTON_TARGET = 'close_window_button'  # several are on screen at once, we want the leftmost
NO_SELECTION_TARGET = 'no_items_selected'  # the placeholder shown while nothing is picked
SELECTION_TARGET = 'item_is_selected'  # the panel shown once something is, the other half of the read
FLEA_ICON_TARGET = 'flea_icon'  # the taskbar entry, one folder holding both its states
# The one pause recovery uses, everywhere: after the click that focuses a window, after the
# escape that closes it, and between rounds of the loop in sell_bot._recover. One number rather
# than a long one for closing and a short one for looking, because the two were never actually
# doing different jobs and two knobs only meant two places to get it wrong.
RECOVER_DELAY = 0.33
# Clicks land a few pixels off the centre of whatever matched, so a session is not a column of
# identical coordinates. Small on purpose: these are a nudge inside a button, not an attempt to
# cover it. Per control, because the smallest of them is a 30x26 gear.
CLICK_JITTER = 3  # px each way, for anything button sized
GEAR_JITTER = 2  # the flea filter gear, small enough to want less
FLEA_OPEN_BRIGHTNESS = 90  # mean channel value: measured 57 closed, 117 open
# How long to let the flea come up after the taskbar entry is clicked, and how often to look.
# Polled rather than slept through, for the reason wait_for exists: WINDOW_DELAY's flat 1.0s is
# a guess at the slowest case, and it was measured opening the flea from the stash.
#
# Opening it from a hideout station is much slower, because the game has to leave the 3D room
# first. Measured on 2026-08-31 with the water collector panel up: the entry reads 63.7 with the
# flea shut, 73.1 one second after the click while the screen is still changing, and 118.6 once
# it has actually opened, about four seconds in. So the old wait read the middle number, called
# the flea shut, and craft.buy_water_filter raised Blind over a flea that was opening normally.
# The threshold itself was never the problem: 63.7 against 118.6 straddles 90 on the hideout's
# lit background just as well as 57 against 117 does on the stash's dark one.
FLEA_OPEN_TIMEOUT = 12.0  # seconds before giving up on the click having taken
FLEA_OPEN_POLL = 0.4  # seconds between reads; each read parks the cursor and matches the entry
# The suggested price readout, as (left, top, right, bottom) fractions of the window.
# Measured at 1920x1080: left 1339, top 147, right 1498, bottom 186.
PRICE_FRACTIONS = (1339 / 1920, 147 / 1080, 1498 / 1920, 186 / 1080)
# The topmost offer row on the flea board, same (left, top, right, bottom) fractions.
# Measured at 2560x1440: left 1109, top 190, right 1774, bottom 284, window relative. Read off
# the viewer's screen coords (3029/3694) with the game on a monitor starting at x 1920.
FIRST_OFFER_FRACTIONS = (1109 / 2560, 190 / 1440, 1774 / 2560, 284 / 1440)
# The asking price on that same row, cut narrow enough to hold the number and the currency glyph
# beside it and nothing from the row either side. Same (left, top, right, bottom) fractions and
# the same scaling, measured on the same 2560x1440 window: left 1778, top 191, right 2004,
# bottom 284. A region of its own rather than a slice of FIRST_OFFER_FRACTIONS, because that one
# is framed around the offer's title for first_offer_is_a_pack and moving either edge of it to
# suit a price read would break the pack check that has to keep working.
FIRST_ITEM_PRICE_FRACTIONS = (1778 / 2560, 191 / 1440, 2004 / 2560, 284 / 1440)
SCAV_TOP_PAD = 5  # px below the scav window title before its grid starts
SCAV_HEIGHT_FRACTION = 0.81  # of the monitor height
OFFER_CORNER = 'bottom left'  # where orientate_offer_creation parks the window by default
SCAV_CORNER = 'top left'  # and where orientate_scav_box parks its window, above and beside it
FILTERS_CORNER = 'top left'  # where orientate_filters_window parks the flea's filter window
# Where those two go while the flea filter window is open. The filter window is drawn over the
# left of the board, which is exactly where the pair sit for the rest of a pass, so the gear and
# every control inside it would be under them. The offer window goes to the opposite corner and
# the scav case follows it across, then both come back afterwards.
FILTERING_OFFER_CORNER = 'bottom right'
FILTERING_SCAV_CORNER = 'top right'
DRAG_SECONDS = 0.4  # fast, but not a teleport; an instant drag gets dropped by the UI
DRAG_REPEATS = 3  # dragged windows trail the cursor, so one drag stops short of the corner
# These two are slow on purpose and were tried faster on 2026-08-22: 0.2s drags, pyautogui's
# between-call pause halved for the trip, and passes cut short once a window stopped moving or
# came within 80px of the corner. It worked out at 54% off the drag time and was reverted whole,
# because landing a window beats landing it quickly. Do not shave them again without a run that
# shows the windows still arriving.
LEFT_PAD = 30  # px right of the All button's right edge, and so the grid's left edge. Was 20
# px right of the autoselect similar button's right edge, which is also the grid's right edge.
# Was 10, then 0, now -30: negative pulls that edge back inside the grid, short of the button.
# Only this edge moves. The left edge and the two pads above are not affected.
RIGHT_PAD = -30
TOP_PAD = 30  # px below the autoselect similar button, and so the grid's top edge. Was 20
# px below auto-sort's bottom edge, and so the grid's bottom edge. Negative like RIGHT_PAD, and
# for the same reason: it lifts that edge back up inside the grid, clear of the button's row.
BOTTOM_PAD = -10
UNDERCUT_FRACTION = 0.90  # of the suggested price
UNDERCUT_FLAT = 2000  # roubles off the suggested price
PRICE_INPUT_TARGET = 'price_rubles_input'
PLACE_OFFER_TARGET = 'place_offer_button'
# The "are you sure, this is below market value" confirmation. It only appears for some items,
# and while it is up the offer has NOT been placed, so a pass that ignores it counts a sale it
# never made and then clicks the next pass into a modal that is still sat there.
CHEAP_OFFER_POPUP_TARGET = 'cheap_offer_popup'
CHEAP_OFFER_POPUP_DELAY = 1.0  # seconds after place offer for the popup to draw, if it is coming
# The game's plain "Error / 0" dialog. Nothing about it is ours: it lands over the flea on its
# own schedule, and while it is up every read underneath it fails, which is what the mode's
# usual failure paths report instead. Dismissing it is the one thing that unsticks a run that
# would otherwise fail item after item until Stop.
ERROR_POPUP_TARGET = 'error_0_popup'
# How far down the matched box OK sits, as a fraction of its height. The OK glyphs span rows
# 77-96 across the five crops in that folder at their stored 1080p size, putting their centre at
# 0.740 to 0.752, so the button itself covers a range wider than either number. 0.77 is the top
# of that range and lands inside the glyphs on all five with room for CLICK_JITTER either way;
# tests/test_error_popup.py is what says so, and is where to check a new crop that sits taller.
ERROR_POPUP_OK_FRACTION = 0.77
ERROR_POPUP_DELAY = 2.0  # seconds after clicking OK for the dialog to go and the screen to settle
MORE_OFFERS_BRIGHTNESS = 190  # max channel in the add offer button: measured 255 lit, 123 greyed
OFFER_SLOT_POLL = 2.0  # seconds between rechecks while every offer slot is full
# Everything belonging to the flea's filter window shares a flea_filters_ prefix, so the
# reference_images listing groups them instead of scattering them through the alphabet.
# filter_by_item is deliberately not one of these: that is the inventory right-click menu.
FILTER_BUTTON_TARGET = 'flea_filters/button'  # opens the flea's filter window
FILTERS_WINDOW_TARGET = 'flea_filters/window_title'  # that window's title bar, for dragging it
# Clears every filter on that window, and closes it doing so. Only the buyer's pass uses it:
# see apply_flea_filters for why a buyer resets and a seller does not.
RESET_TARGET = 'flea_filters/reset_button'
CURRENCY_ANY_TARGET = 'flea_filters/currency_dropdown_any'  # currency, while it still says any
CURRENCY_RUBLES_OPTION = 'flea_filters/currency_dropdown_select_rubles'  # roubles, in the opened dropdown
CURRENCY_RUB_TARGET = 'flea_filters/currency_dropdown_rub'  # the dropdown once it reads roubles
OFFERS_FROM_ANY_TARGET = 'flea_filters/offers_from_any'  # offers-from, while it still says any
OFFERS_FROM_PLAYERS_OPTION = 'flea_filters/offers_from_select_players'  # players, in the opened dropdown
OFFERS_FROM_PLAYERS_TARGET = 'flea_filters/offers_from_players'  # the dropdown once it reads players
OFFERS_FROM_TRADERS_OPTION = 'flea_filters/offers_from_select_traders'  # traders, in the opened dropdown
OFFERS_FROM_TRADERS_TARGET = 'flea_filters/offers_from_traders'  # the dropdown once it reads traders
# The offers-from choice, keyed by the source name callers pass: (option in the open list, settled
# field once picked). 'players' is the default everywhere but crafts mode, which buys from either.
OFFERS_FROM = {'players': (OFFERS_FROM_PLAYERS_OPTION, OFFERS_FROM_PLAYERS_TARGET),
               'traders': (OFFERS_FROM_TRADERS_OPTION, OFFERS_FROM_TRADERS_TARGET)}
FILTERS_OK_TARGET = 'flea_filters/OK_button'  # applies the filters and closes the window
CONDITION_VALUE = '100'  # only sell pristine items, so the board we undercut is pristine ones
# The number box carries no border of its own worth matching and its contents are the thing
# being set, so it is aimed at by crossing two labels that never change instead: the row's Y
# off 'Condition from:' and the column's X off the 'items expiring' text sitting above it.
# Both are plain words, so they match the same whatever the field reads, which is exactly what
# the 80/100 crops cannot do. Keep both crop folders internally consistent in extent: find()
# cannot say which png matched, so a crop with more padding than its neighbours moves the
# centre this aims at.
CONDITION_LABEL_TARGET = 'flea_filters/condition_from_label'  # gives the row: its middle Y
EXPIRING_TEXT_TARGET = 'flea_filters/items_expiring_text'  # gives the column: its middle X
DROPDOWN_DELAY = 0.3  # seconds for the currency dropdown to unroll
OFFERS_FROM_DELAY = 0.33  # and for the offers-from one
# The filter pass's own waits, a tenth of the three general ones above (0.3, 0.3, 0.33) that it
# used to borrow. Consolidating the pass is what pays for the cut. It used to read a dropdown,
# click it, wait, read it back and go round, so every wait had a screen read immediately behind
# it and a wait that came up short read as a control that would not take. Now the whole window
# is read once into a plan, every click goes out in a row, and every confirmation happens at the
# end, so a wait only has to cover one list unrolling and the confirmation pass catches whatever
# did not land in time and does it again.
#
# Measured with tests/speed_test_apply_filters.py, which runs the real pass at multiples of
# these: 1x and 2x passed all three call shapes. 5x is past what that run proved, so if the
# filters start missing on a slower machine this is the first place to look, and FILTER_ATTEMPTS
# below is what stands between a short wait and a wrongly filtered board.
# ponytail: halved from a fifth (0.2) to a tenth (0.1) on 2026-08-31, faster than the 1x the
# speed test proved. It held over a live full pass, and FILTER_ATTEMPTS is the net if a slower
# machine misses; put FILTER_PACE back to 0.2 if the retries start earning their keep here.
FILTER_PACE = 0.1  # what the three waits below are, as a fraction of the general ones
FILTER_MENU_DELAY = 0.03          # MENU_DELAY * FILTER_PACE
FILTER_DROPDOWN_DELAY = 0.03      # DROPDOWN_DELAY * FILTER_PACE
FILTER_OFFERS_FROM_DELAY = 0.033  # OFFERS_FROM_DELAY * FILTER_PACE
# Rounds of read-all / act-all / check-all before the pass gives up. More than one because the
# usual failure is a click landing while a list is still unrolling, which the next round just
# repeats past. Was DROPDOWN_ATTEMPTS, when the retry lived inside one dropdown.
FILTER_ATTEMPTS = 3
# The filter modal is pinned to the top-left corner by orientate_filters_window, so every control
# and every dropdown list that drops under one sits in this box anchored on the title bar. Scoping
# the plan/act/check finds to it is where most of a pass's time was: a match over the full 2560x1440
# window is ~0.55s, the same match inside this ~1/6-screen box ~0.1s. 1080p pixels, grown by
# find.scale() at match time like every other measurement here. Deliberately generous: the exact
# modal extent does not matter as long as the box holds it, so a slightly-off corner drag still reads.
FILTER_REGION_PAD = 30      # slack around the title's top-left, for a drag that lands a little off
FILTER_REGION_WIDTH = 560   # past the offers-from list, the widest thing that opens under a row
FILTER_REGION_HEIGHT = 760  # past a dropdown list opened at the bottom row
CHECKMARK_TARGET = 'checkmark'  # the tick beside the autoselect similar button
# The right half of that button's box grows this much per side before we look inside it. Half,
# because the checkbox is at the right hand end of every reference crop of the button, and a
# region that starts at the left end has the whole label in it for a checkmark to go wrong in.
CHECKMARK_MARGIN = 0.15
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
# the select loop's poll: that one is tuned for a run of cheap retries, and here a search that
# runs early just finds nothing and silently leaves the offer up.
STALE_ROW_DELAY = 1.5
STALE_CONFIRM_DELAY = 0.33  # seconds either side of the y that answers the are-you-sure dialog
STALE_SETTLE = 120  # seconds to let the flea catch up after cancelling, before selling again


def click_all_button(region=None):
    """Click the inventory's 'All' filter button. Returns the clicked (x, y), or None if not found."""
    point = find.find_center(ALL_BUTTON_TARGET, region)
    log(f'clicking the All filter at {point}' if point else 'no All filter button on screen', 1)
    if point:
        pyautogui.click(*point)
    return point


def _region_from(all_btn, similar, sort_btn):
    """The geometry half of infer_inventory_region, split out so it checks without a live screen."""
    left = int(all_btn.left + all_btn.width) + LEFT_PAD
    top = int(similar.top + similar.height) + TOP_PAD
    width = int(similar.left + similar.width) + RIGHT_PAD - left
    height = int(sort_btn.top + sort_btn.height) + BOTTOM_PAD - top
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

    The cursor is parked first because hovering the entry inverts it exactly the same way, so a
    pointer left sitting on the icon after clicking it reads as open no matter what the flea is
    actually doing. That is how the sniper's open, escape, open used to end up as open, escape:
    the escape shut the flea, the cursor was still on the icon, and the reopen saw a lit entry
    and decided there was nothing to click.
    """
    _park_cursor()
    box = find_flea_icon(region)
    if not box:
        return None
    rect = (int(box.left), int(box.top), int(box.width), int(box.height))
    return float(np.asarray(screen.grab(rect).convert('RGB')).mean())


def grab_price_region(region=None, fractions=PRICE_FRACTIONS):
    """The suggested price readout as (left, top, width, height), scaled off the window size.

    Fixed fractions rather than a template match: the box holds a number that changes every
    time, so there is nothing stable to match against. Scaling keeps it right at any
    resolution as long as the UI keeps its proportions.
    """
    left, top, width, height = region if region else screen.rect()
    x0, y0, x1, y1 = fractions
    return (left + round(width * x0), top + round(height * y0),
            round(width * (x1 - x0)), round(height * (y1 - y0)))


def grab_first_offer_region(region=None):
    """The topmost offer row as (left, top, width, height) in screen coords.

    FIRST_OFFER_FRACTIONS through the same scaling as grab_price_region, so it lands in the
    same place at any resolution and keeps a negative left edge on a monitor left of the
    primary.
    """
    return grab_price_region(region, FIRST_OFFER_FRACTIONS)


def grab_first_item_price_region(region=None):
    """The topmost offer's asking price as (left, top, width, height) in screen coords.

    FIRST_ITEM_PRICE_FRACTIONS through the same scaling as grab_price_region, so it lands in the
    same place at any resolution and keeps a negative left edge on a monitor left of the primary.

    Narrower than grab_first_offer_region, and deliberately not carved out of it: that region is
    the whole row and is framed for first_offer_is_a_pack, which reads the offer's title.

    tests/test_find_first_offer_dollar.py draws this box on the screen it was cut from, which is
    the tuning loop for the four numbers above.
    """
    return grab_price_region(region, FIRST_ITEM_PRICE_FRACTIONS)


CAPTCHA_TITLE_TARGET = 'captcha_window_title'      # the 'SECURITY CHECK' bar at the top of the modal
CAPTCHA_CONFIRM_TARGET = 'captcha_confirm_button'  # its 'CONFIRM' button at the bottom


def grab_captcha_region(frame):
    """The box around Tarkov's flea SECURITY CHECK modal on `frame`, or None if none is up.

    The modal has no crop of its own: the challenge grid in the middle is a different set of item
    icons every time, so nothing there is stable to match. It is measured off the two parts that
    do not change, the 'SECURITY CHECK' title bar at the top and the 'CONFIRM' button at the
    bottom, and the box is stitched from them: left, right and bottom off the confirm button,
    top off the title bar. Returns (left, top, width, height) in `frame`'s own coordinates, or
    None if either part is absent, which is the answer when there is no captcha on screen.

    Takes the frame rather than reading the screen, so a caller can hand it a live grab or a saved
    screenshot; the two targets are found inside it with find(haystack=...), which returns boxes
    in the frame's coordinates.
    """
    title = find.find(CAPTCHA_TITLE_TARGET, haystack=frame)
    confirm = find.find(CAPTCHA_CONFIRM_TARGET, haystack=frame)
    if not title or not confirm:
        return None
    left, top = confirm.left, title.top
    width = confirm.width
    height = (confirm.top + confirm.height) - title.top
    return (left, top, width, height)


def first_offer_is_a_pack(region=None):
    """Is the topmost comparable offer a pack rather than a single item?

    A pack offer's title ends '- pack', and the suggested price under it is the price of the
    whole pack. Listing one item at it is not an undercut, it is a giveaway, and nothing later
    in the pass can tell the two apart: the number in the box is perfectly readable either way.
    """
    return find.find('flea_item_pack_sale_text', grab_first_offer_region(region)) is not None


def get_price(region=None):
    """The suggested price as an int, or None if nothing readable is in the box.

    A price quoted against a pack is refused here rather than read, because unreadable is
    already what the caller does the right thing with: it skips the item and starts a fresh
    pass. A wrong price is the one failure that costs money.
    """
    if first_offer_is_a_pack(region):
        log('the top comparable offer is a pack, so the suggested price is for the pack and '
            'not for this item: refusing to read it', 1)
        return None
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
    if brightness is None:
        log('flea icon not on screen, so the flea reads as closed', 1)
        return False
    open_now = brightness >= threshold
    log(f'flea icon mean brightness {brightness:.0f} vs threshold {threshold}, '
        f'so the flea is {"open" if open_now else "closed"}', 1)
    return open_now


def _escape_window(target, what, region=None, delay=RECOVER_DELAY):
    """Click `what`'s title bar to put it in front, then escape out of it. True if it was up.

    The click is what makes the escape reliable. Escape goes to whatever the game thinks is
    focused, and after a run that died part way that is not necessarily the window still drawn
    on top; clicking the title bar first says which one is meant. A title bar is the safe place
    to click for it, being a drag handle rather than a control, so a click that lands on the
    wrong window cannot press anything.

    `delay` is waited twice, once after each input. The one after the click is the one that is
    easy to leave out and pointless to leave out: escaping in the same breath as the click races
    the focus change it was sent to cause, which is the whole reason the click is here.
    """
    point = find.find_center(target, region)
    if not point:
        return False
    log(f'{what} is still open from last time, clicking its title bar at {point} to focus it, '
        f'then escaping out of it', 1)
    pyautogui.click(*point)
    time.sleep(delay)  # let the click land and the window come forward before escaping it
    pyautogui.press('esc')
    time.sleep(delay)  # and let the window actually go before anything looks at the screen
    return True


def close_leftover_windows(region=None, delay=RECOVER_DELAY):
    """Escape out of anything a previous session left on screen. Returns how many escapes went.

    Start is the one moment the bot has no idea what is in front of it. Every other screen it
    meets, it opened itself. A run that was stopped mid pass, or crashed out of one, leaves the
    scav case window, the offer creation window or the flea filter window sitting there, and the
    first thing the next run does is hunt for the flea tab underneath them and not find it.

    Every window is matched on its own title bar. Nothing here keys off the controls inside a
    window: which of those are on screen depends on what the window was opened over, and the
    inventory is a perfectly normal screen to press Start on and must never be escaped.

    Each window is checked on its own and gets its own click and escape. They are not expected
    to be up together, but pairing them off would mean guessing which combinations can happen,
    and a guess that is wrong here leaves a window on screen for the whole next run.

    `delay` is the wait after each escape, for the window to actually go. It is deliberately not
    the same number as the wait between rounds of the loop in sell_bot._recover: this one is a
    window closing and wants a full second, that one is only a pause before looking again.
    """
    # Newest first. The offer creation window is opened over the scav case, so it is the one on
    # top, and taking the top one first means each escape lands on the window it was aimed at.
    presses = sum((_escape_window(OFFER_TARGET, 'the offer creation window', region, delay),
                   _escape_window(SCAV_WINDOW_TARGET, 'a scav case window', region, delay),
                   _escape_window(FILTERS_WINDOW_TARGET, 'the flea filter window', region, delay)))
    if not presses:
        log('nothing left open from a previous session', 2)
    return presses


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
    opened = wait_for_flea(region)
    log(f'flea {"open" if opened else "still shut after the click"}', 1)
    return opened


def wait_for_flea(region=None, timeout=FLEA_OPEN_TIMEOUT, poll=FLEA_OPEN_POLL):
    """Poll until the flea entry reads open. True if it did, False once timeout runs out.

    wait_for's job done on a brightness read instead of a template, because the flea has no
    window title to match: which page is up is only readable off the taskbar entry inverting.

    How long this takes depends on where the click came from, which is why it cannot be one
    number. From the stash the flea is up inside a second; from a hideout station it is nearer
    four, because the game leaves the room first. See FLEA_OPEN_TIMEOUT.
    """
    started = time.monotonic()
    while True:
        if is_flea_open(region):
            log(f'the flea came up {time.monotonic() - started:.1f}s after the click', 1)
            return True
        if time.monotonic() - started >= timeout:
            log(f'the flea never came up, gave up after {timeout:.0f}s', 1)
            return False
        time.sleep(poll)


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
    return int(np.asarray(screen.grab(rect).convert('RGB')).max())


def more_offers_available(region=None, threshold=MORE_OFFERS_BRIGHTNESS):
    """True while the add offer button is lit, ie there is still a free offer slot.

    False when it is greyed out, and false when the button is missing entirely: no button on
    screen is no slot to sell into either way.
    """
    brightness = add_offer_brightness(region)
    if brightness is None:
        log('add offer button not on screen, treating that as no free slot', 1)
        return False
    free = brightness >= threshold
    if free:  # only the lit reading is logged: this is polled every couple of seconds for as
        log(f'add offer button brightest channel {brightness} vs threshold {threshold}, '
            f'a slot is free', 1)  # long as the board stays full, and the caller announces that
    return free


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
    left, top, width, height = region or screen.rect()
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


def jitter(point, x=CLICK_JITTER, y=CLICK_JITTER):
    """`point` nudged by up to x and y pixels each way. None passes straight through.

    Uniform across the range rather than tapered toward the middle: at 2-3px on controls tens of
    pixels wide, every draw is comfortably inside the button, so there is no edge to lean away
    from. Anything wide enough to want a bigger spread would want tapering with it.

    y=0 is a real setting, for the right-click menu rows: their reference crops are a 6px strip
    of text, so the box says nothing about where the row's top and bottom actually are.
    """
    if point is None:
        return None
    return (point[0] + random.randint(-x, x), point[1] + random.randint(-y, y))


def click_add_offer(region=None):
    """Click the add offer button. Returns the clicked (x, y), or None if not found."""
    point = jitter(find.find_center(ADD_OFFER_TARGET, region))
    log(f'clicking add offer at {point}' if point else 'no add offer button on screen', 1)
    if point:
        pyautogui.click(*point)
    return point


def enter_price(value, region=None):
    """Click the roubles field and type value into it. Returns the clicked (x, y), or None.

    Select all first: the field arrives holding the suggested price, and typing into it
    without clearing appends, which turns 99000 into something like 10000099000.
    """
    point = jitter(find.find_center(PRICE_INPUT_TARGET, region))
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
    point = jitter(find.find_center(PLACE_OFFER_TARGET, region))
    log(f'clicking place offer at {point}' if point else 'no place offer button on screen', 1)
    if point:
        pyautogui.click(*point)
    return point


def cheap_offer_popup(region=None):
    """True if the below-market-value confirmation is up, meaning the offer did not go through.

    Read after CHEAP_OFFER_POPUP_DELAY, not immediately: the popup animates in, and asking too
    early answers 'no popup' for the one case this exists to catch.
    """
    up = find.find(CHEAP_OFFER_POPUP_TARGET, region) is not None
    log('the cheap offer confirmation is up, the offer was not placed' if up
        else 'no cheap offer confirmation, the offer went through', 2)
    return up


def dismiss_error_popup(region=None):
    """Click OK on the game's Error dialog if it is on screen. True if one was dismissed.

    Called from a mode's failure paths rather than on a schedule, because that is when it is
    worth the match: a step that failed for no reason we can name is the symptom this dialog
    produces, and a step that succeeded proves the screen was readable.

    Aimed off the matched box rather than off a reference crop of the OK button itself. The
    button is two plain glyphs on flat black, the shape of target that has no false-positive
    headroom (see the note on CONFIDENCES in find.py), while the dialog around it is wide, has
    a title bar and matches at the default 0.9. So the thing that is safe to find is the thing
    we find, and the button is a fixed fraction down it.

    The one click in this file that is not jittered. Everywhere else the point comes straight
    off a matched box and the jitter is free spread inside a button; here the y is a fraction
    down a box that is a different height in every crop, so it is already approximate and the
    jitter is spread stacked on spread. The button is two glyphs 17px tall and there is no room
    to spend on it.

    False when nothing is up, which is the answer on almost every call and is not a problem:
    the caller was already failing and this is only ever an attempt to explain why.
    """
    box = find.find(ERROR_POPUP_TARGET, region)
    if box is None:
        return False
    point = (box.left + box.width // 2,
             box.top + round(box.height * ERROR_POPUP_OK_FRACTION))
    log(f'the game put an Error dialog up; clicking its OK at {point} and waiting '
        f'{ERROR_POPUP_DELAY:.0f}s', 1)
    pyautogui.click(*point)
    time.sleep(ERROR_POPUP_DELAY)
    return True


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
    if find.find(SELECTION_TARGET, region) is None:
        log('not selected: the offer panel is not showing a picked item', 2)
        return False
    if find.find(PLACE_OFFER_TARGET, region) is None:
        log('not selected: no place offer button, so the panel is only half drawn', 2)
        return False
    if find.find(NO_SELECTION_TARGET, region) is not None:
        log('not selected: the nothing-picked placeholder is still on screen', 2)
        return False
    log('selected: picked item and place offer both there, placeholder gone', 2)
    return True


def _crop_to(ltrb, bounds):
    """An expanded (left, top, right, bottom) clipped to a monitor, as (left, top, width, height).

    bounds is that monitor as (left, top, width, height). Clipped to its own edges rather than
    to (0, 0), because a monitor sitting left of the primary one starts at a negative x and
    clamping to zero there would pull the crop onto the wrong screen entirely.
    """
    left, top, right, bottom = ltrb
    edge_left, edge_top, width, height = bounds
    left, top = max(edge_left, left), max(edge_top, top)
    return (left, top, min(edge_left + width, right) - left, min(edge_top + height, bottom) - top)


def _checkmark_region_from(box, bounds, margin=CHECKMARK_MARGIN):
    """The geometry half of autoselect_similar_region, so it checks without a live screen.

    The right half of the button's box, grown by margin per side and clipped to `bounds`.
    """
    half = int(box.width) // 2
    left, top = int(box.left) + half, int(box.top)
    width, height = int(box.width) - half, int(box.height)
    dx, dy = round(width * margin), round(height * margin)
    return _crop_to((left - dx, top - dy, left + width + dx, top + height + dy), bounds)


def autoselect_similar_region(region=None, margin=CHECKMARK_MARGIN):
    """Where to look for the tick: the right half of the autoselect similar button's box, grown.

    Raises LookupError if the button is not on screen, which means the screen is not the one
    we think it is, not that the box is empty.
    """
    box = find.find(AUTOSELECT_TARGET, region)
    if not box:
        raise LookupError('autoselect similar button not on screen')
    return _checkmark_region_from(box, screen.rect(), margin)  # the grown box can run off an edge


def is_autoselect_similar_ticked(region=None, margin=CHECKMARK_MARGIN):
    """True when the checkmark is showing beside the autoselect similar button.

    The tick sits just outside the button's own artwork, hence the widened crop: search the
    whole screen for a checkmark and you find every other one in the UI.
    """
    crop = autoselect_similar_region(region, margin)
    ticked = find.find(CHECKMARK_TARGET, crop) is not None
    log(f'autoselect similar is {"ticked" if ticked else "unticked"}, read inside {crop}', 1)
    return ticked


def set_autoselect_similar(on, region=None):
    """Tick or untick autoselect similar so it matches `on`. Returns True once it reads that way.

    Left on, picking one item pulls in every matching one, so the offer is a stack rather than
    the single item the price was read for. Off is what a pass pricing one item at a time
    wants; on is what someone clearing out duplicates wants, hence the switch. Already in the
    wanted state is a no-op, not a click, because clicking it then would flip it the wrong way.
    """
    want = 'on' if on else 'off'
    if is_autoselect_similar_ticked(region) == bool(on):
        log(f'autoselect similar already {want}', 1)
        return True
    point = find.find_center(AUTOSELECT_TARGET, region)
    if not point:
        log(f'autoselect similar needs switching {want} but its button vanished', 1)
        return False
    log(f'switching autoselect similar {want} at {point}', 1)
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    took = is_autoselect_similar_ticked(region) == bool(on)  # confirm it, do not assume
    log(f'autoselect similar now {want if took else "UNCHANGED, the click did not take"}', 1)
    return took


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
    screen_height = region[3] if region else screen.size()[1]
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
    """Squash the last axis of an RGB array into one int per pixel, so colors compare as scalars."""
    rgb = np.asarray(rgb).astype(np.uint32)
    return (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def _load_dead_colors(name=DEAD_REFERENCE):
    """Every distinct color across every reference image of empty slots, packed and sorted.

    Transparent pixels are skipped, so a screenshot can be masked down to just its empty slots.
    """
    seen = []
    for path in find.images(name):
        pixels = np.asarray(Image.open(path).convert('RGBA')).reshape(-1, 4)
        seen.append(_pack(pixels[pixels[:, 3] > 0][:, :3]))
    return np.unique(np.concatenate(seen))


def _dead_cube(colors, tol=DEAD_TOL):
    """A 256^3 lookup, True for any color within tol of a known one on every channel.

    ponytail: 16MB of bools built once at import, so the per-pixel test is a plain array
    index. Widening every known color beats comparing 500k pixels against 1500 colors.
    """
    cube = np.zeros((256, 256, 256), dtype=bool)
    rgb = np.stack([(colors >> 16) & 255, (colors >> 8) & 255, colors & 255], axis=1)
    span = range(-tol, tol + 1)
    offsets = np.array([(r, g, b) for r in span for g in span for b in span], dtype=np.int16)
    near = np.clip(rgb[:, None, :].astype(np.int16) + offsets, 0, 255).reshape(-1, 3)
    cube[near[:, 0], near[:, 1], near[:, 2]] = True
    return cube


DEAD_COLOURS = _load_dead_colors()
DEAD_CUBE = _dead_cube(DEAD_COLOURS)


def calculate_dead_pixel(pixel, cube=None):
    """True where the color is within DEAD_TOL of one an empty slot takes.

    Takes one (r, g, b) or a whole HxWx3 array. Not a brightness threshold: a dark blue is
    dark but is nowhere near a slot color, so it stays alive.
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
    shot = np.asarray(screen.grab(rect).convert('RGB'))
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
    cases = scav_case_regions(inventory)
    points = _pixels_in(inventory, cases)
    log(f'{len(points)} live pixels in the inventory grid, {len(cases)} scav case(s) excluded'
        + (f' at {cases}' if cases else ''), 2)
    return points


def find_scav_case_pixels(region=None):
    """Screen (x, y) of every pixel in the open scav case that isn't an empty slot.

    No scav exclusion here: inside the case, those items are the point.
    """
    case = infer_scav_case_region(region)
    points = _pixels_in(case)
    log(f'{len(points)} live pixels inside the scav case at {case}', 2)
    return points


def select_item_from_inventory(region=None, attempts=SELECT_ATTEMPTS, stop=None):
    """Grab a random item from the inventory screen and filter by it on the flea.

    Left-clicks a random sellable pixel and asks the offer panel whether that actually
    selected anything. A live pixel is not always a clickable item (icon overhang, a tooltip,
    a stack counter), so a miss just means try again somewhere else: the pixels are re-found
    and a new one drawn each attempt. Only once something is selected does it bother with the
    right-click menu and 'filter by item'. Returns the clicked (x, y), or None if every
    attempt missed.

    Checking the cheap thing first is the point: a miss now costs one left click instead of a
    right click, a menu wait and a menu search.

    stop: a threading.Event that abandons the loop the moment it is set, returning None. This
    is the longest stretch of a pass with nothing else to interrupt it. Every attempt is a
    screenshot, a click and a poll, so without this a Stop pressed at the wrong moment sat
    through the rest of them, which is most of the delay between the button going amber and
    the run actually ending. Checked at the top of the attempt, before the screenshot, so a
    stop already set costs nothing at all.

    ponytail: re-screenshots per attempt as asked, so each retry costs a fraction of a second.
    """
    for attempt in range(1, attempts + 1):
        if stop is not None and stop.is_set():
            log(f'stop asked for after {attempt - 1} attempt(s), abandoning the selection', 2)
            return None
        points = find_sell_pixels(region)
        if not points:
            log('no sellable pixels in the inventory, the stash looks empty', 1)
            return None  # nothing to sell, retrying will not conjure an item
        chosen = random.choice(points)
        log(f'attempt {attempt}/{attempts}: {len(points)} live pixels, clicking {chosen}', 2)
        pyautogui.click(*chosen)
        if _sleep(SELECT_POLL_DELAY, stop):  # cut short means stop, not a poll that finished
            log('stop asked for while waiting on the offer panel, abandoning the selection', 2)
            return None
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
            # Asked first, because a dialog is the one reason to miss that costs nothing to
            # undo. It is modal, so the right click that should have opened the menu landed on
            # it and no menu exists at all; clearing it and picking again keeps the pass, where
            # the return below spends it. One match on an attempt that was already lost.
            #
            # Not what was ending runs at 2560x1440, which is worth saying because it was the
            # first guess. There the menu really is open and 'FILTER BY ITEM' really is in it,
            # and find just could not see it: 0.870 to 0.882 across seven crash screenshots
            # against the 0.9 default, since the crops are 157x10 and 120x6 and lose too much
            # growing to a 1440p screen. find.CONFIDENCES carries filter_by_item at 0.7 now and
            # this branch should be rare again. The dialog check stays because it is a real
            # cause, just not that one.
            if dismiss_error_popup(region):
                log('an error dialog took the right click, cleared it and picking again', 2)
                continue
            # Hand the whole pass back rather than pressing escape here and carrying on. The
            # escape this used to press was meant to reset to the top of the loop, and one blind
            # press cannot do that: escape closes the biggest window on screen, which is the
            # offer creation window and never the little right click menu, so the menu stayed
            # open and the window the rest of the pass measures itself against went away. The
            # next attempt then lost all three of infer_inventory_region's anchors at once and
            # the run ended, blaming the stash for a keypress two seconds earlier.
            #
            # sell_bot already owns that reset and already knows the count this screen needs,
            # INVENTORY_ESCAPES for a bare stash and SCAV_ESCAPES with a case window over it. A
            # None here is what puts it to work: sell_one escapes that many times and raises
            # Retry, which is a fresh pass with the window reopened from scratch. One lost item
            # instead of a stopped bot, and it costs a pass rather than nine more attempts at a
            # screen that has already lost the thing they all measure from.
            log('no filter by item in the menu, backing out for a fresh pass', 2)
            return None
        point = jitter(pyautogui.center(box), y=0)  # a 6px tall crop says nothing about the row
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
    left, top, width, height = screen.rect()
    point = (left + width // 2, top + height // 2)
    log(f'parking the cursor mid screen at {point}, clear of anything it could hover', 2)
    pyautogui.moveTo(*point)
    return point


def _corner_point(corner, bounds):
    """Where a named corner sits on a monitor given as (left, top, width, height).

    Measured from that monitor's own origin rather than from (0, 0), or a drag meant for the
    second screen's corner lands on the primary's instead. The last row is top + height - 1:
    one more than that is the first row of whatever is below, or off the desktop entirely.
    """
    left, top, width, height = bounds
    corners = {'top left': (left, top),
               'top right': (left + width - 1, top),
               'bottom left': (left, top + height - 1),
               'bottom right': (left + width - 1, top + height - 1)}
    try:
        return corners[corner]
    except KeyError:
        raise ValueError(f'unknown corner {corner!r}, want one of '
                         f'{", ".join(sorted(corners))}') from None


def _drag_to_corner(target, corner='top left', region=None, duration=DRAG_SECONDS,
                    repeats=DRAG_REPEATS):
    """Grab the centre of target's bbox and drag it into a corner. Last point grabbed, or None.

    Dragged repeats times over: the window trails the cursor, so one pass stops short and each
    following pass re-finds it wherever it settled. Stops early if it goes missing, which is
    also how a single failed find still returns None.

    Finding the window at the start is the whole success condition, deliberately. A drag cannot
    close a Tarkov window, so a post-drag read that comes back empty is the match failing, not
    the window leaving, and a point that was genuinely grabbed stays the honest answer.

    Every pass runs, including ones that look wasted. A pass that moves the window nothing is
    not proof it has arrived, and cutting those was tried and taken back out on 2026-08-22.

    Parks the cursor mid screen afterwards. Every screen corner is one of pyautogui's panic
    points, so the fail-safe comes off for the drag and only goes back on once the cursor is
    clear of it. Leaving it parked in a corner trips the next call instead, which is a crash
    a long way from its cause.

    Every pass logs where the window was before the drag, the cursor path, and where it ended
    up. That last one is the one that used to be missing: the old log said which point was
    grabbed and never where the window landed, so a run reading back as 72 clean orientations
    said nothing about whether any of them actually reached the corner. The read after the
    last drag is the only genuinely extra match this costs, since the read after every other
    one is the read the next pass was going to do anyway.
    """
    destination = _corner_point(corner, screen.rect())
    log(f'dragging {target} to the {corner} at {destination}, up to {repeats} passes, '
        f'fail-safe off for the corner', 1)
    grabbed = None
    failsafe = pyautogui.FAILSAFE
    pyautogui.FAILSAFE = False
    try:
        box = find.find(target, region)
        for attempt in range(1, repeats + 1):
            if not box:
                log(f'pass {attempt}/{repeats}: {target} not on screen, stopping here', 2)
                break
            point = pyautogui.center(box)
            log(f'pass {attempt}/{repeats}: {target} pre ({int(box.left)}, {int(box.top)}) '
                f'{int(box.width)}x{int(box.height)}, grabbing its centre {tuple(point)}', 2)
            log(f'cursor {tuple(point)} -> {destination} over {duration:.2f}s, left button down', 2)
            grabbed = point
            pyautogui.moveTo(*point)
            pyautogui.dragTo(*destination, duration=duration, button='left')
            box = find.find(target, region)  # the post of this pass, and the pre of the next
            if not box:
                log(f'{target} post: gone from the screen after the drag', 2)
                continue  # the top of the loop reports it and stops
            # int() throughout: pyautogui.center returns floats on some versions, and a
            # '+d' format against one of those raises inside the logging of a working drag.
            after = pyautogui.center(box)
            was, now = (int(point[0]), int(point[1])), (int(after[0]), int(after[1]))
            log(f'{target} post ({int(box.left)}, {int(box.top)}) '
                f'{int(box.width)}x{int(box.height)}, centre {now}: '
                f'moved ({now[0] - was[0]:+d}, {now[1] - was[1]:+d}), '
                f'still ({now[0] - destination[0]:+d}, {now[1] - destination[1]:+d}) '
                f'from the {corner}', 2)
    finally:
        # Parking goes in the finally, not at the end of the try. The cursor is sat on a corner
        # for the whole drag, and every corner is one of pyautogui's panic points, so a raise
        # part way through used to switch the fail-safe back on around a cursor still parked on
        # one. The next pyautogui call anywhere in the bot then died with a fail-safe message
        # that pointed nowhere near the drag that caused it.
        try:
            _park_cursor()
        except Exception as e:  # never let a parking problem replace the failure being unwound
            log(f'could not park the cursor after the drag: {e}', 1)
        pyautogui.FAILSAFE = failsafe
        log(f'fail-safe back to {failsafe}, cursor parked mid screen', 2)
    return grabbed


def orientate_offer_creation(region=None, corner=OFFER_CORNER, duration=DRAG_SECONDS,
                             repeats=DRAG_REPEATS):
    """Drag the offer creation window into a corner of the monitor, into a known place.

    Grabs it by the centre of its bbox, repeats times over like the scav box. Returns the last
    point it grabbed, or None if not found.

    corner: any name _corner_point knows. The bottom left is the default and what the bot has
    always used, but the window covers a different part of the board in each corner, so which
    one is out of the way depends on the layout. region stays the first argument because
    sell_bot calls this positionally.
    """
    point = _drag_to_corner(OFFER_TARGET, corner, region, duration, repeats)
    log(f'dragged the offer window to the {corner} by {point}' if point
        else 'offer creation window not on screen to drag', 1)
    return point


# One dropdown in the filter window: the crop that says it still reads 'any', the option to
# click in the opened list, the crop that says it has settled on that option, and how long that
# list takes to unroll. Currency and offers-from are the same three-step dance, so they are one
# shape here rather than two code paths.
FilterDropdown = namedtuple('FilterDropdown', 'name any_target option_target settled_target delay')
# What one look at the window says is left to do. dropdowns is a list of (FilterDropdown, the
# point to click to open it), read before anything is clicked; condition is whether the
# condition-from box wants typing into, which is always when asked for, see _set_condition_from.
FilterPlan = namedtuple('FilterPlan', 'dropdowns condition')


def filter_dropdowns(source):
    """The dropdowns a filter pass sets, in the order it sets them."""
    option_target, settled_target = OFFERS_FROM[source]
    return (FilterDropdown('currency', CURRENCY_ANY_TARGET, CURRENCY_RUBLES_OPTION,
                           CURRENCY_RUB_TARGET, FILTER_DROPDOWN_DELAY),
            FilterDropdown(f'offers from {source}', OFFERS_FROM_ANY_TARGET, option_target,
                           settled_target, FILTER_OFFERS_FROM_DELAY))


def _read_dropdown(dropdown, region=None):
    """(state, the 'any' box) for one closed dropdown. state is 'set', 'unset' or None.

    None means the window did not answer, and it is never treated as set. A dropdown still
    reading Any because its reference crop simply did not match used to come back configured,
    which is silent in the worst way: the run browses the wrong offers for the rest of the
    session and the log says the filter went on.

    Both crops matching at once is also None rather than a guess. It means one of the two
    reference sets is loose enough to match the other state, and nothing here can say which.
    """
    settled = find.find(dropdown.settled_target, region)
    any_box = find.find(dropdown.any_target, region)
    if settled and any_box:
        log(f'ambiguous read on {dropdown.name}: {dropdown.any_target} and '
            f'{dropdown.settled_target} both matched', 1)
        return (None, None)
    if settled:
        return ('set', None)
    if any_box:
        return ('unset', any_box)
    log(f'{dropdown.name} matched neither {dropdown.any_target} nor {dropdown.settled_target}, '
        f'so its state is unknown; not assuming it is set. Add reference crops for whichever '
        f'it reads', 1)
    return (None, None)


def filter_plan(region=None, source='players', set_condition=True):
    """Read the whole filter window once and say what is left to do, or None if it will not read.

    The reading half of a pass, all of it, before a single click goes out. Each dropdown is
    looked at once and the plan carries the point to click with it, so the acting half never has
    to find a field again on a window it is in the middle of changing.

    None rather than an empty plan when a dropdown is unreadable: an empty plan means everything
    is already set and the pass is done, which is the opposite of what an unreadable window
    means.
    """
    todo = []
    for dropdown in filter_dropdowns(source):
        state, any_box = _read_dropdown(dropdown, region)
        if state is None:
            return None
        if state == 'unset':
            # Centre of the crop, not its right edge. Aiming at where the arrow sits inside the
            # box quietly made every crop's right border a click target: widen a crop by 20px to
            # help it match and the click moves 20px with it, onto whatever is there. Centre
            # still asks the crop to be centred on the control, but a crop that is wrong is then
            # wrong somewhere obvious rather than off its edge.
            todo.append((dropdown, pyautogui.center(any_box)))
        else:
            log(f'{dropdown.name} already reads {dropdown.settled_target}', 1)
    return FilterPlan(todo, set_condition)


def _pick_from_dropdown(dropdown, field, region=None):
    """Open one dropdown at `field` and click its option. True if both clicks went out.

    The one screen read that cannot be hoisted into filter_plan is in here: the option does not
    exist until the field is clicked, so finding it has to sit between this function's own two
    clicks. Everything else this needs came from the plan.

    A missing option returns straight out, no retry and no escape. The click above was already
    followed by the list's own delay and the list is open: if the option is not there now it
    will not be there next round either, and the crops for it simply do not match what the game
    is drawing.

    The escape that used to be here was worse than useless. It shuts the whole FILTERS window
    rather than the open list, so everything after it clicked at coordinates on a window that
    was no longer there, into the live flea board behind it. That is a blind click on a real
    market with real money.

    The list is deliberately left open. It is the only evidence of what the game actually says,
    and this is the one failure that needs a human to look.
    """
    log(f'opening {dropdown.name} at {field}', 2)
    pyautogui.click(*field)
    time.sleep(dropdown.delay)
    point = find.find_center(dropdown.option_target, region)
    if not point:
        log(f'{dropdown.option_target} not in the opened {dropdown.any_target} dropdown. '
            f'Leaving it open so you can see what it reads: the crops for '
            f'{dropdown.option_target} do not match it', 1)
        return False
    log(f'picking {dropdown.option_target} at {point}', 2)
    pyautogui.click(*point)
    time.sleep(FILTER_MENU_DELAY)
    return True


def run_filter_plan(plan, region=None):
    """Do everything the plan asked for. True if every click went out.

    The acting half, and it confirms nothing: every state read happened in filter_plan and every
    confirmation happens in confirm_filters. That is the whole point of the split. The old pass
    interleaved the three, so each wait had a read immediately behind it and a wait that came up
    short read as a control that would not take.

    False here is fatal to the pass rather than something to go round again on, since the only
    way a step fails is the option not being in the list at all.
    """
    for dropdown, field in plan.dropdowns:
        if not _pick_from_dropdown(dropdown, field, region):
            return False
    if plan.condition and not _set_condition_from(region):
        return False
    return True


def confirm_filters(dropdowns, region=None):
    """Re-read the dropdowns this round set. (True, []) if they all took, else the ones that did not.

    The checking half, all of it at the end. The same read filter_plan does, which is the point:
    a pass is done when a fresh look says every dropdown it changed has settled and none still
    says any.

    Only the ones actually clicked, not every filter: a dropdown filter_plan found already settled
    was not touched this round, so re-reading it spends a full match to confirm a click that never
    went out. Those are trusted from the plan's own read. On a first-run board that is one dropdown
    already on roubles, so this halves the confirm.

    The condition box is not in here and cannot be. No crop of it can tell 100 from 0, see
    _set_condition_from.
    """
    unset = [d.name for d in dropdowns if _read_dropdown(d, region)[0] != 'set']
    log('confirm: ' + ('every set dropdown held' if not unset else f'{unset} did not take'), 1)
    return (not unset, unset)


def _set_condition_from(region=None):
    """Type 100 into the filter window's condition-from box.

    Returns True once the value has been typed, which is weaker than the other steps here
    promise and deliberately so: True means the box was found and typed into, not that it now
    reads 100. Nothing on this screen can confirm the value. See below.

    Not a dropdown, so it is not one of filter_dropdowns: this is a number field, clicked
    and typed into the way enter_price does the roubles one.

    The box is aimed at by crossing two labels rather than by matching the box itself, and no
    read guards either end. Both come from the same measurement. A crop of the box is a crop of
    one particular value, and the value is a few percent of its pixels, so it matches the other
    values nearly as well: a whole-row crop of 'Condition from: 100' scored 0.924 against a
    field that actually read 0, and one of '...: 80' scored 0.904 against the same frame. There
    is no threshold under those, and a read that always says yes is worse than no read, because
    the pass then skips the typing and reports the filter as set. That is the checkmark problem
    again, which scores 0.69 against an empty box for the same reason.
    So the row's Y comes off the 'Condition from:' label and the column's X off the 'items
    expiring' text above it, both fixed words that read the same whatever the field holds, and
    the typing simply always happens. It is idempotent: typing 100 into a box already at 100
    leaves 100, so there is nothing a before-read would have saved.

    ponytail: no confirmation, because the crop that would do it cannot tell values apart. To
    add one, crop just the digits rather than the whole row (0.68-0.74 against a wrong value
    against the whole row's 0.90+) and match it inside the box worked out below rather than
    over the window, since searching 3.7M pixels for a small dark needle finds one anywhere.

    Ctrl+A before typing, which the spec for this step did not ask for. Tarkov's number fields
    append rather than replace, which is what turns 99000 into 10000099000 in enter_price; here
    it would leave 0100 in a box that takes three digits and filter to something that is
    neither. With the confirmation gone this is the only thing standing between a typo and a
    wrong filter, so it is not optional.
    """
    label = find.find(CONDITION_LABEL_TARGET, region)
    if not label:
        log(f'{CONDITION_LABEL_TARGET} not on screen, so there is no row to aim at; is the '
            f'filter window open?', 1)
        return False
    expiring = find.find(EXPIRING_TEXT_TARGET, region)
    if not expiring:
        log(f'{EXPIRING_TEXT_TARGET} not on screen, so there is no column to aim at', 1)
        return False
    point = jitter((pyautogui.center(expiring).x, pyautogui.center(label).y))
    log(f'typing {CONDITION_VALUE} into condition from at {point} '
        f'(x off {EXPIRING_TEXT_TARGET}, y off {CONDITION_LABEL_TARGET}); not read back', 1)
    pyautogui.click(*point)
    time.sleep(FILTER_MENU_DELAY)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(CONDITION_VALUE)
    pyautogui.press('enter')
    time.sleep(FILTER_MENU_DELAY)
    return True


def orientate_filters_window(region=None, corner=FILTERS_CORNER, duration=DRAG_SECONDS,
                             repeats=DRAG_REPEATS):
    """Drag the flea's filter window into a corner of the monitor, by its title bar.

    Returns the last point it grabbed, or None if the title bar was never found.

    The top left by default, which is the one corner the rest of a pass keeps clear: while the
    filters are being set the offer creation window is parked bottom right and the scav case
    top right. Any name _corner_point knows works if that ever changes.
    """
    point = _drag_to_corner(FILTERS_WINDOW_TARGET, corner, region, duration, repeats)
    log(f'dragged the filter window to the {corner} by {point}' if point
        else 'filter window not on screen to drag', 1)
    return point


def open_filters(region=None):
    """Click the flea's filter gear, wait for the window, park it. True once all three are done.

    The wait is the point. Clicking the gear is not the same as the window opening: the game
    can put something else in front of the flea (a plain Error dialog, for one, which is what
    ended the run of 19 Aug) and the click then lands on nothing. Everything after this reads
    controls that only exist inside this window, so without the check the first thing to fail
    is a dropdown read, and the log blames a missing reference crop for a window that was never
    on screen.

    GEAR_JITTER rather than the usual spread, since the gear is small.
    """
    point = jitter(find.find_center(FILTER_BUTTON_TARGET, region), GEAR_JITTER, GEAR_JITTER)
    if not point:
        log('no filter button on screen', 1)
        return False
    log(f'opening the filter window at {point}', 1)
    pyautogui.click(*point)
    if not wait_for(FILTERS_WINDOW_TARGET, region, timeout=FILTERS_WINDOW_TIMEOUT):
        log('the filter window did not open. Something else is in front of the flea: check the '
            'frame saved around that click', 1)
        return False
    # Parked here rather than by the caller, so every route to this window ends with it in the
    # same place: the sniper's reset path opens it twice, and apply_flea_filters reads controls
    # off it either way.
    #
    # A failed drag fails the whole open. The title bar was matched a moment ago by the wait
    # above, so not finding it now is not a window sat somewhere awkward, it is the window
    # having gone or something having been drawn over it between the two reads. Carrying on
    # from there means clicking dropdowns by template match on a screen that has already
    # disagreed with itself once, and the first thing to fail would be a dropdown read blaming
    # a reference crop.
    if not orientate_filters_window(region):
        log('the filter window opened but its title bar would not grab, so it cannot be moved '
            'clear of the offer creation window', 1)
        return False
    return True


def filter_window_region(region=None):
    """A tight box around the filter modal, so its controls are matched over ~1/6 the pixels.

    Anchored on the filter window's title bar, which open_filters just matched, dragged into the
    top-left corner and left there. From that corner a generous box (FILTER_REGION_*) covers every
    control and every dropdown list that drops under one. See those constants for the timing this
    buys.

    None-safe by falling back to the full region: if the title bar cannot be found the pass just
    pays the old full-screen search rather than breaking, and open_filters already guaranteed the
    window is up, so this is belt-and-braces.
    """
    title = find.find(FILTERS_WINDOW_TARGET, region)
    if not title:
        return region
    s = find.scale()
    left = max(int(title.left - FILTER_REGION_PAD * s), 0)
    top = max(int(title.top - FILTER_REGION_PAD * s), 0)
    return (left, top, int(FILTER_REGION_WIDTH * s), int(FILTER_REGION_HEIGHT * s))


def apply_flea_filters(region=None, reset=False, source='players', set_condition=True):
    """Open the flea's filter window, set roubles, an offer source and 100% condition, then OK out.

    One round is three phases, in that order and never interleaved:

      1. read   - filter_plan looks at every dropdown once and returns what still needs setting,
                  carrying the point to click with each one.
      2. act    - run_filter_plan does all the clicking and typing in a row, confirming nothing.
      3. check  - confirm_filters re-reads the dropdowns it set and says which, if any, did not take.

    Only a check that comes back short goes round again, up to FILTER_ATTEMPTS. That is what
    pays for the filter waits being a fifth of what the rest of this file uses: nothing here
    depends on a single wait being long enough, because the check at the end of the round is
    what decides, and a click that landed while a list was still unrolling is simply done again.
    Reading and acting used to alternate one dropdown at a time, which meant every wait had a
    read immediately behind it and a wait that came up short read as a control that would not
    take.

    source picks the offers-from dropdown: 'players' (the default, what both flea modes want) or
    'traders' (crafts mode buys inputs from either). Same three phases either way, only the
    option and settled crops differ, see sell.OFFERS_FROM.

    set_condition types 100 into the condition-from box, which both flea modes want (an item at
    less than full durability is worth less). Crafts mode passes False: a craft input is
    consumed, not resold, so its condition does not matter and filtering on it only hides
    cheaper offers. It is the one step with no check phase of its own, because no crop of that
    box can tell 100 from 0; typing it is idempotent, so a round that repeats does no harm.

    Returns True once every dropdown reads the right thing and the window is closed. A dropdown
    already set is left alone rather than reopened, so running this against an already filtered
    board reads the window, finds nothing to do and OKs straight back out.

    reset clears the window first and is the one thing the two modes do differently, which is
    why this is one function with a flag rather than the two near-copies it used to be. Only
    the sniper passes it. Leaving a board's existing filters alone is right for a mode that
    lists items and wrong for one that buys them: a filter we did not set is a board we are not
    reading all of, and an offer missed is invisible in a way a wrong price is not. Whatever
    the sniper wants next (price ceilings, a barter toggle) goes here behind its own argument,
    or forks the function again if the two ever stop sharing this tail.

    'Remember selected filter' is deliberately not touched. It used to be ticked here, and the
    tick was confirmed on screen straight after the click, but reopening the window showed the
    box empty again every time: the setting does not survive the OK. Clicking a control the
    game throws away bought a click, two reads and a failure path that could abort the whole
    filter step, in exchange for nothing.
    """
    if not open_filters(region):
        return False

    if reset:
        point = jitter(find.find_center(RESET_TARGET, region))
        if not point:
            log(f'no {RESET_TARGET} on the flea filter window', 1)
            return False
        log(f'resetting the filters at {point}', 1)
        pyautogui.click(*point)
        time.sleep(FILTER_MENU_DELAY)
        if not open_filters(region):  # the reset closes the window along with clearing it
            return False

    # Every read from here on is a filter control, and they all live in the modal that is now
    # cornered, so scope the finds to it rather than the whole 2560x1440 window.
    window_region = filter_window_region(region)

    for attempt in range(1, FILTER_ATTEMPTS + 1):
        plan = filter_plan(window_region, source, set_condition)
        if plan is None:
            # A window that will not read is not a window to click at, and another look reads
            # the same thing, so this is out rather than round again.
            return False
        if not plan.dropdowns and not plan.condition:
            log('every filter already reads what it should, nothing to set', 1)
            break
        wanted = [d.name for d, _ in plan.dropdowns] + (['condition'] if plan.condition else [])
        log(f'attempt {attempt}/{FILTER_ATTEMPTS}: setting {wanted}', 1)
        if not run_filter_plan(plan, window_region):
            return False
        settled, unset = confirm_filters([d for d, _ in plan.dropdowns], window_region)
        if settled:
            break
        log(f'{unset} did not take on attempt {attempt}', 1)
    else:
        log(f'the filters never settled in {FILTER_ATTEMPTS} attempts', 1)
        return False

    point = jitter(find.find_center(FILTERS_OK_TARGET, window_region))  # applies them and shuts the window
    if not point:
        log('no OK button on the flea filter window', 1)
        return False
    log(f'OK out of the filter window at {point}', 1)
    pyautogui.click(*point)
    time.sleep(FILTER_MENU_DELAY)
    return True


def orientate_scav_box(region=None, corner=SCAV_CORNER, duration=DRAG_SECONDS,
                       repeats=DRAG_REPEATS):
    """Drag the opened scav case window into a corner of the monitor, by its title bar.

    Returns the last point it grabbed, or None if the title bar was never found.

    corner: any name _corner_point knows, the top left by default. It moves to the top right
    for the filter step and back afterwards, the same way the offer window does.
    """
    point = _drag_to_corner(SCAV_WINDOW_TARGET, corner, region, duration, repeats)
    log(f'dragged the scav case window to the {corner} by {point}' if point
        else 'scav case window not on screen to drag', 1)
    return point


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


def select_item_from_random_scav_case(region=None, attempts=SELECT_ATTEMPTS, stop=None):
    """Grab a random item from the open scav case and filter by it on the flea.

    Assumes the case is already open and orientated. Same flow as
    select_item_from_inventory, just over the scav case grid instead of the stash: left click,
    ask the offer panel whether anything got selected, and only then go for the right-click
    menu. Returns the clicked (x, y), or None if every attempt missed.

    stop: as the inventory loop, a threading.Event that abandons the attempts at once.
    """
    for attempt in range(1, attempts + 1):
        if stop is not None and stop.is_set():
            log(f'stop asked for after {attempt - 1} attempt(s), abandoning the selection', 2)
            return None
        points = find_scav_case_pixels(region)
        if not points:
            log('no live pixels in the scav case, it is empty', 1)
            return None  # an empty case will not fill itself on a retry
        chosen = random.choice(points)
        log(f'attempt {attempt}/{attempts}: {len(points)} live pixels, clicking {chosen}', 2)
        pyautogui.click(*chosen)
        if _sleep(SELECT_POLL_DELAY, stop):  # cut short means stop, not a poll that finished
            log('stop asked for while waiting on the offer panel, abandoning the selection', 2)
            return None
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
            # Same as the inventory path above, and for the same reason. Worse here if anything:
            # the escape lands on the scav case window, which the caller then has to reopen.
            if dismiss_error_popup(region):
                log('an error dialog took the right click, cleared it and picking again', 2)
                continue
            # Same as the inventory path, and the count is why it has to be the caller's job
            # rather than a press here: this screen has the case window sat on the offer
            # creation window, so backing out of it takes SCAV_ESCAPES and not one. select_item
            # has already set that on the Selection by the time this returns.
            log('no filter by item in the menu, backing out for a fresh pass', 2)
            return None
        point = jitter(pyautogui.center(box), y=0)  # a 6px tall crop says nothing about the row
        log(f'clicking filter by item at {point}', 2)
        pyautogui.click(*point)
        time.sleep(SELECT_WINDOW_DELAY)  # the flea panel has to catch up before we read it
        return point
    log(f'all {attempts} attempts missed', 1)
    return None


if __name__ == '__main__':  # the geometry, checked without needing Tarkov open
    from pyscreeze import Box
    # All button ends at 1258, autoselect similar spans 1600-1620 and ends at y 80, auto-sort
    # ends at y 920. Every number below is those edges plus the three pads, so retuning a pad
    # moves this line too: left 1258+LEFT_PAD, top 80+TOP_PAD, right 1620+RIGHT_PAD,
    # bottom 920+BOTTOM_PAD.
    assert _region_from(Box(1232, 82, 26, 24), Box(1600, 60, 20, 20),
                        Box(1200, 900, 30, 20)) == (1288, 110, 302, 800)
    try:  # autoselect similar left of the grid's left edge would invert it
        _region_from(Box(1232, 82, 26, 24), Box(100, 60, 20, 20), Box(1200, 900, 30, 20))
        raise AssertionError('expected LookupError')
    except LookupError:
        pass

    assert len(DEAD_COLOURS) > 100, f'{DEAD_REFERENCE}/ gave only {len(DEAD_COLOURS)} colors'
    one = _dead_cube(np.array([_pack(np.array([100, 100, 100]))]), tol=5)  # tolerance, on its own
    assert one[100, 100, 100] and one[105, 100, 95], 'within 5 on every channel is dead'
    assert not one[106, 100, 100], '6 off on any channel is alive'
    assert calculate_dead_pixel((23, 24, 24)) and not calculate_dead_pixel((200, 0, 0))
    img = np.full((3, 4, 3), (23, 24, 24), dtype=np.uint8)  # 3 rows, 4 cols of empty slot
    img[0, 0] = (24, 25, 25)  # another slot color, still empty
    img[1, 2] = (200, 0, 0)  # an item, at row 1 col 2
    img[2, 3] = (0, 200, 0)  # another item, at row 2 col 3
    assert _live_points(img, (100, 200)) == [(102, 201), (103, 202)], 'x/y swapped?'
    assert _live_points(img, (100, 200), exclude=[(102, 201, 103, 202)]) == [(103, 202)]
    assert _live_points(img, (100, 200), exclude=[(0, 0, 50, 50)]) == [(102, 201), (103, 202)]  # off the crop
    assert _expand(Box(100, 200, 20, 40), 0.10) == (98, 196, 122, 244)
    PRIMARY = (0, 0, 1920, 1080)  # a monitor at the origin, and one to the left of it
    LEFT_OF_IT = (-1920, 0, 1920, 1080)
    assert _crop_to((98, 196, 122, 244), PRIMARY) == (98, 196, 24, 48)  # well inside the screen
    assert _crop_to((-6, -4, 30, 40), PRIMARY) == (0, 0, 30, 40)  # grown off the top left
    assert _crop_to((1900, 1060, 1950, 1100), PRIMARY) == (1900, 1060, 20, 20)  # off the bottom right
    # The same crop on the monitor to the left clips to that monitor's edges, not to zero.
    assert _crop_to((-1926, -4, -1890, 40), LEFT_OF_IT) == (-1920, 0, 30, 40)
    assert _crop_to((-100, 10, 40, 50), LEFT_OF_IT) == (-100, 10, 100, 40), 'clipped at its right edge'
    # Dropdowns are opened at pyautogui.center of whatever matched, so a crop's centre is the
    # click target and its edges are not. Nothing local to assert; the crops carry this now.
    assert _corner_point('top left', PRIMARY) == (0, 0)
    assert _corner_point('bottom left', PRIMARY) == (0, 1079), 'last row, not one past it'
    # And on the monitor to the left, the corners are that monitor's, not the primary's.
    assert _corner_point('top left', LEFT_OF_IT) == (-1920, 0)
    assert _corner_point('bottom left', LEFT_OF_IT) == (-1920, 1079)
    assert _corner_point('bottom right', PRIMARY) == (1919, 1079), 'last column and last row'
    assert _corner_point('bottom right', LEFT_OF_IT) == (-1, 1079), 'the column left of the primary'
    assert _corner_point('top right', PRIMARY) == (1919, 0), 'last column, first row'
    assert _corner_point('top right', LEFT_OF_IT) == (-1, 0)
    try:
        _corner_point('middle', PRIMARY)
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

    # Stop lands inside the select loop rather than at the end of it. Faked down to the three
    # things the loop touches, since the real one wants a screen and a game: what is being
    # checked is where the stop is read, not whether a click hits an item.
    import threading

    clicks = []
    saved = {name: globals()[name] for name in ('find_sell_pixels', 'is_item_selected',
                                                '_park_cursor')}
    real_click = pyautogui.click
    try:
        globals()['find_sell_pixels'] = lambda region=None: [(1, 1)]
        globals()['is_item_selected'] = lambda region=None: False  # every attempt misses
        globals()['_park_cursor'] = lambda: None
        pyautogui.click = lambda *args, **kwargs: clicks.append(args)

        assert select_item_from_inventory(stop=threading.Event()) is None, 'every attempt missed'
        assert len(clicks) == SELECT_ATTEMPTS, \
            f'an unset stop runs every attempt, got {len(clicks)} of {SELECT_ATTEMPTS}'

        clicks.clear()
        already = threading.Event()
        already.set()
        assert select_item_from_inventory(stop=already) is None, 'a set stop returns at once'
        assert clicks == [], 'and it never clicked: the stop is read before the screenshot'
    finally:
        globals().update(saved)
        pyautogui.click = real_click
    print('ok')
