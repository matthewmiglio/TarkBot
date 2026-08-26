"""
This module is for the hideout crafting screen.

The first thing it needs is to tell a craft that can be started from one that cannot: a START
button lit green because the ingredients are in the stash, against the same button greyed out
because they are not. That is sell.more_offers_available's problem exactly (a button that keeps
its dark plate in both states and only lights its label), so it is read the same way: the
brightest channel in the button box, thresholded.
"""
import time
from collections import namedtuple

import numpy as np
import pyautogui

import screen
from interact import find, sell, snipe
from narrate import log

START_TARGET = 'crafting/start'  # the START button on a production row
# The slickers craft's two ingredients, and the two marks that sit under each one saying whether
# it is in the stash. A checkmark or an X is drawn directly below its ingredient icon: measured
# on a live 1440p screen, the mark's centre is within a pixel of the icon's centre x and ~96px
# (72 at 1080p) below it. These tolerances are 1080p, scaled by find.scale() at match time like
# every other measurement here.
SLICKERS_TARGET = 'crafting/slickers'  # the slickers item, as an ingredient or as the output
TIMER_TARGET = 'crafting/craft_timer_icon'  # the clock icon that sits left of every output item
SLICKERS_BAND_PAD = 100  # px above the topmost and below the bottommost slickers match, literal
# screen pixels rather than 1080p-scaled: this is slack around a match, not a measured offset.
SLICKERS_BAND_TOP_DROP = 60  # trim this much off the top of the band: the pad alone reached too
# high, catching the craft above's controls. Top only, so the bottom pad is unaffected.
ROW_TOL = 40  # two matches are on the same craft row when their centre y are within this (1080p)
ALYONKA_TARGET = 'crafting/alyonka'
CRACKERS_TARGET = 'crafting/crackers'
CHECK_TARGET = 'crafting/checkmark'
X_TARGET = 'crafting/X'
MARK_ALIGN_X = 30  # a mark counts as under an icon within this many px of its centre x
MARK_DROP_MIN = 40  # ...and at least this far below the icon centre
MARK_DROP_MAX = 130  # ...and no further than this (the next row's marks are ~170 down)
MENU_DELAY = 0.33  # after the right click, for the inventory context menu to draw
FLEA_LOAD_DELAY = 3.0  # after 'filter by item', for the flea board and its filter UI to load
OFFER_WAIT = 10.0  # after the filters go on, how long to keep looking for an offer before giving up
OFFER_POLL = 0.3  # how often to re-check the board for an offer while waiting
OVER_PRICE_WAIT = 10.0  # seconds to sit after backing out of an offer that costs too much
BOUGHT_SETTLE = 2.0  # seconds after a purchase before the caller does anything else
NUTRITION_RETURN_WAIT = 10.0  # how long to wait for the nutrition panel after escaping the flea
NUTRITION_RETURN_POLL = 0.2  # how often to re-check for it while waiting
# Brightest channel anywhere in the START button. Measured on a live 1440p crafting screen with
# one ready craft and four short of ingredients: 231 for the lit green button, 75-86 for the
# four greyed ones. 150 sits in the middle of that gap with wide headroom on both sides.
START_READY_BRIGHTNESS = 150
GET_ITEMS_TARGET = 'crafting/get_items'  # the GET ITEMS button on a finished craft's row
# Brightest channel in the GET ITEMS button that says it is lit (craft done, items collectable)
# rather than greyed. Set by analogy to START, whose lit label reads ~231 and greyed ~75-86; 150
# sits in that gap. ponytail: confirm against a real not-highlighted GET ITEMS frame and retune
# if the two states are closer than START's are.
GET_ITEMS_HIGHLIGHT_BRIGHTNESS = 150
HIDEOUT_TAB_TARGET = 'hideout/hideout_tab'  # a module's tab in the hideout's left-hand list
# Mean brightness of the hideout tab that says it is the selected one. The whole tab lightens
# when active rather than just a label, so mean reads it cleanly (like sell.is_flea_open, not the
# brightest-channel button reads): measured 57 on two inactive crops and 118-122 on two active
# ones, so 90 sits in the middle of that gap.
HIDEOUT_TAB_ACTIVE_BRIGHTNESS = 90
NUTRITION_TARGET = 'hideout/hideout_tabs/nutrition_unit'  # the module we are navigating to
NUTRITION_ACTIVE_TARGET = 'hideout/hideout_station_titles/nutrition_unit'  # the panel header shown once it is open
HIDEOUT_DIR = 'hideout/hideout_tabs'  # the folder of module-label references, one subfolder per module
SWIPE_DISTANCE = 500  # px to drag the hideout view per swipe, 1080p, scaled at swipe time
SWIPE_DURATION = 0.3  # seconds the drag itself takes
SWIPE_SETTLE = 0.5  # seconds after a swipe for the view to stop moving before it is read
RESET_SWIPES = 5  # swipes left to push the view to one end before searching rightwards
MAX_SEARCH_SWIPES = 10  # swipes right looking for the nutrition unit before giving up
TAB_TIMEOUT = 10.0  # seconds for the hideout tab to come back after clicking it
NAV_SETTLE = 3.0  # seconds to let a navigation land before reading or clicking again

