"""
This module is for the hideout crafting screen.

The first thing it needs is to tell a craft that can be started from one that cannot: a START
button lit green because the ingredients are in the stash, against the same button greyed out
because they are not. That is sell.more_offers_available's problem exactly (a button that keeps
its dark plate in both states and only lights its label), so it is read the same way: the
brightest channel in the button box, thresholded.
"""
import random
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
BUY_ATTEMPTS = 6  # tries at one ingredient before giving up on it, see buy_craft_input_item
REFRESH_KEY = 'f5'  # what reloads the flea board without losing the filters already on it
REFRESH_DELAY = 2.0  # seconds after that refresh before the board is read again
# An offer over the ceiling used to end the ingredient on the spot. It does not any more: the
# board is already filtered to this one item and the trip to get here (right click, filter by
# item, open the filter window, set it, OK out) costs about twenty seconds, so throwing that away
# over one reading of a market that turns over constantly was the expensive move. Stay on the
# board, wait, refresh, look again, and only give up once every look has been too dear.
DEAR_REFRESHES = 5  # refreshes spent waiting for a cheaper offer before giving up on the item
DEAR_DELAY = 5.0  # seconds to let the board turn over before each of those refreshes
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
# The module carousel always lists its stations in this fixed left-to-right order. Only some have
# reference crops (see hideout_module_targets); the rest are here so the indices reflect the real
# geography, and so a crop added later slots in without renumbering. Names are the hideout_tabs
# subfolder names. Used to swipe toward a station instead of blindly sweeping both ways: any known
# icon on screen places us in this list, and the target's position says which way it lies.
STATION_ORDER = [
    'gear_rack', 'scav_case', 'weapon_rack', 'bitcoin_farm', 'hall_of_fame', 'heating',
    'intelligence_center', 'medstation', 'shooting_range', 'airfiltering_unit', 'booze_generator',
    'cultist_circle', 'generator', 'gym', 'illumination', 'lavatory', 'library', 'nutrition_unit',
    'rest_space', 'security', 'solar_power', 'stash', 'vents', 'water_collector', 'workbench',
]
STATION_INDEX = {name: i for i, name in enumerate(STATION_ORDER)}
SWIPE_DISTANCE = 500  # px to drag the hideout view per swipe, 1080p, scaled at swipe time
SWIPE_DURATION = 0.3  # seconds the drag itself takes
SWIPE_SETTLE = 0.5  # seconds after a swipe for the view to stop moving before it is read
MAX_SEARCH_SWIPES = 10  # swipes one way looking for a station before turning around
SWIPE_STRIP_HEIGHT = 80  # px tall strip of the module row read to tell whether a swipe moved it
SWIPE_STUCK_DIFF = 3.0  # mean grey change below this means the row did not move at all
TAB_TIMEOUT = 60.0  # seconds for the hideout tab to come back after clicking it
NAV_SETTLE = 3.0  # seconds to let a navigation land before reading or clicking again
PANEL_TIMEOUT = 15.0  # seconds to wait for a station panel after clicking its tab, see _open_station
PANEL_POLL = 0.5  # seconds between looks while that panel is awaited
PANEL_CLOSE_SETTLE = 1.0  # seconds after pressing esc for an open station panel to clear

# An open station panel carries a close (X) button in its top-right corner. Seeing that button in
# this region says a station panel is open whichever station it is, so it reads 'a panel is open'
# without a per-station title crop (which is what station_active needs and the tab-only stations
# lack). Stored as window fractions, not pixels, so it lands in the same place at any resolution.
# The x band was measured on a 2560x1440 screen at columns 2421-2549; the band spans the full screen
# height so the X is caught wherever a panel's top edge sits (different stations draw it at slightly
# different heights). 2026-09-01.
CLOSE_BUTTON_TARGET = 'close_window_button'
CLOSE_BUTTON_REGION_FRACTIONS = (2421 / 2560, 0.0, (2549 - 2421) / 2560, 1.0)

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

# get_to_station sweeps the module carousel until the target tab shows (see _scroll_to_module): one
# way to its end, then back the other way to its end, so it needs no measured span (a span was tried
# and left the far stations, nutrition unit / workbench / water collector, unreachable). SWEEP_LIMIT
# is only a backstop cap on the swipes in one direction, larger than the whole carousel is wide; the
# sweep normally stops earlier when the row hits its end and stops moving. Proven end to end by
# tests/hideout_nav/test_nav_all_stations.py, which reaches every station this way.
SWEEP_LIMIT = 30

# Booze generator: purified water + sugar -> moonshine.
MOONSHINE_TARGET = 'crafting/moonshine'
PURIFIED_WATER_TARGET = 'crafting/purified_water'
SUGAR_TARGET = 'crafting/sugar'
BOOZE_TARGET = 'hideout/hideout_tabs/booze_generator'
BOOZE_ACTIVE_TARGET = 'hideout/hideout_station_titles/booze_generator'

# The lavatory's other craft: sewing kit + sling bag -> cordura. The sewing kit is the fleece
# craft's input under the same name, so it shares that craft's ceiling and offer source.
CORDURA_TARGET = 'crafting/cordura'
SLING_BAG_TARGET = 'crafting/sling_bag'

# The workbench's other craft: green gunpowder + matches -> red gunpowder.
RED_GUNPOWDER_TARGET = 'crafting/red_gunpowder'
GREEN_GUNPOWDER_TARGET = 'crafting/green_gunpowder'
MATCHES_TARGET = 'crafting/matches'

