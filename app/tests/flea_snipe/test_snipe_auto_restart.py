"""A failed sweep relaunches the game and carries on sniping, but a captcha always ends the run.

App layer: snipe_bot.FleaSniper's auto-restart path, which is restart_as, the fatal handler around
sweep_once in start(), _after_restart and the GameRestarts mixin it shares with sell_bot. The
game_client half is tests/platform/test_game_client.py's job; this covers only when a restart
happens and when it must not.

Run:  python tests/flea_snipe/test_snipe_auto_restart.py

No game needed, nothing is clicked, nothing is closed: game_client.tarkov, the board opening and
the captcha look are faked, and sweep_once is a script of outcomes rather than a sweep.

The captcha rows are the point. Restarting through one would be a bot relaunching itself into the
account check over and over all night, so a captcha has to end the run whether it was named
(snipe.Captcha) or hid behind some other failure (a search box that would not match).
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import snipe_bot  # noqa: E402
from game_client import tarkov  # noqa: E402
from interact import snipe  # noqa: E402

SEASONAL = tarkov.Character.SEASONAL


class Ran(Exception):
    """Raised by the last scripted sweep, to end start()'s loop without calling stop()."""


def run(script, restart_as=None, launcher_works=True, game_open=True, captcha_showing=False):
    """start() over `script`, one entry per sweep: None for a clean sweep or an Exception to raise.

    Returns (log, error). The log records ('sweep', n), ('close',), ('start', character),
    ('measure',) and ('board',) in the order they happened.
    """
    log, sweeps = [], [0]
    bot = object.__new__(snipe_bot.FleaSniper)
    bot._stop = threading.Event()
    bot.region = None
    bot.hwnd = 1 if game_open else None
    bot.restart_as = restart_as
    bot.watchlist = [('item', 'Therapist', 1000)]
    bot.stats = {key: 0 for key, _ in snipe_bot.STAT_LABELS}

    def one_sweep():
        sweeps[0] += 1
        log.append(('sweep', sweeps[0]))
        if sweeps[0] > len(script):
            raise Ran()
        outcome = script[sweeps[0] - 1]
        if isinstance(outcome, Exception):
            raise outcome

    bot.sweep_once = one_sweep
    bot._measure_window = lambda: log.append(('measure',))

    def fake_start(character=None, **kw):
        log.append(('start', character))
        return launcher_works

    originals = (tarkov.close_game, tarkov.start_tarkov, snipe.open_clean_board, snipe.captcha_up,
                 snipe_bot.SWEEP_PAUSE)
    tarkov.close_game = lambda *a, **k: log.append(('close',)) or True
    tarkov.start_tarkov = fake_start
    snipe.open_clean_board = lambda region=None: log.append(('board',)) or True
    snipe.captcha_up = lambda region=None: captcha_showing
    snipe_bot.SWEEP_PAUSE = 0
    try:
        bot.start()
        return log, None
    except Ran:
        return log, None
    except Exception as e:  # noqa: BLE001 - the test's job is to report whatever escaped
        return log, e
    finally:
        (tarkov.close_game, tarkov.start_tarkov, snipe.open_clean_board, snipe.captcha_up,
         snipe_bot.SWEEP_PAUSE) = originals


def restarts(log):
    return [entry for entry in log if entry[0] == 'start']


if __name__ == '__main__':
    print('SIMULATED: no game is closed or launched, and every sweep is a scripted outcome.\n')
    boom = LookupError('the flea filters would not go on')

    # 1. Off is off: the fatal ends the run and the game is untouched.
    log, error = run([boom], restart_as=None)
    assert error is boom, f'auto restart off swallowed the fatal, got {error!r}'
    assert restarts(log) == [], f'auto restart off still relaunched the game: {log}'
    print('  ok  off, fatal            run ended, game untouched')

    # 2. On, the same fatal relaunches once and the next sweep runs.
    log, error = run([boom, None], restart_as=SEASONAL)
    assert error is None, f'a restart was meant to absorb the fatal, but {error!r} escaped'
    assert restarts(log) == [('start', SEASONAL)], f'wanted one seasonal relaunch, got {log}'
    assert ('sweep', 2) in log, 'the run stopped after the restart instead of carrying on'
    order = [entry[0] for entry in log]
    after = order[order.index('close'):]
    assert after.index('close') < after.index('start') < after.index('measure') < \
        after.index('board'), f'restart steps out of order: {order}'
    print('  ok  on, fatal             closed, relaunched, re-measured, back on the board, sweep 2')

    # 3. A named captcha ends the run with the setting on.
    captcha = snipe.Captcha('SECURITY CHECK')
    log, error = run([captcha, None], restart_as=SEASONAL)
    assert error is captcha, f'a captcha did not end the run, got {error!r}'
    assert restarts(log) == [], f'it restarted through a captcha: {log}'
    print('  ok  captcha               run ended, no restart')

    # 4. A captcha hiding behind another failure is still looked for, and still ends the run.
    log, error = run([LookupError('no search box'), None], restart_as=SEASONAL,
                     captcha_showing=True)
    assert isinstance(error, snipe.Captcha), f'a hidden captcha was not named, got {error!r}'
    assert restarts(log) == [], f'it restarted into a captcha on screen: {log}'
    print('  ok  hidden captcha        named as a captcha, no restart')

    # 5. Start with the game shut boots it once, then opens the board and sweeps.
    log, error = run([None, None], restart_as=SEASONAL, game_open=False)
    assert error is None, f'a cold start with auto restart on still failed: {error!r}'
    assert restarts(log) == [('start', SEASONAL)], f'wanted one launch, got {log}'
    order = [entry[0] for entry in log]
    assert 'close' not in order, f'it tried to close a game that was never running: {log}'
    assert order.index('start') < order.index('measure') < order.index('board') < \
        order.index('sweep'), f'booted in the wrong order: {order}'
    print('  ok  cold start            launched once, measured, board opened, then swept')

    # 6. A launcher that never comes back ends the run after one attempt.
    log, error = run([boom, None], restart_as=SEASONAL, launcher_works=False)
    assert isinstance(error, RuntimeError), f'a dead launcher did not end the run, got {error!r}'
    assert len(restarts(log)) == 1, f'it kept relaunching a client that will not start: {log}'
    print(f'  ok  launcher failed       run ended: {error}')

    print('\nok, off changes nothing, a fatal restarts once, and a captcha always ends the run')
