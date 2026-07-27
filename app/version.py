"""The version string, written into __version__ at build time from the git tag.

Frozen, __version__ sits next to tarkbot.exe. From source it sits next to this file and
usually does not exist at all, which is what 'dev' means.
"""
import sys
from pathlib import Path

ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
VERSION_FILE = ROOT / '__version__'
__version__ = VERSION_FILE.read_text(encoding='utf-8').strip() if VERSION_FILE.is_file() else 'dev'

if __name__ == '__main__':
    print(__version__)
