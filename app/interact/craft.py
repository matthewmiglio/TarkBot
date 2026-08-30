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
MENU_REHOVER_OFFSET = 120  # 1080p px to pull the cursor off a slot before hovering it again
FLEA_LOAD_DELAY = 3.0  # after 'filter by item', for the flea board and its filter UI to load
OFFER_WAIT = 10.0  # after the filters go on, how long to keep looking for an offer before giving up
OFFER_POLL = 0.3  # how often to re-check the board for an offer while waiting
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
TAB_TIMEOUT = 60.0  # seconds for the hideout tab to come back after clicking it
NAV_SETTLE = 3.0  # seconds to let a navigation land before reading or clicking again
OPEN_ATTEMPTS = 2  # clicks on a station tab before giving up on its panel opening

# Fleece craft, the second one this module runs. Its two inputs and its output each have their own
# reference folder under crafting/, same as the slickers craft's above.
FLEECE_TARGET = 'crafting/fleece'
SEWING_KIT_TARGET = 'crafting/sewing_kit'
BEANIE_TARGET = 'crafting/ux_pro_beanie'
LAVATORY_TARGET = 'hideout/hideout_tabs/lavatory'  # the fleece craft's station, in the module carousel
LAVATORY_ACTIVE_TARGET = 'hideout/hideout_station_titles/lavatory'  # its panel header once open

# Workbench craft: a single input, power cord, into wires.
POWER_CORD_TARGET = 'crafting/power_cord'
WIRES_TARGET = 'crafting/wires'
WORKBENCH_TARGET = 'hideout/hideout_tabs/workbench'
WORKBENCH_ACTIVE_TARGET = 'hideout/hideout_station_titles/workbench'

# Medstation craft: a single input, a pile of meds, into an AI-2.
PILE_OF_MEDS_TARGET = 'crafting/pile_of_meds'
AI2_TARGET = 'crafting/ai2'
MEDSTATION_TARGET = 'hideout/hideout_tabs/medstation'
MEDSTATION_ACTIVE_TARGET = 'hideout/hideout_station_titles/medstation'

# A craft is everything that differs between the slickers and fleece runs, so one set of reading
# and navigation functions serves both. ingredients are (name, icon target); the name doubles as
# the key the runner looks its rouble ceiling and offer source up under, and matches the crafting/
# folder, so buying can aim at crafting/<name> without a second lookup.
class PriceTooHigh(Exception):
    """Raised by buy_craft_input_item when the cheapest offer is over the ceiling: the caller has
    already backed out to the station, and this says to stop buying and move on to the next craft."""


Ingredient = namedtuple('Ingredient', 'name target')
# station is the human name of the hideout module the craft runs at, for prints: the slickers
# craft lives at the nutrition unit, the fleece craft at the lavatory. name is the item/output.
Craft = namedtuple('Craft', 'name output_target ingredients module_target station_title station')

SLICKERS = Craft('slickers', SLICKERS_TARGET,
                 (Ingredient('crackers', CRACKERS_TARGET), Ingredient('alyonka', ALYONKA_TARGET)),
                 NUTRITION_TARGET, NUTRITION_ACTIVE_TARGET, 'nutrition unit')
FLEECE = Craft('fleece', FLEECE_TARGET,
               (Ingredient('sewing_kit', SEWING_KIT_TARGET), Ingredient('ux_pro_beanie', BEANIE_TARGET)),
               LAVATORY_TARGET, LAVATORY_ACTIVE_TARGET, 'lavatory')
WIRES = Craft('wires', WIRES_TARGET,
              (Ingredient('power_cord', POWER_CORD_TARGET),),
              WORKBENCH_TARGET, WORKBENCH_ACTIVE_TARGET, 'workbench')
AI2 = Craft('ai2', AI2_TARGET,
            (Ingredient('pile_of_meds', PILE_OF_MEDS_TARGET),),
            MEDSTATION_TARGET, MEDSTATION_ACTIVE_TARGET, 'medstation')
CRAFTS = {c.name: c for c in (SLICKERS, FLEECE, WIRES, AI2)}


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
    log(f'{craft.station} panel {"open" if active else "not open"}', 1)
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
        log(f'{craft.station} already on screen, no scrolling needed', 1)
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
            log(f'{craft.station} appeared while resetting left', 1)
            return _open_station(craft, region)

    log(f'searching right for the {craft.station}, up to {MAX_SEARCH_SWIPES} swipes', 1)
    found = find.find(craft.module_target, region)
    swipes = 0
    while not found and swipes < MAX_SEARCH_SWIPES:
        _swipe(x, y, dist)
        swipes += 1
        time.sleep(SWIPE_SETTLE)
        found = find.find(craft.module_target, region)
    if not found:
        raise LookupError(f'{craft.station} never appeared after {MAX_SEARCH_SWIPES} swipes')
    return _open_station(craft, region)


