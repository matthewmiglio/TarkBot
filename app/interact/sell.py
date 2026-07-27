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

# The buttons framing the inventory grid: (left edge, right and top edge, bottom edge)
EDGES = ('inventory_all_button', 'autoselect_similar', 'auto_sort')
SCAV_MARGIN = 0.15  # scav case boxes grow this much per side before their pixels are dropped
# Every colour an empty slot is known to take, read off screenshots showing nothing but empty
# slots. Drop another png in that folder to teach it more. ponytail: the images are the list.
DEAD_REFERENCE = 'dead_pixels'  # a folder under reference_images/, any number of pngs
DEAD_TOL = 5  # per-channel slack; this close to a known slot colour still counts as empty
MENU_DELAY = 0.3  # seconds for the right-click menu to draw before we go looking for it
WINDOW_DELAY = 1.0  # seconds for a window to finish appearing before we grab its title bar
SELECT_ATTEMPTS = 50  # clicks to try before admitting we cannot land on an item
# The select loop runs up to SELECT_ATTEMPTS times, so it uses half the usual waits: a miss
# now costs a left click and a glance at the offer panel, not a whole right-click menu round.
SELECT_POLL_DELAY = MENU_DELAY / 2  # after a click, before reading what it did
SELECT_WINDOW_DELAY = WINDOW_DELAY / 2  # after filter by item, for the flea panel to catch up
ADD_OFFER_TARGET = 'add_offer'  # the button that opens the offer creation window
OFFER_TARGET = 'offer_creation'  # reference images for the offer creation window
SCAV_WINDOW_TARGET = 'scav_case_window_title'  # reference images for the opened scav case window
CLOSE_BUTTON_TARGET = 'close_window_button'  # several are on screen at once, we want the leftmost
NO_SELECTION_TARGET = 'no_items_selected'  # the placeholder shown while nothing is picked
FLEA_ICON_TARGET = 'flea_icon'  # the taskbar entry, one folder holding both its states
FLEA_OPEN_BRIGHTNESS = 90  # mean channel value: measured 57 closed, 117 open
# The suggested price readout, as (left, top, right, bottom) fractions of the window.
# Measured at 1920x1080: left 1339, top 147, right 1498, bottom 186.
PRICE_FRACTIONS = (1339 / 1920, 147 / 1080, 1498 / 1920, 186 / 1080)
SCAV_TOP_PAD = 5  # px below the scav window title before its grid starts
SCAV_HEIGHT_FRACTION = 0.81  # of the monitor height
DRAG_SECONDS = 0.4  # fast, but not a teleport; an instant drag gets dropped by the UI
DRAG_REPEATS = 3  # the scav window trails the cursor, so one drag stops short of the corner
LEFT_PAD = 10  # px right of the All button's right edge
RIGHT_PAD = 10  # px right of the autoselect similar button's right edge
TOP_PAD = 10  # px below the autoselect similar button
UNDERCUT_FRACTION = 0.85  # of the suggested price
UNDERCUT_FLAT = 2000  # roubles off the suggested price
PRICE_INPUT_TARGET = 'price_rubles_input'
PLACE_OFFER_TARGET = 'place_offer_button'
MORE_OFFERS_BRIGHTNESS = 190  # max channel in the add offer button: measured 255 lit, 123 greyed
OFFER_SLOT_POLL = 2.0  # seconds between rechecks while every offer slot is full
FILTER_BUTTON_TARGET = 'filter_button'  # opens the flea's filter window
FILTERS_WINDOW_TARGET = 'flea_filters_window_title'  # that window's title bar, for dragging it
CURRENCY_ANY_TARGET = 'currency_dropdown_any'  # the currency dropdown while it still says any
CURRENCY_RUBLES_OPTION = 'currency_dropdown_select_rubles'  # roubles, in the opened dropdown
CURRENCY_RUB_TARGET = 'currency_dropdown_rub'  # the dropdown once it reads roubles
OFFERS_FROM_ANY_TARGET = 'offers_from_any'  # the offers-from dropdown while it still says any
OFFERS_FROM_PLAYERS_OPTION = 'offers_from_select_players'  # players, in the opened dropdown
REMEMBER_ON_TARGET = 'remember_selected_filters_on'  # the remember-filters box, already ticked
REMEMBER_OFF_TARGET = 'remember_selected_filters_off'  # and the same box unticked
FILTERS_OK_TARGET = 'flea_filters_OK_button'  # applies the filters and closes the window
DROPDOWN_DELAY = 0.3  # seconds for the currency dropdown to unroll
OFFERS_FROM_DELAY = 0.33  # and for the offers-from one
CHECKMARK_TARGET = 'checkmark'  # the tick beside the autoselect similar button
CHECKMARK_MARGIN = 0.30  # that button's box grows this much per side before we look inside it


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
    return _region_from(*(found[n] for n in EDGES))


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
    return ocr.read_region(grab_price_region(region))


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
    if is_flea_open(region):
        return True
    point = find.find_center(FLEA_ICON_TARGET, region)
    if not point:
        return False
    pyautogui.click(*point)
    time.sleep(WINDOW_DELAY)
    return is_flea_open(region)


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
    return brightness is not None and brightness >= threshold


