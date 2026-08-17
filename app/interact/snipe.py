"""Everything the flea sniper does to a screen.

Separate module for the same reason interact/gym.py is one: it shares find.py and narrate.py
with interact/sell.py and nothing else. Sniping runs the flea backwards from selling. Selling
picks an item out of the stash and creates an offer; sniping types a name into the flea's own
search box, reads the cheapest offer on the board, and buys it if it is under trader value.

Getting on and off the flea is not repeated here. sell.open_flea, sell.is_flea_open and
sell.return_to_browse are already the shipping versions of all three, and a second copy of them
would be a second thing to keep in step with the game's UI. apply_flea_filters *is* copied,
because it is the step that will diverge: the sniper wants a buyer's filters, not a seller's.

Geometry self-check, no game needed:  python -m interact.snipe
"""
import time

import numpy as np
import pyautogui

import screen
from interact import find, ocr, sell
from narrate import log

SEARCH_BOX_TARGET = 'flea_enter_item_name_input'  # the flea's own item name field
PURCHASE_TARGET = 'flea_purchase_button'  # one per offer row, so there are many on a full board
# The padlock beside a suggestion the account cannot buy. Looked for over the window's top left
# quarter, which is where the suggestion list drops (see reference_image.png in
# _item_search_testing): searching the whole window would find a padlock anywhere in the UI,
# and searching a box around one row would have to know how many rows there are first.
LOCKED_TARGET = 'flea_item_locked_icon'
# Clears every filter on the flea's filter window, and closes it doing so. The sniper's own
# step: see apply_flea_filters for why a buyer resets and a seller does not.
RESET_TARGET = 'flea_filters_reset_button'
# The chip the flea shows above the board when it is filtered to one item, and the little x that
# clears a chip. There is an x per chip, so they are found together and the leftmost one is
# taken: the chips read left to right and the item filter is the first of them.
FILTER_APPLIED_TARGET = 'filter_by_item_filter_applied'
CLEAR_FILTER_TARGET = 'clear_filter_button'

# Where the first suggestion under the search box lands, in heights of the box itself. The box
# is the only thing on that part of the screen with a reference crop, and the suggestion list it
# drops has none, so the row is aimed at rather than matched: 1.5 box heights below the box's
# bottom edge, on its centre line. Measured in the box's own height rather than pixels so it
# scales with the screen the way every other geometry in this repo does.
SUGGESTION_DROP = 1.5

# The offer row's price, as an offset from that row's PURCHASE button's top left corner, in
# 1080p pixels like every other measurement here. The price has no reference crop of its own and
# could not have one, since the number inside it is the thing being read, so it is located off
# the one element on the row that does: fixed offsets from the button, the same trick
# sell.grab_price_region plays against the window.
#
# Measured off 250 recorded frames of a real 1440p board, 1957 rows read: the button sits at
# (2284, 226) 161x32 and the price block spans x 1819-1960 on rows y 214-247, which is
# -484,-14 from the button's corner at 1440p and these numbers once divided by find.scale().
# Every row on every frame read back the price the board was showing.
PRICE_LEFT = -363    # left edge of the price box, from the button's left edge
PRICE_TOP = -11      # top edge, from the button's top edge
PRICE_WIDTH = 128
PRICE_HEIGHT = 29
# The empty strip at the left of that box, which has to stay empty. A price wider than the box
# is a price whose leading digits have been cut off, and a cut price reads low, which is exactly
# the direction that makes the sniper buy. Refusing to read is the only safe answer.
PRICE_GUTTER = 8     # 1080p px of the box's left edge that must have nothing lit in it
PRICE_LIT = 140      # brightest channel that counts as text rather than background

