"""A menu with no 'filter by item' in it ends the pass, and presses nothing on the way out.

App layer under test: interact/sell.py's pick loops (select_item_from_inventory,
select_item_from_random_scav_case) and sell_bot.FleaSeller.sell_one's reset around them, the
'filter by item' right-click backout. Grouped with the flea BUYER's filter-clearing tests
since it turns on the same filter-by-item menu entry, though the code here is the flea SELLER's.

Run:  python tests/flea_snipe/test_filter_by_item_backout.py

No game needed. The screen is stubbed down to the four answers the pick loop reads, so this is
about what the loop does with them rather than about matching pixels.

What this pins. The pick loop used to press escape here and try again. The intent was to reset
to the top of the pass, and one blind press cannot do that: escape closes the biggest window on
screen, which is the offer creation window and never the little right click menu, so the menu
stayed open and the window went away. Every button infer_inventory_region measures from lives on
that window, so the next attempt lost all three at once and the run ended. Seven crash reports
on one machine on 2026-08-24, every screenshot showing the same thing: no offer window, menu
still up.

The reset belongs to sell_bot, which already knows the count this screen needs, and already
backs out that many times and raises Retry when the pick comes back None. So the loop's whole
job here is to stop and return None. The counts are checked too, since they are the half that
makes it a reset rather than a shrug: one escape for a bare stash, two with a case window over
it.
"""
import sys
import threading
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import sell_bot  # noqa: E402
from interact import find, sell  # noqa: E402


def pick_with(menu_has_filter, pick):
    """Run `pick` against a screen whose right-click menu may or may not hold the entry.

    Returns (result, calls). Everything the loop touches is stubbed: an item is always found and
    always selects, so the only thing left to decide the outcome is the menu.
    """
    calls = {'attempts': 0, 'press': 0, 'click': 0, 'rightClick': 0}
    saved = {name: getattr(sell, name, None)
             for name in ('find_sell_pixels', 'is_item_selected', 'dismiss_error_popup',
                          '_sleep', 'infer_scav_case_region', 'scav_case_pixels')}
    saved_find, saved_gui = find.find, sell.pyautogui

    def fake_pixels(region=None, **kw):
        calls['attempts'] += 1
        return [(100, 100)]

    sell.find_sell_pixels = fake_pixels
    sell.scav_case_pixels = fake_pixels
    sell.infer_scav_case_region = lambda region=None, **kw: (0, 0, 500, 500)
    sell.is_item_selected = lambda region=None, **kw: True
    sell.dismiss_error_popup = lambda region=None, **kw: False  # never a dialog in these cases
    sell._sleep = lambda seconds, stop=None: False
    find.find = lambda target, region=None, **kw: ('a box' if menu_has_filter else None)
    sell.pyautogui = types.SimpleNamespace(
        press=lambda *a, **k: calls.__setitem__('press', calls['press'] + 1),
        click=lambda *a, **k: calls.__setitem__('click', calls['click'] + 1),
        rightClick=lambda *a, **k: calls.__setitem__('rightClick', calls['rightClick'] + 1),
        center=lambda box: (10, 10))
    try:
        return pick(), calls
    finally:
        for name, value in saved.items():
            if value is not None:
                setattr(sell, name, value)
        find.find, sell.pyautogui = saved_find, saved_gui


print('the stash: no filter by item in the menu')
result, calls = pick_with(False, lambda: sell.select_item_from_inventory(None))
assert result is None, f'the pick has to hand the pass back, got {result!r}'
assert calls['attempts'] == 1, f'it should stop on the first miss, not retry: {calls}'
assert calls['press'] == 0, f'nothing may be pressed here, that is sell_bot\'s job: {calls}'
print(f'  ok  returned None after one attempt, pressed nothing  {calls}')

print('the scav case: same miss, same answer')
result, calls = pick_with(False, lambda: sell.select_item_from_random_scav_case(None))
assert result is None, f'the pick has to hand the pass back, got {result!r}'
assert calls['press'] == 0, f'nothing may be pressed here either: {calls}'
print(f'  ok  returned None, pressed nothing  {calls}')


def pass_with(scav):
    """A whole sell_one whose pick finds no menu entry. Returns (keys pressed, what was raised).

    The presses are counted where they actually happen, at sell_bot's own pyautogui, rather than
    by stubbing _escape. Counting the constant would only prove the constant; what is worth
    proving is that a pass ending this way really does press escape that many times and then
    start again.
    """
    keys = []
    bot = object.__new__(sell_bot.FleaSeller)
    bot.region, bot.stats = None, {key: 0 for key, _ in sell_bot.STAT_LABELS}
    bot._stop = threading.Event()
    bot.target_scav_cases, bot.scav_chance = scav, (1.0 if scav else 0.0)
    bot._pause = lambda *a: None
    bot.open_offer_creation = lambda: None

    saved = (sell_bot.pyautogui, sell_bot.time, sell.open_scav_case,
             sell.select_item_from_random_scav_case, sell.select_item_from_inventory)
    sell_bot.pyautogui = types.SimpleNamespace(press=lambda key: keys.append(key))
    sell_bot.time = types.SimpleNamespace(sleep=lambda s: None, monotonic=lambda: 0.0)
    sell.open_scav_case = lambda region=None, **kw: True
    # Stubbed at the seam the cases above already cover: both real pick loops return None on a
    # menu with no entry in it, which is what those two assertions prove.
    sell.select_item_from_random_scav_case = lambda region=None, **kw: None
    sell.select_item_from_inventory = lambda region=None, **kw: None
    try:
        raised = None
        try:
            bot.sell_one()
        except sell_bot.Retry as e:
            raised = e
        return keys, raised
    finally:
        (sell_bot.pyautogui, sell_bot.time, sell.open_scav_case,
         sell.select_item_from_random_scav_case, sell.select_item_from_inventory) = saved


print('the whole pass, stash: one escape, then a fresh pass')
keys, raised = pass_with(scav=False)
assert keys == ['esc'], f'the stash needs exactly one escape, got {keys}'
assert isinstance(raised, sell_bot.Retry), f'the pass has to end in a Retry, got {raised!r}'
print(f'  ok  pressed {keys}, raised Retry({raised})')

print('the whole pass, scav case: two escapes, then a fresh pass')
keys, raised = pass_with(scav=True)
assert keys == ['esc', 'esc'], f'a case window over the offer window needs two, got {keys}'
assert isinstance(raised, sell_bot.Retry), f'the pass has to end in a Retry, got {raised!r}'
print(f'  ok  pressed {keys}, raised Retry({raised})')

print('ok, a missing menu entry costs the pass and nothing else')
