"""Where Tarkov is installed on this machine, whether it is running, and how to close it."""
import enum
import subprocess
import sys
import time
import winreg
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))  # ponytail: app/ is the import root
import pyautogui

import screen
import window
from interact import find

EXE = "EscapeFromTarkov.exe"
LAUNCHER = "BsgLauncher.exe"  # the game will not boot without it, see start_tarkov
LAUNCHER_TITLE = "BsgLauncher"
PLAY_TARGET = "launcher_play"
CLOSE_TIMEOUT = 60  # seconds to wait for the window to go before calling the close a failure
CLOSE_POLL = 0.5  # seconds between window checks while waiting
LAUNCHER_TIMEOUT = 60  # seconds to wait for the launcher's own window after starting it
PLAY_TIMEOUT = 30  # ...then for its Play button to be on screen
PROFILE_TIMEOUT = 120  # ...then for the profile screen and its three SELECT buttons
LOBBY_TIMEOUT = 180  # ...then for the lobby, which is both tabs being up (28s measured to here)
START_POLL = 1.0  # seconds between looks while any of those are awaited

HIDEOUT_TAB_TARGET = 'hideout/hideout_tab'  # the two the lobby is recognised by, both required:
FLEA_TAB_TARGET = 'flea_icon'  # either alone is on screen during the loading that precedes it
PROFILE_TARGET = 'profile_select'
BUTTONS_APART = 200  # px between two SELECT centres that are different buttons (real gap is 547)
DISPLAY_NAME = "Escape from Tarkov"  # the launcher's own uninstall entry, not Arena's

# Where Windows records installed programs. The 32-bit view is listed too because BSG's
# installer is 32-bit on some machines, and a 64-bit Python cannot see it any other way.
UNINSTALL = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]


def _value(key, name):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def _candidates():
    """Every path the registry offers for the game's exe, best first."""
    for root, path in UNINSTALL:
        try:
            parent = winreg.OpenKey(root, path)
        except OSError:
            continue
        with parent:
            for i in range(winreg.QueryInfoKey(parent)[0]):
                try:
                    with winreg.OpenKey(parent, winreg.EnumKey(parent, i)) as key:
                        if _value(key, "DisplayName") != DISPLAY_NAME:
                            continue
                        location = _value(key, "InstallLocation")
                        if location:
                            yield Path(location) / EXE
                        icon = _value(key, "DisplayIcon")
                        if icon:
                            yield Path(icon.split(",")[0].strip('"'))
                except OSError:
                    continue


def find_game():
    """Path to EscapeFromTarkov.exe. Raises FileNotFoundError if the game is not installed.

    ponytail: registry only, no drive scan. If someone moves the folder without reinstalling,
    the fix is to read a path out of settings, not to walk three terabytes hunting for an exe.
    """
    for exe in _candidates():
        if exe.name.lower() == EXE.lower() and exe.is_file():
            return exe
    raise FileNotFoundError(f"No {DISPLAY_NAME} install found in the registry")


def is_running():
    """True while the game's window exists. False the moment it is closed (or never opened)."""
    return bool(window._handles())