# The water collector, which does not work like the others: see tend_water_collector in craft_bot.
# There is no START and no ingredient row. A water filter goes in the slot and the station begins
# producing on its own, so the whole job is keeping a filter in that slot.
WATER_FILTER_TARGET = 'crafting/water_filter'  # a filter itself, on the panel or in the dropdown
WATER_FILTER_DROPDOWN_TARGET = 'crafting/water_filter_dropdown'  # opens the list of filters to fit
MISSING_WATER_FILTER_TARGET = 'crafting/missing_water_filter'  # the empty slot: no filter is in
WATER_COLLECTOR_TARGET = 'hideout/hideout_tabs/water_collector'
# The panel header's crop folder is named water_filter rather than water_collector, because that
# is the folder the crop was added to. The station is the water collector.
WATER_COLLECTOR_ACTIVE_TARGET = 'hideout/hideout_station_titles/water_filter'
WATER_FILTER_NAME = 'water filter'  # what to type into the flea search to find one
WATER_DROPDOWN_DELAY = 1.0  # after opening the filter dropdown, for its list to draw
WATER_FIT_SETTLE = 1.0  # after clicking a filter, before reading the slot back
# A purchase that never took the money is an offer somebody else got to first, which on a busy
# board is the common case rather than a fault: on 2026-08-31 a 59,000 filter was clicked, the
# confirmation came up, and the dialog closed by itself with the balance untouched.
#
# No refresh between tries, unlike buy_craft_input_item's dear-board loop. That one is waiting
# for the market to change, so it has to reload the board to see it; this one is racing other
# buyers for offers that are already on screen, and reloading only throws away the rows we have.
WATER_BUY_ATTEMPTS = 5  # tries before leaving the collector empty for this pass
WATER_BUY_RETRY_DELAY = 2.0  # seconds between them
# Where the cursor goes between purchase attempts, as (across, down) fractions of the window.
#
# A PURCHASE button with the pointer resting on it is drawn in its hover state, which is a pale
# plate rather than the dark one every flea_purchase_button crop was taken from. find_all does
# not match it, so purchase_buttons misses that row entirely and the "top offer" becomes the row
# underneath. The board is sorted cheapest first, so the row that goes missing is always the one
# we wanted, and the price read afterwards is honest about the wrong row: nothing downstream can
# tell. On 2026-08-31 that bought sugar at 33,333 with a 28,999 offer sitting directly above it,
# unmatched because the cursor was still parked on its button from the attempt that just failed.
#
# The left quarter of the flea is the category tree, which holds nothing this module ever looks
# for. Mid screen, where sell._park_cursor goes, is over the offer rows themselves, and every
# corner is one of pyautogui's panic points.
PARK_FRACTIONS = (0.25, 0.5)

# A craft is everything that differs between the slickers and fleece runs, so one set of reading
# and navigation functions serves both. ingredients are (name, icon target); the name doubles as
# the key the runner looks its rouble ceiling and offer source up under, and matches the crafting/
# folder, so buying can aim at crafting/<name> without a second lookup.
class Blind(Exception):
    """An element that has to be drawn was not on screen, so the bot cannot see what it is doing.

    Never caught by the runner, and that is the whole point of it being its own class. Every
    other failure in a craft pass is a thing the game is legitimately doing (too dear, no offers,
    nothing in the dropdown) and the answer is to go tend another craft. This one means a read
    came back empty for something that is definitely drawn: an ingredient icon on a row the game
    is showing, a START button the state read just matched, a filter window that is open. That is
    a broken reference crop or a screen we are not really looking at, and neither gets better by
    trying again.

    It is deliberately not a LookupError. step() catches LookupError to swap crafts, which is
    right for the one recoverable case it is for (Tarkov's Error dialog eating a right-click
    menu) and exactly wrong here: on 2026-08-30 the green gunpowder crops stopped matching, the
    runner read "not ready, nowhere to click", logged one line and did the identical pass again
    every seven seconds for seven minutes, buying nothing and raising nothing. Subclassing
    LookupError would have turned that silent loop into a noisy one and nothing more.
    """


class Unbuyable(Exception):
    """Raised by buy_craft_input_item when this ingredient is not worth staying on the flea for.

    Three different things end that way and the runner answers all three the same, by backing out
    and going to tend another craft, so they share one exception rather than one each. What they
    must not share is a name: this was called Unbuyable while it also carried a locked offer
    and a lost race, so a log or a traceback said "too expensive" about an item whose price was
    fine. The cause lives in the message, and each of the three is worded differently on purpose,
    because reading back a run and telling them apart is the whole point:

      - "<price> over the <ceiling> ceiling"           the offer really is too dear
      - "has no PURCHASE button, ..."                  a spent trader limit, or an empty board
      - "could not be bought in <n> attempts"          outbid, over and over

    The caller has already backed out to the station by the time this is raised.
    """


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
MOONSHINE = Craft('moonshine', MOONSHINE_TARGET,
                  (Ingredient('purified_water', PURIFIED_WATER_TARGET),
                   Ingredient('sugar', SUGAR_TARGET)),
                  BOOZE_TARGET, BOOZE_ACTIVE_TARGET, 'booze generator')
CORDURA = Craft('cordura', CORDURA_TARGET,
                (Ingredient('sewing_kit', SEWING_KIT_TARGET),
                 Ingredient('sling_bag', SLING_BAG_TARGET)),
                LAVATORY_TARGET, LAVATORY_ACTIVE_TARGET, 'lavatory')
RED_GUNPOWDER = Craft('red_gunpowder', RED_GUNPOWDER_TARGET,
                      (Ingredient('green_gunpowder', GREEN_GUNPOWDER_TARGET),
                       Ingredient('matches', MATCHES_TARGET)),
                      WORKBENCH_TARGET, WORKBENCH_ACTIVE_TARGET, 'workbench')
# The water collector's "output" and its one "ingredient" are both the water filter, so the
# normal row reads have something to aim at, but craft_bot never runs the ready/producing state
# machine over it: WATER_COLLECTOR_NAME sends it down tend_water_collector instead. The
# ingredient entry exists so the GUI gives the filter a max-price field like any other input.
WATER_COLLECTOR = Craft('water_collector', WATER_FILTER_TARGET,
                        (Ingredient('water_filter', WATER_FILTER_TARGET),),
                        WATER_COLLECTOR_TARGET, WATER_COLLECTOR_ACTIVE_TARGET, 'water collector')
