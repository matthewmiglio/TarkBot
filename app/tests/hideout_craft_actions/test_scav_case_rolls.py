"""Both scav case rolls get tended whatever the panel's list is scrolled to.

App layer: craft.find_scav_case_row and craft_bot.HideoutCraft.tend_scav_case. No game: the
matcher, the mouse and the clock are stubbed, so this is about which looks and scrolls happen in
what order rather than about pixels.

What it guards is the run of 2026-09-17. tend_scav_case assumed the moonshine roll was the visible
one at the top of the list and only ever scrolled for the 95k roll below it. The panel actually
opened on the 95k roll with the moonshine row below the fold, so the moonshine read found nothing
and raised Blind, which is in craft_bot's restart tuple, and the 95k roll sequenced behind it was
never reached. Neither roll was tended once, all night, and the station kept restarting the game.

The load-bearing case is the last one: the panel opened on the 95k roll. Revert the scroll in
_tend_scav_case_moonshine and it raises Blind exactly the way the real run did.

Run:  python tests/hideout_craft_actions/test_scav_case_rolls.py
"""
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402

Box = namedtuple('Box', 'left top width height')

MOON = craft.MOONSHINE_TARGET
K95 = craft.NINETY_FIVE_K_TARGET


class FakeList:
    """A production list taller than the panel: VISIBLE rows drawn, the rest above or below it.

    rows maps a target to its index in the list; offset is the index of the topmost drawn row, so
    a target is findable only while offset <= index < offset + VISIBLE. That is the whole of the
    behaviour the real panel has that the old code did not model.
    """
    VISIBLE = 2

    def __init__(self, rows, offset=0, length=4):
        self.rows, self.offset, self.length = rows, offset, length
        self.scrolls, self.clicks, self.looks = 0, 0, []

    def find(self, target, region=None):
        self.looks.append(target)
        i = self.rows.get(target)
        if i is None or not (self.offset <= i < self.offset + self.VISIBLE):
            return None
        return Box(0, 100 * i, 40, 20)

    def scroll(self, notches):
        self.scrolls += 1
        step = 1 if notches < 0 else -1  # negative notches wheel down, i.e. further into the list
        self.offset = max(0, min(self.length - self.VISIBLE, self.offset + step))

    def click(self, *_args, **_kw):
        self.clicks += 1


def install(panel):
    """Point craft's matcher and mouse at this fake panel. No restore: the script then exits."""
    craft.find.find = panel.find
    craft.find.find_all = lambda *a, **k: []  # no START / GET ITEMS anywhere, so a row reads 'producing'
    craft.pyautogui.scroll = panel.scroll
    craft.pyautogui.click = panel.click
    craft.SCAV_CASE_SCROLL_SETTLE = 0  # do not really sleep between steps
    return panel


failures = []


def check(name, condition, detail=''):
    print(f'{"ok  " if condition else "FAIL"}  {name}{"  " + detail if detail else ""}')
    if not condition:
        failures.append(name)


# 1. Already drawn: one look, no wheel touched at all, and no dead-space click either.
panel = install(FakeList({MOON: 0, K95: 1}, offset=0))
box = craft.find_scav_case_row(MOON)
check('a visible roll is found without scrolling', box is not None and panel.scrolls == 0,
      f'scrolls={panel.scrolls}')
check('a visible roll does not click the panel', panel.clicks == 0, f'clicks={panel.clicks}')

# 2. Below the fold: the 2026-09-17 shape. Wheels down and finds it.
panel = install(FakeList({K95: 0, MOON: 3}, offset=0))
box = craft.find_scav_case_row(MOON)
check('a roll below the fold is scrolled down to', box is not None, f'scrolls={panel.scrolls}')
check('scrolling takes the wheel focus first', panel.clicks == 1, f'clicks={panel.clicks}')

# 3. Above the current position: the down sweep cannot reach it, the sweep back up must.
panel = install(FakeList({MOON: 0, K95: 3}, offset=2))
box = craft.find_scav_case_row(MOON)
check('a roll above the fold is found on the sweep back up', box is not None,
      f'scrolls={panel.scrolls}')
check('it really needed the up sweep', panel.scrolls > craft.SCAV_CASE_SCROLL_STEPS,
      f'scrolls={panel.scrolls} > steps={craft.SCAV_CASE_SCROLL_STEPS}')

# 4. Not on the panel at all: None rather than a raise, and bounded rather than spinning.
panel = install(FakeList({K95: 0}, offset=0))
box = craft.find_scav_case_row(MOON)
check('a roll that is never there comes back None', box is None)
check('and the hunt is bounded', panel.scrolls == craft.SCAV_CASE_SCROLL_STEPS * 3,
      f'scrolls={panel.scrolls}')


def bot_for(panel):
    """A HideoutCraft with just the attributes tend_scav_case touches. __init__ wants a Tarkov
    window and a monitor, and neither is what any of this turns on."""
    b = object.__new__(craft_bot.HideoutCraft)
    b.region = None
    b.stats = {'started:scav_case': 0, 'total_started': 0}
    b._pause = lambda *a, **k: None
    b.swaps = 0

    def swap():
        b.swaps += 1
    b._swap = swap
    return b


def read_craft_stub(_craft, region=None):
    """Stand-in for the real read, which searches the whole region for the moonshine bottle and
    raises Blind when it is not drawn. Raising here is the point: it is what the shipping code
    does, and it is what the missing scroll used to walk straight into."""
    if panel.find(MOON) is None:
        raise craft.Blind('moonshine output not on screen, cannot read the craft row')
    return craft.CraftRead('producing', None, None, None, None, None)


craft.read_craft = read_craft_stub
Job = namedtuple('Job', 'craft max_prices sources')
job = Job(craft.SCAV_CASE, {'moonshine': 230000}, {})

# 5. The regression itself: the panel opens on the 95k roll, moonshine below the fold.
panel = install(FakeList({K95: 0, MOON: 3}, offset=0))
bot = bot_for(panel)
try:
    bot.tend_scav_case(job)
    raised = None
except Exception as e:  # noqa: BLE001 - any raise at all is the failure being guarded
    raised = e
check('a panel opened on the 95k roll does not raise', raised is None, f'raised={raised!r}')
check('both rolls were looked for', MOON in panel.looks and K95 in panel.looks)
check('the station is left exactly once', bot.swaps == 1, f'swaps={bot.swaps}')

# 6. The mirror of it, which is what the old code assumed was the only case.
panel = install(FakeList({MOON: 0, K95: 3}, offset=0))
bot = bot_for(panel)
try:
    bot.tend_scav_case(job)
    raised = None
except Exception as e:  # noqa: BLE001
    raised = e
check('a panel opened on the moonshine roll does not raise either', raised is None,
      f'raised={raised!r}')
check('both rolls were looked for there too', MOON in panel.looks and K95 in panel.looks)

# 7. A roll genuinely absent is skipped, not fatal: the other roll and the swap still happen.
panel = install(FakeList({K95: 0}, offset=0, length=2))
bot = bot_for(panel)
try:
    bot.tend_scav_case(job)
    raised = None
except Exception as e:  # noqa: BLE001
    raised = e
check('a missing moonshine roll is skipped rather than fatal', raised is None, f'raised={raised!r}')
check('and the pass still leaves the station', bot.swaps == 1, f'swaps={bot.swaps}')

print()
if failures:
    sys.exit(f'{len(failures)} check(s) failed: {", ".join(failures)}')
print('ok: both scav case rolls are tended whatever the list is scrolled to')
