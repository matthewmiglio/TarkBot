"""Switching tabs stops the mode being left, and a disabled tab cannot be switched to.

Run:  python tests/test_tab_switch.py

No game needed. A stand-in runner takes the place of a real bot: a thread that sits on an event
until stop() sets it, which is the same contract FleaSeller and HideoutGym both keep. Exits
non-zero if a switch leaves that thread running, because a window showing one mode while
another is still clicking is the thing this is here to prevent.
"""
import sys
import threading
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gui import app as gui_app  # noqa: E402  the module, to reach DISABLED_TABS
from gui.app import App  # noqa: E402


class FakeRunner:
    """Blocks until stop(), like a real pass sitting in one of sell.py's waits."""

    def __init__(self):
        self.event = threading.Event()
        self.stopped = False

    def start(self):
        self.event.wait(30)  # a ceiling, so a broken stop fails the run instead of hanging it

    def stop(self):
        self.stopped = True
        self.event.set()


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.update()

    if 'gym' in gui_app.DISABLED_TABS:
        print('gym is in DISABLED_TABS, so checking the refusal first')
        app._show_tab('gym')
        if app.tab == 'gym':
            sys.exit('FAILED: switched to a disabled tab')
        print(f'ok, still on {app.tab!r}')

    gui_app.DISABLED_TABS = set()  # so the switch itself can be exercised
    for key, _, _ in gui_app.TABS:
        app.tabs[key].config(True)

    # Whichever tab the GUI did not open on. Not hardcoded to 'gym': the tab it opens on is
    # whichever one was last used, so once gym mode became selectable this test started
    # switching to the tab it was already on, which stops nothing and proves nothing.
    target = next(key for key, _, _ in gui_app.TABS if key != app.tab)
    origin = app.tab

    runner = FakeRunner()
    app.bot = runner
    app.thread = threading.Thread(target=runner.start, daemon=True)
    app.thread.start()
    root.update()
    if not app.thread.is_alive():
        sys.exit('FAILED: the stand-in runner never started, so this proves nothing')
    print(f'runner alive on the {app.tab!r} tab, switching to {target!r}')

    app._show_tab(target)
    root.update()

    if not runner.stopped:
        sys.exit('FAILED: switching tabs did not ask the running mode to stop')
    if app.thread.is_alive():
        sys.exit('FAILED: switched away while the old mode was still running')
    if app.tab != target:
        sys.exit(f'FAILED: the switch did not happen, still on {app.tab!r}')
    print(f'ok, runner stopped and the tab is {app.tab!r}')

    # A switch with nothing running is still just a switch, and must not trip over a dead thread.
    app._show_tab(origin)
    if app.tab != origin:
        sys.exit(f'FAILED: switching back with nothing running left it on {app.tab!r}')

    root.destroy()
    print('ok')
