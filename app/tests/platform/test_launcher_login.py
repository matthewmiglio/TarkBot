"""A launcher sat on its sign-in page stops the run and says so, instead of crashing or restarting.

App layer: game_client/tarkov.py's LOGIN_TARGET, login_page_up, _play_or_login, _play_point and
start_tarkov, plus craft_bot.HideoutCraft.start's NeedsLogin handler. No game: the matcher, the
window and the screen are all stubbed, so this is about what the boot does with the answers.

Two runs are behind this, both on 2026-09-17:

  11:41  craft mode died 0.08s in with "ValueError: needle dimension(s) exceed the haystack image
         or region dimensions" out of pyscreeze, naming neither the launcher nor the window. The
         launcher was showing its sign-in dialog, so no Play button existed to find.

  The restart trap it would have become: NeedsLogin must NOT be a RuntimeError, because
  craft_bot.start catches RuntimeError and answers it by calling _restart_game, which calls
  start_tarkov again. Raised as a RuntimeError this would close and relaunch the client into the
  same dialog for as long as the run lasted. The `not issubclass` check below is the guard.

Run:  python tests/platform/test_launcher_login.py
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
from game_client import tarkov  # noqa: E402

failures = []


def check(name, condition, detail=''):
    print(f'{"ok  " if condition else "FAIL"}  {name}{"  " + detail if detail else ""}')
    if not condition:
        failures.append(name)


class FakeScreen:
    """Just enough of screen.py for _play_point: a named monitor that can be switched to."""
    name = 'FAKE'

    @staticmethod
    def current():
        return FakeScreen()

    @staticmethod
    def containing(_point):
        return FakeScreen()

    @staticmethod
    def use(_name):
        pass


tarkov.screen = FakeScreen
tarkov.window.bounds = lambda _hwnd: (0, 0, 1920, 1080)

# 1. The guard that keeps this out of every mode's restart tuple. If this ever fails, a sign-in
#    page becomes an endless close-and-relaunch loop.
check('NeedsLogin is not a RuntimeError', not issubclass(tarkov.NeedsLogin, RuntimeError))
check('NeedsLogin is still an Exception', issubclass(tarkov.NeedsLogin, Exception))

# 2. login_page_up is a plain bool over the matcher.
tarkov.find.find = lambda target, region=None: 'a box' if target == tarkov.LOGIN_TARGET else None
check('login_page_up is True when the dialog matches', tarkov.login_page_up() is True)
tarkov.find.find = lambda target, region=None: None
check('login_page_up is False when it does not', tarkov.login_page_up() is False)

# 3. _play_or_login raises rather than returning, so _wait unwinds at once instead of burning
#    PLAY_TIMEOUT waiting for a button that cannot appear.
tarkov.find.find = lambda target, region=None: 'a box' if target == tarkov.LOGIN_TARGET else None
raised = None
try:
    tarkov._play_or_login(1234)
except tarkov.NeedsLogin as e:
    raised = e
check('_play_or_login raises NeedsLogin on the sign-in page', isinstance(raised, tarkov.NeedsLogin))
check('and the message tells the user what to do',
      raised is not None and 'sign in' in str(raised).lower())

# 4. With no dialog up it just answers with the Play point, as before.
tarkov.find.find = lambda target, region=None: None
tarkov.find.find_center = lambda target, region=None: (100, 200)
check('_play_or_login returns the Play point otherwise', tarkov._play_or_login(1234) == (100, 200))

# 5. A window smaller than the Play crop is "not found yet", not a ValueError out of the matcher.
#    A minimised window reports about 160x28, which is what produced the 11:41 crash.
def _boom(_target, _region=None):
    raise ValueError('needle dimension(s) exceed the haystack image or region dimensions')


tarkov.find.find_center = _boom
check('_play_point swallows the needle-too-big ValueError', tarkov._play_point(1234) is None)

# 6. start_tarkov lets NeedsLogin out rather than returning False. False would become
#    "Tarkov would not start", a RuntimeError, and the restart loop this exists to prevent.
tarkov.is_running = lambda: False
tarkov._launcher_window = lambda: 4321
tarkov.find.find = lambda target, region=None: 'a box' if target == tarkov.LOGIN_TARGET else None
tarkov.find.find_center = lambda target, region=None: None
raised = None
try:
    tarkov.start_tarkov(tarkov.Character.SEASONAL)
except tarkov.NeedsLogin as e:
    raised = e
except Exception as e:  # noqa: BLE001 - anything else is the failure being guarded
    raised = e
check('start_tarkov raises NeedsLogin out of the boot', isinstance(raised, tarkov.NeedsLogin),
      f'got {type(raised).__name__}')

# 7. craft mode catches it, logs it, and ends the run quietly: no traceback, no restart.
bot = object.__new__(craft_bot.HideoutCraft)
bot._stop = threading.Event()
bot.hwnd = None
bot.restart_as = tarkov.Character.SEASONAL
bot.region = None
bot.stats = {'total_started': 0, 'total_profit': 0}
bot.restarts = 0


def _boot_into_login():
    raise tarkov.NeedsLogin('the launcher is on its sign-in page: sign in and start again')


def _must_not_restart(_why):
    bot.restarts += 1


bot._boot_game = _boot_into_login
bot._restart_game = _must_not_restart

raised = None
try:
    bot.start()
except Exception as e:  # noqa: BLE001
    raised = e
check('craft mode start() ends cleanly on NeedsLogin', raised is None, f'raised={raised!r}')
check('and never tries to restart the game', bot.restarts == 0, f'restarts={bot.restarts}')

print()
if failures:
    sys.exit(f'{len(failures)} check(s) failed: {", ".join(failures)}')
print('ok: a sign-in page stops the run with an explanation instead of crashing or looping')