WATER_COLLECTOR_NAME = WATER_COLLECTOR.name  # craft_bot tests against this to pick its own branch
CRAFTS = {c.name: c for c in (SLICKERS, FLEECE, WIRES, AI2, MOONSHINE, CORDURA, RED_GUNPOWDER,
                              WATER_COLLECTOR)}


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


def wait_hideout_tab_active(region=None, timeout=TAB_TIMEOUT, poll=0.3):
    """Poll until the hideout tab reads active (lit), or time out. The brightness read, not the crop.

    The HIDEOUT_TAB_TARGET crop is the dim/inactive tab, so template-matching it against the lit
    active tab after clicking in is flaky and gave the false 'tab never came back' failures. The
    brightness read tells lit from dim cleanly, and lit is the actual thing we are waiting for.
    """
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if is_hideout_tab_active(region):
            return True
        time.sleep(poll)
    return is_hideout_tab_active(region)


def station_active(craft, region=None):
    """True when this craft's station panel is open, read off its header title."""
    active = find.find(craft.station_title, region) is not None
    log(f'{craft.station} panel {"open" if active else "not open"}', 1)
    return active


def check_if_nutrition_unit_active(region=None):
    """Back-compat wrapper: is the slickers craft's station (the nutrition unit) open."""
    return station_active(SLICKERS, region)


def _region_from_fractions(fractions, region=None):
    """Turn (left, top, width, height) window fractions into an absolute (l, t, w, h) screen region."""
    left, top, width, height = region if region is not None else screen.rect()
    lf, tf, wf, hf = fractions
    return (left + round(lf * width), top + round(tf * height),
            round(wf * width), round(hf * height))


def check_if_station_active(region=None):
    """True when a station panel is open, read off its close (X) button in the panel's top-right.

    Station-independent, unlike station_active(craft, ...): it looks for the close_window_button in
    CLOSE_BUTTON_REGION_FRACTIONS of the window rather than a per-station title crop, so it works for
    every station including the tab-only ones that have no title reference. The region scopes the
    match so a close button anywhere else in the UI cannot read as an open station panel.
    """
    box = find.find(CLOSE_BUTTON_TARGET, _region_from_fractions(CLOSE_BUTTON_REGION_FRACTIONS, region))
    log(f'station panel {"open" if box else "not open"} (close button)', 1)
    return box is not None


def close_open_station_panel(region=None):
    """Click an open station panel's close (X) button so it stops covering the module row. True if one was.

    A station panel left open from the last craft sits over part of the carousel. Closed by clicking
    the X we already locate rather than pressing esc: a click lands in the game and self-focuses the
    window, where a bare esc keypress only reaches the game when it is already the foreground window,
    which is not guaranteed before navigation's first click (seen 2026-09-01: the panel stayed open
    and the run stalled). No-op when nothing is open.
    """
    box = find.find(CLOSE_BUTTON_TARGET, _region_from_fractions(CLOSE_BUTTON_REGION_FRACTIONS, region))
    if not box:
        log('no station panel open', 1)
        return False
    log('a station panel is open; clicking its close button before navigating', 1)
    pyautogui.click(*sell.jitter(pyautogui.center(box)))
    time.sleep(PANEL_CLOSE_SETTLE)
    return True


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


def _module_basename(target):
    """The station key ('nutrition_unit') out of a module target ('hideout/hideout_tabs/nutrition_unit')."""
    return target.rsplit('/', 1)[-1]


def visible_station_positions(region=None):
    """STATION_ORDER indices of every known module icon on screen, sorted. [] when none show.

    Only the modules with reference crops (hideout_module_targets) can be seen, a subset of
    STATION_ORDER, but any one of them places us: the carousel shows a contiguous run of the order,
    so a single known icon says roughly where in the list we are looking.
    """
    positions = []
    for target in hideout_module_targets():
        i = STATION_INDEX.get(_module_basename(target))
        if i is not None and find.find_all(target, region):
            positions.append(i)
    return sorted(positions)


def _preferred_first_dx(craft, dist, region=None):
    """The drag to try first, +dist or -dist, or None when the target's side cannot be told.

    STATION_ORDER runs left to right. Dragging the row left (negative dx) reveals stations further
    right in that order, dragging right (positive dx) reveals ones further left. So a target past
    every icon on screen lies to the right (drag left for it); one before them all lies to the left
    (drag right); one inside the visible span is already at hand and the blind order is fine. Only a
    hint: get_to_station sweeps the other way too when this one comes up empty, so a wrong guess (or
    a carousel that drags the opposite way to this assumption) costs a reversal, not the station.
    """
    target_i = STATION_INDEX.get(_module_basename(craft.module_target))
    if target_i is None:
        return None
    visible = visible_station_positions(region)
    if not visible:
        return None
    if target_i > visible[-1]:
        return -dist
    if target_i < visible[0]:
        return dist
    return None


def _swipe(x, y, dx):
    """Drag the hideout view horizontally by dx from (x, y). Negative dx swipes left."""
    log(f'swiping from ({x}, {y}) by {dx}', 2)
    pyautogui.moveTo(x, y)
    pyautogui.dragTo(x + dx, y, duration=SWIPE_DURATION, button='left')


def _scroll_to_module(target, x, y, dist, region=None):
    """Sweep the module carousel until `target`'s tab is on screen. True if it showed.

    Sweeps one way to its end, then the other way to its end, checking before every swipe, so the tab
    is found whichever side of the row it lies on without trusting a measured swipe-count span (that
    span left the far stations unreachable). 'End' is the row no longer moving (_row_moved off a strip
    diff) for two swipes running, since the hideout is never perfectly still; SWEEP_LIMIT is only a
    backstop if end-detection never trips. Proven by tests/hideout_nav/test_nav_all_stations.py.
    """
    if find.find(target, region):
        return True
    for step in (dist, -dist):  # one way to the wall, then back the other way to the wall
        stuck = 0
        for _ in range(SWEEP_LIMIT):
            before = _row_strip(y, region)
            _swipe(x, y, step)
            time.sleep(SWIPE_SETTLE)
            if find.find(target, region):
                return True
            if _row_moved(before, _row_strip(y, region)):
                stuck = 0
            else:
                stuck += 1
                if stuck >= 2:
                    break  # this end reached; try the other direction
    return False


