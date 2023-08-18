from os.path import abspath, join, pardir
from pathlib import Path
from winreg import HKEY_LOCAL_MACHINE, ConnectRegistry, OpenKey, QueryValueEx


def get_bsg_launcher_path() -> str:
    """get the path to the bsg launcher"""
    try:
        akey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{B0FDA062-7581-4D67-B085-C4E7C358037F}_is1"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    except FileNotFoundError:
        akey = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{B0FDA062-7581-4D67-B085-C4E7C358037F}_is1"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    launcher_file = abspath(
        join(QueryValueEx(akey, "InstallLocation")[0], "BsgLauncher.exe")
    )
    if not Path(launcher_file).exists():
        try:
            akey = (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov"
            )
            areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            akey = OpenKey(areg, akey)
        except FileNotFoundError:
            akey = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov"
            areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
            akey = OpenKey(areg, akey)
        launcher_file = abspath(
            join(
                QueryValueEx(akey, "InstallLocation")[0],
                pardir,
                "BsgLauncher",
                "BsgLauncher.exe",
            )
        )
    return launcher_file