def _open_station(craft, region=None):
    """Settle, re-find the station's module label, click it, confirm its panel opened. True/raises.

    Shared by all three ways get_to_station spots the module: already on screen, seen while
    resetting left, or found swiping right.

    The click gets OPEN_ATTEMPTS goes, re-finding the tab in between because the carousel is
    still drifting for a second or so after a swipe. One look was enough to end two runs an hour
    into them: on 2026-08-29 a Windows low disk notification took focus and ate the click, and on
    2026-08-30 the screen went black for a few seconds and the panel could not be read at all.
    Neither says the station is unreachable, and both pass on a second look.
    """
    log(f'{craft.station} found, settling {NAV_SETTLE}s before clicking', 1)
    time.sleep(NAV_SETTLE)
    box = find.find(craft.module_target, region)
    if not box:
        raise LookupError(f'lost the {craft.station} while the screen settled')
    for attempt in range(OPEN_ATTEMPTS):
        if attempt:
            log(f'the {craft.station} panel did not open, clicking it again '
                f'(try {attempt + 1})', 1)
        pyautogui.click(*sell.jitter(pyautogui.center(box)))
        time.sleep(NAV_SETTLE)
        if station_active(craft, region):
            return True
        box = find.find(craft.module_target, region) or box  # the carousel drifts between tries
    raise LookupError(f'clicked the {craft.station} but its panel never opened')


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


def _on_row(boxes, row_y):
    """The match whose centre y is within ROW_TOL (scaled) of row_y, nearest one, or None.

    get_craft_state reads START and GET ITEMS off the craft's own row, but _row_band pads the band
    (SLICKERS_BAND_PAD) and a producing craft has no button of its own, so a band tall enough to
    frame the row also reaches the next craft's row and borrows its START. On 2026-08-28 that read
    a fleece craft producing at 7% as 'ready' (a START button 71px below the output, on the row
    under it, sat inside the 180px band), and the runner looped buying its inputs into an already
    running craft. Constrain the read to the output's own row, the way output_items constrains the
    timer: same row means centre y within ROW_TOL.
    """
    tol = ROW_TOL * find.scale()
    on = [b for b in boxes if abs(_center(b)[1] - row_y) <= tol]
    return min(on, key=lambda b: abs(_center(b)[1] - row_y)) if on else None


def get_craft_state(craft, region=None):
    """One of 'not started', 'done', 'ready', 'producing' for this craft. Raises if unreadable.

    Scoped to the craft output's own row so another craft's button cannot be read by mistake:
      - GET ITEMS present and greyed  -> 'not started'
      - GET ITEMS present and lit     -> 'done' (items are waiting to be collected)
      - START button present          -> 'ready' (ingredients are in the stash)
      - none of those                 -> 'producing' (the craft is running)

    'On its own row' is the whole point and is enforced against the output's centre y, not just the
    padded band: the band is deliberately tall enough to frame a row in any state, which means it
    also overlaps the next craft's row, and a button read anywhere in it can belong to the craft
    below. See _on_row for the run that cost.

    An output that is not on screen is a LookupError and ends the run, because it is not a state.
    It used to answer 'producing', which reads as a sensible default and is the worst possible
    one: 'producing' is precisely the state the runner responds to by doing nothing and swapping
    away, so a craft the bot could not see became a craft the bot politely skipped, once per pass,
    forever, with one indent-1 log line and no error. The wires craft did exactly that on every
    pass of 2026-08-27 while its output sat on screen the whole time, unmatched because
    crafting/wires needed a threshold the 0.9 default would not give it. Nothing in the run said
    so: the counters looked normal and the loop looked healthy. Failing loudly here costs a
    stopped run on a bad frame and buys the only signal that a craft has gone blind.
    """
    output = output_box(craft, region)
    if output is None:
        raise LookupError(f'{craft.name} output not on screen, cannot read the craft state')
    band = _row_band(output, region)
    row_y = _center(output)[1]

    get_items = _on_row(find.find_all(GET_ITEMS_TARGET, band), row_y)
    if get_items:
        state = 'done' if get_items_highlighted(get_items) else 'not started'
    elif _on_row(find.find_all(START_TARGET, band), row_y):
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


