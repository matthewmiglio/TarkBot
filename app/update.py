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
import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import urllib.request
from tkinter import ttk

import narrate
from version import __version__


def _log(msg):
    """Timestamped line into the session log, so this whole path can be read back after a boot."""
    narrate.log(f'update: {msg}')

REPO = 'matthewmiglio/TarkBot'
API = f'https://api.github.com/repos/{REPO}/releases/latest'
CHECK_TIMEOUT = 6  # short, so a dead network delays boot by seconds, not the download's 15
# CREATE_NO_WINDOW, not DETACHED_PROCESS: the windowed exe has no console and no valid std
# handles, and a DETACHED_PROCESS child inherits that and dies before running a line (measured:
# the waiter launched but msiexec never started). CREATE_NO_WINDOW gives it its own hidden
# console, and CREATE_NEW_PROCESS_GROUP plus DEVNULL handles below keep it clean and detached.
NO_WINDOW = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP


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
    """Detached: keep an 'updating' window up, install the MSI, relaunch the app.

    The window has to live out here, in the waiter, not in the app: the app that showed the
    download popup must exit before msiexec can overwrite its files, so without this the screen
    goes blank for the whole install. The waiter shows a small marquee window first, waits for
    us to die (or Windows Installer sees tarkbot.exe in use and defers to a reboot), installs
    while pumping the window so it stays painted, then closes it and relaunches. Single-quoted
    paths: %LOCALAPPDATA%/%TEMP% never contain a single quote.
    """
    log = msi + '.log'
    ps = f"""
        $ErrorActionPreference='SilentlyContinue'
        Add-Type -AssemblyName System.Windows.Forms,System.Drawing
        $f=New-Object Windows.Forms.Form
        $f.Text='Tarkbot'; $f.FormBorderStyle='FixedDialog'; $f.ControlBox=$false
        $f.StartPosition='CenterScreen'; $f.TopMost=$true
        $f.ClientSize=New-Object Drawing.Size(320,84)
        $f.BackColor=[Drawing.Color]::FromArgb(16,17,16)
        $b=New-Object Windows.Forms.ProgressBar; $b.Style='Marquee'; $b.Dock='Bottom'; $b.Height=22
        $l=New-Object Windows.Forms.Label; $l.Text='Tarkbot is updating...'
        $l.ForeColor='White'; $l.TextAlign='MiddleCenter'; $l.Dock='Fill'
        $f.Controls.Add($l); $f.Controls.Add($b)
        $f.Show(); [Windows.Forms.Application]::DoEvents()
        Wait-Process -Id {os.getpid()}
        $p=Start-Process msiexec -ArgumentList '/i','{msi}','/quiet','/norestart','/l*v','{log}' -PassThru
        while(-not $p.HasExited){{ [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 80 }}
        $f.Close()
        Start-Process '{sys.executable}'
    """
    # DEVNULL for all three: a windowed exe's own std handles are invalid, and the child chokes
    # on them without this. See NO_WINDOW above for why that flag and not DETACHED_PROCESS.
    subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps],
                     creationflags=NO_WINDOW, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def boot_gate():
    """Returns True if an update is being applied (caller should exit), False to boot normally."""
    if not getattr(sys, 'frozen', False):
        return False
    _log(f'running {__version__}, checking for a newer release')  # names who ran the check
    try:
        found = _latest()
    except Exception as e:
        _log(f'update check failed: {e!r}')  # offline, rate-limited, bad json: just boot
        return False
    if not found:
        _log(f'up to date at {__version__}')
        return False
    tag, url = found
    _log(f'update available: {tag} (have {__version__}); downloading')
    try:
        return _run_popup(url)  # True once the installer is launched, False if it fell through
    except Exception as e:
        _log(f'update download/launch failed: {e!r}')  # fall through to a normal boot
        return False


def _run_popup(url):
    """Progress window; downloads the MSI and launches the installer. True if it launched."""
    root = tk.Tk()
    root.title('Tarkbot')
    root.resizable(False, False)
    root.configure(bg='#101110')
    tk.Label(root, text='Tarkbot is downloading an update…', bg='#101110', fg='#e8e8e8',
             font=('Segoe UI', 11), pady=14).pack(padx=28)
    bar = ttk.Progressbar(root, length=280, mode='determinate', maximum=100)
    bar.pack(padx=28, pady=(0, 18))

    state = {'done': False, 'err': '', 'msi': None, 'launched': False}

    def worker():
        try:
            path = os.path.join(tempfile.gettempdir(), url.rsplit('/', 1)[-1])
            urllib.request.urlretrieve(url, path, _report(state, bar, root))
            state['msi'] = path
        except Exception as e:
            state['err'] = repr(e)
        finally:
            state['done'] = True

    def poll():
        if not state['done']:
            root.after(100, poll)
            return
        if state['err'] or not state['msi']:
            _log(f'download failed: {state["err"] or "no file"}')
            root.destroy()  # leaves launched False -> boot_gate opens the app as normal
            return
        _log(f'downloaded {state["msi"]}; launching installer, will exit and relaunch')
        try:
            _install_after_exit(state['msi'])
            state['launched'] = True  # we exit right after; the detached installer waits for that
        except Exception as e:
            _log(f'installer launch failed: {e!r}')  # stay open rather than exit into nothing
        root.destroy()

    threading.Thread(target=worker, daemon=True).start()
    root.after(100, poll)
    _center(root)
    root.mainloop()
    return state['launched']


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
    print('ok. current version:', __version__)


if __name__ == '__main__':
    demo()