# Fleece craft, the second one this module runs. Its two inputs and its output each have their own
# reference folder under crafting/, same as the slickers craft's above.
FLEECE_TARGET = 'crafting/fleece'
SEWING_KIT_TARGET = 'crafting/sewing_kit'
BEANIE_TARGET = 'crafting/ux_pro_beanie'
LAVATORY_TARGET = 'hideout/hideout_tabs/lavatory'  # the fleece craft's station, in the module carousel
LAVATORY_ACTIVE_TARGET = 'hideout/hideout_station_titles/lavatory'  # its panel header once open

# A craft is everything that differs between the slickers and fleece runs, so one set of reading
# and navigation functions serves both. ingredients are (name, icon target); the name doubles as
# the key the runner looks its rouble ceiling and offer source up under, and matches the crafting/
# folder, so buying can aim at crafting/<name> without a second lookup.
Ingredient = namedtuple('Ingredient', 'name target')
Craft = namedtuple('Craft', 'name output_target ingredients module_target station_title')

SLICKERS = Craft('slickers', SLICKERS_TARGET,
                 (Ingredient('crackers', CRACKERS_TARGET), Ingredient('alyonka', ALYONKA_TARGET)),
                 NUTRITION_TARGET, NUTRITION_ACTIVE_TARGET)
FLEECE = Craft('fleece', FLEECE_TARGET,
               (Ingredient('sewing_kit', SEWING_KIT_TARGET), Ingredient('ux_pro_beanie', BEANIE_TARGET)),
               LAVATORY_TARGET, LAVATORY_ACTIVE_TARGET)
CRAFTS = {c.name: c for c in (SLICKERS, FLEECE)}


def hideout_tab_brightness(region=None):
    """Mean channel value of the hideout tab, or None if it is not on screen."""
    box = find.find(HIDEOUT_TAB_TARGET, region)
    if not box:
        return None
    rect = (int(box.left), int(box.top), int(box.width), int(box.height))
    return float(np.asarray(screen.grab(rect).convert('RGB')).mean())


def is_hideout_tab_active(region=None, threshold=HIDEOUT_TAB_ACTIVE_BRIGHTNESS):
    """True when the hideout tab is the selected (lightened) one, False when dim or not found."""
    brightness = hideout_tab_brightness(region)
    if brightness is None:
        log('hideout tab not on screen', 1)
        return False
    active = brightness >= threshold
    log(f'hideout tab mean {brightness:.0f} vs {threshold}: {"active" if active else "inactive"}', 1)
    return active


def station_active(craft, region=None):
    """True when this craft's station panel is open, read off its header title."""
    active = find.find(craft.station_title, region) is not None
    log(f'{craft.name} station panel {"open" if active else "not open"}', 1)
    return active


def check_if_nutrition_unit_active(region=None):
    """Back-compat wrapper: is the slickers craft's station (the nutrition unit) open."""
    return station_active(SLICKERS, region)


def hideout_module_targets():
    """Every 'hideout/hideout_tabs/<module>' folder that holds reference crops, nutrition unit included."""
    d = find.REFS / HIDEOUT_DIR
    return [f'{HIDEOUT_DIR}/{p.name}' for p in sorted(d.iterdir())
            if p.is_dir() and any(p.glob('*.png'))]