# Seconds between the last keystroke and the click at the suggestion. The list is not drawn the
# moment typing stops: the flea goes away and looks the name up, and clicking into the gap lands
# on whatever was underneath, which is the board rather than a suggestion.
# The rouble balance in the flea's header, as fractions of the window: (left, top, right,
# bottom). Fractions rather than pixels for the same reason gym.REP_ROI_FRACTIONS is: there is
# nothing here to template match, since the number inside is the thing being watched.
#
# It is not read, only photographed. Whether a purchase actually went through is answered by
# whether this rectangle changed, which is a far cheaper question than what the number says and
# does not care that the balance is drawn with thin spaces between its thousands.
#
# Tune with:  python tests/test_ruble_region.py
# Measured off a 2560x1440 flea: the balance occupies x 1943-2112, y 93-131, which is
# 0.759-0.825 across and 0.065-0.091 down. Padded a little each way, so a longer or shorter
# number still lands inside rather than growing out of the box.
RUBLE_ROI_FRACTIONS = (0.75, 0.055, 0.84, 0.10)

SEARCH_DELAY = 3.0
BOARD_DELAY = 3.0    # seconds for the board to repopulate after a suggestion is clicked
FILTER_SETTLE = 1.0  # seconds for the reopened flea's header to draw its filter chips
BUY_CONFIRM_DELAY = 0.1  # seconds between the purchase click and the key that confirms it
BUY_CONFIRM_KEY = 'y'    # what Tarkov's purchase confirmation is bound to
BUY_CANCEL_KEY = 'n'     # and what answers it no, for a dialog that will not take the yes
BUY_SETTLE = 0.6         # seconds for the dialog to close and the balance to redraw

# Whether a purchase actually happened, measured off the balance box either side of the click.
# Both numbers come from real captures and both are needed, because either one alone gets it
# wrong.
#
# BALANCE_MOVED: the fraction of pixels that have to differ by more than 20 on a channel. A real
# purchase moved 13.6% of them; two grabs of an unchanged balance move 0.000%. 2% sits in the
# middle of a gap that wide with room to spare either side.
#
# BALANCE_DIM: how much darker the second grab may be before it is read as a dialog still
# covering the screen rather than a balance that changed. Tarkov dims everything behind the
# purchase confirmation, and that dimming *by itself* moves 12.8% of these pixels, which is
# indistinguishable from the 13.6% a real purchase moves. So a pixel count alone cannot tell a
# purchase from a confirmation that never got answered, and that is precisely the failure this
# whole check exists to catch: the run of 2026-08-17 counted 55,000 roubles of purchases whose
# dialogs were still sat on screen. Brightness separates them cleanly. Measured: a real purchase
# left the box at 0.95 of its old mean, a stuck dialog at 0.50.
BALANCE_MOVED = 0.02
BALANCE_DIM = 0.75


def _open_filters(region=None):
    """Click the flea's filter gear. True once the click has gone out.

    Its own function because the sniper opens that window twice: once to reset it and once to
    fill it in. GEAR_JITTER rather than the usual spread, since the gear is small.
    """
    point = sell.jitter(find.find_center(sell.FILTER_BUTTON_TARGET, region),
                        sell.GEAR_JITTER, sell.GEAR_JITTER)
    if not point:
        log('no filter button on screen', 1)
        return False
    log(f'opening the filter window at {point}', 1)
    pyautogui.click(*point)
    time.sleep(sell.MENU_DELAY)
    return True


