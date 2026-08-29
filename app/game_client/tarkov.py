"""Where Tarkov is installed on this machine, and whether it is running right now."""
import enum
import sys
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