def _row_strip(y, region=None):
    """A thin strip across the module row, read only to tell whether a swipe moved anything."""
    left, top, width, height = region if region is not None else screen.rect()
    half = round(SWIPE_STRIP_HEIGHT * find.scale() / 2)
    y = min(max(round(y), top + half), top + height - half)  # keep the strip inside the window
    return np.asarray(screen.grab((left, y - half, width, half * 2)).convert('L'), dtype=float)


def _row_moved(before, after):
    """Did the carousel actually shift, or is it up against its end and ignoring the drag.

    Compared as a mean grey difference rather than pixel for pixel: the hideout is never perfectly
    still, so an exact match would only ever happen on a frozen screen. A row that moved changes
    this strip by tens of levels; one that did not moves it by well under one.
    """
    moved = float(np.abs(after - before).mean())
    log(f'module row changed by {moved:.1f} vs {SWIPE_STUCK_DIFF}', 2)
    return moved >= SWIPE_STUCK_DIFF


def get_to_station(craft, region=None):
    """Navigate the hideout to this craft's station and open it. True on success, else raises.

    Ensures the hideout tab is active (clicking it if not), closes any open station panel (it covers
    the module row and eats the drag), then sweeps the module carousel until the station's tab shows
    (see _scroll_to_module): one way to its end, then the other way to its end. This replaces an
    anchor-on-the-medstation-and-count-swipes walk whose measured span left the far stations
    (nutrition unit, workbench, water collector) permanently one swipe out of reach. Every dead end
    (no tab, tab will not activate, no module row to grab, the station never reached anywhere on the
    row) raises LookupError rather than clicking blind. tests/hideout_nav/test_nav_all_stations.py
    drives this against the live hideout and reaches every station.
    """
    if is_hideout_tab_active(region):
        log('already on the hideout tab, skipping to the module search', 1)
    else:
        tab = find.find(HIDEOUT_TAB_TARGET, region)
        if not tab:
            raise LookupError('hideout tab button not on screen')
        log('not on the hideout tab, clicking it', 1)
        pyautogui.click(*sell.jitter(pyautogui.center(tab)))
        time.sleep(SWIPE_SETTLE)  # let it start transitioning before we poll for the lit state
        if not wait_hideout_tab_active(region, TAB_TIMEOUT):
            raise LookupError('hideout tab did not become active after clicking it')

    # A station panel left open from the last craft covers part of the module row and eats the drag,
    # so close it before reading or scrolling the carousel.
    close_open_station_panel(region)

    icons = hideout_icons(region)
    if not icons:
        raise LookupError('no hideout module icons on screen to grab the view by')
    x = round(sum(_center(b)[0] for b in icons) / len(icons))
    y = round(sum(_center(b)[1] for b in icons) / len(icons))
    log(f'module row grab point ({x}, {y}) off {len(icons)} icons', 1)

    dist = round(SWIPE_DISTANCE * find.scale())
    log(f'sweeping the carousel for the {craft.station}', 1)
    if not _scroll_to_module(craft.module_target, x, y, dist, region):
        raise LookupError(f'{craft.station} never appeared sweeping the whole carousel both ways')
    log(f'{craft.station} found', 1)
    return _open_station(craft, region)


def _open_station(craft, region=None):
    """Settle, re-find the station's module label, click it, confirm its panel opened. True/raises.

    Called once get_to_station's sweep has the module's tab on screen.

    Exactly one click, then wait up to PANEL_TIMEOUT for the panel. Clicking a second time is
    worse than useless: the tab is already the selected one by then, so the second click navigates
    back out of the station it just entered. That is what a two-click retry was really doing when
    it ended a run on 2026-08-30 with the Medstation tab already lit up in the captured frame.

    The wait is long because the hideout flies the camera to the room before drawing anything, and
    a fixed 3s sleep plus a single look lands inside that animation: the frame that ended the run
    was a half-painted room on a mostly black screen. Polling costs nothing when the panel is
    already up, since the first look returns.
    """
    log(f'{craft.station} found, settling {NAV_SETTLE}s before clicking', 1)
    time.sleep(NAV_SETTLE)
    box = find.find(craft.module_target, region)
    if not box:
        raise LookupError(f'lost the {craft.station} while the screen settled')
    pyautogui.click(*sell.jitter(pyautogui.center(box)))
    log(f'clicked the {craft.station}, waiting up to {PANEL_TIMEOUT}s for its panel', 1)
    deadline = time.monotonic() + PANEL_TIMEOUT
    while True:
        if station_active(craft, region):
            return True
        if time.monotonic() >= deadline:
            raise LookupError(f'clicked the {craft.station} but its panel never opened '
                              f'within {PANEL_TIMEOUT}s')
        time.sleep(PANEL_POLL)


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
    return _output_matches(craft, region)[0]


def _output_matches(craft, region=None):
    """(the timer-anchored outputs, every match of the output item). One search of each.

    Split out so output_box can ask both questions from one pass over the screen. It used to
    call output_items and then, when that came back empty, search the output item all over
    again for its fallback: two find_alls of the same target, about 0.3s each on a 1440p screen,
    every time a craft was producing or done.
    """
    tol = ROW_TOL * find.scale()
    timers = find.find_all(TIMER_TARGET, region)
    items = find.find_all(craft.output_target, region)
    outputs = []
    for item in items:
        ix, iy = _center(item)
        if any(_center(t)[0] < ix and abs(_center(t)[1] - iy) <= tol for t in timers):
            outputs.append(item)
    return outputs, items