def hideout_icons(region=None):
    """Every hideout module label on screen, across all modules. [] if none are showing."""
    boxes = []
    for target in hideout_module_targets():
        boxes += find.find_all(target, region)
    return boxes


def _swipe(x, y, dx):
    """Drag the hideout view horizontally by dx from (x, y). Negative dx swipes left."""
    log(f'swiping from ({x}, {y}) by {dx}', 2)
    pyautogui.moveTo(x, y)
    pyautogui.dragTo(x + dx, y, duration=SWIPE_DURATION, button='left')


def get_to_station(craft, region=None):
    """Navigate the hideout to this craft's station and open it. True on success, else raises.

    Ensures the hideout tab is the active one (clicking it if not), then treats the module row as
    a horizontal carousel: swipe left RESET_SWIPES times to reach one end, swipe right up to
    MAX_SEARCH_SWIPES times until the station's module label appears, then click it. Every dead
    end (no tab, tab will not activate, no module row to grab, station never found or lost while
    the screen settles) raises LookupError rather than clicking blind.
    """
    if is_hideout_tab_active(region):
        log('already on the hideout tab, skipping to the module search', 1)
    else:
        tab = find.find(HIDEOUT_TAB_TARGET, region)
        if not tab:
            raise LookupError('hideout tab button not on screen')
        log('not on the hideout tab, clicking it', 1)
        pyautogui.click(*sell.jitter(pyautogui.center(tab)))
        time.sleep(SWIPE_SETTLE)  # let it start transitioning before we wait for it back
        if sell.wait_for(HIDEOUT_TAB_TARGET, region, timeout=TAB_TIMEOUT) is None:
            raise LookupError('hideout tab never came back after clicking it')
        if not is_hideout_tab_active(region):
            raise LookupError('hideout tab did not become active after clicking it')

    # Already looking at it? Click it and skip the scrolling entirely.
    if find.find(craft.module_target, region):
        log(f'{craft.name} station already on screen, no scrolling needed', 1)
        return _open_station(craft, region)

    icons = hideout_icons(region)
    if not icons:
        raise LookupError('no hideout module icons on screen to grab the view by')
    x = round(sum(_center(b)[0] for b in icons) / len(icons))
    y = round(sum(_center(b)[1] for b in icons) / len(icons))
    log(f'module row grab point ({x}, {y}) off {len(icons)} icons', 1)

    dist = round(SWIPE_DISTANCE * find.scale())
    log(f'resetting: up to {RESET_SWIPES} swipes left by {dist}', 1)
    for _ in range(RESET_SWIPES):
        _swipe(x, y, -dist)
        time.sleep(SWIPE_SETTLE)
        if find.find(craft.module_target, region):  # spotted it while resetting, stop early
            log(f'{craft.name} station appeared while resetting left', 1)
            return _open_station(craft, region)

    log(f'searching right for the {craft.name} station, up to {MAX_SEARCH_SWIPES} swipes', 1)
    found = find.find(craft.module_target, region)
    swipes = 0
    while not found and swipes < MAX_SEARCH_SWIPES:
        _swipe(x, y, dist)
        swipes += 1
        time.sleep(SWIPE_SETTLE)
        found = find.find(craft.module_target, region)
    if not found:
        raise LookupError(f'{craft.name} station never appeared after {MAX_SEARCH_SWIPES} swipes')
    return _open_station(craft, region)


def _open_station(craft, region=None):
    """Settle, re-find the station's module label, click it, confirm its panel opened. True/raises.

    Shared by all three ways get_to_station spots the module: already on screen, seen while
    resetting left, or found swiping right.
    """
    log(f'{craft.name} station found, settling {NAV_SETTLE}s before clicking', 1)
    time.sleep(NAV_SETTLE)
    box = find.find(craft.module_target, region)
    if not box:
        raise LookupError(f'lost the {craft.name} station while the screen settled')
    pyautogui.click(*sell.jitter(pyautogui.center(box)))
    time.sleep(NAV_SETTLE)
    if not station_active(craft, region):
        raise LookupError(f'clicked the {craft.name} station but its panel never opened')
    return True


def get_to_nutrition_unit(region=None):
    """Back-compat wrapper: navigate to the slickers craft's station (the nutrition unit)."""
    return get_to_station(SLICKERS, region)