def apply_flea_filters(region=None):
    """Reset the flea's filters, then set roubles, player offers and 100% condition, and OK out.

    Five steps: open the filter window, click reset, open it again (the reset closes it), fill it
    in, OK. The reset is what makes this a buyer's version. Whatever the board was left filtered
    by, from a previous session or from a hand, is gone before anything is set, so the board the
    sniper reads is only ever the one it asked for.

    A copy of sell.apply_flea_filters rather than a call to it, and deliberately so: the seller
    wants the board filtered the way a seller reads it, and the sniper is about to want
    something else entirely (price ceilings, a barter toggle, offers it can actually afford).
    Two callers of one function would mean every change to one having to be safe for the other.

    The private helpers it leans on are still sell's. Copying _set_dropdown and
    _set_condition_from as well would be copying the part that is not going to change, and each
    of those carries a paragraph of hard-won detail about which crop matches what.
    """
    if not _open_filters(region):
        return False

    # Reset first, then start again from a window we know the state of. The seller does not do
    # this and does not need to: it only ever touches a dropdown while that dropdown still says
    # 'any', so a board somebody already filtered is left exactly as it was found. That is the
    # right call for a mode that lists items and the wrong one for a mode that buys them,
    # because a filter we did not set is a board we are not reading all of, and an offer missed
    # is invisible in a way a wrong price is not.
    point = sell.jitter(find.find_center(RESET_TARGET, region))
    if not point:
        log(f'no {RESET_TARGET} on the flea filter window', 1)
        return False
    log(f'resetting the filters at {point}', 1)
    pyautogui.click(*point)
    time.sleep(sell.MENU_DELAY)

    # Reopened, because the reset closes the window along with clearing it.
    if not _open_filters(region):
        return False

    if not sell._set_dropdown(sell.CURRENCY_ANY_TARGET, sell.CURRENCY_RUBLES_OPTION,
                              sell.CURRENCY_RUB_TARGET, region, sell.DROPDOWN_DELAY):
        return False
    if not sell._set_dropdown(sell.OFFERS_FROM_ANY_TARGET, sell.OFFERS_FROM_PLAYERS_OPTION,
                              sell.OFFERS_FROM_PLAYERS_TARGET, region, sell.OFFERS_FROM_DELAY):
        return False
    if not sell._set_condition_from(region):
        return False

    point = sell.jitter(find.find_center(sell.FILTERS_OK_TARGET, region))
    if not point:
        log('no OK button on the flea filter window', 1)
        return False
    log(f'OK out of the filter window at {point}', 1)
    pyautogui.click(*point)
    time.sleep(sell.MENU_DELAY)
    return True


def open_flea(region=None):
    """Open the flea, shut it, open it again. True once it is open.

    Not sell.open_flea called once, and the difference is deliberate. Reopening the flea puts
    its header back to the state the sniper needs: the filter chips come back to the front, so
    a filter-by-item left over from before is visible and can be cleared. A flea that was
    already open, or that was opened once, can be sat on some other view with those chips
    scrolled out of reach.

    Escape rather than clicking the taskbar icon a second time, because the icon toggles on
    brightness and sell.open_flea would read it as already open and not click at all.
    """
    if not sell.open_flea(region):
        return False
    log('closing the flea again, so reopening it brings the filter chips to the front', 1)
    pyautogui.press('esc')
    time.sleep(sell.WINDOW_DELAY)
    return sell.open_flea(region)


def open_clean_board(region=None):
    """Get the flea up with nothing filtering it by item. True once the board is ready.

    The whole opening: open, escape, open again, let the header draw, and clear a leftover
    filter-by-item if one is showing. Only then is the board the sniper searches against the
    whole board rather than one item's worth of it.

    The wait after clearing is the board reloading, and it only happens when something was
    actually cleared: a run that starts on a clean board has nothing to wait for.
    """
    if not open_flea(region):
        return False
    time.sleep(FILTER_SETTLE)  # the header's chips are drawn after the window itself
    if remove_filter_by_item_filter(region):
        log(f'filter cleared, giving the board {BOARD_DELAY}s to reload', 1)
        time.sleep(BOARD_DELAY)
    return True