def output_box(craft, region=None):
    """This craft's output bar, in whatever state the craft is in, or None.

    Prefers the timer-anchored output (right in the ready state), and falls back to the rightmost
    item match when there is no timer, which is every other state: the output sits at the far
    right of its row, right of the ingredients, so it is the rightmost match of the item on screen.
    """
    timed, items = _output_matches(craft, region)
    if timed:
        return max(timed, key=lambda b: b.left)
    return max(items, key=lambda b: b.left) if items else None


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


# One look at a craft's row. state is the same four strings get_craft_state answers with;
# output/band/start/get_items are the boxes that answer was based on, so a caller acting on the
# state never has to search for them again; inputs is [(name, ready, where to click)] in the
# craft's ingredient order, and is None in every state but 'ready' because nothing else needs it.
CraftRead = namedtuple('CraftRead', 'state output band start get_items inputs')


def read_craft(craft, region=None):
    """Read this craft's whole row once and hand back everything a pass acts on.

    The runner used to search the same row four times a pass: get_craft_state looked for the
    output, craft_plan looked for it twice more (once through find_craft, once through
    output_box), and validate_craftable then ran the whole of craft_plan again. Each of those
    searches is a find_all of the timer icon plus a find_all of the output item, about 0.55s a
    pair on a 1440p screen, so a red gunpowder pass spent 4.4 of its 7.1 seconds re-answering
    a question it had already answered. Nothing is clicked between those looks, so they could
    only ever agree, and when one disagreed (a flaky match) the pass silently did nothing.

    So: one search, and the boxes come back with the answer. start_craft clicks read.start,
    collect_craft clicks read.get_items, and the buying loop walks read.inputs.

    The ingredient and checkmark searches only happen in the 'ready' state, since that is the
    only state with a queue to build.

    Raises Blind when the output is not on screen, or when an ingredient icon is not on a row
    the game is drawing. Both mean a read came back empty for something that is definitely
    there, and neither is a state the runner can do anything sensible with.
    """
    output = output_box(craft, region)
    if output is None:
        raise Blind(f'{craft.name} output not on screen, cannot read the craft row')
    band = _row_band(output, region)
    row_y = _center(output)[1]

    start = None
    get_items = _on_row(find.find_all(GET_ITEMS_TARGET, band), row_y)
    if get_items:
        state = 'done' if get_items_highlighted(get_items) else 'not started'
    else:
        start = _on_row(find.find_all(START_TARGET, band), row_y)
        state = 'ready' if start else 'producing'
    log(f'{craft.name} craft state: {state}', 1)

    inputs = None
    if state == 'ready':
        checks = find.find_all(CHECK_TARGET, band)
        inputs = []
        for ing in craft.ingredients:
            icons = find.find_all(ing.target, band)
            if not icons:
                raise Blind(
                    f'{ing.name} icon is not on the {craft.name} row, which the game is drawing '
                    f'right now: every input is shown there with a tick or a cross under it. The '
                    f'crops in reference_images/{ing.target} do not match what is on screen')
            icon = min(icons, key=lambda b: abs(_center(b)[1] - row_y))
            ready = _mark_beneath(icon, checks) is not None
            log(f'{ing.name}: {"ready" if ready else "not ready"}', 1)
            inputs.append((ing.name, ready, _center(icon)))
    return CraftRead(state, output, band, start, get_items, inputs)


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
    return read_craft(craft, region).state


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
        raise Blind(f'no {craft.name} craft output on screen, so there is no row to frame')
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
        # Tarkov's plain Error dialog is modal, so while it is up the right click landed on it
        # and no menu exists at all. It is the one reason to miss here that costs nothing to
        # undo, and every other mode already clears it on a failure like this. Only worth a
        # look on the last try: the earlier ones are the hover race above, not a dialog.
        if attempt == attempts - 1 and sell.dismiss_error_popup(region):
            log('an Error dialog was over the menu; cleared it and trying the slot once more', 1)
            pyautogui.moveTo(*location)
            time.sleep(MENU_DELAY)
            pyautogui.rightClick(*location)
            time.sleep(MENU_DELAY)
            return find.find('filter_by_item', region)
    return None


