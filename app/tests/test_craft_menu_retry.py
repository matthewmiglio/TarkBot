"""A craft input slot that does not open its menu is retried, and never ends the run.

Run:  python tests/test_craft_menu_retry.py

No game needed. The mouse calls and the matcher are stubbed, so this is about the order the
clicks go out in and what the loop does with a miss, not about matching pixels.

What this pins. On 2026-08-28 a craft run that had opened the 'filter by item' menu nine times
in a row missed on the tenth and ended on a LookupError, 58 minutes and 8 crafts in. The frames
show the cursor on the right slot with its tooltip up and no menu behind it: rightClick() puts
the cursor there and presses in the same instant, and the game can read the press before its own
hover has caught up. Hovering first fixes the common case; moving off the row and back fixes the
case where the cursor is already sitting on the slot, which is what a fresh press alone cannot
undo. And a slot that still will not open says nothing about the other three crafts, so the miss
costs a swap now instead of the session.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import craft_bot  # noqa: E402
from interact import craft  # noqa: E402

BOX = types.SimpleNamespace(left=100, top=200, width=200, height=13)


def menu_with(hits):
    """Run _open_item_menu against a screen where find() returns `hits` in turn.

    Returns (result, calls), calls being every mouse action in the order it went out.
    """
    calls = []
    saved = (craft.pyautogui, craft.find, craft.time)
    craft.pyautogui = types.SimpleNamespace(
        moveTo=lambda x, y: calls.append(('moveTo', round(x))),
        rightClick=lambda x, y: calls.append(('rightClick', round(x))))
    craft.find = types.SimpleNamespace(find=lambda *a, **k: hits.pop(0) if hits else None,
                                       scale=lambda: 1.0)
    craft.time = types.SimpleNamespace(sleep=lambda s: None)
    try:
        return craft._open_item_menu((500, 400)), calls
    finally:
        craft.pyautogui, craft.find, craft.time = saved


def step_with(buy):
    """One craft_bot step whose only missing input is bought by `buy`. Returns what it did."""
    did = []
    runner = object.__new__(craft_bot.Runner)  # ponytail: skip __init__, it wants a live window
    runner.jobs = [types.SimpleNamespace(craft=types.SimpleNamespace(name='wires'))]
    runner.index = 0
    runner.region = None
    runner._ensure_on = lambda job: None
    runner._pause = lambda *a: None
    runner._swap = lambda: did.append('swap')
    runner.start_craft = lambda job: did.append('start')
    runner.buy_input = buy
    saved = (craft.get_craft_state, craft.craft_plan, craft.validate_craftable)
    craft.get_craft_state = lambda *a, **k: 'ready'
    craft.craft_plan = lambda *a, **k: [('power_cord', False, (500, 400))]
    craft.validate_craftable = lambda *a, **k: (False, ['power_cord'])  # still short after buying
    try:
        runner.step()
        return did
    finally:
        craft.get_craft_state, craft.craft_plan, craft.validate_craftable = saved


if __name__ == '__main__':
    # The first press is preceded by a hover of the same slot, not fired the instant the cursor
    # lands. That ordering is the whole fix for the common case.
    box, calls = menu_with([BOX])
    assert box is BOX, f'the menu was up and was not read: {box}'
    assert calls == [('moveTo', 500), ('rightClick', 500)], f'pressed without hovering: {calls}'

    # A miss goes back for another try, and gets off the slot first so the second press arrives
    # as a fresh mouse-enter. Without the step away the retry is the same press that just failed.
    box, calls = menu_with([None, BOX])
    assert box is BOX, 'the retry did not read the menu it opened'
    assert [c for c in calls if c[0] == 'rightClick'] == [('rightClick', 500)] * 2, \
        f'expected two presses, got {calls}'
    assert ('moveTo', 380) in calls, f'the retry never left the slot: {calls}'

    # Two misses give up, rather than pressing at the slot forever.
    box, calls = menu_with([])
    assert box is None, 'a slot that never opens has to come back None'
    assert len([c for c in calls if c[0] == 'rightClick']) == 2, f'{calls} is not two tries'

    # And giving up costs a swap, not the run: the other crafts are still worth tending.
    def refuses(job, name, location):
        raise LookupError('no filter by item in the menu, cannot narrow the board to this item')

    assert step_with(refuses) == ['swap'], 'a slot with no menu has to swap craft, not raise'
    assert step_with(lambda job, name, location: True) == [], 'a bought input should not swap'

    print('ok: hover then press, one retry off the slot, and a miss costs a swap')