def remove_filter_by_item_filter(region=None):
    """Clear a filter-by-item chip off the board. True if one was there and got clicked.

    Three steps and it gives up at the first one that comes back empty:

      1. is the board filtered to an item at all (FILTER_APPLIED_TARGET)? If not, there is
         nothing to remove and False is the honest answer, not a failure.
      2. find every clear-filter x on screen (CLEAR_FILTER_TARGET). There is one per chip.
      3. click the centre of the leftmost. The chips read left to right and the item filter is
         the first of them, so leftmost is the one asked for.

    The applied check comes first rather than just looking for an x, and that ordering is the
    point of the function. CLEAR_FILTER_TARGET is a 12 to 14 pixel crop of a small plain glyph,
    which is exactly the shape of target CLAUDE.md warns has no false-positive headroom, so
    something bigger and more distinctive has to say the chip is there before its x is trusted.
    """
    if not find.find(FILTER_APPLIED_TARGET, region):
        log('no filter-by-item chip on the board, so there is nothing to clear', 1)
        return False

    buttons = find.find_all(CLEAR_FILTER_TARGET, region)
    if not buttons:
        log(f'the board says it is filtered by item but no {CLEAR_FILTER_TARGET} is on screen '
            f'to clear it', 1)
        return False

    leftmost = min(buttons, key=lambda box: box.left)
    point = sell.jitter(pyautogui.center(leftmost))
    log(f'{len(buttons)} clear-filter button(s), clicking the leftmost at {point} '
        f'(box {tuple(leftmost)})', 1)
    pyautogui.click(*point)
    time.sleep(sell.MENU_DELAY)
    return True


def find_search_box(region=None, cached=None):
    """The flea's search box, or `cached` if it cannot be found, or None if there is neither.

    Every crop under flea_enter_item_name_input/ is of the *placeholder* text, 'enter item
    name', which the field only shows while it is empty. That makes the box findable exactly
    once per name: after the typing there is nothing there to match until it is cleared again.

    So the box is remembered. A find that comes back empty when we already know where the box
    was means the field still has text in it, which is a clear that did not take rather than a
    flea that has moved, and the answer to that is to click the box we know about and clear it
    again. Without this one failed clear ends the sweep: every item after it fails to find the
    box, types nothing, and the run does nothing but log.

    A cold start with text already in the field is the one case neither can help, since there is
    no cached box yet either. That returns None and says so.
    """
    box = find.find(SEARCH_BOX_TARGET, region)
    if box:
        return box
    if cached:
        log(f'{SEARCH_BOX_TARGET} did not match, so the field still has text in it; using the '
            f'box we found it at, {tuple(cached)}', 1)
        return cached
    log(f'{SEARCH_BOX_TARGET} not on screen. If the flea is open, its search box already has '
        f'something typed in it: clear it and start again', 1)
    return None


def ruble_region(region):
    """The rouble balance's rectangle, as (left, top, width, height) in screen coords.

    RUBLE_ROI_FRACTIONS applied to the game window. Screen coords in and screen coords out, so
    a Tarkov on a monitor left of the primary keeps its negative left edge.
    """
    left, top, width, height = region
    x0, y0, x1, y1 = RUBLE_ROI_FRACTIONS
    return (left + round(width * x0), top + round(height * y0),
            round(width * (x1 - x0)), round(height * (y1 - y0)))


def grab_player_ruble_image(region):
    """A picture of the rouble balance right now.

    Taken either side of a purchase and compared. A click that bought something moves the
    balance and so changes these pixels; a click whose confirmation dialog never got answered
    leaves them identical. That is the difference between counting what the bot did and counting
    what it meant to do, and the run of 2026-08-17 counted two purchases that never happened for
    exactly this reason.

    screen.grab rather than screen.fast_grab: fast_grab's pixels come back one or two levels a
    channel off Pillow's, and this is a comparison between two captures.
    """
    return screen.grab(ruble_region(region))


