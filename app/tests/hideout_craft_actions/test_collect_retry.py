"""A GET ITEMS click that Tarkov never registered is clicked again, and books no profit until it lands.

App layer: craft_bot.HideoutCraft.collect_craft (GET_ITEMS_ATTEMPTS) and craft.get_items_cleared.
No game: the matcher, the mouse and the clock are stubbed, so this is about what the collect does
with the answers rather than about pixels.

What it guards is a collect watched on 2026-09-17. The bot clicked GET ITEMS on the red gunpowder
craft, the game froze for a beat and never registered the click, and the pass moved on having
booked the craft's profit for loot that was still sat on the row. Nothing downstream could catch
it: a click Tarkov ignores leaves the button exactly where it was and changes nothing else, and the
old collect_craft treated the click going out as success.

The load-bearing checks are the profit ones. A retry that still booked profit on a failed collect
would pass every click-count check here and leave the totals just as wrong as before.

The other half is get_items_cleared's row scoping. Its band is padded tall enough to frame a row in
any state, so it overlaps the next craft's row (see craft._on_row for the run that cost); without
the row check a neighbour's lit GET ITEMS reads as this one never clearing, and the collect would
re-click a button that had already gone and then refuse to book the profit it had earned.

Run:  python tests/hideout_craft_actions/test_collect_retry.py
"""
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402

Box = namedtuple('Box', 'left top width height')
Job = namedtuple('Job', 'craft max_prices sources')
Desc = namedtuple('Desc', 'name')

CRAFT_NAME = 'red_gunpowder'  # has a PROFIT_PER_CRAFT figure, so a booking is visible
PROFIT = craft_bot.PROFIT_PER_CRAFT[CRAFT_NAME]

BUTTON = Box(1000, 500, 120, 30)  # the GET ITEMS the read found, centre y 515
BAND = (0, 400, 1920, 260)

craft_bot.GET_ITEMS_SETTLE = 0  # do not really wait 5s a click
craft.find.scale = lambda: 1.0  # ROW_TOL is scaled at match time; no real screen here
craft.check_stash_full = lambda region=None: False

failures = []


def check(name, condition, detail=''):
    print(f'{"ok  " if condition else "FAIL"}  {name}{"  " + detail if detail else ""}')
    if not condition:
        failures.append(name)


class Collect:
    """A HideoutCraft with only what collect_craft touches, plus a scripted button.

    clears_on is the attempt number the button finally goes away on; a number past
    GET_ITEMS_ATTEMPTS means it never does, which is the frozen-game case.
    """

    def __init__(self, clears_on):
        self.clears_on = clears_on
        self.clicks, self.parks, self.looks = [], 0, 0
        self.bot = object.__new__(craft_bot.HideoutCraft)
        self.bot.region = None
        self.bot.stats = {f'profit:{CRAFT_NAME}': 0, 'total_profit': 0}
        self.bot._park = self._park
        craft_bot.pyautogui.click = self._click
        craft.get_items_cleared = self._cleared

    def _click(self, x=None, y=None, *_a, **_kw):
        self.clicks.append((x, y))

    def _park(self, point):
        self.parks += 1
        # The park has to happen before the look, or the hover highlight is in the pixels the look
        # reads. Recording the order is the only way to tell from here.
        self.order = getattr(self, 'order', [])
        self.order.append('park')

    def _cleared(self, _box, _band):
        self.looks += 1
        self.order = getattr(self, 'order', [])
        self.order.append('look')
        return self.looks >= self.clears_on

    def run(self):
        read = craft.CraftRead('done', None, BAND, None, BUTTON, None)
        return self.bot.collect_craft(Job(Desc(CRAFT_NAME), {}, {}), read)


# 1. The ordinary case: one click, it clears, the profit is booked once.
c = Collect(clears_on=1)
point = c.run()
check('a collect that lands clicks once', len(c.clicks) == 1, f'clicks={len(c.clicks)}')
check('and returns the point it clicked', point is not None)
check('and books the profit exactly once', c.bot.stats[f'profit:{CRAFT_NAME}'] == PROFIT,
      f'booked={c.bot.stats[f"profit:{CRAFT_NAME}"]} want={PROFIT}')
check('and the cursor is parked before the look', getattr(c, 'order', [])[:2] == ['park', 'look'],
      f'order={getattr(c, "order", [])}')

# 2. The 2026-09-17 shape: the first click is swallowed, the second lands.
c = Collect(clears_on=2)
point = c.run()
check('a swallowed click is clicked again', len(c.clicks) == 2, f'clicks={len(c.clicks)}')
check('a retried collect still books the profit once', c.bot.stats['total_profit'] == PROFIT,
      f'total={c.bot.stats["total_profit"]}')
check('the retry is re-jittered, not a repeat of the same pixel',
      len(set(c.clicks)) > 1 or c.clicks[0] != c.clicks[1], f'clicks={c.clicks}')

# 3. Clears on the last allowed attempt: still a success, still one booking.
c = Collect(clears_on=craft_bot.GET_ITEMS_ATTEMPTS)
point = c.run()
check('a collect that lands on the last attempt is a success', point is not None,
      f'clicks={len(c.clicks)}')
check('and books once, not once per click', c.bot.stats['total_profit'] == PROFIT,
      f'total={c.bot.stats["total_profit"]}')

# 4. The frozen game: it never clears. Bounded, no profit, and not a raise.
c = Collect(clears_on=99)
try:
    point = c.run()
    raised = None
except Exception as e:  # noqa: BLE001 - a raise here would end the run, which is not the answer
    point, raised = None, e
check('a button that never clears does not raise', raised is None, f'raised={raised!r}')
check('it is bounded at GET_ITEMS_ATTEMPTS clicks',
      len(c.clicks) == craft_bot.GET_ITEMS_ATTEMPTS, f'clicks={len(c.clicks)}')
check('it reports the failure by returning None', point is None, f'point={point}')
check('and books NO profit for loot that never arrived', c.bot.stats['total_profit'] == 0,
      f'total={c.bot.stats["total_profit"]}')

# 5. get_items_cleared's scoping, with the real function rather than the stub above.
#    Reload order matters: Collect replaced craft.get_items_cleared, so take it off the module
#    fresh here by re-importing the name.
from interact.craft import get_items_cleared as real_cleared  # noqa: E402

craft.get_items_highlighted = lambda box, *a, **k: True


def only(boxes):
    craft.find.find_all = lambda target, region=None: list(boxes)


only([BUTTON])
check('a lit GET ITEMS still on the row reads as not cleared', real_cleared(BUTTON, BAND) is False)

only([])
check('no lit GET ITEMS at all reads as cleared', real_cleared(BUTTON, BAND) is True)

# The neighbour's row: inside the padded band, far outside ROW_TOL of our own centre y.
only([Box(1000, 500 + 200, 120, 30)])
check('a neighbouring row\'s lit GET ITEMS does not count as ours',
      real_cleared(BUTTON, BAND) is True)

# A greyed button on our row is a row that was never started, not one still waiting to collect.
craft.get_items_highlighted = lambda box, *a, **k: False
only([BUTTON])
check('a greyed GET ITEMS on our row reads as cleared', real_cleared(BUTTON, BAND) is True)

print()
if failures:
    sys.exit(f'{len(failures)} check(s) failed: {", ".join(failures)}')
print('ok: a swallowed GET ITEMS click is retried, and profit is booked only once it lands')
