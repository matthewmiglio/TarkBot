"""The watchlist loads and the TRADER dropdown has traders on it.

Run:  python tests/test_snipe_watchlist.py

v1.1.0 shipped snipe_targets.csv into lib/ and then could not find it: snipe_bot is a top-level
module, cx_Freeze packs those into lib/library.zip, and Path(__file__).parent pointed inside the
zip. targets() returns [] rather than crashing when the file is missing, so the only thing the
user saw was a TRADER dropdown offering 'All traders' and nothing else. That is what this checks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import snipe_bot  # noqa: E402


def check(ok, what):
    print(f'  {"ok" if ok else "FAILED"}  {what}')
    if not ok:
        sys.exit(1)


print('Snipe watchlist')
check(snipe_bot.TARGETS_PATH.is_file(), f'the csv is where snipe_bot looks: {snipe_bot.TARGETS_PATH}')

watchlist = snipe_bot.targets()
check(len(watchlist) > 0, f'{len(watchlist)} items on the watchlist')
check(all(price > 0 for _, _, price in watchlist), 'every row has a trader price')

choices = snipe_bot.trader_choices()
check(choices[0] == snipe_bot.ALL_TRADERS, "'All traders' is first")
check(len(choices) > 1, f'and named traders follow it: {", ".join(choices[1:])}')
check(snipe_bot.DEFAULT_TRADER in choices, f'the default {snipe_bot.DEFAULT_TRADER} is one of them')

only_default = snipe_bot.for_trader(watchlist, snipe_bot.DEFAULT_TRADER)
check(0 < len(only_default) <= len(watchlist), f'{len(only_default)} of them are {snipe_bot.DEFAULT_TRADER}\'s')

# The frozen branch, without freezing anything: pretend to be a build living in C:/Tarkbot and
# reload, then check the csv is looked for in lib/ beside the exe rather than inside library.zip.
import importlib  # noqa: E402

sys.frozen = True
real_exe, sys.executable = sys.executable, r'C:\Tarkbot\tarkbot.exe'
try:
    frozen_path = importlib.reload(snipe_bot).TARGETS_PATH
finally:
    del sys.frozen
    sys.executable = real_exe
    importlib.reload(snipe_bot)
check(frozen_path == Path(r'C:\Tarkbot\lib\snipe_targets.csv'),
      f'frozen, it looks in lib/ beside the exe: {frozen_path}')

print('ok')
