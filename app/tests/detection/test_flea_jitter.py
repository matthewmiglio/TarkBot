"""_human_jitter pads the sell code's own waits and clicks, leaves pyautogui's exact, and puts
everything back on the way out.

App layer: interact/sell.py's human-timing wait padding, reached here as sell_bot._human_jitter
(the same context manager), which lengthens time.sleep calls made from the sell code while
leaving pyautogui's own pauses and tweened drags untouched.

Run:  python tests/detection/test_flea_jitter.py

NO GAME needed: time.sleep is stubbed to a recorder, the clicks to no-ops, and random.uniform is
pinned, so nothing sleeps or moves the mouse. The load-bearing branch is the caller gate: a
time.sleep from the sell code is padded, the same call from inside pyautogui (its PAUSE and its
tweened drags) is not, or a 0.4s drag would balloon by up to a second per tween step. The two
exec'd stubs carry the module names the gate reads.
"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pyautogui
import sell_bot


def sleep_from(module_name, seconds):
    """Call the live time.sleep from a frame whose module reads as `module_name`."""
    g = {'__name__': module_name, 'time': time}
    exec('def call(s):\n    time.sleep(s)', g)
    g['call'](seconds)


real_sleep, real_uniform = time.sleep, random.uniform
real_clicks = {n: getattr(pyautogui, n) for n in ('click', 'rightClick', 'dragTo')}
recorded = []
try:
    for n in real_clicks:
        setattr(pyautogui, n, lambda *a, **k: None)  # no real mouse if a wrapper calls through
    time.sleep = lambda s=0.0: recorded.append(s)     # the CM captures this as its real_sleep
    random.uniform = lambda a, b: 0.5

    with sell_bot._human_jitter():
        assert pyautogui.click is not real_clicks['click'], 'click should be wrapped inside'
        sleep_from('interact.sell', 2.0)   # sell caller: padded
        sleep_from('sell_bot', 2.0)        # sell caller: padded
        sleep_from('pyautogui', 2.0)       # pyautogui caller: exact
        before = len(recorded)
        pyautogui.click(1, 2)              # a click waits first, then no-ops
        after = len(recorded)

    assert recorded[:3] == [2.5, 2.5, 2.0], f'caller gate wrong: {recorded[:3]}'
    assert after - before == 1 and recorded[before] == 0.5, 'click should wait ~0.5s first'
    assert pyautogui.click is real_clicks['click'], 'click not restored'
    assert pyautogui.rightClick is real_clicks['rightClick'], 'rightClick not restored'
    assert pyautogui.dragTo is real_clicks['dragTo'], 'dragTo not restored'
finally:
    time.sleep, random.uniform = real_sleep, real_uniform
    for n, fn in real_clicks.items():
        setattr(pyautogui, n, fn)

# time.sleep restored to the real one only after the CM exited (not to the recorder)
assert time.sleep is real_sleep, 'time.sleep not restored on exit'
print('ok, _human_jitter pads sell waits/clicks, leaves pyautogui exact, and restores everything')
