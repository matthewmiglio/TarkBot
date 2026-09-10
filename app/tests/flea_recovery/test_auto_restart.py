"""A wedged run closes the game, brings it back, and carries on selling.

App layer: sell_bot.FleaSeller's auto-restart path, which is AUTO_RESTART / restart_as, the
_dismiss_error_popup tally, _game_looks_wedged, _restart_game, and the two hooks in start()'s
pass loop. The game_client half (what close_game and start_tarkov actually do to the client) is
tests/platform/test_game_client.py's job; this covers only when they are called and what state
is put back afterwards.

Run:  python tests/flea_recovery/test_auto_restart.py

No game needed, nothing is clicked, nothing is closed: game_client.tarkov, sell.dismiss_error_popup
and the two methods that touch the real screen are all faked, and sell_one is a script of
outcomes rather than a pass.

Why it exists. The failure this was written for is silent, which is the worst kind to leave
untested. On 2026-09-09 a run sold 46 items and then sold nothing for the last fifteen minutes:
the flea stopped returning offers, so every pass read an empty price box, gave up and started
again, and the game's Error dialog came up ten times and was clicked away ten times. Nothing
raised. The log looked busy. The counters agreed the bot was working. So the rule has to hold in
both directions or it is worse than nothing: too eager and a healthy run pays a two minute
relaunch for one harmless dialog, too shy and the night is gone again.

The cases that matter are auto-restart off changing nothing at all, a fatal becoming a restart
instead of the end of the run, one dialog being ignored, two close together restarting exactly
once, two far apart being ignored, and a client that will not come back ending the run rather
than looping on it.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import sell_bot  # noqa: E402
from game_client import tarkov  # noqa: E402
from interact import sell  # noqa: E402

SEASONAL = tarkov.Character.SEASONAL


class Ran(Exception):
    """Raised by the last scripted pass, to end start()'s loop without calling stop()."""


def run(script, restart_as=None, launcher_works=True, seed_errors=()):
    """start() over `script`, one entry per pass. Returns (log, error) with what happened.

    Each entry is what that pass does before it returns:
      None        a clean pass
      'dialog'    the pass clears one Error dialog, the way a real one does deep inside itself
      Exception   the pass raises it

    `seed_errors` pre-loads the dialog tally with ages in seconds, so "half an hour ago" can be
    tested without waiting or faking a clock. `launcher_works` False is a client that never
    comes back up.

    The log records ('pass', n), ('close',), ('start', character), ('measure',) and ('recover',)
    in the order they happened, which is the only way to tell "restarted between passes" from
    "restarted mid pass".
    """
    log, passes = [], [0]
    bot = object.__new__(sell_bot.FleaSeller)
    bot._stop = threading.Event()
    bot.region = None
    bot.restart_as = restart_as
    bot._restarts = 0
    bot.stats = {key: 0 for key, _ in sell_bot.STAT_LABELS}
    now = sell_bot.time.monotonic()
    bot._error_times = [now - age for age in seed_errors]

    def one_pass():
        passes[0] += 1
        log.append(('pass', passes[0]))
        if passes[0] > len(script):
            raise Ran()  # the script is spent; stop the loop without pretending Stop was pressed
        outcome = script[passes[0] - 1]
        if outcome == 'dialog':
            bot._dismiss_error_popup()
        elif isinstance(outcome, Exception):
            raise outcome

    bot.sell_one = one_pass
    bot._recover = lambda: log.append(('recover',))
    bot._measure_window = lambda: log.append(('measure',))

    originals = (sell.dismiss_error_popup, tarkov.close_game, tarkov.start_tarkov)
    sell.dismiss_error_popup = lambda region=None: True  # a dialog is always there when looked for
    tarkov.close_game = lambda *a, **k: log.append(('close',)) or True

    def fake_start(character=None, **kw):
        log.append(('start', character))
        return launcher_works

    tarkov.start_tarkov = fake_start
    try:
        bot.start()
        return log, None
    except Ran:
        return log, None
    except Exception as e:  # noqa: BLE001 - the test's job is to report whatever escaped
        return log, e
    finally:
        (sell.dismiss_error_popup, tarkov.close_game, tarkov.start_tarkov) = originals


def restarts(log):
    return [entry for entry in log if entry[0] == 'start']