def start_buttons(region=None):
    """Every START button box on screen, however many rows are showing."""
    return find.find_all(START_TARGET, region)


def button_brightness(box):
    """Brightest channel value anywhere in one START button box.

    Brightest rather than mean, like sell.add_offer_brightness: the button keeps its dark plate
    in both states and only the label lights, so an average is mostly plate and barely moves.
    """
    rect = (int(box.left), int(box.top), int(box.width), int(box.height))
    return int(np.asarray(screen.grab(rect).convert('RGB')).max())


def is_ready(box, threshold=START_READY_BRIGHTNESS):
    """True when this START button is lit, ie the craft's ingredients are in the stash."""
    return button_brightness(box) >= threshold


def first_ready_button(region=None, threshold=START_READY_BRIGHTNESS):
    """The topmost startable craft's START box, or None when nothing on screen is ready."""
    for box in sorted(start_buttons(region), key=lambda b: b.top):
        if is_ready(box, threshold):
            return box
    log('no ready craft on screen', 1)
    return None


def output_items(craft, region=None):
    """Every match of this craft's item that is a craft's OUTPUT rather than one of its ingredients.

    An item bar is the output when a timer clock sits to its left on the same row; the same item
    used as an ingredient has no timer left of it. Same row means centre y within ROW_TOL (scaled),
    to the left means the timer's centre x is smaller.
    """
    tol = ROW_TOL * find.scale()
    timers = find.find_all(TIMER_TARGET, region)
    outputs = []
    for item in find.find_all(craft.output_target, region):
        ix, iy = _center(item)
        if any(_center(t)[0] < ix and abs(_center(t)[1] - iy) <= tol for t in timers):
            outputs.append(item)
    return outputs


def output_box(craft, region=None):
    """This craft's output bar, in whatever state the craft is in, or None.

    Prefers the timer-anchored output (right in the ready state), and falls back to the rightmost
    item match when there is no timer, which is every other state: the output sits at the far
    right of its row, right of the ingredients, so it is the rightmost match of the item on screen.
    """
    timed = output_items(craft, region)
    if timed:
        return max(timed, key=lambda b: b.left)
    boxes = find.find_all(craft.output_target, region)
    return max(boxes, key=lambda b: b.left) if boxes else None


def output_slickers(region=None):
    """Back-compat wrapper: the slickers craft's timer-anchored output matches."""
    return output_items(SLICKERS, region)


def slickers_output_box(region=None):
    """Back-compat wrapper: the slickers craft's output bar in any state."""
    return output_box(SLICKERS, region)


def _row_band(box, region=None):
    """A full-width band SLICKERS_BAND_PAD above and below one match's row."""
    left, _, width, _ = region if region else screen.rect()
    top = box.top - SLICKERS_BAND_PAD + SLICKERS_BAND_TOP_DROP
    bottom = box.top + box.height + SLICKERS_BAND_PAD
    return (left, top, width, bottom - top)


def craft_row_band(craft, region=None):
    """This craft's row band in any state, or None if its output is not on screen.

    Unlike find_craft, which anchors on the ready-state timer, this uses output_box (rightmost
    item match when there is no timer), so it also frames the row when the craft is producing or
    done, ie when the GET ITEMS button rather than a timer is on it. That is what a caller reading
    GET ITEMS or START off the row needs.
    """
    box = output_box(craft, region)
    return _row_band(box, region) if box else None


def slickers_row_band(region=None):
    """Back-compat wrapper: the slickers craft's state-independent row band."""
    return craft_row_band(SLICKERS, region)


def get_items_highlighted(box, threshold=GET_ITEMS_HIGHLIGHT_BRIGHTNESS):
    """True when the GET ITEMS button is lit (craft done) rather than greyed."""
    return button_brightness(box) >= threshold