def buy_craft_input_item(location, max_price, region=None, source='players', craft=SLICKERS):
    """Buy one craft ingredient off the flea, if the cheapest offer is at or under max_price.

    location is where the ingredient sits in the craft row (a point to right click). source is who
    to buy from, 'players' or 'traders', and only changes the offers-from filter. craft is which
    craft this input belongs to, so the flea can be escaped back to the right station afterwards.
    The flow is the flea sniper's, aimed from a right click rather than a typed search: filter the
    board to this one item through the inventory menu, put the filters on, read the top offer's
    price, and buy that row only when it is cheap enough.

    Two things send it round again on the same board rather than back out to the station, both
    by refreshing with REFRESH_KEY and reading the new top offer:

      - a purchase that lost a race to another buyer, up to BUY_ATTEMPTS times in all
      - a top offer over the ceiling, or too clipped to read, DEAR_REFRESHES more looks
        at DEAR_DELAY apart

    The second one is the newer of the two and is worth the wait for the same reason as the
    first: the board is already filtered to this one item, and getting back to this point from
    the station is a right click, a menu, a filter window and about twenty seconds. A single
    reading of a market that turns over constantly is a thin reason to spend that.

    Returns True if it bought. Raises Unbuyable when every look was over the ceiling or too
    clipped to read (both are a live board that a refresh may improve, so both are waited out
    DEAR_REFRESHES times before giving up), when no row has a PURCHASE button to click (a spent
    trader limit shows the offer as LOCKED, and an empty board looks the same), or when
    BUY_ATTEMPTS ran out.
    All of those mean the same thing: leave this ingredient and go tend another craft. Raises LookupError if the 'filter by item'
    menu entry never appears, since without it there is no way to narrow the board to this
    ingredient and nothing after this step would mean anything. craft_bot catches both and swaps
    craft rather than ending the run: one slot the game will not open a menu on, or one offer
    that keeps getting sniped, says nothing about the other crafts.
    """
    log(f'buying craft input at {location}, ceiling {max_price}')
    box = _open_item_menu(location, region)
    if not box:
        raise LookupError('no filter by item in the menu, cannot narrow the board to this item')
    point = sell.jitter(pyautogui.center(box), y=0)  # a 6px tall crop says nothing about the row
    log(f'clicking filter by item at {point}', 1)
    pyautogui.click(*point)

    time.sleep(FLEA_LOAD_DELAY)  # the flea board opens from scratch here, give its UI time to draw

    # A look before the filters go on. The right click already narrowed the board to this one
    # item, and its cheapest offer is often a rouble one already under the ceiling, so buying it
    # here saves opening the filter window and setting it. Only a clean read is trusted:
    # snipe.read_price refuses a dollar row and a clipped price, so a mixed-currency board comes
    # back None and falls through to the filtered flow rather than buying a number off the wrong
    # market. What it does skip is the offers-from filter, so a cheap enough offer from the other
    # source (a trader when 'players' was asked, or the reverse) can be taken here: the deliberate
    # cost of the shortcut, and it only ever fires on an offer already at or under the ceiling.
    top = _top_offer(region)
    if top is not None:
        price = snipe.read_price(top)
        if price is not None and price <= max_price:
            log(f'{price} is at or under {max_price} before filtering, buying', 1)
            if snipe.buy(top, region):
                time.sleep(BOUGHT_SETTLE)
                return_to_station(craft, region)  # the buy leaves the flea up over the panel
                return True
            log('lost that offer before filtering; setting the filters and reading the board '
                'properly', 1)

    # No condition filter: a craft input is consumed, not resold, so a scuffed one is fine and
    # filtering on 100% only hides the cheaper offers we are here for.
    #
    # The return value is checked, which it was not until 2026-08-31. Every price read after
    # this is only meaningful because the board is in roubles and showing the right offer
    # source; an unfiltered board answers with a number that looks exactly as valid and is
    # about a different market. apply_flea_filters only comes back False when it could not
    # read its own controls, which is a window it cannot see rather than a filter the game
    # refused, so it is Blind rather than something to shrug at.
    if not sell.apply_flea_filters(region, source=source, set_condition=False):
        raise Blind('the flea filters could not be confirmed, so no price on this board can be '
                    'trusted')

    # Read the top offer and buy it, and go round again on either of the two things that leave
    # us still wanting the item, refreshing the board with REFRESH_KEY each time rather than
    # walking back out to the station and starting the twenty second trip over from the top:
    #
    #   - the money did not actually leave. snipe.buy answers that off the rouble balance either
    #     side of the click, so a race lost to another buyer is a False here and not a silent
    #     nothing. BUY_ATTEMPTS tries in all.
    #   - the top offer is over the ceiling. DEAR_REFRESHES more looks, DEAR_DELAY apart, since
    #     the board is a live market and the cheap offer that is not there now may be there in
    #     half a minute. Counted separately from the races: they are different waits for
    #     different reasons and one should not eat the other's tries.
    # Two counters, not one, because the two reasons to go round again are different waits for
    # different reasons and neither should eat the other's tries.
    dear = 0  # looks that came back over the ceiling
    races = 0  # purchase clicks whose money never left
    while True:
        top = _top_offer(region)
        if top is None:
            # No PURCHASE button on any row. Two things look like this and neither is worth
            # standing here for: a trader offer showing LOCKED because its per-hour limit is
            # spent, and a board with nothing on it at all. The price beside a locked row can be
            # perfectly good, which is the trap: the row reads as a bargain and can never be
            # bought, so a bot that waits on it waits until the hour turns over.
            #
            # Backing out lets the runner swap craft, which comes back round to this one next
            # lap with the limit that much closer to reset. That does mean any other input still
            # queued for this craft goes unbought this pass, and for the same reason as ever:
            # the craft cannot start without this one anyway.
            log('no PURCHASE button on the filtered board, so this cannot be bought right now '
                '(a trader limit shows the offer as LOCKED), backing out', 1)
            return_to_station(craft, region)
            raise Unbuyable('has no PURCHASE button, most likely a spent trader limit')

        price = snipe.read_price(top)
        # Two ways the top offer is no good this look, both waited out the same way. A clipped
        # price used to bail here at once, on the theory that a refresh brings the same board
        # back; the run of 2026-08-31 disproved it, the top offer changed every refresh
        # (135555 -> 137000 -> clipped -> 133333, then bought), and because buy_craft_input_item
        # returned False rather than raising, step() ignored it and re-bought the same still
        # missing input pass after pass. So an unreadable price now shares the dear budget and
        # ends in Unbuyable, which is what makes the runner swap craft instead of looping.
        if price is None or price > max_price:
            why = ('unreadable (clipped at the edge of its box)' if price is None
                   else f'over the {max_price} ceiling')
            if dear >= DEAR_REFRESHES:
                log(f'top offer {why} on all {dear + 1} looks, backing out', 1)
                return_to_station(craft, region)
                raise Unbuyable(f'{why} on all {dear + 1} looks'
                                + (f', cheapest {price}' if price is not None else ''))
            dear += 1
            # ponytail: a plain sleep, so a Stop pressed here lands up to DEAR_DELAY late. The
            # same is already true of FLEA_LOAD_DELAY and OFFER_WAIT on this path. Thread the
            # runner's stop Event down the way sell.wait_for_offer_slot takes one if it grates.
            log(f'top offer {why}; waiting {DEAR_DELAY:.0f}s on the board for a better offer '
                f'(look {dear} of {DEAR_REFRESHES})', 1)
            time.sleep(DEAR_DELAY)
            _refresh_board(region)
            continue

        log(f'{price} is at or under {max_price}, buying', 1)
        if snipe.buy(top, region):
            time.sleep(BOUGHT_SETTLE)
            return_to_station(craft, region)  # the buy leaves the flea up over the panel
            return True

        races += 1
        log('the purchase did not go through, most likely someone else took the offer', 1)
        if races >= BUY_ATTEMPTS:
            # Out of tries. Same answer as a board that stayed dear, because it means the same
            # thing to the runner: there is no sense standing on the flea for this ingredient
            # any longer, so back out and let it go tend another craft.
            log(f'gave up after {BUY_ATTEMPTS} attempts, backing out', 1)
            return_to_station(craft, region)
            raise Unbuyable(f'could not be bought in {BUY_ATTEMPTS} attempts')
        log(f'refreshing the board with {REFRESH_KEY.upper()} and buying again '
            f'(attempt {races + 1} of {BUY_ATTEMPTS})', 1)
        _refresh_board(region)


