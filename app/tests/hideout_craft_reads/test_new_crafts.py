"""The workbench (power cord -> wires) and medstation (pile of meds -> AI-2) crafts are wired end
to end.

App layer under test: interact/craft.py's multi-craft descriptor set, craft.CRAFTS, plus the
defaults that hang off each descriptor in craft_bot (DEFAULT_MAX, DEFAULT_SOURCE_BY,
PROFIT_PER_CRAFT) and gui/settings (DEFAULTS keys) and the GUI craft icons on disk. This is the
data that every craft READ and action is parameterised by; it does not itself read the screen.

What it verifies: the two new crafts lead the cycle in order, are single-input at the right
station producing the right output_target/module_target, their ceilings and default source reach
the runner, their settings keys exist, and their four GUI icon pngs are on disk.

No game and no tk: pure data checks, so this runs anywhere.

Run: python tests/hideout_craft_reads/test_new_crafts.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import craft_bot
from gui import settings
from interact import craft

# These two crafts are present and lead the cycle. The crafts added after them are
# tests/test_more_crafts.py's, which owns the full order.
assert list(craft.CRAFTS)[:4] == ['slickers', 'fleece', 'wires', 'ai2'], list(craft.CRAFTS)

# The two new ones are single-input, at the right station, producing the right item.
wires = craft.CRAFTS['wires']
assert [i.name for i in wires.ingredients] == ['power_cord'], wires.ingredients
assert wires.station == 'workbench' and wires.output_target == 'crafting/wires'
assert wires.module_target == 'hideout/hideout_tabs/workbench'

ai2 = craft.CRAFTS['ai2']
assert [i.name for i in ai2.ingredients] == ['pile_of_meds'], ai2.ingredients
assert ai2.station == 'medstation' and ai2.output_target == 'crafting/ai2'
assert ai2.module_target == 'hideout/hideout_tabs/medstation'

# The user's ceilings and default source (players) reach the runner's defaults.
assert craft_bot.DEFAULT_MAX['power_cord'] == 62000
assert craft_bot.DEFAULT_MAX['pile_of_meds'] == 16600
assert craft_bot.DEFAULT_SOURCE_BY.get('power_cord', 'players') == 'players'
assert craft_bot.DEFAULT_SOURCE_BY.get('pile_of_meds', 'players') == 'players'
assert 'wires' in craft_bot.PROFIT_PER_CRAFT and 'ai2' in craft_bot.PROFIT_PER_CRAFT

# The GUI's saved-settings shape has every key the crafts tab reads for the two new crafts.
for key in ('power_cord_max', 'power_cord_source', 'pile_of_meds_max', 'pile_of_meds_source',
            'wires_enabled', 'ai2_enabled'):
    assert key in settings.DEFAULTS, key

# The icons the redesigned tab draws exist on disk.
icons = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'gui', 'craft_icons')
for png in ('power_cord.png', 'wires.png', 'pile_of_meds.png', 'ai2.png'):
    assert os.path.isfile(os.path.join(icons, png)), png

print('ok, workbench + medstation crafts wired: defs, defaults, settings keys, icons all present')
