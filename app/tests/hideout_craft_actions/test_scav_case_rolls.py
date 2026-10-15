"""The scav case pass: one scroll, then read both rolls and act until both are running, then leave.

App layer: craft_bot.HideoutCraft.tend_scav_case and _tend_scav_case_roll, over
craft.scroll_scav_case_list and craft.read_craft. No game: the scroll, the reads, START, the
collect and the buy are all stubbed onto a fake panel of two rolls, so this is about which actions
happen in what order and when the loop stops, not about pixels.

The shape it pins (from 2026-10-13, replacing a per-roll look-scroll-look hunt and a second
collect-only sweep behind a panel reopen):

  1. entering the station is the caller's business, not this pass's
  2. wheel the list once, and again only after a buy (the flea trip resets it to the top)
  3. read both rows and do the one thing each needs: collect a finished roll, START a ready one,
     buy the input of one whose START did nothing (once per roll per visit), then START it again
  4. repeat 3 until both are producing, or have nothing more this visit can do, then leave

Every case also checks the pass scrolled once plus once per buy, and never reopened the panel.
The fake panel hides every row until a scroll and again after each buy, so a pass that forgets
the post-buy wheel fails the missing-bottle case (the roll goes "not on screen" and never starts).

Run:  python tests/hideout_craft_actions/test_scav_case_rolls.py
"""
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402

Box = namedtuple('Box', 'left top width height')
MOON, INTEL = craft.SCAV_CASE, craft.SCAV_CASE_INTEL


class FakePanel:
    """Two scav case rows. Each roll has a state, whether its input is in the stash, and whether
    START works at all (`stuck` models a START the game ignores whatever the stash holds)."""

    def __init__(self, **rolls):
        # rolls: name -> dict(state=..., stash=bool, stuck=bool, absent=bool, unbuyable=bool)
        self.rolls = {n: dict(dict(stash=False, stuck=False, absent=False, unbuyable=False), **r)
                      for n, r in rolls.items()}
        self.scrolls = self.reopens = self.buys = self.collects = self.start_clicks = 0
        # Rows are only on screen once the list is wheeled down, and a flea trip resets it to
        # the top, as the live list does (2026-10-15).
        self.scrolled = False

    def row(self, craft_):
        return self.rolls[craft_.ingredients[0].name]

    def find(self, target, region=None):
        if not self.scrolled:
            return None
        for c in (MOON, INTEL):
            r = self.rolls.get(c.ingredients[0].name)
            if c.output_target == target and r and not r['absent']:
                return Box(1200, 400, 60, 50)
        return None

    def read(self, craft_, region=None):
        r = self.row(craft_)
        button = Box(1500, 420, 60, 20)
        return craft.CraftRead(r['state'], None, None,
                               button if r['state'] == 'ready' else None,
                               button if r['state'] in ('done', 'not started') else None,
                               [(craft_.ingredients[0].name, r['stash'], (1230, 425))]
                               if r['state'] == 'ready' else None)

    def start(self, name):
        self.start_clicks += 1
        r = self.rolls[name]
        if r['stash'] and not r['stuck']:
            r['state'], r['stash'] = 'producing', False

    def collect(self, name):
        self.collects += 1
        self.rolls[name]['state'] = 'ready'


def run(panel, jobs=(MOON, INTEL)):
    """One tend_scav_case visit over this panel. Returns the bot, for its stats and swaps."""
    craft.find.find = panel.find
    craft.read_craft = panel.read
    craft.check_stash_full = lambda region=None: False

    def scroll(region=None):
        panel.scrolls += 1
        panel.scrolled = True
    craft.scroll_scav_case_list = scroll

    def reopen(*a, **k):
        panel.reopens += 1
    craft.get_to_station = craft.close_open_station_panel = reopen

    def buy(location, ceiling, region=None, craft=None, **k):  # noqa: A002 - mirrors the real kwarg
        panel.buys += 1
        panel.scrolled = False  # back from the flea with the list at the top
        r = panel.row(craft)
        if r['unbuyable']:
            raise craft_module.Unbuyable('over the ceiling')
        r['stash'] = True
        return True
    craft.buy_craft_input_item = buy

    b = object.__new__(craft_bot.HideoutCraft)
    b.region = None
    b.jobs = [craft_bot.CraftJob(c, {c.ingredients[0].name: 100000}, {}) for c in jobs]
    b.index = 0
    b.stats = {key: 0 for key, _ in craft_bot.STAT_LABELS}
    b._pause = lambda *a, **k: None
    b._confirm_receive = lambda *a, **k: None
    b._click_scav_start = lambda name, read: panel.start(name)
    b.collect_ok = True

    def click_until_taken(what, box, landed, settle=None):
        if not b.collect_ok:
            return None
        name = 'moonshine' if 'moonshine' in what else 'intelligence'
        panel.collect(name)
        return (0, 0)
    b._click_until_taken = click_until_taken
    b.swaps = 0

    def swap():
        b.swaps += 1
    b._swap = swap
    return b


craft_module = craft
failures = []


