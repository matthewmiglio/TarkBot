"""An unreadable craft row stops the run instead of being read as 'producing'.

Run:  python tests/test_craft_state_unreadable.py

No game needed: output_box and the two button reads are stubbed, since what is under test is what
get_craft_state does with their answers rather than whether they match pixels.

Why this exists. get_craft_state used to answer 'producing' for an output it could not find, and
'producing' is the one state the runner responds to by doing nothing and swapping away. So a
craft that had gone blind was indistinguishable from a craft that was running, and the loop
skipped it once per pass with a single indent-1 log line and no error. The wires craft did that
on every pass of 2026-08-27 while its output was on screen the whole time, unmatched because
crafting/wires could not reach the 0.9 default. Crafts started 0, no failure anywhere in the run.

Three things have to hold, and the third is the point: the raise has to reach the top.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyscreeze  # noqa: E402

import craft_bot  # noqa: E402
from interact import craft, find  # noqa: E402

BOX = pyscreeze.Box(1000, 600, 60, 60)
failures = []


def check(label, condition):
    print(f'{"ok  " if condition else "FAIL"} {label}')
    if not condition:
        failures.append(label)


# 1. No output on screen is a raise, not a state. It became craft.Blind on 2026-08-31, when
# every "a thing that is drawn did not match" failure was given one class of its own. The
# stricter half is that Blind is NOT a LookupError, so step()'s catch (which swaps crafts for a
# right-click menu that would not open) cannot swallow it back into another lap.
craft.output_box = lambda c, region=None: None
try:
    craft.get_craft_state(craft.WIRES)
    check('an output that is not on screen raises', False)
except craft.Blind as e:
    check(f'an output that is not on screen raises: {e}', True)
check('and Blind is not a LookupError, so the swap catch cannot eat it',
      not issubclass(craft.Blind, LookupError))

# 2. With an output there, the reader still returns the states it always did.
craft.output_box = lambda c, region=None: BOX
find.scale = lambda: 1.0  # ROW_TOL is a 1080p number and there is no screen to measure
READY_ROW = {craft.START_TARGET, *(i.target for i in craft.WIRES.ingredients)}
find.find_all = lambda name, region=None, confidence=None, haystack=None: (
    [BOX] if name in READY_ROW else [])
check("a row with START on it still reads 'ready'",
      craft.get_craft_state(craft.WIRES) == 'ready')

find.find_all = lambda name, region=None, confidence=None, haystack=None: []
check("a row with neither button still reads 'producing'",
      craft.get_craft_state(craft.WIRES) == 'producing')

# 3. The raise ends the run. start() catches Stopped and nothing else, so a Blind from the
# state read has to travel out through step() to the caller (gui/app.py's _run, which reddens the
# lamp and files the crash) rather than being swallowed into another lap of the loop.
runner = craft_bot.HideoutCraft.__new__(craft_bot.HideoutCraft)  # no game, no window, no monitor
runner.region = None
runner.index = 0
runner.jobs = [craft_bot.CraftJob(craft.WIRES, {}, {})]
runner.stats = {key: 0 for key, _ in craft_bot.STAT_LABELS}
runner._stop = threading.Event()
runner._ensure_on = lambda job: None  # navigation is not what this is about
craft.output_box = lambda c, region=None: None

laps = []
original_step = craft_bot.HideoutCraft.step


def counting_step(self):
    laps.append(1)
    return original_step(self)


craft_bot.HideoutCraft.step = counting_step
try:
    runner.start()
    check('the Blind escapes start() rather than being swallowed', False)
except craft.Blind:
    check('the Blind escapes start() rather than being swallowed', True)
finally:
    craft_bot.HideoutCraft.step = original_step
check(f'the loop stopped on the first bad read (took {len(laps)} lap(s))', len(laps) == 1)

print(f'\n{len(failures)} failure(s)')
for line in failures:
    print(f'  {line}')
sys.exit(1 if failures else 0)