def top_left_quadrant(region):
    """The top left quarter of `region`, as (left, top, width, height) in the same coords.

    Halves rounded down, so the four quadrants of an odd sized window do not overlap. The
    region comes in as screen coordinates and goes out as screen coordinates: nothing here may
    assume a window starts at (0, 0), since Tarkov on a monitor left of the primary has a
    negative left edge.
    """
    left, top, width, height = region
    return (left, top, width // 2, height // 2)


def is_locked(region):
    """True if a padlock is showing in the window's top left quarter.

    That quarter is where the suggestion list drops, and a padlock in it means the item cannot
    be bought by this account: too low a level, or an offer the flea will not sell us. Buying is
    skipped rather than attempted, because the click would either do nothing or open something
    we then have to escape out of.

    Looking over the whole quarter rather than at one row is only safe because the list has
    exactly one row in it. Every name on the watchlist was typed into a real flea and
    photographed (see _item_search_testing/), and the fourteen that brought back several rows or
    none were dropped from snipe_targets.csv. One row means one padlock to find and no question
    of whose it is. Put an ambiguous name back on that list and this reads the wrong row's lock,
    so the two belong together: _price_scraper/rouble_flips.py's AMBIGUOUS set is what keeps
    this honest.

    A missing reference_images/flea_item_locked_icon/ raises out of find, and is meant to. This
    is the check that stands between the sniper and clicking purchase on an item it cannot buy,
    so it failing quietly is worse than the run stopping and saying which folder is empty.
    """
    box = find.find(LOCKED_TARGET, top_left_quadrant(region))
    if box:
        log(f'a locked padlock is showing at {tuple(box)}, so this one cannot be bought', 1)
    return box is not None


def search_for(name, box, region=None):
    """Type an item name into the flea's search box, pick the suggestion, then empty the box.

    Returns the suggestion point clicked, or None if the item came back locked and was left
    alone. `box` is the search box as find_search_box gave it, and everything here is aimed from
    it: the suggestion list that drops has no reference image of its own, so the box is the only
    thing on that part of the screen worth measuring from.

    The padlock is read while the list is still up, which is the only moment it can be: the list
    closes the instant a suggestion is clicked. A locked item is not clicked at all, so the
    board is left showing whatever it showed before and nothing downstream has to know.

    Emptying the box is the last step rather than the first. Clearing it *before* typing would
    do just as well for the field, but it would leave the previous item's name in it for the
    whole of the read that follows, and the board underneath is filtered by whatever the field
    holds. Clearing straight after the suggestion is clicked leaves the board showing the item
    that was picked and the field ready for the next name.

    Ctrl+A then backspace rather than a bare backspace, for the reason sell.enter_price gives:
    Tarkov's text fields append rather than replace, so a field left half full would look the
    next item up under two names at once and find nothing.
    """
    log(f'search box at {tuple(box)}, typing {name!r} into it', 1)
    pyautogui.click(*sell.jitter(pyautogui.center(box)))
    time.sleep(sell.MENU_DELAY)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(name)
    time.sleep(SEARCH_DELAY)

    if region is not None and is_locked(region):
        clear_search(box)  # still emptied, or the next name goes in on top of this one
        return None

    point = suggestion_point(box)
    log(f'clicking the first suggestion at {point}, {SUGGESTION_DROP} box heights under the '
        f'box bottom at {box.top + box.height}', 1)
    pyautogui.click(*point)
    time.sleep(sell.MENU_DELAY)

    clear_search(box)
    return point


def clear_search(box):
    """Empty the search box, given the box as it was found before anything was typed.

    Takes the box rather than looking for it again on purpose. By the time this runs the field
    has a name in it, and every crop under flea_enter_item_name_input/ is of an empty one, so a
    fresh find() here would come back with nothing and leave the field full.
    """
    point = sell.jitter(pyautogui.center(box))
    log(f'clearing the search box at {point}', 1)
    pyautogui.click(*point)
    time.sleep(sell.MENU_DELAY)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    time.sleep(sell.MENU_DELAY)
    return point


def suggestion_point(box):
    """Where the first suggestion sits, given the search box as it was before anything was typed.

    Kept out of search_for so the arithmetic can be checked without a screen: this is the one
    step that is a calculation rather than a match, and a wrong one clicks a row that is not
    there or the wrong row on the list.
    """
    return (box.left + box.width // 2,
            box.top + box.height + round(box.height * SUGGESTION_DROP))


def purchase_buttons(region=None):
    """Every PURCHASE button on the board, topmost first. One per offer row."""
    return sorted(find.find_all(PURCHASE_TARGET, region), key=lambda box: box.top)


def price_region(button):
    """The screen rect holding the price on `button`'s own offer row.

    Scaled by find.scale() for the same reason every reference image is: the offsets were
    measured on a 1440p board and written down at 1080p, which is the one size everything in
    this repo is derived from.
    """
    factor = find.scale()
    return (button.left + round(PRICE_LEFT * factor),
            button.top + round(PRICE_TOP * factor),
            round(PRICE_WIDTH * factor),
            round(PRICE_HEIGHT * factor))


def read_price(button):
    """The asking price on `button`'s row as an int, or None if it cannot be read safely.

    Two ways to come back None, and they mean different things. Nothing matched means the
    glyphs were not the price font, which is ocr.read_number being all or nothing about it.
    Something lit in the gutter means the number is wider than its box, so its leading digits
    are outside the crop: a six figure price read as its last three is a bargain that is not
    there, and this is a function whose answer gets money spent on it.
    """
    rect = price_region(button)
    crop = screen.grab(rect)
    if _clipped(crop):
        log(f'price at {rect} runs into the left edge of its box, so it is cut off and will '
            f'not be trusted', 1)
        return None
    factor = find.scale()
    if factor != 1.0:  # the same shrink ocr.read_region does, see the note there
        crop = crop.resize((max(1, round(crop.width / factor)),
                            max(1, round(crop.height / factor))))
    price = ocr.read_number(crop)
    log(f'read the offer price box at {rect}: '
        + (f'{price}' if price is not None else 'no glyph matched, unreadable'), 1)
    return price


def _clipped(crop):
    """True if anything is lit in the crop's left gutter, which means the price overflows it."""
    gutter = np.array(crop.convert('RGB'))[:, :max(1, round(PRICE_GUTTER * find.scale()))]
    return bool((gutter.max(axis=2) > PRICE_LIT).any())


def purchase_landed(before, after):
    """True if the balance moved between these two grabs, and money therefore left the stash.

    Two tests, and both have to be here. See BALANCE_MOVED and BALANCE_DIM: the dimming behind
    an unanswered confirmation dialog moves almost exactly as many pixels as a real purchase
    does, so counting changed pixels on its own says yes to both. The brightness check is what
    tells them apart, and it goes first, because a dimmed grab says nothing about the balance
    either way.
    """
    a = np.asarray(before.convert('RGB')).astype(int)
    b = np.asarray(after.convert('RGB')).astype(int)
    if a.shape != b.shape:  # a resized window mid purchase, which is nobody's happy path
        log(f'the balance box changed size between grabs, {a.shape} then {b.shape}', 1)
        return False

    ratio = b.mean() / a.mean() if a.mean() else 1.0
    if ratio < BALANCE_DIM:
        log(f'the screen is {ratio:.2f} of its old brightness, so the purchase dialog is still '
            f'up and nothing has been bought', 1)
        return False

    moved = (np.abs(a - b).max(axis=2) > 20).mean()
    log(f'{moved:.1%} of the balance box moved (needs {BALANCE_MOVED:.0%}), brightness ratio '
        f'{ratio:.2f}', 1)
    return moved >= BALANCE_MOVED


def buy(button, region):
    """Click a PURCHASE button, confirm it, and check the money actually left. True if it did.

    The confirmation is a keypress rather than a second match: Tarkov's buy dialog answers to
    the same key wherever it lands on screen, so there is nothing to find and nothing that can
    fail to be found. What there is, is a dialog that sometimes does not take the key at all,
    which is why nothing here is taken on trust and the balance is read either side.

    A second yes is sent if the first did not land. It cannot double buy: with no dialog on
    screen the key does nothing. If that fails too the dialog is answered no, so a confirmation
    nobody answered cannot sit there swallowing the clicks of every item after this one.
    """
    before = grab_player_ruble_image(region)
    point = sell.jitter(pyautogui.center(button))
    log(f'purchasing at {point}, confirming with {BUY_CONFIRM_KEY!r} in '
        f'{BUY_CONFIRM_DELAY}s', 1)
    pyautogui.click(*point)
    time.sleep(BUY_CONFIRM_DELAY)
    pyautogui.press(BUY_CONFIRM_KEY)
    time.sleep(BUY_SETTLE)

    if purchase_landed(before, grab_player_ruble_image(region)):
        return True

    log(f'that did not take, pressing {BUY_CONFIRM_KEY!r} once more', 1)
    pyautogui.press(BUY_CONFIRM_KEY)
    time.sleep(BUY_SETTLE)
    if purchase_landed(before, grab_player_ruble_image(region)):
        return True

    log(f'still nothing, answering {BUY_CANCEL_KEY!r} so the dialog cannot block the next item', 1)
    pyautogui.press(BUY_CANCEL_KEY)
    time.sleep(BUY_SETTLE)
    return False


if __name__ == '__main__':  # the geometry, checked without needing Tarkov open
    from pyscreeze import Box

    # The suggestion click, which is the one step that is arithmetic rather than a match.
    # A 150x20 box at (400, 300) has its bottom at 320, and 1.5 heights under that is 350.
    assert suggestion_point(Box(400, 300, 150, 20)) == (475, 350)
    assert suggestion_point(Box(400, 300, 150, 40)) == (475, 400), 'a taller box drops further'

    # The price box, off the button that was actually measured. At 1080p the offsets are used
    # as written; find.scale() is what a real screen multiplies them by.
    scale = find.scale
    find.scale = lambda: 1.0
    assert price_region(Box(2284, 226, 161, 32)) == (1921, 215, 128, 29)
    find.scale = lambda: 1440 / 1080  # the board these numbers were measured on
    assert price_region(Box(2284, 226, 161, 32)) == (1800, 211, 171, 39)
    find.scale = scale

    # The quarter the padlock is looked for in. Screen coords in, screen coords out, and the
    # halves round down so the four quadrants of an odd sized window cannot overlap.
    assert top_left_quadrant((0, 0, 1920, 1080)) == (0, 0, 960, 540)
    assert top_left_quadrant((1920, 0, 2560, 1440)) == (1920, 0, 1280, 720), 'second monitor'
    assert top_left_quadrant((-1920, 0, 1920, 1080)) == (-1920, 0, 960, 540), 'left of primary'
    assert top_left_quadrant((0, 0, 1921, 1081)) == (0, 0, 960, 540), 'odd sizes round down'

    # The purchase check, which is the one piece of arithmetic here that spends money by being
    # wrong. Numbers are the measured ones: a real purchase moved 13.6% of the box's pixels at
    # 0.95 of its brightness, a stuck dialog moved 12.8% at 0.50.
    from PIL import Image

    def box(digits_at=0, width=15, dim=1.0):
        """A stand-in balance box: a bright block of 'digits' on a dark ground.

        Moving the block is a balance that changed. dim=0.5 is what the purchase dialog does to
        everything behind it, which darkens the digits as well as the ground, and getting that
        right is the whole point of the fixture: painting bright pixels *onto* a dark box raises
        its mean instead of lowering it, and reads as no dialog at all.
        """
        a = np.full((20, 100, 3), 25.0)
        a[:, digits_at:digits_at + width] = 200.0
        return Image.fromarray((a * dim).clip(0, 255).astype('uint8'))

    plain = box()
    assert not purchase_landed(plain, box()), 'an unchanged balance is not a purchase'
    assert purchase_landed(plain, box(digits_at=8)), 'a balance that changed is a purchase'
    assert not purchase_landed(plain, box(width=16)), 'a hair of noise is not a purchase'
    # The two that matter. A confirmation dialog left on screen moves as many of these pixels as
    # a real purchase does, so only the brightness tells them apart, and both must read False.
    assert not purchase_landed(plain, box(digits_at=8, dim=0.5)), 'dimmed means a live dialog'
    assert not purchase_landed(plain, box(dim=0.5)), 'dimmed and unchanged, still a live dialog'

    print('ok, the suggestion point, the price box and the purchase check all agree with '
          'what was measured')
