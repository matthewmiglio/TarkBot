"""Frozen entry point. Same thing `python -m gui.app` does, but importable by cx_Freeze.

Kept separate from gui/app.py because the frozen main script's __file__ is not a real path,
and gui/app.py derives the repo root from its own __file__.
"""
import sys
import tkinter as tk

from gui import settings
from gui.app import App

LOG = settings.APP_DIR / 'tarkbot.log'


def _redirect_output():
    """Frozen windowed, sys.stdout is None and bot.py's every print() would raise. Point it at
    a log file beside settings.json instead, which is also the only copy of the narration a
    user can send back. Installed under Program Files, so the log cannot live next to the exe.
    """
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stream = open(LOG, 'w', encoding='utf-8', buffering=1)  # line buffered, readable mid-run
    sys.stdout = sys.stderr = stream


if __name__ == '__main__':
    if sys.stdout is None:
        _redirect_output()
    root = tk.Tk()
    App(root)
    root.mainloop()