if __name__ == '__main__':
    print('SIMULATED: no game is closed or launched, and every pass is a scripted outcome '
          'rather than\n           a real listing. The narration below is the real thing\'s.\n')

    # 1. Off is off. The run ends on a fatal exactly where it always did, and nothing is closed.
    boom = RuntimeError('could not open the flea market')
    log, error = run([None, boom], restart_as=None)
    assert error is boom, f'auto restart off swallowed the fatal, got {error!r}'
    assert restarts(log) == [], f'auto restart off still relaunched the game: {log}'
    print(f'  ok  off, fatal          run ended on {error}, game untouched')

    # 2. On, the same fatal keeps the run alive and the next pass happens.
    log, error = run([boom, None, None], restart_as=SEASONAL)
    assert error is None, f'a restart was meant to absorb the fatal, but {error!r} escaped'
    assert restarts(log) == [('start', SEASONAL)], f'wanted one seasonal relaunch, got {log}'
    assert ('pass', 2) in log, 'the run stopped after the restart instead of carrying on'
    print(f'  ok  on, fatal           relaunched as {SEASONAL.name.lower()}, then pass 2 ran')

    # And it put the state back: a relaunched client is a new window handle, and the lobby is
    # not the flea. Missing either one leaves every later pass searching the wrong rectangle or
    # clicking at a menu.
    order = [entry[0] for entry in log]
    assert order.index('close') < order.index('start') < order.index('measure') < \
        order.index('recover'), f'restart steps out of order: {order}'
    print('  ok  state put back      closed, relaunched, re-measured the window, back to the flea')

    # 3. One Error dialog is ordinary. Ten of them across a healthy run is a normal Tuesday.
    log, error = run(['dialog', None, None], restart_as=SEASONAL)
    assert error is None and restarts(log) == [], f'one dialog cost a restart: {log}'
    print('  ok  one dialog          cleared and forgotten, no restart')

    # 4. Two close together is the wedge. Exactly one restart, and it lands between passes.
    log, error = run(['dialog', 'dialog', None, None, None], restart_as=SEASONAL)
    assert error is None, f'{error!r} escaped a run that should have restarted cleanly'
    assert len(restarts(log)) == 1, f'wanted exactly one restart, got {len(restarts(log))}: {log}'
    where = [entry[0] for entry in log].index('close')
    assert log[where - 1] == ('pass', 2), f'restarted mid pass, not between them: {log}'
    print(f'  ok  two dialogs         one restart, after pass 2 finished '
          f'({sell_bot.ERROR_DIALOG_LIMIT} inside '
          f'{sell_bot.ERROR_DIALOG_WINDOW // 60}m)')

    # The tally is cleared by the restart. Without that, every later pass sees the same two
    # dialogs still on the list and restarts again, which is a relaunch loop that never sells.
    assert len(restarts(log)) == 1, 'it restarted again on dialogs the first restart already fixed'
    print('  ok  tally cleared       passes 3-5 ran without restarting on the old dialogs')

    # 5. Two dialogs, but an hour apart. The window is what makes this a wedge, not the count.
    old = sell_bot.ERROR_DIALOG_WINDOW + 60
    log, error = run(['dialog', None, None], restart_as=SEASONAL, seed_errors=(old,))
    assert error is None and restarts(log) == [], \
        f'a dialog from {old // 60}m ago still counted toward the wedge: {log}'
    print(f'  ok  two far apart       the older one ({old // 60}m ago) pruned, no restart')

    # And the same pair inside the window does restart, so the case above is the age and not
    # some other difference in how a seeded dialog is counted.
    log, error = run(['dialog', None, None], restart_as=SEASONAL,
                     seed_errors=(sell_bot.ERROR_DIALOG_WINDOW - 60,))
    assert len(restarts(log)) == 1, f'the same pair inside the window did not restart: {log}'
    print('  ok  two just inside     same pair, one minute inside the window, restarted')

    # 6. A client that will not come back ends the run. There is no cap on restarts on purpose,
    # so the launcher failing has to be fatal or an unattended night is spent relaunching nothing.
    log, error = run([boom, None, None], restart_as=SEASONAL, launcher_works=False)
    assert isinstance(error, RuntimeError), f'a dead launcher did not end the run, got {error!r}'
    assert len(restarts(log)) == 1, f'it kept trying to relaunch a client that will not start: {log}'
    print(f'  ok  launcher failed     run ended after one attempt: {error}')

    print('\nok, off changes nothing, a wedge restarts once, and a dead launcher stops the run')
