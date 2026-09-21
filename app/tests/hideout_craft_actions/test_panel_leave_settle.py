"""Leaving a station waits before navigation starts clicking that station's close button.

App layer: craft_bot.HideoutCraft.step (the 'producing' branch, PANEL_LEAVE_SETTLE) and
craft.close_open_station_panel (PANEL_CLOSE_ATTEMPTS).
No game: the matcher, the mouse, the clock, the row read and the swap are all stubbed, so this is
about ordering and re-click counts rather than about pixels.

What it guards is the 2026-09-17 overnight soak. Navigation's first act is closing the panel of the
station being left, and step() used to go from 'this row is producing' straight into that navigation
with no gap at all: the comment there said the swap's own navigation paced the loop, which it does
not, because closing the panel is the very first thing navigation does.

The soak made the cost visible. On the workbench-to-medstation leg the panel swallowed its FIRST
close click 35 times in 57, and 9 of those ran out of re-clicks and restarted Tarkov. The other six
stations closed first time across ~400 attempts, which is what says this is a panel being slow
rather than a bad crop: the same button, found at the same (1865, 89) every time, with the find
reporting it correctly gone whenever it did go.

So two things are pinned here. That step() actually waits before swapping, and that a panel needing
a fourth click now gets one, since 26 of those 35 first-misses did clear on a later attempt.

Run:  python tests/hideout_craft_actions/test_panel_leave_settle.py
"""
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402

Box = namedtuple('Box', 'left top width height')
Desc = namedtuple('Desc', 'name station')
Job = namedtuple('Job', 'craft max_prices sources')

failures = []


def check(name, condition, detail=''):
    print(f'{"ok  " if condition else "FAIL"}  {name}{"  " + detail if detail else ""}')
    if not condition:
        failures.append(name)


# 1. step() on a producing row: it must wait, and it must wait BEFORE handing over to the swap.
class Step:
    """A HideoutCraft with only what step()'s producing branch touches."""

    def __init__(self):
        self.calls = []
        self.bot = object.__new__(craft_bot.HideoutCraft)
        self.bot.region = None
        self.bot.index = 0
        # Any craft that is not the water collector or the scav case; those two have their own
        # passes and never reach the branch under test.
        self.bot.jobs = [Job(Desc('red_gunpowder', 'workbench'), {}, {})]
        self.bot._ensure_on = lambda job: self.calls.append('ensure_on')
        self.bot._pause = lambda secs=None: self.calls.append(('pause', secs))
        self.bot._swap = lambda: self.calls.append('swap')
        craft.read_craft = lambda desc, region=None: craft.CraftRead(
            'producing', None, (0, 400, 1920, 260), None, None, None)

    def run(self):
        self.bot.step()
        return self.calls


calls = Step().run()
pauses = [c for c in calls if isinstance(c, tuple) and c[0] == 'pause']
check('a producing row still swaps away', 'swap' in calls, f'calls={calls}')
check('and it pauses before the swap, not after',
      bool(pauses) and 'swap' in calls and calls.index(pauses[0]) < calls.index('swap'),
      f'calls={calls}')
check('and the pause is the leave settle',
      bool(pauses) and pauses[0][1] == craft_bot.PANEL_LEAVE_SETTLE,
      f'paused={pauses[0][1] if pauses else None} want={craft_bot.PANEL_LEAVE_SETTLE}')
# The load-bearing one: a settle of 0 would satisfy every check above and change nothing on screen.
check('and that settle is a real wait, not zero', craft_bot.PANEL_LEAVE_SETTLE > 0,
      f'PANEL_LEAVE_SETTLE={craft_bot.PANEL_LEAVE_SETTLE}')


