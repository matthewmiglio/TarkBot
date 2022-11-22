from os.path import abspath, pardir, join

from winreg import HKEY_LOCAL_MACHINE, ConnectRegistry, OpenKey, QueryValueEx


def get_bsg_launcher_path() -> str:
    """get the path to the bsg launcher"""
    try:
        akey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    except FileNotFoundError:
        akey = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\EscapeFromTarkov"
        areg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
        akey = OpenKey(areg, akey)
    return abspath(
        join(
            QueryValueEx(akey, "InstallLocation")[0],
            pardir,
            "BsgLauncher",
            "BsgLauncher.exe",
        )
    )