def craft_plan(craft, region=None):
    """Read the craft's whole row in one pass and report what each ingredient needs.

    Returns a list of (name, ready, location) in the craft's ingredient order, from a single
    find_craft band read rather than one read per ingredient. location is the ingredient icon's
    centre (the point to right-click when buying), or None if the icon is not on the row. ready is
    whether a checkmark sits under it. With no craft on screen every ingredient is (name, False,
    None). The band scopes to one row, but a pad can catch a neighbour, so of any matches the icon
    nearest the output's row is taken.
    """
    band = find_craft(craft, region)
    if band is None:
        return [(ing.name, False, None) for ing in craft.ingredients]
    output = output_box(craft, region)
    oy = _center(output)[1] if output else None
    checks = find.find_all(CHECK_TARGET, band)
    plan = []
    for ing in craft.ingredients:
        icons = find.find_all(ing.target, band)
        if not icons:
            icon = None
        elif oy is not None:
            icon = min(icons, key=lambda b: abs(_center(b)[1] - oy))
        else:
            icon = min(icons, key=lambda b: b.top)
        ready = icon is not None and _mark_beneath(icon, checks) is not None
        location = _center(icon) if icon else None
        log(f'{ing.name}: {"ready" if ready else "not ready"}', 1)
        plan.append((ing.name, ready, location))
    return plan


def validate_craftable(craft, region=None):
    """Are all of this craft's ingredients in the stash? (all_ready, [names not ready]).

    One read of the craft's own row through craft_plan, so an ingredient of the same name on
    another craft's row cannot be mistaken for one of these, and the row is not re-found per
    ingredient. Not ready means an X under the icon, nothing under it, or the icon off screen.
    """
    missing = [name for name, ready, _ in craft_plan(craft, region) if not ready]
    return (not missing, missing)


def validate_slickers_craftable(region=None):
    """Back-compat wrapper: are both slickers ingredients in the stash."""
    return validate_craftable(SLICKERS, region)


def _open_item_menu(location, region=None, attempts=2):
    """Right-click a craft input and return the 'filter by item' entry's box, or None.

    Hovers the slot and waits a beat before pressing, because rightClick() teleports the cursor
    and presses in the same instant: the game can read the button before its own hover has caught
    up, and then the menu never opens at all. On a miss the cursor is moved off the row and back,
    so the second try arrives as a fresh mouse-enter rather than a press on a slot the game
    already thinks is under the cursor.

    Seen on 2026-08-28: a run that had opened this menu nine times in a row missed on the tenth
    and ended, with the frames showing the cursor on the right slot, its tooltip up, and no menu.
    """
    for attempt in range(attempts):
        if attempt:
            log(f'no menu on the slot, hovering it again (try {attempt + 1})', 1)
            pyautogui.moveTo(location[0] - MENU_REHOVER_OFFSET * find.scale(), location[1])
            time.sleep(MENU_DELAY)
        pyautogui.moveTo(*location)
        time.sleep(MENU_DELAY)  # let the hover register before the press
        pyautogui.rightClick(*location)
        time.sleep(MENU_DELAY)
        box = find.find('filter_by_item', region)
        if box:
            return box
    return None


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
    anything. craft_bot catches that and swaps craft rather than ending the run: one slot the
    game will not open a menu on says nothing about the other crafts.
    """
    log(f'buying craft input at {location}, ceiling {max_price}')
    box = _open_item_menu(location, region)
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
        log(f'not buying ({why}), backing out', 1)
        return_to_station(craft, region)  # esc off the flea, back to the hideout station
        if price is not None:  # a real price over the ceiling: tell the runner to move on
            raise PriceTooHigh(f'{price} over the {max_price} ceiling')
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
            log(f'back on the {craft.station}', 1)
            return
        if time.monotonic() >= deadline:
            raise LookupError(
                f'{craft.station} panel did not reappear within {NUTRITION_RETURN_WAIT}s of '
                'leaving the flea')
        time.sleep(NUTRITION_RETURN_POLL)


def return_to_nutrition_unit(region=None):
    """Back-compat wrapper: escape the flea back to the slickers craft's station."""
    return return_to_station(SLICKERS, region)


if __name__ == '__main__':
    # _on_row keeps get_craft_state reading START/GET ITEMS off the output's own row, not the whole
    # padded band. The band is tall enough to overlap the next craft's row, and a producing craft
    # has no button of its own, so without this a neighbour's START read as 'ready' and the runner
    # looped buying inputs into an already running craft (fleece, 2026-08-28). No game needed.
    from pyscreeze import Box

    find.scale = lambda: 1.0  # no screen to measure against; ROW_TOL is a 1080p number
    row_y = 714  # a fleece output row centre, from the frame that exposed this
    same = Box(1600, 700, 56, 20)   # centre y 710, within ROW_TOL (40) of the output row
    below = Box(1600, 785, 56, 20)  # centre y 795, 81px down: the next craft's START
    assert _on_row([below], row_y) is None, 'a START on the row below must not count'
    assert _on_row([same], row_y) is same, 'a START on the output row does'
    assert _on_row([below, same], row_y) is same, 'the same-row match wins over a neighbour'
    assert _on_row([], row_y) is None, 'nothing found is nothing'
    print('ok: get_craft_state reads START/GET ITEMS on the output row only')
