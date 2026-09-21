"""Buying the scav case's moonshine bottle never opens the flea filter window.

Run:  python tests/hideout_craft_actions/test_moonshine_no_filters.py

App layer: interact/craft.py's buy_craft_input_item (the new `filters` argument) and the one
call site that passes it False, craft_bot.HideoutCraft._start_scav_case_moonshine. The mouse,
the clock, the matcher and the flea are all stubbed, so this is about which steps run and in
what order, not about pixels. No game needed.

What this pins. A moonshine bottle is always 100% condition and only ever sold by players, so
every control in the filter window would be set to what the board already shows. That window is
about fifteen seconds of clicks and it is walked into on every moonshine buy, which is the most
frequent buy in the whole craft cycle: the soak of 2026-09-18 made 53 trips to that board in
three hours.

Two halves, and the second is the load-bearing one. First, that `filters=False` really does skip
apply_flea_filters and still buys a cheap offer, since a shortcut that also skips the purchase
saves nothing. Second, that the scav case moonshine path actually passes it: a flag no call site
sets is dead code that reads like a feature, and nothing else in this repo would notice.

The default is checked too. Every other ingredient still opens the window, because for those the
condition and the source genuinely vary and an unfiltered board answers with a price about a
different market.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402

BUTTON = types.SimpleNamespace(left=1800, top=600, width=120, height=30)
MENU = types.SimpleNamespace(left=900, top=500, width=180, height=6)
CEILING = 300000


def buy_with(**kwargs):
    """Run buy_craft_input_item over a board holding one cheap offer. (result, filter_passes)."""
    passes = []
    names = ('pyautogui', 'find', 'sell', 'snipe', 'time', 'return_to_station', '_open_item_menu')
    saved = {n: getattr(craft, n) for n in names}

    def apply_flea_filters(*a, **k):
        passes.append(k)
        return True

    craft.pyautogui = types.SimpleNamespace(
        click=lambda *a: None, press=lambda key: None,
        center=lambda b: (b.left + b.width / 2, b.top + b.height / 2))
    craft.find = types.SimpleNamespace(find=lambda *a, **k: MENU, scale=lambda: 1.0)
    craft.sell = types.SimpleNamespace(jitter=lambda point, **k: point,
                                       apply_flea_filters=apply_flea_filters)
    craft.snipe = types.SimpleNamespace(purchase_buttons=lambda *a, **k: [BUTTON],
                                        read_price=lambda b: 222222, buy=lambda b, r: True)
    now = {'t': 0.0}

    def monotonic():
        now['t'] += 1.0
        return now['t']
    craft.time = types.SimpleNamespace(sleep=lambda s: None, monotonic=monotonic)
    craft.return_to_station = lambda *a, **k: True
    craft._open_item_menu = lambda *a, **k: MENU
    try:
        return craft.buy_craft_input_item((100, 200), CEILING, **kwargs), passes
    finally:
        for name, value in saved.items():
            setattr(craft, name, value)


def scav_case_moonshine_buy():
    """Drive the roll's start with the bottle missing. Returns the buy's kwargs, or None."""
    sent = {}
    read = types.SimpleNamespace(state='ready', start=BUTTON,
                                 inputs=[('moonshine', False, (400, 500))])
    names = ('find_scav_case_row', 'read_craft', 'buy_craft_input_item', 'MOONSHINE_TARGET')
    saved = {n: getattr(craft, n) for n in names}
    saved_pyautogui, saved_sell = craft_bot.pyautogui, craft_bot.sell

    def buy(*a, **k):
        sent.update(k)
        return True

    craft.find_scav_case_row = lambda *a, **k: BUTTON
    craft.read_craft = lambda *a, **k: read  # 'ready' before the click and still after it
    craft.buy_craft_input_item = buy
    craft_bot.pyautogui = types.SimpleNamespace(
        click=lambda *a: None, moveTo=lambda *a: None,
        center=lambda b: (b.left + b.width / 2, b.top + b.height / 2))
    craft_bot.sell = types.SimpleNamespace(jitter=lambda point, **k: point)

    bot = craft_bot.HideoutCraft.__new__(craft_bot.HideoutCraft)  # no window, no monitor
    bot.region = (0, 0, 1920, 1080)
    bot.stats = {}
    bot._pause = lambda seconds=0: None
    bot._park = lambda point: None
    bot._confirm_handover = lambda required=True: True
    job = craft_bot.CraftJob(craft.SCAV_CASE, {'moonshine': CEILING}, {'moonshine': 'players'})
    try:
        bot._start_scav_case_moonshine(job)
        return sent or None
    finally:
        for name, value in saved.items():
            setattr(craft, name, value)
        craft_bot.pyautogui, craft_bot.sell = saved_pyautogui, saved_sell


if __name__ == '__main__':
    failures = []

    bought, passes = buy_with(filters=False)
    print(f'filters=False: bought={bought}, filter passes={len(passes)}')
    if passes:
        failures.append(f'filters=False still opened the filter window {len(passes)} time(s)')
    if bought is not True:
        failures.append(f'filters=False did not buy the cheap offer (got {bought!r})')

    bought, passes = buy_with()
    print(f'default:       bought={bought}, filter passes={len(passes)}')
    if len(passes) != 1:
        failures.append(f'the default should filter exactly once, it filtered {len(passes)}')
    if bought is not True:
        failures.append(f'the default did not buy the cheap offer (got {bought!r})')

    sent = scav_case_moonshine_buy()
    print(f'scav case moonshine buy: {sent}')
    if sent is None:
        failures.append('the scav case moonshine path never reached the buy at all')
    elif sent.get('filters') is not False:
        failures.append(f"the scav case moonshine buy passed filters={sent.get('filters')!r}, "
                        'so the whole shortcut is dead code')

    if failures:
        for line in failures:
            print(f'FAIL: {line}')
        sys.exit(1)
    print('ok: the moonshine buy skips the filter window, every other input still opens it')