def get_craft_state(craft, region=None):
    """One of 'not started', 'done', 'ready', 'producing' for this craft.

    Scoped to the craft output's own row so another craft's button cannot be read by mistake:
      - GET ITEMS present and greyed  -> 'not started'
      - GET ITEMS present and lit     -> 'done' (items are waiting to be collected)
      - START button present          -> 'ready' (ingredients are in the stash)
      - none of those                 -> 'producing' (the craft is running)
    """
    output = output_box(craft, region)
    if output is None:
        log(f'no {craft.name} output on screen, cannot read the craft state', 1)
        return 'producing'
    band = _row_band(output, region)

    get_items = find.find(GET_ITEMS_TARGET, band)
    if get_items:
        state = 'done' if get_items_highlighted(get_items) else 'not started'
    elif find.find(START_TARGET, band):
        state = 'ready'
    else:
        state = 'producing'
    log(f'{craft.name} craft state: {state}', 1)
    return state


def get_slickers_craft_state(region=None):
    """Back-compat wrapper: the slickers craft's state."""
    return get_craft_state(SLICKERS, region)


def find_craft(craft, region=None):
    """A full-width horizontal band around this craft on screen, or None if not found.

    The craft is the row whose item bar is the output, ie has the timer clock to its left; the
    same item used as an ingredient on some other craft's row is ignored. The band spans
    SLICKERS_BAND_PAD above the topmost output and the same below the bottommost (less
    SLICKERS_BAND_TOP_DROP off the top), across the whole width of the search region. A
    (left, top, width, height) rect, ready to hand to find as the region for that craft's
    ingredients, marks and START button.
    """
    boxes = output_items(craft, region)
    if not boxes:
        log(f'no {craft.name} craft output on screen', 1)
        return None
    top = min(b.top for b in boxes) - SLICKERS_BAND_PAD + SLICKERS_BAND_TOP_DROP
    bottom = max(b.top + b.height for b in boxes) + SLICKERS_BAND_PAD
    left, _, width, _ = region if region else screen.rect()
    log(f'{craft.name} band {top}..{bottom} across x {left}..{left + width}', 1)
    return (left, top, width, bottom - top)


def find_slickers_craft(region=None):
    """Back-compat wrapper: the slickers craft's timer-anchored band."""
    return find_craft(SLICKERS, region)


def _center(box):
    return (box.left + box.width / 2, box.top + box.height / 2)


def _mark_beneath(icon, marks):
    """The mark sitting directly under `icon`, closest one if there are several, or None.

    A mark belongs to an icon when its centre is within MARK_ALIGN_X of the icon's centre x and
    between MARK_DROP_MIN and MARK_DROP_MAX below it, all scaled to the live screen.
    """
    scale = find.scale()
    align_x, drop_min, drop_max = (MARK_ALIGN_X * scale, MARK_DROP_MIN * scale, MARK_DROP_MAX * scale)
    ix, iy = _center(icon)
    best, best_dy = None, None
    for mark in marks:
        mx, my = _center(mark)
        dy = my - iy
        if abs(mx - ix) <= align_x and drop_min <= dy <= drop_max:
            if best_dy is None or dy < best_dy:
                best, best_dy = mark, dy
    return best


def ingredient_icon(craft, ingredient, region=None):
    """This ingredient's icon on the craft's own row, or None. The band scopes to one row, but a
    pad can catch a neighbouring row, so of any matches pick the one nearest the output's row."""
    band = find_craft(craft, region)
    output = output_box(craft, region)
    if band is None or output is None:
        return None
    icons = find.find_all(ingredient.target, band)
    if not icons:
        return None
    _, oy = _center(output)
    return min(icons, key=lambda b: abs(_center(b)[1] - oy))


def validate_craftable(craft, region=None):
    """Are all of this craft's ingredients in the stash?

    Only the craft's own row is read: the search is scoped to the band find_craft draws around the
    output, so an ingredient of the same name on another craft's row cannot be mistaken for one of
    these. With no craft on screen every ingredient reads as not ready.

    Reads the checkmark or X drawn under each ingredient icon. Returns (all_ready, missing):
    (True, []) when all show a checkmark, else (False, [names not ready]) in the craft's own
    ingredient order. An ingredient is not ready when an X sits under it, when nothing does, or
    when its icon is not on screen at all.
    """
    band = find_craft(craft, region)
    if band is None:
        return (False, [ing.name for ing in craft.ingredients])
    checks = find.find_all(CHECK_TARGET, band)
    missing = []
    for ing in craft.ingredients:
        icon = ingredient_icon(craft, ing, region)
        ready = icon is not None and _mark_beneath(icon, checks) is not None
        log(f'{ing.name}: {"ready" if ready else "not ready"}', 1)
        if not ready:
            missing.append(ing.name)
    return (not missing, missing)