def park_off_the_board(region=None):
    """Move the pointer to the left middle, clear of any PURCHASE button. Returns where it went.

    Called between purchase attempts, never before the first: the cursor only ends up on a
    button by having just clicked one. See PARK_FRACTIONS for what a hovered button costs.
    """
    left, top, width, height = region if region else screen.rect()
    across, down = PARK_FRACTIONS
    point = (left + round(width * across), top + round(height * down))
    log(f'parking the cursor at {point}, off any PURCHASE button the next look has to match', 2)
    pyautogui.moveTo(*point)
    return point


def _refresh_board(region=None):
    """Reload the flea board without losing the filters already on it, and let it redraw.

    The cursor comes off the board first. A refresh redraws every row, but it does not move the
    pointer, so a button under it comes back hovered and unmatchable exactly as before.
    """
    park_off_the_board(region)
    pyautogui.press(REFRESH_KEY)
    time.sleep(REFRESH_DELAY)


def _top_offer(region=None):
    """The cheapest offer's PURCHASE button on the filtered board, or None if none arrives.

    The board reloads after the filters go on, and again after a refresh, and offers do not all
    appear at once, so this polls rather than reading once: up to OFFER_WAIT, every OFFER_POLL.
    """
    deadline = time.monotonic() + OFFER_WAIT
    while True:
        buttons = snipe.purchase_buttons(region)
        if buttons:
            return buttons[0]
        if time.monotonic() >= deadline:
            return None
        time.sleep(OFFER_POLL)


def water_filter_state(region=None):
    """'fitted' or 'empty' for the water collector's input slot. Raises Blind if it will not read.

    Two crops for two states, read positively, the way browse_button_selected and
    browse_button_unselected already split the flea's browse tab. The old version asked one
    question, "is the missing-filter icon on screen", and answered False for both "a filter is
    in" and "I could not see the missing icon". A blind read came back as the good state, so a
    crop that stopped matching read as a collector quietly producing and the runner swapped away
    from a station that was doing nothing.

    Neither crop matching is Blind, and so is both matching: one of the two sets would then be
    loose enough to match the other state, and nothing here can say which.
    """
    fitted = find.find(WATER_FILTER_TARGET, region)
    empty = find.find(MISSING_WATER_FILTER_TARGET, region)
    if fitted and empty:
        raise Blind('the water collector slot matched both a fitted filter and the empty-slot '
                    'icon, so one of those two crop sets is too loose to tell them apart')
    if fitted:
        return 'fitted'
    if empty:
        return 'empty'
    raise Blind('the water collector slot matched neither a fitted filter nor the empty-slot '
                'icon, so its state cannot be read; the panel is open, so one of them is drawn')


def open_filter_dropdown(region=None):
    """Click the collector's filter dropdown open and return what it lists.

    A list of the water filter boxes in it, empty when it has none to offer, which is the
    honest answer that sends the caller off to buy one. The dropdown itself not being on the
    panel is Blind: the panel is open and the slot just read as empty, so the control is drawn.

    The wait after the click is the list drawing. Reading it before it has drawn turns a stash
    with filters in it into a trip to the flea.
    """
    point = find.find_center(WATER_FILTER_DROPDOWN_TARGET, region)
    if point is None:
        raise Blind('no water filter dropdown on the water collector panel, which is open and '
                    'showing an empty slot, so the control is there to be clicked')
    point = sell.jitter(point)
    log(f'opening the water filter dropdown at {point}', 1)
    pyautogui.click(*point)
    time.sleep(WATER_DROPDOWN_DELAY)
    listed = find.find_all(WATER_FILTER_TARGET, region)
    log(f'the dropdown lists {len(listed)} water filter(s)', 1)
    if not listed:
        # Nothing to fit, so shut the list again before handing back. An empty answer sends the
        # caller to the flea, and an open dropdown is an overlay that eats every click aimed
        # past it: the flea taskbar entry gets clicked, absolutely nothing happens, and
        # buy_water_filter raises Blind about a flea that was never actually asked to open.
        #
        # Seen twice on 2026-08-31. The tell in the log is a run of identical brightness reads,
        # 64 every time across the whole wait, where a flea that is merely slow climbs (63.7
        # shut, 73.1 mid-transition, 118.6 open). A flat line is a click that never landed.
        #
        # A second click on the same control, not escape: escape closes the biggest thing on
        # screen, which here is the station panel itself, and that is the one thing every step
        # after this needs.
        log('nothing listed, closing the dropdown again so the rest of the screen takes clicks', 1)
        pyautogui.click(*point)
        time.sleep(WATER_DROPDOWN_DELAY)
    return listed


def fit_water_filter(listed, region=None):
    """Click one of the filters the dropdown listed, then check the slot took it.

    A random one rather than the topmost: they are interchangeable, and always taking the first
    means always taking the same slot in a list the game is free to reorder.

    True once the slot reads 'fitted', at which point the station is producing on its own; there
    is no START here to press afterwards. False means the click went out and the slot still
    reads empty, which is a real thing the game does and worth another pass rather than an
    error. A slot that will not read at all is Blind, from water_filter_state.
    """
    box = random.choice(listed)
    point = sell.jitter(pyautogui.center(box))
    log(f'fitting a water filter at {point}, one of {len(listed)} listed', 1)
    pyautogui.click(*point)
    time.sleep(WATER_FIT_SETTLE)
    fitted = water_filter_state(region) == 'fitted'
    log('the collector has a filter in it and is producing' if fitted
        else 'the slot still reads empty after the click', 1)
    return fitted