def close_game(timeout=CLOSE_TIMEOUT):
    """Force Tarkov shut and block until its window is gone. True once it is, False on timeout.

    Straight to /F, no WM_CLOSE first: the game ignores the polite request, so asking only ever
    bought a wait before forcing anyway. Returns only on the verified answer, either the window
    being gone or the timeout running out with it still there.
    """
    if not is_running():
        return True
    subprocess.run(['taskkill', '/F', '/IM', EXE], capture_output=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not is_running():
            return True
        time.sleep(CLOSE_POLL)
    return not is_running()


class Character(enum.Enum):
    """A profile on the SELECT PROFILE AND MODE screen. The value is its column, left to right."""
    PVE = 0
    PERMANENT = 1  # PvP Zone, the regular character
    SEASONAL = 2  # PvP Season, the one that resets


def _launcher_window():
    """The launcher's window, or None if it is not open."""
    try:
        return window.handle(LAUNCHER_TITLE)
    except window.WindowError:
        return None


def _play_point(hwnd):
    """Where the launcher's Play button is on screen, or None if it cannot be found.

    The launcher is a movable window rather than the fullscreen game, so the search is scoped to
    its own rect and the matcher is pointed at whichever monitor the window is sitting on. That
    monitor is put back afterwards: find.scale() reads it, and a caller mid-bot-run is measuring
    against the game's screen, not this one.
    """
    left, top, right, bottom = window.bounds(hwnd)
    was = screen.current()
    screen.use(screen.containing((left, top)).name)
    try:
        return find.find_center(PLAY_TARGET, (left, top, right - left, bottom - top))
    finally:
        screen.use(was.name)


def _wait(look, timeout, poll=START_POLL):
    """Poll look() until it answers with something truthy, or the timeout runs out. Its answer.

    None on the timeout, so a caller can tell "it never showed" from whatever look() returns.
    """
    deadline = time.monotonic() + timeout
    while True:
        found = look()
        if found:
            return found
        if time.monotonic() >= deadline:
            return None
        time.sleep(poll)


def _game_region():
    """The game window as a region, and the matcher pointed at its monitor. None if it is not up.

    Called from a poll, but screen.use only runs on the look that finds the window, which is the
    same look that stops the polling, so the monitor is chosen once and not once a second.
    """
    try:
        left, top, right, bottom = window.bounds(window.handle())
    except window.WindowError:
        return None
    screen.use(screen.containing((left, top)).name)
    return (left, top, right - left, bottom - top)


def _profile_buttons(region):
    """The profile screen's three SELECT buttons, left to right, or [] until all three are up.

    Each button matches a full crop of itself and a sub-crop of itself, and those two overlap by
    about a third, which is under find's IOU dedupe, so every button comes back twice. Cluster on
    centre instead and keep the widest box of each cluster. Fewer than three means the screen is
    still drawing, so the caller keeps waiting rather than clicking a card that has no neighbours
    yet and might not be the one it thinks.
    """
    kept = []
    for box in sorted(find.find_all(PROFILE_TARGET, region), key=lambda b: b.left):
        centre = box.left + box.width // 2
        near = [b for b in kept if abs(b.left + b.width // 2 - centre) < BUTTONS_APART]
        if not near:
            kept.append(box)
        elif box.width > near[0].width:
            kept[kept.index(near[0])] = box
    return kept if len(kept) == 3 else []


def in_lobby(region=None):
    """Is the game sat in the lobby, ie are both the hideout tab and the flea tab on screen.

    Both, because either alone shows up during the loading that precedes the lobby, and a click
    aimed at a half-drawn screen lands on nothing.
    """
    return bool(find.find(HIDEOUT_TAB_TARGET, region) and find.find(FLEA_TAB_TARGET, region))


def start_tarkov(character=Character.PVE, installation_path=None):
    """Boot the game onto `character`'s profile and wait for the lobby. True once it is there.

    Four steps, each with its own budget, because the game will not start from any one of them
    alone: EscapeFromTarkov.exe runs and never draws a window (it wants a session token from the
    launcher), the launcher opens and then just sits there, and the profile screen waits for a
    card to be picked. Measured on 2026-08-30.

      1. start BsgLauncher.exe, unless its window is already up   (LAUNCHER_TIMEOUT)
      2. wait for its Play button and click it                    (PLAY_TIMEOUT)
      3. wait for the three SELECT buttons and click this one     (PROFILE_TIMEOUT)
      4. wait for the lobby, both tabs                            (LOBBY_TIMEOUT)

    character is a Character, whose value is the card's column, left to right on that screen.
    installation_path defaults to find_game(); the launcher is taken from beside it. Returns
    False at whichever step timed out, having said which in the log.
    """
    if is_running():
        return True
    exe = Path(installation_path) if installation_path else find_game()

    hwnd = _launcher_window()
    if hwnd is None:
        launcher = exe.parent / "BsgLauncher" / LAUNCHER
        if not launcher.is_file():
            print(f"no launcher at {launcher}")
            return False
        subprocess.Popen([str(launcher)], cwd=str(launcher.parent))
        hwnd = _wait(_launcher_window, LAUNCHER_TIMEOUT)
        if hwnd is None:
            print(f"the launcher window never appeared in {LAUNCHER_TIMEOUT}s")
            return False

    point = _wait(lambda: _play_point(hwnd), PLAY_TIMEOUT)
    if point is None:
        print(f"no Play button on the launcher after {PLAY_TIMEOUT}s")
        return False
    print(f"clicking Play at {point}")
    pyautogui.click(*point)

    deadline = time.monotonic() + PROFILE_TIMEOUT
    region = _wait(_game_region, PROFILE_TIMEOUT)
    if region is None:
        print(f"the game window never appeared in {PROFILE_TIMEOUT}s")
        return False
    if not select_character_type(character, region, max(1.0, deadline - time.monotonic())):
        print(f"the three profile buttons never appeared in {PROFILE_TIMEOUT}s")
        return False

    if _wait(lambda: in_lobby(region), LOBBY_TIMEOUT) is None:
        print(f"the lobby never appeared in {LOBBY_TIMEOUT}s")
        return False
    return True


def select_character_type(character, region=None, timeout=PROFILE_TIMEOUT):
    """Wait for the profile screen and click `character`'s card. True if it was there to click.

    The card is picked by column rather than by a crop of its own: the three SELECT buttons are
    pixel-identical, so which one is which is their order on screen and nothing else.
    """
    region = region if region is not None else _game_region()
    if region is None:
        return False
    buttons = _wait(lambda: _profile_buttons(region), timeout)
    if not buttons:
        return False
    box = buttons[character.value]
    print(f"selecting {character.name} at column {character.value}, box {box}")
    pyautogui.click(box.left + box.width // 2, box.top + box.height // 2)
    return True


if __name__ == "__main__":
    try:
        print(f"install  {find_game()}")
    except FileNotFoundError as e:
        print(f"install  {e}")
    print(f"running  {is_running()}")
    if "--close" in sys.argv:  # ponytail: opt in, so a plain run never shuts the game
        print(f"closed   {close_game()}")
        print(f"running  {is_running()}")
