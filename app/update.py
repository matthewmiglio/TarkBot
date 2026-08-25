"""Silent, per-user auto-update, applied on boot.

The MSI installs into %LocalAppData%\\Tarkbot (see scripts/setup_msi.py), so a newer MSI upgrades
in place with no elevation and no UAC. boot_gate() runs before the main window: it asks GitHub for
the latest release, and if it is newer than ours it hands off to one detached updater window that
downloads the MSI (a determinate progress bar), waits for this process to exit (so the running exe
is never the one being overwritten), installs with msiexec /quiet (the bar switches to a cycling
marquee for that indeterminate stage), then closes and relaunches the app. One window start to
finish. The gate returns True when an update is under way, so the caller exits instead of opening
the main window.

Frozen builds only; from source it is a no-op. Every failure falls through to a normal boot: an
update must never be why the app won't open. Self-check, no network: python -m update
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

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


# The whole update runs in this one detached window: a borderless, app-styled form that downloads
# the MSI on a determinate bar, then flips the same bar to a cycling marquee for the msiexec
# install, then closes and relaunches. It lives in a separate process because the app that
# launched it must exit before msiexec can overwrite its files. Tokens (@URL@ etc.) are filled in
# by _spawn_updater; a normal string, not an f-string, so PowerShell's own { } need no escaping.
# Colors mirror gui/theme.py so it reads as part of the app. Single-quoted paths: %LOCALAPPDATA%
# and %TEMP% never contain a single quote.
_UPDATER_PS = r"""
$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$ink=[Drawing.Color]::FromArgb(216,215,210); $dim=[Drawing.Color]::FromArgb(143,146,143)
$close=[Drawing.Color]::FromArgb(138,74,74); $closeHot=[Drawing.Color]::FromArgb(208,90,90)
$body=[Drawing.Color]::FromArgb(16,17,16); $bar=[Drawing.Color]::FromArgb(13,14,13)

$f=New-Object Windows.Forms.Form
$f.FormBorderStyle='None'; $f.StartPosition='CenterScreen'; $f.TopMost=$true; $f.Text='Tarkbot'
$f.ClientSize=New-Object Drawing.Size(360,132); $f.BackColor=$body; $f.ShowInTaskbar=$true
$f.Icon=[Drawing.Icon]::ExtractAssociatedIcon('@EXE@')  # Tarkbot icon in the taskbar on minimise

$tb=New-Object Windows.Forms.Panel; $tb.SetBounds(0,0,360,30); $tb.BackColor=$bar; $f.Controls.Add($tb)
$title=New-Object Windows.Forms.Label; $title.Text='Tarkbot'; $title.ForeColor=$ink
$title.Font=New-Object Drawing.Font('Segoe UI',10); $title.AutoSize=$false
$title.SetBounds(10,0,200,30); $title.TextAlign='MiddleLeft'; $tb.Controls.Add($title)

$x=New-Object Windows.Forms.Label; $x.Text=[char]0x2715; $x.ForeColor=$close
$x.Font=New-Object Drawing.Font('Segoe UI',10); $x.TextAlign='MiddleCenter'
$x.SetBounds(326,0,34,30); $x.Cursor='Hand'; $tb.Controls.Add($x)
$x.add_MouseEnter({ $x.ForeColor=$closeHot }); $x.add_MouseLeave({ $x.ForeColor=$close })
$x.add_Click({ $f.Hide() })

$m=New-Object Windows.Forms.Label; $m.Text=[char]0x2013; $m.ForeColor=$dim
$m.Font=New-Object Drawing.Font('Segoe UI',11); $m.TextAlign='MiddleCenter'
$m.SetBounds(292,0,34,30); $m.Cursor='Hand'; $tb.Controls.Add($m)
$m.add_MouseEnter({ $m.ForeColor=$ink }); $m.add_MouseLeave({ $m.ForeColor=$dim })
$m.add_Click({ $f.WindowState='Minimized' })

$script:drag=$false
$down={ $script:drag=$true; $script:sp=[Windows.Forms.Cursor]::Position; $script:fp=$f.Location }
$move={ if($script:drag){ $c=[Windows.Forms.Cursor]::Position
  $f.Location=New-Object Drawing.Point(($script:fp.X+$c.X-$script:sp.X),($script:fp.Y+$c.Y-$script:sp.Y)) } }
$up={ $script:drag=$false }
$tb.add_MouseDown($down); $tb.add_MouseMove($move); $tb.add_MouseUp($up)
$title.add_MouseDown($down); $title.add_MouseMove($move); $title.add_MouseUp($up)

$l=New-Object Windows.Forms.Label; $l.Text='Updating to @TAG@...'; $l.ForeColor=$ink
$l.Font=New-Object Drawing.Font('Segoe UI',11); $l.TextAlign='MiddleCenter'
$l.SetBounds(30,50,300,24); $f.Controls.Add($l)
$pb=New-Object Windows.Forms.ProgressBar; $pb.SetBounds(30,90,300,16); $pb.Maximum=100
$f.Controls.Add($pb)
$f.Show(); [Windows.Forms.Application]::DoEvents()

$wc=New-Object System.Net.WebClient; $script:pct=0
Register-ObjectEvent -InputObject $wc -EventName DownloadProgressChanged -Action { $script:pct=$Event.SourceEventArgs.ProgressPercentage } | Out-Null
$wc.DownloadFileAsync([Uri]'@URL@','@MSI@')
while($wc.IsBusy){ $pb.Value=[Math]::Min(100,$script:pct); [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 60 }
$pb.Value=100; [Windows.Forms.Application]::DoEvents()

if(Test-Path '@MSI@'){
  $pb.Style='Marquee'; $pb.MarqueeAnimationSpeed=30
  Wait-Process -Id @PID@
  $p=Start-Process msiexec -ArgumentList '/i','@MSI@','/quiet','/norestart','/l*v','@LOG@' -PassThru
  while(-not $p.HasExited){ [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 80 }
}
$f.Close()
Start-Process '@EXE@'
"""


def _spawn_updater(url, msi, tag):
    """Detached: run the one-window updater (download -> install -> relaunch). See _UPDATER_PS."""
    ps = (_UPDATER_PS.replace('@TAG@', tag).replace('@URL@', url).replace('@MSI@', msi)
          .replace('@PID@', str(os.getpid())).replace('@LOG@', msi + '.log')
          .replace('@EXE@', sys.executable))
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
    msi = os.path.join(tempfile.gettempdir(), url.rsplit('/', 1)[-1])
    _log(f'update available: {tag} (have {__version__}); handing off to the updater')
    try:
        _spawn_updater(url, msi, tag)
        return True  # the updater window now owns the download, install and relaunch
    except Exception as e:
        _log(f'update launch failed: {e!r}')  # fall through to a normal boot
        return False


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
