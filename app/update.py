"""Silent, per-user auto-update, applied on boot.

The MSI installs into %LocalAppData%\\Tarkbot (see scripts/setup_msi.py), so a newer MSI upgrades
in place with no elevation and no UAC. boot_gate() runs before the main window: it asks GitHub for
the latest release, and if it is newer than ours it shows a small "Tarkbot is updating..." popup
with a progress bar, downloads the MSI, then hands it to msiexec /quiet through a detached waiter
that lets this process exit first (so the running exe is never the one being overwritten) and
relaunches the app once the install finishes. The gate returns True when an update is under way, so
the caller exits instead of opening the main window.

Frozen builds only; from source it is a no-op. Every failure falls through to a normal boot: an
update must never be why the app won't open. Self-check, no network: python -m update
"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
from ctypes import wintypes
from tkinter import ttk

from version import __version__

REPO = 'matthewmiglio/TarkBot'
API = f'https://api.github.com/repos/{REPO}/releases/latest'
CHECK_TIMEOUT = 6  # short, so a dead network delays boot by seconds, not the download's 15
DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
# Same GUID scripts/setup_msi.py stamps into every MSI, uppercased to MSI's stored form. Both the
# old per-machine build and the new per-user one carry it, which is how we find the stale one.
UPGRADE_CODE = '{31798CB3-83B3-4ED1-A318-A005166EDA24}'


def _asset(release):
    """The release's .msi download url, or None if it has none."""
    return next((a['browser_download_url'] for a in release.get('assets', [])
                 if a['name'].lower().endswith('.msi')), None)


def _newer(tag):
    # ponytail: exact mismatch, not semver. releases/latest is always the newest stable, so a tag
    # != ours means an update; a user on an rc ahead of stable just gets a no-op downgrade, which
    # the MSI's lower ProductVersion refuses on its own.
    return bool(tag) and tag != __version__


def _latest():
    """(tag, msi_url) for the newest release if it is newer than us and has an MSI, else None."""
    req = urllib.request.Request(API, headers={'Accept': 'application/vnd.github+json',
                                               'User-Agent': 'tarkbot'})
    with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as r:
        release = json.load(r)
    tag, url = release.get('tag_name'), _asset(release)
    return (tag, url) if (_newer(tag) and url) else None


def _install_after_exit(msi):
    """Detached: wait for us to die, install the MSI silently, relaunch the app."""
    log = msi + '.log'
    # Wait-Process on our PID first, or Windows Installer sees tarkbot.exe in use and defers to a
    # reboot. Single-quoted paths (%LOCALAPPDATA%/%TEMP% never contain a single quote).
    ps = (f"Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue; "
          f"Start-Process msiexec -ArgumentList '/i','{msi}','/quiet','/norestart','/l*v','{log}' "
          f"-Wait; Start-Process '{sys.executable}'")
    subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps],
                     creationflags=DETACHED, close_fds=True)


def _related_products(upgrade_code):
    """Every installed ProductCode registered under this UpgradeCode, any install context."""
    msi = ctypes.windll.msi
    buf = ctypes.create_unicode_buffer(39)  # a GUID is 38 chars + null
    out, i = [], 0
    while msi.MsiEnumRelatedProductsW(upgrade_code, 0, i, buf) == 0:  # 0 == ERROR_SUCCESS
        out.append(buf.value)
        i += 1
    return out


def _is_per_machine(product_code):
    """True if this product was installed for the whole machine (AssignmentType 1)."""
    msi = ctypes.windll.msi
    size = wintypes.DWORD(0)
    msi.MsiGetProductInfoW(product_code, 'AssignmentType', None, ctypes.byref(size))
    size.value += 1
    buf = ctypes.create_unicode_buffer(size.value)
    if msi.MsiGetProductInfoW(product_code, 'AssignmentType', buf, ctypes.byref(size)) != 0:
        return False
    return buf.value == '1'


def remove_stale_machine_install():
    """One-time migration: uninstall the old per-machine build if this user has it.

    Removing a machine-wide install needs elevation, so this is the one UAC prompt in the whole
    updater, and it is shown only to users who still carry the old ProgramFiles MSI. Our own
    per-user install shares the UpgradeCode but is AssignmentType 0, so it is never a target.
    Once the old one is gone the enumeration comes back empty and this never prompts again.
    """
    if not getattr(sys, 'frozen', False):
        return
    try:
        stale = [p for p in _related_products(UPGRADE_CODE) if _is_per_machine(p)]
    except Exception:
        return  # msi.dll unhappy: skip the cleanup, never block boot over it
    for code in stale:
        # runas -> one UAC prompt; /qn -> silent uninstall behind it. Declined or failed is
        # swallowed by ShellExecuteW's return, and boot carries on with both installs present.
        ctypes.windll.shell32.ShellExecuteW(None, 'runas', 'msiexec',
                                            f'/x {code} /qn /norestart', None, 0)


def boot_gate():
    """Returns True if an update is being applied (caller should exit), False to boot normally."""
    if not getattr(sys, 'frozen', False):
        return False
    try:
        found = _latest()
    except Exception:
        return False  # offline, rate-limited, no release: just boot
    if not found:
        return False
    _tag, url = found
    try:
        _run_popup(url)  # blocks until the MSI is downloaded and the installer is launched
        return True
    except Exception:
        return False  # any failure downloading or launching: fall through to a normal boot


def _run_popup(url):
    """Small progress window; downloads the MSI, then launches the detached installer."""
    root = tk.Tk()
    root.title('Tarkbot')
    root.resizable(False, False)
    root.configure(bg='#101110')
    tk.Label(root, text='Tarkbot is updating…', bg='#101110', fg='#e8e8e8',
             font=('Segoe UI', 11), pady=14).pack(padx=28)
    bar = ttk.Progressbar(root, length=280, mode='determinate', maximum=100)
    bar.pack(padx=28, pady=(0, 18))

    state = {'done': False, 'error': False, 'msi': None}

    def worker():
        try:
            path = os.path.join(tempfile.gettempdir(), url.rsplit('/', 1)[-1])
            urllib.request.urlretrieve(url, path, _report(state, bar, root))
            state['msi'] = path
        except Exception:
            state['error'] = True
        finally:
            state['done'] = True

    def poll():
        if not state['done']:
            root.after(100, poll)
            return
        if state['error'] or not state['msi']:
            root.destroy()
            raise RuntimeError('update download failed')
        _install_after_exit(state['msi'])
        root.destroy()  # we exit right after; the detached installer waits for that

    threading.Thread(target=worker, daemon=True).start()
    root.after(100, poll)
    _center(root)
    root.mainloop()


def _report(state, bar, root):
    """urlretrieve reporthook -> drive the bar from the main thread via after()."""
    def hook(count, block, total):
        if total > 0:
            pct = min(100, count * block * 100 // total)
            root.after(0, lambda: bar.config(value=pct))
    return hook


def _center(root):
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f'+{x}+{y}')


def demo():
    assert _asset({'assets': [{'name': 'notes.txt', 'browser_download_url': 'x'},
                              {'name': 'tarkbot-v9-win64.msi', 'browser_download_url': 'ok'}]}) == 'ok'
    assert _asset({'assets': []}) is None
    assert _newer('v0.0.0-never') is True
    assert _newer(__version__) is False
    assert _newer(None) is False
    assert boot_gate() is False  # not frozen: never gates
    assert remove_stale_machine_install() is None  # not frozen: no enumeration, no prompt
    print('ok. current version:', __version__)


if __name__ == '__main__':
    demo()
