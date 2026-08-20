"""Start unwinds a stack of leftover windows, one layer per round.

Run:  python tests/test_recover_loop.py

No game needed, nothing is clicked. FleaSeller._recover is driven against a fake screen: a list of
windows with the newest on top, where escape closes the top one and the flea tab is only visible
once the list is empty. That is the shape of the real thing, and it is the shape that broke it.

A single escape was not enough. A scav case run interrupted mid pass leaves the case window with
an offer creation window over it, so one pass closed the top one, found no flea tab underneath,
and handed a still-covered screen to pass 1, which raised 'could not open the flea market'.

The three cases that matter are a clean screen doing nothing, a stack unwinding to the bottom,
and something unrecognised not turning into an infinite loop.
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import sell_bot  # noqa: E402
from interact import find, sell  # noqa: E402

# What each window answers to, top of the stack last. Every one of them is its own title bar,
# which is the point: a control inside a window is only there when the window was opened over
# the right thing, and the title bar is there regardless.
WINDOWS = {'scav': (sell.SCAV_WINDOW_TARGET,),
           'offer': (sell.OFFER_TARGET,),
           'filters': (sell.FILTERS_WINDOW_TARGET,)}
CENTRE = (10, 20)  # what every faked window reports as its title bar, so the log is all stubs


def recover_with(stack, stuck=(), stop_after=None, real_sleep=False):
    """_recover against a screen showing `stack`, newest last. Returns (what is left, rounds).

    `stuck` is anything that escape cannot close, which is how an unrecognised window is
    modelled. `stop_after` presses Stop once that many escapes have gone.

    Returns (what is left, rounds, escapes, naps), where naps is every duration passed to
    time.sleep. Nothing actually sleeps, so the whole thing runs in a millisecond, which is
    exactly why the durations have to be asserted rather than eyeballed in the log timestamps.
    """
    on_screen, rounds, escapes, naps = list(stack), [0], [0], []
    bot = object.__new__(sell_bot.FleaSeller)
    bot._stop = threading.Event()
    bot.region = None
    # Rounds are counted by sweeps, one per time round the loop. Not by sleeps: sell_bot.time,
    # sell.time and this module's time are all the same module object, so faking one fakes them
    # all and a sleep counter picks up every wait inside close_leftover_windows too.
    sweep = sell.close_leftover_windows
    originals = (find.find_center, sell.close_leftover_windows, sell.open_flea, pyautogui.press,
                 pyautogui.click, time.sleep)

    def fake_find_center(name, region=None, **kw):
        visible = {t for w in on_screen + list(stuck) for t in WINDOWS.get(w, ())}
        return CENTRE if name in visible else None

    def fake_press(key, **kw):
        assert key == 'esc', f'recovery pressed {key!r}, which is not its job'
        escapes[0] += 1
        if on_screen:  # the top window goes, anything in `stuck` never does
            on_screen.pop()
        if stop_after is not None and escapes[0] >= stop_after:
            bot._stop.set()

    def counted_sweep(region=None, **kw):
        rounds[0] += 1
        return sweep(region)  # real delay, so its waits show up in naps alongside the loop's

    find.find_center = fake_find_center
    # The flea tab is what the loop watches for, and it is covered until the stack is empty.
    sell.find_flea_icon = lambda region=None: None if (on_screen or stuck) else 'a box'
    sell.close_leftover_windows = counted_sweep
    sell.open_flea = lambda region=None: not on_screen and not stuck
    pyautogui.press = fake_press
    pyautogui.click = lambda x, y=None, **kw: None  # the title bar click that focuses a window
    if real_sleep:  # actually wait, so the wall clock can be read as evidence
        real = originals[-1]

        def slow(seconds):
            naps.append(seconds)
            real(seconds)

        time.sleep = slow
    else:
        time.sleep = naps.append  # records instead of waiting, so the run is instant
    try:
        bot._recover()
        return on_screen, rounds[0], escapes[0], naps
    finally:
        del sell.find_flea_icon  # a module attribute the test added over the real function
        (find.find_center, sell.close_leftover_windows, sell.open_flea, pyautogui.press,
         pyautogui.click, time.sleep) = originals


if __name__ == '__main__':
    # Said up front because the narration below is the real thing's, and reads as if a screen
    # were being worked on. It is not. Every coordinate logged is CENTRE, the same stub point
    # for every window, and every wait returns instantly, so the whole run lands inside one
    # millisecond and the timestamps look like a loop spinning flat out. Neither is evidence
    # about the bot. For clicks at real coordinates and waits you can time on a clock, run
    # tests/test_recover_targets.py --run against the live game.
    print(f'SIMULATED: find is faked and every window reports {CENTRE}, so the coordinates and\n'
          f'           timestamps below are stubs. Waits are asserted rather than served, which\n'
          f'           is why this returns at once. The last check but one is the exception: it\n'
          f'           runs unfaked and prints what a stopwatch actually read.\n')

    left, rounds, escapes, naps = recover_with([])
    assert left == [] and escapes == 0, f'escaped {escapes} times on an already clear screen'
    assert rounds == 1, f'{rounds} rounds to notice a screen that was already clear'
    assert naps == [], f'waited {naps} on a screen that needed nothing doing'
    print(f'  ok  clear screen        {escapes} escapes, out after {rounds} round, no waiting')

    # The run that produced the bug report: a scav case with an offer window sat on top of it.
    left, rounds, escapes, naps = recover_with(['scav', 'offer'])
    assert left == [], f'gave up with {left} still on screen, pass 1 would raise on the flea'
    assert escapes == 2, f'{escapes} escapes for a stack of 2'
    print(f'  ok  scav under offer    {escapes} escapes over {rounds} rounds, screen clear')

    left, rounds, escapes, naps = recover_with(['scav', 'offer', 'filters'])
    assert left == [] and escapes == 3, f'{escapes} escapes, {left} left of a stack of 3'
    print(f'  ok  all three stacked   {escapes} escapes over {rounds} rounds, screen clear')

    # Something recovery has no reference images for. It must run out of rounds, not spin.
    left, rounds, escapes, naps = recover_with([], stuck=('mystery',))
    assert rounds == sell_bot.RECOVER_ROUNDS, (f'ran {rounds} rounds, wanted exactly '
                                               f'{sell_bot.RECOVER_ROUNDS}; a screen it cannot '
                                               f'clear must still end')
    print(f'  ok  unrecognised window gave up after {rounds} rounds instead of spinning')

    # It rests between rounds. Nothing above would notice if it did not, because the fake sleep
    # returns instantly and the log timestamps all land in the same millisecond, which reads as
    # a loop spinning flat out whether it is or not. So the durations are checked, not the clock.
    # This is the case with nothing to escape, so every wait is the between-rounds one.
    assert len(naps) == sell_bot.RECOVER_ROUNDS, (f'{len(naps)} waits across {rounds} rounds; '
                                                  f'it is not resting between every one')
    assert set(naps) == {sell.RECOVER_DELAY}, f'rested for {sorted(set(naps))}'
    print(f'  ok  rests every round   {len(naps)} waits of {sell.RECOVER_DELAY}s, '
          f'{sum(naps):.2f}s on a real screen')

    # Every input is followed by a wait, the click as well as the escape. Escaping in the same
    # breath as the click races the focus change the click was sent to cause, and the whole
    # point of the click is that the escape lands on the window that was just brought forward.
    left, rounds, escapes, naps = recover_with(['scav'])
    assert len(naps) == escapes * 2, (f'{escapes} escape(s) but {len(naps)} waits; wanted two '
                                      f'each, one after the click and one after the escape')
    assert set(naps) == {sell.RECOVER_DELAY}, f'not every wait was {sell.RECOVER_DELAY}s: {naps}'
    print(f'  ok  waits after each     click then {sell.RECOVER_DELAY}s, esc then '
          f'{sell.RECOVER_DELAY}s, {sum(naps):.2f}s for one window')

    # The number the whole thing adds up to, which is what a stopwatch would show.
    left, rounds, escapes, naps = recover_with(['scav', 'offer', 'filters'])
    assert sum(naps) >= rounds * sell.RECOVER_DELAY, (f'{sum(naps):.2f}s over {rounds} rounds is '
                                                      f'under the {rounds} x '
                                                      f'{sell.RECOVER_DELAY}s floor')
    print(f'  ok  adds up             {escapes} escapes over {rounds} rounds = '
          f'{sum(naps):.2f}s of real waiting')

    # And once with the real time.sleep, timed. Everything above asserts durations against a
    # fake clock, which is airtight and still looks like nothing happened, because the whole
    # file returns in a millisecond. This one actually waits, so the elapsed seconds printed
    # here are a stopwatch reading and not a claim. One window only: enough to prove the waits
    # are served rather than merely passed to something, without pausing the suite for 3s.
    started = time.monotonic()
    left, rounds, escapes, naps = recover_with(['scav'], real_sleep=True)
    elapsed = time.monotonic() - started
    assert elapsed >= sum(naps) * 0.9, (f'asked for {sum(naps):.2f}s of waiting but the whole '
                                        f'thing took {elapsed:.2f}s; the sleeps are not landing')
    print(f'  ok  REALLY waits        {elapsed:.2f}s actually elapsed for {escapes} window '
          f'({len(naps)} x {sell.RECOVER_DELAY}s, unfaked)')

    # Stop pressed while it is still unwinding. It must come straight back, not finish the ten.
    # Stop lands between rounds, not inside one: close_leftover_windows is a single sweep of up
    # to three escapes and is not interruptible half way, so the round already in flight finishes
    # and the next one does not start. That leaves the bottom window up, which is correct. The
    # user asked for it to stop, not for it to tidy up first.
    left, rounds, escapes, naps = recover_with(['scav', 'offer', 'filters'], stop_after=1)
    assert rounds == 1, f'ran {rounds} rounds after Stop, wanted the one already in flight'
    assert left == ['scav'], f'{left} left; it kept clearing after Stop instead of returning'
    print(f'  ok  stop mid recovery   out after 1 round, {escapes} escapes, {left} left up')

    print('ok, recovery unwinds a stack, gives up on the unknown and honours Stop')
