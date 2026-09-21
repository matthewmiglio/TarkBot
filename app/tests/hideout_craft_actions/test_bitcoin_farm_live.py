"""The bitcoin farm end to end against the live game: get to the hideout, get to the farm, click
GET ITEMS if it is lit.

Run:  python tests/hideout_craft_actions/test_bitcoin_farm_live.py
      python tests/hideout_craft_actions/test_bitcoin_farm_live.py --dry   navigate, click nothing

App layer: craft.get_to_station over the bitcoin farm's two new reference crops, then
craft_bot.HideoutCraft._collect_if_lit. LIVE GAME: this really swipes the carousel and really
clicks GET ITEMS, so Tarkov has to be up and on any main-menu screen.

It reports the three steps separately and exits non-zero on the first that fails, because they
fail for different reasons and a single pass/fail would not say which crop to go and look at:

  0  menu             escaped back to the main menu, where the hideout tab lives at all. The game
                      was found on the inventory screen the first time this ran, which has no tab
                      to click, and that read as the farm's crops failing.
  1  hideout          the hideout tab lit. A failure here is nothing to do with the farm.
  2  bitcoin farm     the carousel swept to it and its panel drew. A failure here is
                      hideout_tabs/bitcoin_farm (the carousel label, never matched) or
                      hideout_station_titles/bitcoin_farm (the panel header, so the click landed
                      and we cannot tell).
  3  GET ITEMS        a lit button clicked, or no collectable button correctly left alone. All
                      three outcomes pass, because the farm has nothing ready for most of its
                      life and demanding a collect would make the result depend on when it was
                      run. The line says which happened.

Step 3 is the only one that can pass without proving much, so it says which of the three it saw.
An absent button is the farm's resting state rather than a failure, which is measured and not
assumed: collecting removes the button rather than greying it, and the row goes back to a timer.

--dry does steps 1 and 2 for real (there is no way to read the panel without opening it) and
stops before the click, reporting what step 3 would have done.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402
import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing

import craft_bot  # noqa: E402
import window  # noqa: E402
from interact import craft, find  # noqa: E402

# Escape presses spent getting back to the main menu before step 1. The hideout tab only exists
# on the menu's own nav bar, so a game sitting on the inventory, the tasks list or the flea has no
# tab to click and the test fails saying so, which blames the farm's crops for the screen it was
# left on. Three is enough for every menu screen (the deepest is one window over one tab), and
# Escape on the bare menu opens the settings dialog, which the next press closes again: harmless,
# and cheaper than a crop of every screen it might be on.
MENU_ESCAPES = 3
MENU_ESCAPE_SETTLE = 1.0  # seconds per press for the screen it closed to actually go


def bot_on(region):
    """A HideoutCraft wired for the farm and nothing else.

    object.__new__ rather than the real __init__, which wants a monitor and a set of prefs,
    neither of which is what this turns on. _swap is stubbed away because there is no cycle
    to swap into, and _pause because there is no Stop event to wait on.
    """
    bot = object.__new__(craft_bot.HideoutCraft)
    bot.jobs = [craft_bot.CraftJob(craft.BITCOIN, {}, {})]
    bot.index = 0
    bot.region = region
    bot.stats = dict.fromkeys([key for key, _ in craft_bot.STAT_LABELS], 0)
    bot._swap = lambda: None
    bot._pause = lambda seconds=0: None
    return bot


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry', action='store_true', help='navigate for real, but never click GET ITEMS')
    args = ap.parse_args()

    find.VERBOSE = True  # the point of this test is which crop matched; craft mode runs like this
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    print(f'tarkov window {region}, screen scale {find.scale():.3f}')

    # 0. Back out to the main menu, where the hideout tab lives. Stops as soon as the tab is on
    # screen, so a game already on the menu is pressed at once and then left alone.
    for press in range(MENU_ESCAPES + 1):
        if craft.is_hideout_tab_active(region) or find.find(craft.HIDEOUT_TAB_TARGET, region):
            break
        if press == MENU_ESCAPES:
            print(f'0  menu: FAILED, no hideout tab after {MENU_ESCAPES} escapes. Either the game '
                  'is not on the main menu (in a raid?) or hideout/hideout_tab stopped matching')
            raise SystemExit(1)
        print(f'0  menu: no hideout tab yet, pressing escape ({press + 1}/{MENU_ESCAPES})')
        pyautogui.press('escape')
        time.sleep(MENU_ESCAPE_SETTLE)

    # 1. the hideout tab. Checked on its own first so a menu that never got there is not reported
    # as the farm's crops failing to match. get_to_station clicks it too, which is harmless: it
    # skips straight to the module search when the tab already reads active.
    if not craft.is_hideout_tab_active(region):
        print('1  hideout: not there yet, get_to_station will click the tab')
    else:
        print('1  hideout: already on the hideout tab')

    # 2. the farm. get_to_station raises LookupError on every dead end rather than clicking blind,
    # so there is nothing to check afterwards beyond it having returned.
    try:
        craft.get_to_station(craft.BITCOIN, region)
    except Exception as exc:
        print(f'2  bitcoin farm: FAILED {type(exc).__name__}: {exc}')
        raise SystemExit(1)
    if not craft.is_hideout_tab_active(region):
        print('1  hideout: FAILED, the hideout tab never lit')
        raise SystemExit(1)
    print('1  hideout: OK')
    print('2  bitcoin farm: OK, its panel is open')

    # 3. GET ITEMS. Read the button before acting so the line can say lit or greyed either way;
    # _collect_if_lit reads it again itself, which costs one match and keeps the shipping code
    # the thing under test rather than a copy of it.
    box = find.find(craft.GET_ITEMS_TARGET, region)
    if box is None:
        # The farm's resting state, measured: collecting removes the button rather than greying
        # it, and the row goes back to a timer. Seen on the laptop on 2026-09-21, where the run
        # before this one collected a bitcoin and the panel then read
        # 'Farming (42:15:07)...' with 0/3 bitcoins and no button anywhere on it.
        print('3  GET ITEMS: OK, no button on the panel, so nothing is ready to collect')
        print('OK')
        return
    lit = craft.get_items_highlighted(box)
    state = 'lit' if lit else 'greyed'
    print(f'3  GET ITEMS: found at {tuple(box)}, reads {state} '
          f'(threshold {craft.GET_ITEMS_HIGHLIGHT_BRIGHTNESS})')
    if args.dry:
        print(f'3  GET ITEMS: --dry, would {"click it" if lit else "leave it alone"}')
        print('OK (dry)')
        return

    bot = bot_on(region)
    collected = bot._collect_if_lit(bot.jobs[0])
    if collected != lit:
        print(f'3  GET ITEMS: FAILED, button read {state} but collect returned {collected}')
        raise SystemExit(1)
    if collected:
        print(f'3  GET ITEMS: OK, clicked and booked {bot.stats["profit:bitcoin"]} roubles')
    else:
        print('3  GET ITEMS: OK, greyed so nothing was clicked and nothing was booked')
    print('OK')


if __name__ == '__main__':
    main()
