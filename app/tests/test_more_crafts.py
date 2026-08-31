"""The booze generator (moonshine), the lavatory's cordura craft, the workbench's red gunpowder
craft and the water collector are wired end to end: defined in interact.craft, defaulted in
craft_bot and settings, and their GUI icons on disk. Plus the one piece of real logic the water
collector added, the branch in HideoutCraft.step that sends it down its own pass instead of the
ready/producing state machine. Pure data and one stubbed call, no game and no tk, so this runs
anywhere. Run: python tests/test_more_crafts.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import craft_bot
from gui import settings
from interact import craft

# Every craft is present and the cycle order is stable.
assert list(craft.CRAFTS) == ['slickers', 'fleece', 'wires', 'ai2', 'moonshine', 'cordura',
                              'red_gunpowder', 'water_collector'], list(craft.CRAFTS)

moonshine = craft.CRAFTS['moonshine']
assert [i.name for i in moonshine.ingredients] == ['purified_water', 'sugar'], moonshine.ingredients
assert moonshine.station == 'booze generator'
assert moonshine.output_target == 'crafting/moonshine'
assert moonshine.module_target == 'hideout/hideout_tabs/booze_generator'

cordura = craft.CRAFTS['cordura']
assert [i.name for i in cordura.ingredients] == ['sewing_kit', 'sling_bag'], cordura.ingredients
assert cordura.station == 'lavatory' and cordura.output_target == 'crafting/cordura'
# The sewing kit is the fleece craft's input under the same name, which is what makes the two
# crafts share one ceiling and one source. If this ever splits, they stop sharing silently.
assert cordura.ingredients[0] == craft.CRAFTS['fleece'].ingredients[0]

red = craft.CRAFTS['red_gunpowder']
assert [i.name for i in red.ingredients] == ['green_gunpowder', 'matches'], red.ingredients
assert red.station == 'workbench' and red.output_target == 'crafting/red_gunpowder'

water = craft.CRAFTS['water_collector']
assert [i.name for i in water.ingredients] == ['water_filter'], water.ingredients
assert water.station == 'water collector'
assert water.module_target == 'hideout/hideout_tabs/water_collector'
assert craft.WATER_COLLECTOR_NAME == 'water_collector'

# The user's ceilings and sources reach the runner's defaults. The sling bag is the only one of
# these bought from traders.
for name, ceiling in (('purified_water', 140000), ('sugar', 48900), ('sling_bag', 11000),
                      ('green_gunpowder', 50000), ('matches', 20000), ('water_filter', 70000)):
    assert craft_bot.DEFAULT_MAX[name] == ceiling, name
assert craft_bot.DEFAULT_SOURCE_BY.get('sling_bag') == 'traders'
for name in ('purified_water', 'sugar', 'green_gunpowder', 'matches', 'water_filter'):
    assert craft_bot.DEFAULT_SOURCE_BY.get(name, 'players') == 'players', name

for name, profit in (('moonshine', 32111), ('cordura', 27984), ('red_gunpowder', 40250)):
    assert craft_bot.PROFIT_PER_CRAFT[name] == profit, name
# Deliberately absent: no profit figure was measured for the water collector, so collecting it
# books nothing rather than a guess. See the note above PROFIT_PER_CRAFT.
assert 'water_collector' not in craft_bot.PROFIT_PER_CRAFT

# The GUI's saved-settings shape has every key the crafts tab reads for the four new crafts.
for stem in ('purified_water', 'sugar', 'sling_bag', 'green_gunpowder', 'matches', 'water_filter'):
    assert f'{stem}_max' in settings.DEFAULTS, stem
    assert f'{stem}_source' in settings.DEFAULTS, stem
for name in ('moonshine', 'cordura', 'red_gunpowder', 'water_collector'):
    assert f'{name}_enabled' in settings.DEFAULTS, name

# Eight rows have to clear the stat rows beneath them, or the list draws over its own numbers.
from gui import app as gui_app  # noqa: E402  (after the sys.path insert above)
last_row = gui_app.CRAFT_LIST_TOP + (len(gui_app.CRAFTS) - 1) * gui_app.CRAFT_LIST_STEP
assert last_row < gui_app.CRAFTS_ROW_TOP, (last_row, gui_app.CRAFTS_ROW_TOP)
assert [name for name, *_ in gui_app.CRAFTS] == list(craft.CRAFTS), 'GUI list must match the cycle'

icons = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'gui',
                     'craft_icons')
for png in ('sling_bag.png', 'green_gunpowder.png', 'matches.png', 'red_gunpowder.png',
            'cordura.png', 'water_filter.png', 'purified_water.png', 'sugar.png',
            'moonshine.png'):
    assert os.path.isfile(os.path.join(icons, png)), png


# The water collector's branch in step(). Stubbed rather than run against a screen: the point is
# that a water collector job never reaches get_craft_state, which would raise on a station that
# has no craft row to read. Any other craft must still fall through to the state machine.
class _Stub:
    def __init__(self, job):
        self.jobs, self.index, self.calls = [job], 0, []

    def _ensure_on(self, job):
        self.calls.append('ensure')

    def tend_water_collector(self, job):
        self.calls.append('tend')


stub = _Stub(craft_bot.CraftJob(water, {'water_filter': 70000}, {'water_filter': 'players'}))
craft_bot.HideoutCraft.step(stub)
assert stub.calls == ['ensure', 'tend'], stub.calls

# A normal craft goes the other way: it gets as far as reading the state, which with no game on
# screen raises rather than quietly tending the water collector.
other = _Stub(craft_bot.CraftJob(cordura, {}, {}))
try:
    craft_bot.HideoutCraft.step(other)
except Exception:  # get_craft_state with no screen; reaching it at all is the assertion
    pass
assert other.calls == ['ensure'], other.calls

print('ok, booze/cordura/red gunpowder/water collector wired: defs, defaults, settings keys, '
      'icons, GUI layout and the water collector branch')
