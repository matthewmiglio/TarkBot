"""Booting and closing the game: what each step does, and what it refuses to do.

Run:  python tests/test_game_client.py

No game needed. The launcher, the mouse, the matcher and the clock are stubbed, so this is about
the order the steps go out in and what each answer leads to, not about matching pixels.

What this pins. start_tarkov is three steps because the first two do not work on their own, and
that was measured rather than assumed on 2026-08-30: EscapeFromTarkov.exe runs and never draws a
window (it wants a session token), BsgLauncher.exe opens and then just sits there, and the game
only appears about 28 seconds after Play is clicked. Each of those is easy to "simplify" away
later by someone who has not watched it fail, so the click and the wait are checked here.

The no-click cases are the load-bearing half. Clicking Play at a game that is already running
would put a second launcher press into a live session, and clicking when the button was never
found would put a click at wherever the cursor happened to be, on a screen holding the game.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'game_client'))
import tarkov  # noqa: E402

PLAY = (-571, 1204)


def start_with(running, play_point=PLAY, launcher=object()):
    """Run start_tarkov against stubbed answers. Returns (result, clicks).

    running is what is_running() answers on each call in turn, then False forever. play_point is
    what the Play search comes back with, and launcher is the window handle (None for one that
    never opens).
    """
    clicks = []
    saved = (tarkov.is_running, tarkov._launcher_window, tarkov._play_point,
             tarkov.pyautogui, tarkov.time, tarkov.find_game, tarkov.subprocess)
    answers = list(running)
    tarkov.is_running = lambda: answers.pop(0) if answers else False
    tarkov._launcher_window = lambda: launcher
    tarkov._play_point = lambda hwnd: play_point
    tarkov.pyautogui = types.SimpleNamespace(click=lambda x, y: clicks.append((x, y)))
    tarkov.time = types.SimpleNamespace(monotonic=lambda: 0.0, sleep=lambda s: None)
    tarkov.find_game = lambda: Path(r'D:\Battlestate Games\EscapeFromTarkov.exe')
    tarkov.subprocess = types.SimpleNamespace(
        Popen=lambda *a, **k: None,
        run=lambda *a, **k: types.SimpleNamespace(stdout=''))
    try:
        return tarkov.start_tarkov(timeout=0), clicks
    finally:
        (tarkov.is_running, tarkov._launcher_window, tarkov._play_point,
         tarkov.pyautogui, tarkov.time, tarkov.find_game, tarkov.subprocess) = saved


def close_with(running):
    """Run close_game against an is_running() that answers `running` in turn. (result, kills)."""
    kills = []
    saved = (tarkov.is_running, tarkov.subprocess, tarkov.time)
    answers = list(running)
    tarkov.is_running = lambda: answers.pop(0) if answers else False
    tarkov.subprocess = types.SimpleNamespace(
        run=lambda cmd, **k: kills.append(cmd) or types.SimpleNamespace(stdout=''))
    tarkov.time = types.SimpleNamespace(monotonic=lambda: 0.0, sleep=lambda s: None)
    try:
        return tarkov.close_game(timeout=0), kills
    finally:
        tarkov.is_running, tarkov.subprocess, tarkov.time = saved


if __name__ == '__main__':
    # A game already up is left alone. No Play click into a live session.
    result, clicks = start_with([True])
    assert result is True, f'a running game should report started, got {result}'
    assert clicks == [], f'nothing should have been clicked, got {clicks}'

    # The normal boot: not running, launcher up, Play found and pressed, window appears.
    result, clicks = start_with([False, True])
    assert result is True, 'the game window came up and that has to count'
    assert clicks == [PLAY], f'Play was not clicked once at its centre: {clicks}'

    # A launcher with no Play button on it gives up without clicking anywhere. A click here
    # would land wherever the cursor was, on a screen showing the game.
    result, clicks = start_with([False], play_point=None)
    assert result is False, 'no Play button cannot report a successful start'
    assert clicks == [], f'clicked with no button found: {clicks}'

    # A launcher that never opens is a False, not a crash, and still nothing is clicked.
    result, clicks = start_with([False], launcher=None)
    assert result is False, 'no launcher window cannot report a successful start'
    assert clicks == [], f'clicked with no launcher: {clicks}'

    # Play clicked but no game window inside the timeout is a False, not a hopeful True.
    result, clicks = start_with([False, False])
    assert result is False, 'a game that never appeared must not report started'
    assert clicks == [PLAY], 'the click still went out'

    # Closing: a game that is already gone is not killed again.
    result, kills = close_with([False])
    assert result is True and kills == [], f'closed a game that was not running: {kills}'

    # And a live one is forced, not asked. The polite request is ignored by this game, which is
    # why /F is there rather than a WM_CLOSE first.
    result, kills = close_with([True, False])
    assert result is True, 'the window went, so the close worked'
    assert kills == [['taskkill', '/F', '/IM', tarkov.EXE]], f'not a forced kill: {kills}'

    print('ok: boots through Play, refuses to click without one, and forces the close')