def wait_for_offer_slot(region=None, poll=OFFER_SLOT_POLL, stop=None):
    """Block until the add offer button lights up. Returns the seconds spent waiting.

    No timeout on purpose: a full offer board clears when something sells or expires, and
    there is nothing else worth doing in the meantime. Pass a threading.Event as stop to
    make it abandon the wait the moment that is set; without one only Ctrl+C gets you out.
    """
    started = time.monotonic()
    announced = False
    while not more_offers_available(region):
        if not announced:  # once, not every poll, or the log is nothing but this
            print(f'all offer slots full, rechecking every {poll:.0f}s')
            announced = True
        if stop is None:
            time.sleep(poll)
        elif stop.wait(poll):  # woken by stop rather than by the timeout
            break  # the caller checks the same flag and unwinds from there
    return time.monotonic() - started


def click_add_offer(region=None):
    """Click the add offer button. Returns the clicked (x, y), or None if not found."""
    point = find.find_center(ADD_OFFER_TARGET, region)
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
        return None
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.typewrite(str(value))
    return point


def click_place_offer(region=None):
    """Click the place offer button. Returns the clicked (x, y), or None if not found."""
    point = find.find_center(PLACE_OFFER_TARGET, region)
    if point:
        pyautogui.click(*point)
    return point


def is_item_selected(region=None):
    """True when something is selected, ie the 'no items selected' placeholder is absent."""
    return find.find(NO_SELECTION_TARGET, region) is None


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
        return True
    point = find.find_center('autoselect_similar', region)
    if not point:
        return False
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    return not is_autoselect_similar_ticked(region)  # confirm the click took, do not assume


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
    return _scav_region_from(title, min(closes, key=lambda b: b.left), screen_height)


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
    for _ in range(attempts):
        points = find_sell_pixels(region)
        if not points:
            return None  # nothing to sell, retrying will not conjure an item
        chosen = random.choice(points)
        pyautogui.click(*chosen)
        time.sleep(SELECT_POLL_DELAY)
        if not is_item_selected(region):
            continue  # landed on a gap, the placeholder is still showing
        pyautogui.rightClick(*chosen)
        time.sleep(SELECT_POLL_DELAY)
        box = find.find('filter_by_item', region)
        if not box:
            pyautogui.press('esc')  # shut whatever did open, or the next find hits a stale menu
            continue
        point = pyautogui.center(box)
        pyautogui.click(*point)
        time.sleep(SELECT_WINDOW_DELAY)  # the flea panel has to catch up before we read it
        return point
    return None


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


