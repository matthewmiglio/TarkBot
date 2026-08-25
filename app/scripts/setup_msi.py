"""Freeze app/ into a Windows onedir build and wrap it in an MSI.

    python scripts/setup_msi.py bdist_msi --target-version v0.0.0-local

Run from app/. The version comes off the git tag in CI and is written to app/__version__,
which is gitignored and only exists during a build. See docs/build_and_release.md.
"""
import re
import sys
from pathlib import Path

from cx_Freeze import Executable, setup

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

NAME = 'Tarkbot'
AUTHOR = 'Matthew Miglio'
DESCRIPTION = 'Automated Escape From Tarkov flea market seller'
COPYRIGHT = '2026 Matthew Miglio'
UPGRADE_CODE = '{31798cb3-83b3-4ed1-a318-a005166eda24}'  # fresh GUID, never reuse another app's
ICON = ROOT / 'gui' / 'tarkbot.ico'  # generated from gui/tarkbot.svg by scripts/make_icon.py

try:
    _idx = sys.argv.index('--target-version')
    VERSION = sys.argv[_idx + 1]
    del sys.argv[_idx:_idx + 2]
except (ValueError, IndexError):
    VERSION = 'v0.0.0'

version_file = ROOT / '__version__'
version_file.write_text(VERSION, encoding='utf-8')

# Windows Installer only accepts a numeric a.b.c ProductVersion, so a tag like v1.2.3-rc1 has
# to be trimmed down to 1.2.3. The full tag still names the file and lands in __version__.
_match = re.search(r'\d+(\.\d+){0,2}', VERSION)
PRODUCT_VERSION = _match.group() if _match else '0.0.0'

# Every asset resolves at runtime through Path(__file__).parent, and frozen modules live under
# lib/, so each one has to land beside its own module. Listed explicitly rather than left to
# cx_Freeze's package-data discovery, because gui/ and interact/ are namespace packages.
build_exe_options = {
    # matplotlib is tests-only. The rest are optional imports cx_Freeze finds by scanning
    # site-packages; nothing under app/ imports any of them, and they were 100+ MB of the build.
    'excludes': [
        'test', 'tests', 'setuptools', 'matplotlib',
        'IPython', 'ipykernel', 'jupyter_client', 'jupyter_core', 'jedi', 'debugpy', 'zmq',
        'gevent', 'greenlet', 'dill', 'cloudpickle', 'dns', 'defusedxml', 'lib2to3', 'curses',
    ],
    'include_files': [
        (ROOT / 'interact' / 'reference_images', 'lib/interact/reference_images'),
        (ROOT / 'gui' / 'backgrounds', 'lib/gui/backgrounds'),
        (ROOT / 'gui' / 'characters', 'lib/gui/characters'),
        (ROOT / 'snipe_targets.csv', 'lib/snipe_targets.csv'),  # snipe_bot reads it beside itself
        (ICON, 'lib/gui/tarkbot.ico'),  # the exe embeds it, iconbitmap() still reads the file
        (version_file, '__version__'),  # version.py reads this next to the exe when frozen
    ],
    'include_msvcr': True,
}

bdist_msi_options = {
    'upgrade_code': UPGRADE_CODE,
    'add_to_path': False,
    # cx_Freeze 8.4+ dropped bdist_msi's target_version; without these two the MSI ships as
    # v0.0.0 no matter what --target-version said.
    'product_version': PRODUCT_VERSION,
    'output_name': f'tarkbot-{VERSION}-win64.msi',
    # Per-user install: all_users=False makes it ALLUSERS=2 + MSIINSTALLPERUSER=1, so it lands
    # without elevation, and update.py can then apply a newer MSI silently with msiexec /quiet.
    # cx_Freeze still defaults the dir to ProgramFiles even per-user, so LocalAppData is set by
    # hand or the install would want admin after all.
    'all_users': False,
    'initial_target_dir': rf'[LocalAppDataFolder]\{NAME}',
    'summary_data': {'author': AUTHOR, 'comments': DESCRIPTION},
}

setup(
    name=NAME,
    version=PRODUCT_VERSION,
    description=DESCRIPTION,
    executables=[Executable(
        script=ROOT / 'main.py',
        # No console window. sell_bot.py's narration goes to a session log instead, see session_log.py.
        base='Win32GUI',
        uac_admin=False,  # driving mouse/keyboard needs no elevation until proven otherwise
        target_name='tarkbot.exe',
        icon=ICON,
        shortcut_name=f'{NAME} {VERSION}',
        shortcut_dir='DesktopFolder',
        copyright=COPYRIGHT,
    )],
    options={'build_exe': build_exe_options, 'bdist_msi': bdist_msi_options},
)
