"""A failed craft step relaunches the game and carries on, but a full stash always ends the run.

App layer: craft_bot.HideoutCraft's auto-restart path, which is restart_as, the fatal handler
around step() in start(), and the GameRestarts mixin it shares with sell_bot. The game_client half
is tests/platform/test_game_client.py's job; this covers only when a restart happens and when it
must not.

Run:  python tests/hideout_craft_actions/test_craft_auto_restart.py

No game needed, nothing is clicked, nothing is closed: game_client.tarkov and the stash-full look
are faked, and step() is a script of outcomes rather than a craft.

The stash rows are the point. A full stash comes straight back after a relaunch, so restarting
through it would loop all night. It has to end the run whether it was named (craft.StashFull) or
hid behind some other failure, the way it surfaced as a Blind on 2026-09-02.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import craft_bot  # noqa: E402
from game_client import tarkov  # noqa: E402
from interact import craft  # noqa: E402

SEASONAL = tarkov.Character.SEASONAL


class Ran(Exception):
    """Raised by the last scripted step, to end start()'s loop without calling stop()."""


def run(script, restart_as=None, launcher_works=True, game_open=True, stash_full=False):
    """start() over `script`, one entry per step: None for a clean step or an Exception to raise.

    Returns (log, error). The log records ('step', n), ('close',), ('start', character),
    ('measure',) and ('dismiss',) in the order they happened.
    """
    log, steps = [], [0]
    bot = object.__new__(craft_bot.HideoutCraft)
    bot._stop = threading.Event()
    bot.region = None
    bot.hwnd = 1 if game_open else None
    bot.restart_as = restart_as
    bot.stats = {key: 0 for key, _ in craft_bot.STAT_LABELS}

    def one_step():
        steps[0] += 1
        log.append(('step', steps[0]))
        if steps[0] > len(script):
            raise Ran()
        outcome = script[steps[0] - 1]
        if isinstance(outcome, Exception):
            raise outcome

    bot.step = one_step
    bot._measure_window = lambda: log.append(('measure',))

    def fake_start(character=None, **kw):
        log.append(('start', character))
        return launcher_works

    def fake_check(region=None):
        if stash_full:
            raise craft.StashFull('the stash is full')

    originals = (tarkov.close_game, tarkov.start_tarkov, craft.check_stash_full,
                 craft.dismiss_stash_full)
    tarkov.close_game = lambda *a, **k: log.append(('close',)) or True
    tarkov.start_tarkov = fake_start
    craft.check_stash_full = fake_check
    craft.dismiss_stash_full = lambda region=None: log.append(('dismiss',)) or True
    try:
        bot.start()
        return log, None
    except Ran:
        return log, None
    except Exception as e:  # noqa: BLE001 - the test's job is to report whatever escaped
        return log, e
    finally:
        (tarkov.close_game, tarkov.start_tarkov, craft.check_stash_full,
         craft.dismiss_stash_full) = originals


def restarts(log):
    return [entry for entry in log if entry[0] == 'start']


if __name__ == '__main__':
    print('SIMULATED: no game is closed or launched, and every step is a scripted outcome.\n')
    boom = craft.Blind('no handover dialog appeared')

    # 1. Off is off: the fatal ends the run and the game is untouched.
    log, error = run([boom], restart_as=None)
    assert error is boom, f'auto restart off swallowed the fatal, got {error!r}'
    assert restarts(log) == [], f'auto restart off still relaunched the game: {log}'
    print('  ok  off, fatal            run ended, game untouched')

    # 2. On, the same fatal relaunches once and the next step runs.
    for fatal in (boom, LookupError('hideout tab button not on screen'), RuntimeError('x')):
        log, error = run([fatal, None], restart_as=SEASONAL)
        assert error is None, f'a restart was meant to absorb {fatal!r}, but {error!r} escaped'
        assert restarts(log) == [('start', SEASONAL)], f'wanted one relaunch, got {log}'
        assert ('step', 2) in log, 'the run stopped after the restart instead of carrying on'
    print('  ok  on, fatal             Blind, LookupError and RuntimeError each restart once')

    # 3. A named full stash ends the run cleanly with the setting on: dialog cleared, no restart.
    log, error = run([craft.StashFull('the stash is full'), None], restart_as=SEASONAL)
    assert error is None, f'a full stash should stop cleanly, not crash: {error!r}'
    assert restarts(log) == [], f'it restarted through a full stash: {log}'
    assert ('dismiss',) in log and ('step', 2) not in log, f'the run did not stop there: {log}'
    print('  ok  stash full            dialog cleared, run stopped, no restart')

    # 4. A full stash hiding behind another failure is still looked for, and still ends the run.
    log, error = run([boom, None], restart_as=SEASONAL, stash_full=True)
    assert error is None, f'a hidden full stash should stop cleanly: {error!r}'
    assert restarts(log) == [], f'it restarted into a full stash: {log}'
    assert ('dismiss',) in log and ('step', 2) not in log, f'the run did not stop there: {log}'
    print('  ok  hidden stash full     found before restarting, run stopped')

    # 5. Start with the game shut boots it once, then steps.
    log, error = run([None, None], restart_as=SEASONAL, game_open=False)
    assert error is None, f'a cold start with auto restart on still failed: {error!r}'
    assert restarts(log) == [('start', SEASONAL)], f'wanted one launch, got {log}'
    order = [entry[0] for entry in log]
    assert 'close' not in order, f'it tried to close a game that was never running: {log}'
    assert order.index('start') < order.index('measure') < order.index('step'), \
        f'booted in the wrong order: {order}'
    print('  ok  cold start            launched once, measured, then stepped')

    # 6. A launcher that never comes back ends the run after one attempt.
    log, error = run([boom, None], restart_as=SEASONAL, launcher_works=False)
    assert isinstance(error, RuntimeError), f'a dead launcher did not end the run, got {error!r}'
    assert len(restarts(log)) == 1, f'it kept relaunching a client that will not start: {log}'
    print(f'  ok  launcher failed       run ended: {error}')

    print('\nok, off changes nothing, a fatal restarts once, and a full stash always ends the run')