# 2. close_open_station_panel: how many re-clicks a stubborn panel actually gets.
class Close:
    """close_open_station_panel with the matcher, mouse, keyboard and clock stubbed.

    clears_on is the click count at which the X finally disappears; a number past
    PANEL_CLOSE_ATTEMPTS means no click ever closes it, which is the case that ended 9 laps.
    esc_clears says whether the fallback keypress closes a panel the clicks could not.
    """

    def __init__(self, clears_on, esc_clears=False):
        self.clears_on = clears_on
        self.esc_clears = esc_clears
        self.clicks = 0
        self.escs = 0
        craft.find.find = self._find
        craft.pyautogui.click = self._click
        craft.pyautogui.press = self._press
        craft.time.sleep = lambda _s: None
        craft.frames.capture = lambda *a, **k: None
        craft.sell.jitter = lambda point: point
        craft._region_from_fractions = lambda fractions, region=None: None
        craft._screen_state = lambda region=None: 'stubbed'

    def _find(self, _target, _region=None):
        if self.escs and self.esc_clears:
            return None
        return None if self.clicks >= self.clears_on else Box(1865, 89, 21, 15)

    def _click(self, _x=None, _y=None, *_a, **_kw):
        self.clicks += 1

    def _press(self, _key, *_a, **_kw):
        self.escs += 1

    def run(self):
        return craft.close_open_station_panel(None)


# The fix in one check: four clicks is past the old limit of 3, so this case used to end the run.
c = Close(clears_on=4)
closed = c.run()
check('a panel that only gives way on the 4th click now closes', closed is True,
      f'clicks={c.clicks}')
check('and it took exactly four clicks', c.clicks == 4, f'clicks={c.clicks}')

c = Close(clears_on=1)
check('a panel that closes at once still costs one click', c.run() is True, f'clicks={c.clicks}')

c = Close(clears_on=99)
try:
    c.run()
    raised = None
except LookupError as e:
    raised = e
check('a panel that never closes still raises rather than silently carrying on',
      raised is not None, f'raised={raised!r}')
check('and gives up after exactly PANEL_CLOSE_ATTEMPTS clicks',
      c.clicks == craft.PANEL_CLOSE_ATTEMPTS,
      f'clicks={c.clicks} limit={craft.PANEL_CLOSE_ATTEMPTS}')
check('and that limit is above the old 3, which the soak exhausted 9 times',
      craft.PANEL_CLOSE_ATTEMPTS > 3, f'PANEL_CLOSE_ATTEMPTS={craft.PANEL_CLOSE_ATTEMPTS}')


# 3. The esc fallback. Added 2026-09-18, after v1.25.8's settle and extra clicks were measured and
# changed nothing: the workbench leg still needed a retry on 53% of closes and still ran out on
# 13%, and going 3 -> 5 clicks had rescued exactly one sequence in 118. The point of these checks
# is that esc is a LAST resort and never a replacement for the click that works 103 times in 118.
c = Close(clears_on=99, esc_clears=True)
check('esc closes a panel no number of clicks would, instead of ending the run',
      c.run() is True, f'clicks={c.clicks} escs={c.escs}')
check('and it is pressed exactly once', c.escs == 1, f'escs={c.escs}')
check('and only after every click has been spent',
      c.clicks == craft.PANEL_CLOSE_ATTEMPTS, f'clicks={c.clicks}')

# The load-bearing one: a fallback that fires on the ordinary path is not a fallback.
c = Close(clears_on=1)
c.run()
check('a panel that closes on the first click never reaches the esc at all',
      c.escs == 0, f'escs={c.escs}')

c = Close(clears_on=99, esc_clears=False)
try:
    c.run()
    raised = None
except LookupError as e:
    raised = e
check('a panel that refuses esc too still raises', raised is not None, f'raised={raised!r}')
check('and the error says esc was tried, so a log reader knows the fallback ran',
      raised is not None and 'esc' in str(raised), f'raised={raised!r}')
check('and esc was tried once before giving up', c.escs == 1, f'escs={c.escs}')

print()
if failures:
    sys.exit(f'{len(failures)} check(s) failed: {", ".join(failures)}')
print('ok: a station panel gets a settle before navigation clicks its X, and five clicks to close')
