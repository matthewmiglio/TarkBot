"""Frozen entry point. Same thing `python -m gui.app` does, but importable by cx_Freeze.

Kept separate from gui/app.py because the frozen main script's __file__ is not a real path,
and gui/app.py derives the repo root from its own __file__.
"""
import tkinter as tk

import frames
import session_log
from gui.app import App

if __name__ == '__main__':
    # Before anything else: frozen windowed there is no console, sys.stdout is None, and the
    # first print() in the selling path would kill the run. See session_log.py for the rest.
    session_log.start()
    frames.start()  # and a screenshot either side of every click, to read beside that log
    root = tk.Tk()
    App(root)
    root.mainloop()