def validate_slickers_craftable(region=None):
    """Back-compat wrapper: are both slickers ingredients in the stash."""
    return validate_craftable(SLICKERS, region)


def buy_craft_input_item(location, max_price, region=None, source='players', craft=SLICKERS):
    """Buy one craft ingredient off the flea, if the cheapest offer is at or under max_price.

    location is where the ingredient sits in the craft row (a point to right click). source is who
    to buy from, 'players' or 'traders', and only changes the offers-from filter. craft is which
    craft this input belongs to, so the flea can be escaped back to the right station afterwards.
    The flow is the flea sniper's, aimed from a right click rather than a typed search: filter the
    board to this one item through the inventory menu, put the filters on, read the top offer's
    price, and buy that row only when it is cheap enough.

    Returns True if it bought, False otherwise (too dear, or the price could not be read safely).
    Raises LookupError if the 'filter by item' menu entry never appears, since without it there
    is no way to narrow the board to this ingredient and nothing after this step would mean
    anything.
    """
    log(f'buying craft input at {location}, ceiling {max_price}')
    pyautogui.rightClick(*location)
    time.sleep(MENU_DELAY)

    box = find.find('filter_by_item', region)
    if not box:
        raise LookupError('no filter by item in the menu, cannot narrow the board to this item')
    point = sell.jitter(pyautogui.center(box), y=0)  # a 6px tall crop says nothing about the row
    log(f'clicking filter by item at {point}', 1)
    pyautogui.click(*point)

    time.sleep(FLEA_LOAD_DELAY)  # the flea board opens from scratch here, give its UI time to draw
    # No condition filter: a craft input is consumed, not resold, so a scuffed one is fine and
    # filtering on 100% only hides the cheaper offers we are here for.
    sell.apply_flea_filters(region, source=source, set_condition=False)

    # The board reloads after the filters go on and offers do not all appear at once, so poll for
    # the first purchase button rather than reading once: up to OFFER_WAIT, every OFFER_POLL.
    deadline = time.monotonic() + OFFER_WAIT
    while True:
        buttons = snipe.purchase_buttons(region)
        if buttons:
            break
        if time.monotonic() >= deadline:
            log(f'no offers on the filtered board after {OFFER_WAIT}s, nothing to buy', 1)
            return False
        time.sleep(OFFER_POLL)
    top = buttons[0]
    price = snipe.read_price(top)

    if price is None or price > max_price:
        why = 'unreadable' if price is None else f'{price} over the {max_price} ceiling'
        log(f'not buying ({why}), backing out and waiting {OVER_PRICE_WAIT}s', 1)
        pyautogui.press('esc')
        time.sleep(OVER_PRICE_WAIT)
        return False

    log(f'{price} is at or under {max_price}, buying', 1)
    bought = snipe.buy(top, region)
    time.sleep(BOUGHT_SETTLE)
    return_to_station(craft, region)  # the buy leaves the flea up over the panel; get back to it
    return bought


def return_to_station(craft, region=None):
    """Escape the flea and wait for this craft's station panel to come back on screen.

    A purchase leaves the flea board sitting over the hideout, so the next craft read finds no
    output and the loop stalls. Press esc, then poll for the panel header up to
    NUTRITION_RETURN_WAIT. Raises LookupError if it never reappears, since everything after this
    reads off that panel and would otherwise misfire against whatever the flea left on screen.
    """
    pyautogui.press('esc')
    deadline = time.monotonic() + NUTRITION_RETURN_WAIT
    while True:
        if find.find(craft.station_title, region) is not None:
            log(f'back on the {craft.name} station', 1)
            return
        if time.monotonic() >= deadline:
            raise LookupError(
                f'{craft.name} station panel did not reappear within {NUTRITION_RETURN_WAIT}s of '
                'leaving the flea')
        time.sleep(NUTRITION_RETURN_POLL)


def return_to_nutrition_unit(region=None):
    """Back-compat wrapper: escape the flea back to the slickers craft's station."""
    return return_to_station(SLICKERS, region)
