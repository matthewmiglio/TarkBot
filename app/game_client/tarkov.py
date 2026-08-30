"""Where Tarkov is installed on this machine, whether it is running, and how to close it."""
import enum
import subprocess
import sys
import time
import winreg
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))  # ponytail: app/ is the import root
import window

EXE = "EscapeFromTarkov.exe"
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


def close_game(timeout=20):
    """Close Tarkov and wait for its window to go. True once it is gone, False if it hangs on.

    Asks first (taskkill with no /F posts WM_CLOSE), and only forces if the game is still up
    when the timeout runs out. A game sitting in the hideout has nothing to lose either way, but
    a raid does, so the polite request goes first.
    """
    if not is_running():
        return True
    subprocess.run(['taskkill', '/IM', EXE], capture_output=True)
    if _gone_within(timeout):
        return True
    log = f'{EXE} ignored the close request after {timeout}s, forcing it'
    print(log)
    subprocess.run(['taskkill', '/F', '/IM', EXE], capture_output=True)
    return _gone_within(timeout)


def _gone_within(timeout):
    """Poll until the game's window is gone, or the timeout runs out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not is_running():
            return True
        time.sleep(0.5)
    return not is_running()


class Character(enum.Enum):
    """The character the launcher offers to play as."""
    PVE = "pve"
    SEASONAL = "seasonal"
    PERMANENT = "permanent"


def start_tarkov(installation_path=None):
    """SKELETON, not implemented yet. Boot the game and return True once it is up.

    installation_path defaults to find_game(). Returns False if the game never appears.
    """
    raise NotImplementedError("start_tarkov")


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
