"""
DailyReset: the fifth mode, the SUDAK tab. Rerolls Ragman's operational 'Find and transfer' daily
with REPLACE until it offers the craftable item the GUI's SUDAK ITEM dropdown picked, then stops
on its own.

Start it on TRADERS > TASKS with Ragman selected. Accepting the task is left to the player.
Grew out of _sudak_daily_resetter/daily_resetter.py, which is where the region and thresholds
were measured; the item corpus and SUDAK_CONFIDENCE were measured in _sudak_options/ and are
pinned by tests/sudak/test_sudak_name_match.py.
"""
import threading

import pyautogui

import screen
from interact import find
from narrate import log
from sell_bot import Stopped

OFFER = 'tasks/find_and_transfer_daily_offer'
REPLACE = 'tasks/replace_daily_button'

# Where the objective line sits, as fractions of the screen (left, top, width, height). Measured
# off the item-name search region (552, 577, 1919, 703) in 1080p pixels with
# _sudak_options/region_picker.html, so find() only matches a name where an offer's objective
# line really is. Was the tighter box the WD-40-only reader used; this is the whole line, which
# the reference crops below are cut from.
OBJECTIVE_FRACTIONS = (0.2875, 0.5343, 0.7120, 0.1167)

# The craftable items the daily can offer, display name -> reference folder under
# interact/reference_images/sudak/. Each reference is a crop of the whole objective line. That
# line shares its 'Hand over the found in raid item:' prefix with every offer, so a wrong item
# still matches up to 0.901 while the right one matches 0.990 at both 1080p and 1440p.
# SUDAK_CONFIDENCE sits in that gap. Evidence: tests/sudak/test_sudak_name_match.py (46 true
# matches >= 0.990, 1035 false <= 0.901). WD-40 (100ml) vs (400ml), the case the old tight
# '(100ml)' crop was built to tell apart, reads 0.871 here, clear of the threshold outright.
ITEMS = {
    'WD-40 (100ml)': 'wd_40_100ml',
    'Power cord': 'power_cord',
    'Fleece fabric': 'fleece_fabric',
    'Can of thermite': 'can_of_thermite',
    'Rechargeable battery': 'rechargeable_battery',
    'Water filter': 'water_filter',
    'Can of Majaica coffee beans': 'can_of_majaica_coffee_beans',
    'Ripstop fabric': 'ripstop_fabric',
    'Spark plug': 'spark_plug',
    'Printed circuit board': 'printed_circuit_board',
    'GreenBat lithium battery': 'greenbat_lithium_battery',
    '6-STEN-140-M military battery': '6sten_140m_military_battery',
    'Broken LCD': 'broken_lcd',
    'Magnet': 'magnet',
    'Cordura polyamide fabric': 'cordura_polyamide_fabric',
    'Piece of plexiglass': 'piece_of_plexiglass',
    'Electric motor': 'electric_motor',
    'Broken GPhone smartphone': 'broken_gphone_smartphone',
    'Gas mask air filter': 'gas_mask_air_filter',
    'Aramid fiber fabric': 'aramid_fiber_fabric',
    'KEKTAPE duct tape': 'kektape_duct_tape',
    'Car battery': 'car_battery',
    'Working LCD': 'working_lcd',
}
DEFAULT_ITEM = 'WD-40 (100ml)'  # what the mode hunted before it could hunt anything
SUDAK_CONFIDENCE = 0.95

SETTLE = 0.5  # after clicking the offer, before reading its objective. ponytail: a guess, worked
# After clicking REPLACE, before 'y'. The confirmation fades in with YES greyed, and a 'y' sent then
# is dropped: 2026-10-06 on the laptop, replace 50 left the dialog up, the offer click landed on it,
# and REPLACE (dimmed behind it) read as gone.
CONFIRM_SETTLE = 0.3
REPLACE_SETTLE = 1.0  # after confirming REPLACE with 'y'
RESELECT_SETTLE = 0.2  # before clicking the offer again after a replace

