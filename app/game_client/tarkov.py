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
START_TIMEOUT = 180  # seconds to wait for the game window after Play is clicked (28s measured)
START_POLL = 1.0  # seconds between window checks while the game boots
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
    """The character the launcher offers to play as."""
    PVE = "pve"
    SEASONAL = "seasonal"
    PERMANENT = "permanent"


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


def start_tarkov(installation_path=None, timeout=START_TIMEOUT):
    """Boot the game through the launcher and block until its window is up. True/False.

    Three steps, because the game will not start from either of the first two alone: the exe on
    its own runs and never draws a window (it is waiting on a session token), and the launcher on
    its own opens and sits there. Play has to be clicked. Measured on 2026-08-30: the game window
    came up 28 seconds after the click.

    installation_path defaults to find_game(); the launcher is taken from beside it. Returns
    False if the launcher never opens, Play is never found, or the game never appears in time.
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
        deadline = time.monotonic() + LAUNCHER_TIMEOUT
        while hwnd is None and time.monotonic() < deadline:
            time.sleep(START_POLL)
            hwnd = _launcher_window()
        if hwnd is None:
            print(f"the launcher window never appeared in {LAUNCHER_TIMEOUT}s")
            return False

    point = _play_point(hwnd)
    if point is None:
        print("no Play button on the launcher")
        return False
    pyautogui.click(*point)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_running():
            return True
        time.sleep(START_POLL)
    return is_running()


def select_character_type(type):
    """SKELETON, not implemented yet. Pick PVE / seasonal / permanent on the character screen.

    Takes a Character. Returns nothing: the caller checks the result by reading the screen.
    """
    raise NotImplementedError("select_character_type")


if __name__ == "__main__":
    try:
        print(f"install  {find_game()}")
    except FileNotFoundError as e:
        print(f"install  {e}")
    print(f"running  {is_running()}")
    if "--close" in sys.argv:  # ponytail: opt in, so a plain run never shuts the game
        print(f"closed   {close_game()}")
        print(f"running  {is_running()}")
