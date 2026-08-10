"""A dropdown missing its option fails at once, and never presses escape.

Run:  python tests/test_dropdown_no_retry.py

No game needed, nothing is clicked. find and pyautogui are faked, so this is only about which
branch _set_dropdown takes and how many times it clicks.

The branch matters because escape does not do what the old code thought. It shuts the whole
FILTERS window rather than the open list, so attempts 2 and 3 clicked at coordinates on a window
that had gone, into the live flea board behind it. Blind clicks on a real market.

The retry itself is still wanted for the other failure, a click that landed while the list was
unrolling, so both are checked here: the option being absent must not retry, and the pick not
taking must.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

from interact import find, sell  # noqa: E402

ANY, OPTION, SETTLED = 'currency_any', 'currency_rubles_option', 'currency_rub'
BOX = (100, 200, 60, 20)  # whatever the 'any' field matched as, centre (130, 210)


def run(reads, option_point):
    """_set_dropdown with the screen faked.

    `reads` is one (settled, any) pair per time round the loop, each a bool for whether that
    target is on screen. `option_point` is what looking for the option in the open list finds.

    Returns (what it returned, clicks, escapes).
    """
    clicks, keys, seen = [], [], iter(reads)
    state = {'settled': False, 'any': True}
    originals = (find.find, find.find_center, pyautogui.click, pyautogui.press, sell.time.sleep)

    def fake_find(name, region=None):
        if name == SETTLED:
            state.update(zip(('settled', 'any'), next(seen)))  # one read pair per attempt
            return BOX if state['settled'] else None
        return BOX if state['any'] else None

    find.find = fake_find
    find.find_center = lambda name, region=None: option_point
    pyautogui.click = lambda x, y=None, **kw: clicks.append((x, y))
    pyautogui.press = lambda key, **kw: keys.append(key)
    sell.time.sleep = lambda *a: None
    try:
        return sell._set_dropdown(ANY, OPTION, SETTLED), clicks, keys
    finally:
        (find.find, find.find_center, pyautogui.click, pyautogui.press,
         sell.time.sleep) = originals


if __name__ == '__main__':
    # The option's crops do not match the open list. One attempt, then out.
    ok, clicks, keys = run([(False, True)] * sell.DROPDOWN_ATTEMPTS, None)
    assert ok is False, 'a dropdown missing its option reported success'
    assert keys == [], f'pressed {keys}, and escape shuts the whole filter window'
    assert clicks == [(130, 210)], (f'clicked {clicks}; anything past the first opens a window '
                                    f'that escape already closed, onto the live flea board')
    print(f'  ok  option not in the list   1 click, 0 escapes, gave up on attempt 1 of '
          f'{sell.DROPDOWN_ATTEMPTS}')

    # The pick did not take the first time. That is the retry's actual job, so it must survive.
    ok, clicks, keys = run([(False, True), (True, False)], (300, 400))
    assert ok is True, 'a dropdown that settled on the second attempt reported failure'
    assert keys == [], f'pressed {keys}, nothing on this path should touch the keyboard'
    assert clicks == [(130, 210), (300, 400)], f'clicked {clicks}, wanted open then pick'
    print('  ok  pick did not take        opened and picked, settled on attempt 2')

    print('ok, a missing option is fatal at once and a missed click still retries')