def buy_water_filter(max_price, region=None, source='players', craft=WATER_COLLECTOR):
    """Buy one water filter off the flea, if the cheapest offer is at or under max_price.

    Not buy_craft_input_item, and the difference is where the board's item filter comes from.
    Every other ingredient sits in a craft row that can be right clicked into 'filter by item';
    a water filter the collector does not have is on no row at all, so the board is narrowed by
    typing the name the way the sniper does. The condition filter is on here for the same
    reason it is off there: a filter is fitted and consumed over its whole durability, so a
    scuffed one is worth proportionally less rather than being just as good.

    Returns True if it bought. False covers every way it did not: the flea would not open, the
    search came back locked or empty, the price could not be read, or the top offer was over the
    ceiling. The station is back on screen either way.
    """
    log(f'buying a water filter off the flea, ceiling {max_price}')
    # Both of these are Blind rather than a shrug, for the same reason. open_clean_board comes
    # back False when the flea icon is not on screen or the click did not take, which is a
    # screen we are not really looking at rather than the game declining to open. And an
    # unfiltered board answers a price read with a number that looks exactly as valid and is
    # about a different market.
    if not snipe.open_clean_board(region):
        raise Blind('the flea would not open, so there is no board to buy a water filter from')
    if not sell.apply_flea_filters(region, reset=True, source=source, set_condition=True):
        raise Blind('the flea filters could not be confirmed, so no price on this board can be '
                    'trusted')

    # And a second look for a filter-by-item chip, after the filter window rather than only
    # before it, the same pair of clears snipe_bot.sweep_once does. Two things put one back:
    # the filter window's reset can restore a saved filter set with a chip in it, and this mode
    # in particular arrives here with one far more often than the sniper does, because
    # buy_craft_input_item narrows the board by setting exactly this chip for every other
    # ingredient it buys.
    #
    # A board still filtered to one item answers every search with that item, and this is the
    # one buying path that finds its item by typing a name. So the failure is not an empty board
    # that gives up: it is the previous ingredient's offers sat under a 'water filter' search,
    # read as if they were filters, and bought if they happen to be under the ceiling.
    if snipe.remove_filter_by_item_filter(region):
        log(f'the board came out of the filter window still filtered by item; cleared it and '
            f'giving it {snipe.BOARD_DELAY}s to reload', 1)
        time.sleep(snipe.BOARD_DELAY)

    box = snipe.find_search_box(region)
    if snipe.search_for(WATER_FILTER_NAME, box, region) is None:
        log('water filter came back locked, not buying', 1)
        return_to_station(craft, region)
        return False
    time.sleep(snipe.BOARD_DELAY)  # the board repopulates after the suggestion is clicked

    buttons = snipe.purchase_buttons(region)
    if not buttons:
        log('no water filter offers on the board, nothing to buy', 1)
        return_to_station(craft, region)
        return False

    top = buttons[0]
    price = snipe.read_price(top)
    if price is None or price > max_price:
        why = 'unreadable' if price is None else f'{price} over the {max_price} ceiling'
        log(f'not buying a water filter ({why}), backing out', 1)
        return_to_station(craft, region)
        return False

    log(f'{price} is at or under {max_price}, buying a water filter', 1)
    # snipe.buy answers off the rouble balance either side of the click, so a False here is the
    # money genuinely not having left rather than a click we failed to see land. That means an
    # offer taken by another buyer between reading its price and pressing yes, and the answer is
    # simply to go again: the board is still on screen, still filtered, and still full of filters
    # at this price. Five tries, WATER_BUY_RETRY_DELAY apart.
    for attempt in range(1, WATER_BUY_ATTEMPTS + 1):
        if snipe.buy(top, region):
            time.sleep(BOUGHT_SETTLE)
            return_to_station(craft, region)
            return True
        if attempt < WATER_BUY_ATTEMPTS:
            log(f'the money never moved, so somebody else took that offer; going again in '
                f'{WATER_BUY_RETRY_DELAY:.0f}s (attempt {attempt + 1} of {WATER_BUY_ATTEMPTS})', 1)
            # Off the button before the wait, not after: this loop does not refresh, so the
            # cursor would otherwise sit on the row it just clicked for the whole delay and the
            # next look would skip it. Same park, different reason from the refreshing loop.
            park_off_the_board(region)
            time.sleep(WATER_BUY_RETRY_DELAY)

    # Out of tries. False rather than a raise, because losing five races says nothing is wrong
    # with the bot or the board: tend_water_collector leaves the collector empty, swaps to the
    # next craft, and comes back to this station next lap.
    log(f'lost the offer {WATER_BUY_ATTEMPTS} times running, leaving the collector empty and '
        f'coming back to it next lap', 1)
    return_to_station(craft, region)
    return False


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

    # _preferred_first_dx points the first sweep at the target's side of the carousel off the icons
    # on screen, and abstains when it cannot tell. visible_station_positions is stubbed so no game
    # is needed; the indices are STATION_ORDER positions.
    Fake = namedtuple('Fake', 'module_target station')
    med = Fake('hideout/hideout_tabs/medstation', 'medstation')    # index 7
    work = Fake('hideout/hideout_tabs/workbench', 'workbench')      # index 24, the last
    lav = Fake('hideout/hideout_tabs/lavatory', 'lavatory')        # index 15
    visible_station_positions = lambda region=None: [17]           # nutrition unit (17) on screen
    assert _preferred_first_dx(med, 100) == 100, 'target left of the visible icon: drag right'
    assert _preferred_first_dx(work, 100) == -100, 'target right of the visible icon: drag left'
    visible_station_positions = lambda region=None: [7, 24]        # target between them: no hint
    assert _preferred_first_dx(lav, 100) is None, 'target inside the visible span: no hint'
    visible_station_positions = lambda region=None: []             # nothing placeable on screen
    assert _preferred_first_dx(med, 100) is None, 'no known icons on screen: no hint'
    print('ok: _preferred_first_dx points at the target side and abstains when blind')
