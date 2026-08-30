"""Booting and closing the game: the four steps, what each refuses to do, and which card is clicked.

Run:  python tests/test_game_client.py

No game needed. The launcher, the mouse, the matcher and the clock are all stubbed, so this is
about the order the steps go out in and what each answer leads to, not about matching pixels.

What this pins. start_tarkov is four waits because none of the earlier steps work alone, and that
was measured rather than guessed on 2026-08-30: EscapeFromTarkov.exe runs and never draws a
window (it wants a session token), BsgLauncher.exe opens and then sits there, and the profile
screen waits for a card. Each of those is easy to "simplify" away later by someone who has not
watched it fail, so the clicks and the waits are checked here.

Two things carry the most risk and get the most attention. Which card is clicked is decided by
column and nothing else, because the three SELECT buttons are pixel-identical, so a bug there
picks the wrong profile in silence rather than failing. And every step that cannot find what it
needs must click nothing at all: a click aimed at a button that was never found lands wherever
the cursor happened to be, on a screen showing the game.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'game_client'))
import tarkov  # noqa: E402

PLAY = (-570, 1204)
REGION = (-2560, 260, 2560, 1440)
# The three SELECT buttons as they really came back, evenly spaced 547px apart.
CARDS = [types.SimpleNamespace(left=x, top=1435, width=129, height=40)
         for x in (-1892, -1345, -798)]
CENTRES = [(-1828, 1455), (-1281, 1455), (-734, 1455)]


def ticking_clock(step=10.0):
    """A monotonic that moves on every read, so a wait that never succeeds still times out."""
    state = {'now': 0.0}

    def monotonic():
        state['now'] += step
        return state['now']
    return types.SimpleNamespace(monotonic=monotonic, sleep=lambda s: None)


def start_with(character=None, running=(False,), play=PLAY, region=REGION,
               buttons=None, lobby=True, launcher=object()):
    """Run start_tarkov against stubbed answers. Returns (result, clicks)."""
    clicks = []
    names = ('is_running', '_launcher_window', '_play_point', '_game_region', '_profile_buttons',
             'in_lobby', 'pyautogui', 'time', 'find_game', 'subprocess')
    saved = {n: getattr(tarkov, n) for n in names}
    answers = list(running)
    tarkov.is_running = lambda: answers.pop(0) if answers else False
    tarkov._launcher_window = lambda: launcher
    tarkov._play_point = lambda hwnd: play
    tarkov._game_region = lambda: region
    tarkov._profile_buttons = lambda r: (CARDS if buttons is None else buttons)
    tarkov.in_lobby = lambda r=None: lobby
    tarkov.pyautogui = types.SimpleNamespace(click=lambda x, y: clicks.append((x, y)))
    tarkov.time = ticking_clock()
    tarkov.find_game = lambda: Path(r'D:\Battlestate Games\EscapeFromTarkov.exe')
    tarkov.subprocess = types.SimpleNamespace(Popen=lambda *a, **k: None)
    try:
        return tarkov.start_tarkov(character or tarkov.Character.PVE), clicks
    finally:
        for name, value in saved.items():
            setattr(tarkov, name, value)


def close_with(running):
    """Run close_game against an is_running() that answers `running` in turn. (result, kills)."""
    kills = []
    saved = (tarkov.is_running, tarkov.subprocess, tarkov.time)
    answers = list(running)
    tarkov.is_running = lambda: answers.pop(0) if answers else False
    tarkov.subprocess = types.SimpleNamespace(
        run=lambda cmd, **k: kills.append(cmd) or types.SimpleNamespace(stdout=''))
    tarkov.time = ticking_clock()
    try:
        return tarkov.close_game(timeout=0), kills
    finally:
        tarkov.is_running, tarkov.subprocess, tarkov.time = saved


def cluster(boxes):
    """_profile_buttons over a stubbed find_all."""
    saved = tarkov.find
    tarkov.find = types.SimpleNamespace(find_all=lambda *a, **k: boxes)
    try:
        return tarkov._profile_buttons(REGION)
    finally:
        tarkov.find = saved


if __name__ == '__main__':
    # Every profile is clicked at its own column, and that is the whole of how they are told
    # apart: the three buttons are pixel-identical, so an off-by-one here is a silent wrong
    # profile rather than a failure.
    for character, centre in zip(tarkov.Character, CENTRES):
        assert character.value == CENTRES.index(centre), f'{character} is not its column'
        result, clicks = start_with(character)
        assert result is True, f'{character.name} should have booted, got {result}'
        assert clicks == [PLAY, centre], f'{character.name} clicked {clicks}, wanted {centre}'

    # A game already up is left alone: no second Play press into a live session.
    result, clicks = start_with(running=(True,))
    assert result is True and clicks == [], f'clicked at a running game: {clicks}'

    # Nothing found means nothing clicked, at each of the three things that can go missing.
    for label, kwargs, expected in (
            ('no launcher', {'launcher': None}, []),
            ('no Play button', {'play': None}, []),
            ('no profile buttons', {'buttons': []}, [PLAY]),
            ('no lobby', {'lobby': False}, [PLAY, CENTRES[0]])):
        result, clicks = start_with(**kwargs)
        assert result is False, f'{label} must not report a successful start'
        assert clicks == expected, f'{label} clicked {clicks}, wanted {expected}'

    # The clustering. Every button matches its full crop and its sub-crop, and those overlap by
    # about a third, under find's IOU dedupe, so all six come back and have to be collapsed to
    # three by centre. The widest of each pair is the one kept.
    subs = [types.SimpleNamespace(left=c.left + 8, top=c.top + 5, width=59, height=29)
            for c in CARDS]
    both = [b for pair in zip(CARDS, subs) for b in pair]
    assert cluster(both) == CARDS, 'six matches did not collapse to the three full boxes'
    assert cluster(CARDS) == CARDS, 'three clean matches should pass straight through'

    # A half-drawn screen is not a screen to click on. Two buttons is not three.
    assert cluster(CARDS[:2]) == [], 'two buttons must read as not ready'
    assert cluster([]) == [], 'no buttons must read as not ready'

    # Closing: a game already gone is not killed again, and a live one is forced rather than
    # asked, since this game ignores the polite request.
    result, kills = close_with([False])
    assert result is True and kills == [], f'killed a game that was not running: {kills}'
    result, kills = close_with([True, False])
    assert result is True, 'the window went, so the close worked'
    assert kills == [['taskkill', '/F', '/IM', tarkov.EXE]], f'not a forced kill: {kills}'

    print('ok: boots each profile at its own column, clicks nothing it cannot see, forces closes')