def check(name, condition, detail=''):
    print(f'{"ok  " if condition else "FAIL"}  {name}{"  " + detail if detail else ""}')
    if not condition:
        failures.append(name)


def common(label, panel, bot):
    check(f'{label}: scrolled once, plus once after each buy', panel.scrolls == 1 + panel.buys,
          f'scrolls={panel.scrolls} buys={panel.buys}')
    check(f'{label}: never reopened the panel', panel.reopens == 0, f'reopens={panel.reopens}')
    check(f'{label}: left the station once', bot.swaps == 1, f'swaps={bot.swaps}')


# 1. Both finished, both inputs in the stash: collect both, start both, in the one visit.
panel = FakePanel(moonshine=dict(state='done', stash=True), intelligence=dict(state='done', stash=True))
bot = run(panel)
bot.tend_scav_case(bot.jobs[0])
common('both done', panel, bot)
check('both done: both collected', panel.collects == 2, f'collects={panel.collects}')
check('both done: both started and counted', bot.stats['total_started'] == 2
      and bot.stats['started:scav_case'] == 1 and bot.stats['started:scav_case_intel'] == 1,
      f'stats started={bot.stats["total_started"]}')
check('both done: nothing bought', panel.buys == 0, f'buys={panel.buys}')

# 2. Moonshine ready with no bottle, intelligence already running: START does nothing, buy one,
#    START again. The running roll is left alone.
panel = FakePanel(moonshine=dict(state='ready'), intelligence=dict(state='producing'))
bot = run(panel)
bot.tend_scav_case(bot.jobs[0])
common('missing bottle', panel, bot)
check('missing bottle: one buy', panel.buys == 1, f'buys={panel.buys}')
check('missing bottle: START, then START again after the buy', panel.start_clicks == 2,
      f'start clicks={panel.start_clicks}')
check('missing bottle: moonshine counted once, intelligence not at all',
      bot.stats['started:scav_case'] == 1 and bot.stats['started:scav_case_intel'] == 0)

# 3. Both already running: read once, touch nothing, leave.
panel = FakePanel(moonshine=dict(state='producing'), intelligence=dict(state='producing'))
bot = run(panel)
bot.tend_scav_case(bot.jobs[0])
common('both running', panel, bot)
check('both running: no clicks of any kind', panel.start_clicks == panel.collects == panel.buys == 0)

# 4. A folder over the ceiling: the roll is given up for this visit, the other still started.
panel = FakePanel(moonshine=dict(state='ready', stash=True),
                  intelligence=dict(state='ready', unbuyable=True))
bot = run(panel)
bot.tend_scav_case(bot.jobs[0])
common('unbuyable', panel, bot)
check('unbuyable: one buy tried, no retry', panel.buys == 1, f'buys={panel.buys}')
check('unbuyable: moonshine still started', bot.stats['started:scav_case'] == 1)
check('unbuyable: intelligence not counted', bot.stats['started:scav_case_intel'] == 0)

# 5. A START the game ignores even with the input bought: one buy, two STARTs, then give up.
#    The load-bearing one for money: it must not buy a second folder.
panel = FakePanel(intelligence=dict(state='ready', stuck=True))
bot = run(panel, jobs=(INTEL,))
bot.tend_scav_case(bot.jobs[0])
common('stuck START', panel, bot)
check('stuck START: exactly one buy', panel.buys == 1, f'buys={panel.buys}')
check('stuck START: two START clicks, not more', panel.start_clicks == 2,
      f'start clicks={panel.start_clicks}')

# 6. A roll not on screen is skipped, not a raise into the restart path.
panel = FakePanel(moonshine=dict(state='producing'), intelligence=dict(state='ready', absent=True))
bot = run(panel)
try:
    bot.tend_scav_case(bot.jobs[0])
    raised = None
except Exception as e:  # noqa: BLE001 - any raise at all is the failure being guarded
    raised = e
check('absent roll: no raise', raised is None, f'raised={raised!r}')
common('absent roll', panel, bot)

# 7. A GET ITEMS whose loot reveal never opens: given up, not clicked forever.
panel = FakePanel(moonshine=dict(state='done', stash=True), intelligence=dict(state='producing'))
bot = run(panel)
bot.collect_ok = False
bot.tend_scav_case(bot.jobs[0])
common('stuck collect', panel, bot)
check('stuck collect: no START on a roll that never emptied', panel.start_clicks == 0)

# 8. Profit is booked per roll on a collect (0 today: no scav case figure in PROFIT_PER_CRAFT).
panel = FakePanel(moonshine=dict(state='done', stash=True))
bot = run(panel, jobs=(MOON,))
bot.tend_scav_case(bot.jobs[0])
check('profit: a collect books 0 and is not a start on its own',
      bot.stats['profit:scav_case'] == 0 and bot.stats['total_started'] == 1,
      f'profit={bot.stats["profit:scav_case"]} started={bot.stats["total_started"]}')

print()
if failures:
    sys.exit(f'{len(failures)} check(s) failed: {", ".join(failures)}')
print('ok: one scroll (plus one per buy), both rolls read and acted on until both run, then the pass leaves')
