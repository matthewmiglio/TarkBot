"""Does SCAV CASES ONLY refuse the stash when there is no case to open. No game needed.

Run:  python tests/test_scav_only_fallback.py

The bug this pins: with no scav case on screen, every mode used to fall through to
select_item_from_inventory, so "SCAV CASES ONLY" listed whatever the stash held. Scav only
must come back with an empty Selection instead, which sell_one escapes out of and retries.

FleaSeller is built without __init__ on purpose: the real one looks for a Tarkov window and
a monitor, and none of that is what the decision below depends on.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sell_bot  # noqa: E402
from sell_bot import MODES, FleaSeller  # noqa: E402

failures = []


class FakeSell:
    """Just the four calls select_item makes, plus what the real module's constants are."""

    def __init__(self, case_opens):
        self.case_opens = case_opens
        self.stash_touched = False

    def open_scav_case(self, region=None):
        return (100, 100) if self.case_opens else None

    def select_item_from_random_scav_case(self, region=None, stop=None):
        return (200, 200)

    def select_item_from_inventory(self, region=None, stop=None):
        self.stash_touched = True
        return (300, 300)


def pick(mode, case_opens):
    """Run select_item for a GUI mode against a screen with or without a case on it."""
    _, scav, chance = MODES[mode]
    bot = object.__new__(FleaSeller)
    bot.target_scav_cases, bot.scav_chance = scav, chance
    bot.region, bot._stop = None, threading.Event()
    fake = FakeSell(case_opens)
    real, sell_bot.sell = sell_bot.sell, fake
    try:
        return bot.select_item(), fake
    finally:
        sell_bot.sell = real


def check(mode, case_opens, want_point, want_stash, why):
    selection, fake = pick(mode, case_opens)
    got = (selection.point is not None, fake.stash_touched)
    ok = got == (want_point, want_stash)
    print(f'{"ok  " if ok else "FAIL"} {why}: picked={got[0]} stash={got[1]}')
    if not ok:
        failures.append(f'{why}: wanted {(want_point, want_stash)}, got {got}')


# The one the user reported: scav only, no case on screen, must not touch the stash.
check('scav', False, want_point=False, want_stash=False, why='scav only, no case')
check('scav', True, want_point=True, want_stash=False, why='scav only, case there')
# Every other mode keeps the fallback it always had.
check('both', False, want_point=True, want_stash=True, why='inventory+scav, no case')
check('inventory', False, want_point=True, want_stash=True, why='inventory only')

print(f'\n{len(failures)} failure(s)')
for line in failures:
    print(f'  {line}')
sys.exit(1 if failures else 0)
