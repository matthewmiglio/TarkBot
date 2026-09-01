"""A dropdown missing its option fails at once and never presses escape, and a pick that did
not take still gets another go.

App layer under test: interact/sell.py, sell._pick_from_dropdown and sell.apply_flea_filters.
Verifies _pick_from_dropdown gives up on the first attempt (one click, no escape) when the
option is not in the open list, since escape would shut the whole FILTERS window and later
clicks would land on the live board behind it; and that apply_flea_filters still runs another
whole round when a click landed while the list was unrolling.

No-game stub test: find and pyautogui are faked, nothing is really clicked, so this is only
about which branch the filter pass takes and how many times it clicks. No live game.

Run:  python tests/flea_filters/test_dropdown_no_retry.py

The branch matters because escape does not do what the old code thought. It shuts the whole
FILTERS window rather than the open list, so a second attempt clicked at coordinates on a window
that had gone, into the live flea board behind it. Blind clicks on a real market.

The retry itself is still wanted for the other failure, a click that landed while the list was
unrolling, so both are checked here. The two now live at different levels: giving up on a
missing option is _pick_from_dropdown's, and going round again is apply_flea_filters', which
reads the whole window, does all the clicking, then checks all of it and repeats the round if
the check comes back short.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

from interact import find, sell  # noqa: E402

import pyscreeze  # noqa: E402

# A real Box, not a tuple: apply_flea_filters measures the filter window off its title
# bar's .left/.top, so a plain tuple gets as far as filter_window_region and dies there.
BOX = pyscreeze.Box(100, 200, 60, 20)  # whatever a field matched as, centre (130, 210)
FIELD = (130, 210)
OPTION_POINT = (300, 400)
OK_POINT = (500, 600)


def near(click, point):
    """Is this click the jittered version of `point`? sell.jitter nudges every real click by up
    to CLICK_JITTER each way, so an exact match is the wrong assertion here."""
    return max(abs(a - b) for a, b in zip(click, point)) <= sell.CLICK_JITTER


def patched(fake_find, fake_find_center):
    """Swap in the fakes and give back what to restore. One place, since both cases need it."""
    originals = (find.find, find.find_center, pyautogui.click, pyautogui.press, sell.time.sleep)
    find.find = fake_find
    find.find_center = fake_find_center
    return originals


def restore(originals):
    (find.find, find.find_center, pyautogui.click, pyautogui.press, sell.time.sleep) = originals


def run_pick(option_point):
    """_pick_from_dropdown with the screen faked. (returned, clicks, keys pressed)."""
    clicks, keys = [], []
    originals = patched(lambda name, region=None: BOX,
                        lambda name, region=None: option_point)
    pyautogui.click = lambda x, y=None, **kw: clicks.append((x, y))
    pyautogui.press = lambda key, **kw: keys.append(key)
    sell.time.sleep = lambda *a: None
    dropdown = sell.filter_dropdowns('players')[0]
    try:
        return sell._pick_from_dropdown(dropdown, FIELD), clicks, keys
    finally:
        restore(originals)


def run_pass(rounds):
    """apply_flea_filters with the screen faked. (returned, clicks, keys, rounds consumed).

    `rounds` is one bool per read of the window: True means every dropdown reads as settled,
    False means both still read 'any'. filter_plan and confirm_filters each consume one, which
    is what lets a round be scripted as "not set, then set".
    """
    clicks, keys, state = [], [], {'reads': list(rounds), 'used': 0}

    def fake_find(name, region=None):
        if name in (sell.FILTERS_WINDOW_TARGET, sell.CONDITION_LABEL_TARGET,
                    sell.EXPIRING_TEXT_TARGET, sell.FILTER_BUTTON_TARGET):
            return BOX
        settled_targets = {d.settled_target for d in sell.filter_dropdowns('players')}
        any_targets = {d.any_target for d in sell.filter_dropdowns('players')}
        if name in settled_targets:
            # A read pair is (settled, any); one entry is consumed per dropdown per look.
            state['used'] += 1
            return BOX if state['reads'][min(state['used'] - 1, len(state['reads']) - 1)] else None
        if name in any_targets:
            return None if state['reads'][min(state['used'] - 1, len(state['reads']) - 1)] else BOX
        return None

    originals = patched(fake_find, lambda name, region=None: OK_POINT)
    pyautogui.click = lambda x, y=None, **kw: clicks.append((x, y))
    pyautogui.press = lambda key, **kw: keys.append(key)
    sell.time.sleep = lambda *a: None
    sell.open_filters = lambda region=None: True
    try:
        return sell.apply_flea_filters(set_condition=False), clicks, keys, state['used']
    finally:
        restore(originals)


if __name__ == '__main__':
    real_open_filters = sell.open_filters

    # The option's crops do not match the open list. One click to open it, then out.
    ok, clicks, keys = run_pick(None)
    assert ok is False, 'a dropdown missing its option reported success'
    assert keys == [], f'pressed {keys}, and escape shuts the whole filter window'
    assert clicks == [FIELD], (f'clicked {clicks}; anything past the first opens a window that '
                               f'escape already closed, onto the live flea board')
    print('  ok  option not in the list   1 click, 0 escapes, gave up on the spot')

    # The option is there: open, then pick, and no keyboard on this path.
    ok, clicks, keys = run_pick(OPTION_POINT)
    assert ok is True, 'a dropdown whose option was found reported failure'
    assert clicks == [FIELD, OPTION_POINT], f'clicked {clicks}, wanted open then pick'
    assert keys == [], f'pressed {keys}, nothing on this path should touch the keyboard'
    print('  ok  option in the list       opened and picked')

    # Both dropdowns already read what they should: the plan is empty, so the pass reads the
    # window, clicks nothing but OK, and never opens a list.
    sell.open_filters = lambda region=None: True
    ok, clicks, keys, _ = run_pass([True])
    sell.open_filters = real_open_filters
    assert ok is True, 'an already filtered window reported failure'
    assert len(clicks) == 1, f'clicked {clicks}, wanted OK only'
    assert near(clicks[0], OK_POINT),         f'clicked {clicks[0]}, which is not the jittered OK button at {OK_POINT}'
    print('  ok  already filtered         read the window, clicked OK only')

    # A pick that did not take. The first look says unset, the act clicks, the check still says
    # unset, so the round runs again; the second check agrees and the pass OKs out. That the
    # window is read more times than there are dropdowns is the whole point: the check is a
    # phase of its own at the end of the round, not a read wedged in after each click.
    sell.open_filters = lambda region=None: True
    ok, clicks, keys, reads = run_pass([False, False, True, True, True, True, True, True])
    sell.open_filters = real_open_filters
    assert ok is True, 'a pass whose filters settled on the second round reported failure'
    assert any(near(click, OK_POINT) for click in clicks), f'clicked {clicks}, never reached OK'
    assert reads > 2, f'only {reads} window reads: the check phase never ran'
    print(f'  ok  pick did not take        went round again, {reads} reads, settled and OKd')

    print('ok, a missing option is fatal at once and a missed click still gets another round')
