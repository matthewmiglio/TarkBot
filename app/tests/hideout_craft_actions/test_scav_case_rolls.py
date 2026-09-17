"""Both scav case rolls get started, and every finished roll gets collected, whatever the scroll.

App layer: craft.scav_case_scroll_positions, craft.find_scav_case_row, craft.lit_get_items and
craft_bot.HideoutCraft.tend_scav_case. No game: the matcher, the mouse, the clock and the screen
rect are all stubbed, so this is about which looks, scrolls and clicks happen in what order rather
than about pixels.

Two failures are behind it, both 2026-09-17, and they are opposite halves of the same panel.

  Starting. tend_scav_case assumed the moonshine roll was the visible one at the top of the list
  and only ever scrolled for the 95k roll below it. The panel actually opened on the 95k roll with
  the moonshine row below the fold, so the moonshine read found nothing and raised Blind, which is
  in craft_bot's restart tuple, and the 95k roll sequenced behind it was never reached. Neither
  roll was tended once, all night, and the station kept restarting the game. Checks 5 and 6.

  Collecting. A scav case row is named only by its input icon, because every reward variant outputs
  the same '?' box, and that icon stops being drawn once the roll is running. So a finished roll's
  lit GET ITEMS belonged to no row the anchored read could find, and its loot was never collected:
  the screenshot from that day shows a lit GET ITEMS on a row with no input icon on it at all.
  Collecting is now roll-agnostic, and check 8 is the one that fails against the anchored version.

The load-bearing cases are 5 (the panel opens on the 95k roll) and 8 (the finished roll is below
the fold and unnamed). Revert either half and the matching check goes red.

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
GET_ITEMS = craft.GET_ITEMS_TARGET

ROW_PITCH = 100  # px between row tops in the fake list, so row i sits at y = 100i


class FakeList:
    """A production list taller than the panel: VISIBLE rows drawn, the rest above or below it.

    `rows` maps an input-icon target to its row index; a target is findable only while
    offset <= index < offset + VISIBLE. That is the whole of the behaviour the real panel has that
    the old code did not model.

    `lit` and `greyed` are row indices carrying a GET ITEMS button, and they are deliberately
    separate from `rows`: a row can have a button and no input icon, which is exactly the state
    that hid finished rolls from the anchored read. Clicking a lit one collects it, so the button
    goes away the way the real row flips back once the loot is received.
    """
    VISIBLE = 2

    def __init__(self, rows, offset=0, length=4, lit=(), greyed=()):
        self.rows, self.offset, self.length = rows, offset, length
        self.lit, self.greyed = set(lit), set(greyed)
        self.scrolls, self.clicks, self.looks = 0, 0, []
        self.collected = []

    def _box(self, i):
        return Box(0, ROW_PITCH * i, 40, 20)

    def _drawn(self, i):
        return self.offset <= i < self.offset + self.VISIBLE

    def is_lit(self, box):
        return round(box.top / ROW_PITCH) in self.lit

    def find(self, target, region=None):
        self.looks.append(target)
        i = self.rows.get(target)
        if i is None or not self._drawn(i):
            return None
        return self._box(i)

    def find_all(self, target, region=None):
        self.looks.append(target)
        if target != GET_ITEMS:
            return []  # no START anywhere, so a startable row reads 'producing'
        return [self._box(i) for i in sorted(self.lit | self.greyed) if self._drawn(i)]

    def scroll(self, notches):
        self.scrolls += 1
        step = 1 if notches < 0 else -1  # negative notches wheel down, i.e. further into the list
        self.offset = max(0, min(self.length - self.VISIBLE, self.offset + step))

    def click(self, x=None, y=None, *_args, **_kw):
        self.clicks += 1
        if y is None:
            return
        for i in sorted(self.lit):
            if abs((ROW_PITCH * i + 10) - y) <= 40:  # the jittered click landed on this row
                self.lit.discard(i)
                self.collected.append(i)
                return


def install(panel):
    """Point craft's matcher, mouse, clock and screen at this fake panel. No restore: the script
    then exits. Reopening the panel resets the list to the top, which is the behaviour
    _reopen_scav_case is built on, so the get_to_station stub models that rather than no-opping."""
    craft.find.find = panel.find
    craft.find.find_all = panel.find_all
    craft.pyautogui.scroll = panel.scroll
    craft.pyautogui.click = panel.click
    craft.SCAV_CASE_SCROLL_SETTLE = 0  # do not really sleep between steps
    craft.get_items_highlighted = lambda box, *a, **k: panel.is_lit(box)
    craft.screen.rect = lambda: (0, 0, 1920, 1080)  # so the 95k band needs no real display
    craft.check_stash_full = lambda region=None: False
    panel.reopens = 0

    def close(region=None):
        return True

    def get_to(_craft, region=None):
        panel.reopens += 1
        panel.offset = 0  # a reopened panel draws its list from the top
        return True

    craft.close_open_station_panel = close
    craft.get_to_station = get_to
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
    b.stats = {'started:scav_case': 0, 'total_started': 0, 'profit:scav_case': 0,
               'total_profit': 0}
    b._pause = lambda *a, **k: None
    b._park = lambda *a, **k: None
    b._confirm_receive = lambda *a, **k: None
    # The collect's proof that its GET ITEMS click landed is the loot reveal appearing, so a fake
    # panel has to answer that too or the real poll would go to the matcher. A point means 'the
    # reveal is up', i.e. the click registered first time. test_collect_retry.py is where a click
    # that does not register is covered.
    b._receive_point = lambda *a, **k: (0, 0)
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

# 5. The starts regression: the panel opens on the 95k roll, moonshine below the fold.
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
check('the panel is reopened once, between the two phases', panel.reopens == 1,
      f'reopens={panel.reopens}')
check('nothing is collected when no GET ITEMS is lit', panel.collected == [],
      f'collected={panel.collected}')

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

# 8. The collect regression, and the reason this file was rewritten. Row 4 has a lit GET ITEMS and
#    NO input icon, which is what a running-or-finished scav case row actually looks like, and it
#    sits below the fold. The anchored read could not name that row, so its loot was never taken.
panel = install(FakeList({K95: 0, MOON: 1}, offset=0, length=5, lit={4}))
bot = bot_for(panel)
try:
    bot.tend_scav_case(job)
    raised = None
except Exception as e:  # noqa: BLE001
    raised = e
check('an unnamed finished roll below the fold does not raise', raised is None, f'raised={raised!r}')
check('and it is collected anyway', panel.collected == [4], f'collected={panel.collected}')
check('the collect goes through _book_profit and books 0', bot.stats['profit:scav_case'] == 0,
      f'stats={bot.stats}')  # 0 on purpose: PROFIT_PER_CRAFT lists no scav_case figure yet, and a
# guess would inflate the GUI's Est. profit. This is here so that adding one starts counting with
# no other change, and so a non-zero value cannot appear without somebody measuring it first.
check('and a collect is not counted as a start', bot.stats['total_started'] == 0,
      f'stats={bot.stats}')

# 9. A greyed GET ITEMS is a roll that was never started, not a finished one. Left alone.
panel = install(FakeList({K95: 0, MOON: 1}, offset=0, length=5, greyed={4}))
bot = bot_for(panel)
bot.tend_scav_case(job)
check('a greyed GET ITEMS is not collected', panel.collected == [],
      f'collected={panel.collected}')

print()
if failures:
    sys.exit(f'{len(failures)} check(s) failed: {", ".join(failures)}')
print('ok: both rolls are started and every finished roll is collected, whatever the scroll')