STAT_LABELS = (('replaced', 'Quests replaced'),)
TINT_STAT = 'replaced'


def item_name(target):
    """The display name for a reference slug, or the slug itself if it is not a known item."""
    return next((name for name, slug in ITEMS.items() if slug == target), target)


class DailyReset:
    def __init__(self, target=None, stats=None):
        self.target = target or ITEMS[DEFAULT_ITEM]  # a slug under interact/reference_images/sudak/
        self.stats = stats if stats is not None else {key: 0 for key, _ in STAT_LABELS}
        self._stop = threading.Event()

    def _pause(self, seconds=0):
        if self._stop.wait(seconds):
            raise Stopped()

    def _find_or_raise(self, name):
        point = find.find_center(name, region=screen.rect())
        if point is None:
            raise LookupError(f'{name} is not on screen')
        return point

    def objective_region(self):
        left, top, width, height = screen.rect()
        fl, ft, fw, fh = OBJECTIVE_FRACTIONS
        return (left + round(width * fl), top + round(height * ft),
                round(width * fw), round(height * fh))

    def is_target_offer(self):
        """Is the selected offer's objective line the item this run is hunting."""
        return find.find(f'sudak/{self.target}', region=self.objective_region(),
                         confidence=SUDAK_CONFIDENCE) is not None

    def click_daily_offer(self):
        pyautogui.click(*self._find_or_raise(OFFER))
        self._pause(SETTLE)

    def replace_daily_task(self):
        """Replace the task, then reopen it: the panel keeps showing the old offer until clicked."""
        pyautogui.click(*self._find_or_raise(REPLACE))
        self._pause(CONFIRM_SETTLE)
        pyautogui.press('y')
        self._pause(REPLACE_SETTLE + RESELECT_SETTLE)
        self.click_daily_offer()

    def start(self):
        """Replace until the target item is up or stop() is called. Blocks, so give it a thread."""
        name = item_name(self.target)
        log(f'Starting Daily Reset, hunting {name}')
        self._stop.clear()
        try:
            self.click_daily_offer()
            while not self.is_target_offer():
                self.replace_daily_task()
                self.stats['replaced'] += 1
                log(f'replaced ({self.stats["replaced"]})', 1)
            log(f'{name} offer up after {self.stats["replaced"]} replacements')
        except Stopped:
            log('stopped between replacements')

    def stop(self):
        log('Stopping Daily Reset')
        self._stop.set()


def build(prefs, stats):
    """A DailyReset on the GUI's chosen monitor, hunting the GUI's chosen item."""
    screen.use(prefs.get('monitor', screen.AUTO))
    target = ITEMS.get(prefs.get('sudak_item', DEFAULT_ITEM), ITEMS[DEFAULT_ITEM])
    return DailyReset(target=target, stats=stats)


if __name__ == '__main__':
    # No game: every item the dropdown offers must have a reference folder with crops in it, the
    # default must be a real item, and build() must turn a picked name into its slug (and a junk
    # pick into the default). This is what stops a renamed folder or a typo'd slug from shipping a
    # dropdown entry that can never match.
    for name, slug in ITEMS.items():
        assert find.images(f'sudak/{slug}'), f'{name} -> sudak/{slug} has no reference crops'
    assert DEFAULT_ITEM in ITEMS, 'the default is not one of the items'
    assert build({'sudak_item': 'Magnet'}, None).target == 'magnet', 'build did not map the pick'
    assert build({'sudak_item': 'not a real item'}, None).target == ITEMS[DEFAULT_ITEM], \
        'an unknown pick should fall back to the default'
    assert build({}, None).target == ITEMS[DEFAULT_ITEM], 'no pick should be the default'
    assert item_name('wd_40_100ml') == 'WD-40 (100ml)' and item_name('mystery') == 'mystery'
    print(f'ok, {len(ITEMS)} craftable items, all with reference crops; default {DEFAULT_ITEM}')