def _drag_to_corner(target, corner='top left', region=None, duration=DRAG_SECONDS):
    """Grab the centre of target's bbox and drag it into a corner. The grabbed point, or None.

    Parks the cursor mid screen afterwards. Every screen corner is one of pyautogui's panic
    points, so the fail-safe comes off for the drag and only goes back on once the cursor is
    clear of it. Leaving it parked in a corner trips the next call instead, which is a crash
    a long way from its cause.
    """
    point = find.find_center(target, region)
    if not point:
        return None
    width, height = pyautogui.size()
    destination = _corner_point(corner, (width, height))
    failsafe = pyautogui.FAILSAFE
    pyautogui.FAILSAFE = False
    try:
        pyautogui.moveTo(*point)
        pyautogui.dragTo(*destination, duration=duration, button='left')
        pyautogui.moveTo(width // 2, height // 2)  # must happen before the fail-safe is back on
    finally:
        pyautogui.FAILSAFE = failsafe
    return point


def orientate_offer_creation(region=None, duration=DRAG_SECONDS):
    """Drag the offer creation window to the bottom left of the monitor, into a known place.

    Grabs it by the centre of its bbox. Returns the point it grabbed, or None if not found.
    """
    return _drag_to_corner(OFFER_TARGET, 'bottom left', region, duration)


def _dropdown_arrow(box):
    """Middle of a box's right edge, where a dropdown's arrow sits. Inside it, not one past."""
    return int(box.left + box.width) - 1, int(box.top + box.height // 2)


def _set_dropdown(any_target, option_target, region=None, delay=DROPDOWN_DELAY):
    """Open a dropdown that still reads 'any' and pick option_target out of it.

    A missing 'any' is success, not a failure: the dropdown is already set to something, and
    the only thing clicking it again could do is change it back. Returns False only when the
    dropdown was open and the option was not in it.
    """
    box = find.find(any_target, region)
    if not box:
        return True  # already set to something other than any
    pyautogui.click(*_dropdown_arrow(box))
    time.sleep(delay)
    point = find.find_center(option_target, region)
    if not point:
        print(f'{option_target} not in the opened {any_target} dropdown')
        return False
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    return True


def apply_flea_filters(region=None):
    """Open the flea's filter window, tick remember, set roubles and players only, then OK out.

    Returns True once everything reads the right thing and the window is closed. Nothing that
    is already set gets clicked: the dropdowns are only touched while they still say 'any',
    and the remember box only while it is off, so running this against an already filtered
    board opens the window and OKs straight back out rather than undoing the settings.
    """
    point = find.find_center(FILTER_BUTTON_TARGET, region)
    if not point:
        print('no filter button on screen')
        return False
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)

    # Off, or the window never opened at all: either way the 'off' image has to be there next
    if not find.find(REMEMBER_ON_TARGET, region):
        toggle = find.find_center(REMEMBER_OFF_TARGET, region)
        if not toggle:
            print('remember selected filters checkbox not on screen, did the window open?')
            return False
        pyautogui.click(*toggle)
        time.sleep(MENU_DELAY)

    if not _set_dropdown(CURRENCY_ANY_TARGET, CURRENCY_RUBLES_OPTION, region, DROPDOWN_DELAY):
        return False
    if find.find(CURRENCY_ANY_TARGET, region) or not find.find(CURRENCY_RUB_TARGET, region):
        print('currency dropdown did not settle on roubles')  # confirm it took, do not assume
        return False

    if not _set_dropdown(OFFERS_FROM_ANY_TARGET, OFFERS_FROM_PLAYERS_OPTION,
                         region, OFFERS_FROM_DELAY):
        return False

    point = find.find_center(FILTERS_OK_TARGET, region)  # applies them and shuts the window
    if not point:
        print('no OK button on the flea filter window')
        return False
    pyautogui.click(*point)
    time.sleep(MENU_DELAY)
    return True


def orientate_scav_box(region=None, duration=DRAG_SECONDS, repeats=DRAG_REPEATS):
    """Drag the opened scav case window to the top left of the monitor, by its title bar.

    Dragged repeats times over: the window trails the cursor, so one pass stops short and
    each following pass re-grabs it wherever it settled. Returns the last point it grabbed,
    or None if the title bar was never found.
    """
    grabbed = None
    for _ in range(repeats):
        point = _drag_to_corner(SCAV_WINDOW_TARGET, 'top left', region, duration)
        if point is None:
            break
        grabbed = point
    return grabbed


def open_scav_case(region=None):
    """Right-click a random scav case and choose open from the menu that appears.

    Returns the clicked (x, y) of the open entry, or None if there was no case on screen
    or the menu never showed up.
    """
    cases = find.find_all('scav_case', region)
    if not cases:
        return None
    pyautogui.rightClick(*pyautogui.center(random.choice(cases)))
    time.sleep(MENU_DELAY)
    box = find.find('open_scav_case', region)
    if not box:
        return None
    point = pyautogui.center(box)
    pyautogui.click(*point)
    time.sleep(WINDOW_DELAY)  # the window has to exist before there is a title bar to grab
    orientate_scav_box(region)
    return point


def select_item_from_random_scav_case(region=None, attempts=SELECT_ATTEMPTS):
    """Grab a random item from the open scav case and filter by it on the flea.

    Assumes the case is already open and orientated. Same flow as
    select_item_from_inventory, just over the scav case grid instead of the stash: left click,
    ask the offer panel whether anything got selected, and only then go for the right-click
    menu. Returns the clicked (x, y), or None if every attempt missed.
    """
    for _ in range(attempts):
        points = find_scav_case_pixels(region)
        if not points:
            return None  # an empty case will not fill itself on a retry
        chosen = random.choice(points)
        pyautogui.click(*chosen)
        time.sleep(SELECT_POLL_DELAY)
        if not is_item_selected(region):
            continue  # landed on a gap, the placeholder is still showing
        pyautogui.rightClick(*chosen)
        time.sleep(SELECT_POLL_DELAY)
        box = find.find('filter_by_item', region)
        if not box:
            continue
        point = pyautogui.center(box)
        pyautogui.click(*point)
        time.sleep(SELECT_WINDOW_DELAY)  # the flea panel has to catch up before we read it
        return point
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
    assert _scav_region_from(Box(100, 50, 200, 20), Box(500, 50, 20, 20), 1080) == (100, 75, 420, 875)
    try:  # a close button left of the title would invert it
        _scav_region_from(Box(100, 50, 200, 20), Box(10, 50, 20, 20), 1080)
        raise AssertionError('expected LookupError')
    except LookupError:
        pass
    print('ok')
