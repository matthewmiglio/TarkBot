"""The one run button says what it will do, and F5 does the same thing the button does.

Run:  python tests/test_run_button.py

No game needed. A stand-in runner takes the place of a real bot, the same one test_tab_switch
uses: a thread that blocks until stop() is called. What this checks is the state machine behind
the button, since that is the part that can strand it: an amber 'Stopping...' that never goes
back to green is a window with no way to start the bot again short of restarting it.

Exits non-zero if a state does not follow, or if the label and the color disagree.
"""
import sys
import threading
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gui import app as gui_app  # noqa: E402
from gui import theme  # noqa: E402
from gui.app import App  # noqa: E402


class FakeRunner:
    """Blocks until stop(), like a real pass sitting in one of sell.py's waits."""

    def __init__(self):
        self.event = threading.Event()

    def start(self):
        self.event.wait(30)  # a ceiling, so a broken stop fails the run instead of hanging it

    def stop(self):
        self.event.set()


def shown(app):
    """What is actually painted on the button: (label, face color, pressable)."""
    return (app.canvas.itemcget(app.run_plate.label, 'text'),
            app.canvas.itemcget(app.run_plate.rect, 'fill'),
            app.run_plate.enabled)


def expect(app, state, why):
    if app.run_state != state:
        sys.exit(f'FAILED: {why}, but the button is {app.run_state!r} not {state!r}')
    label, color, pressable = shown(app)
    if (label, color, pressable) != gui_app.RUN_STATES[state]:
        sys.exit(f'FAILED: {state!r} is drawn as {(label, color, pressable)}, '
                 f'not {gui_app.RUN_STATES[state]}')
    print(f'  ok  {why}: {label!r}, {color}, {"pressable" if pressable else "not pressable"}')


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.update()

    expect(app, 'start', 'a fresh window is stopped')
    if len({color for _, color, _ in gui_app.RUN_STATES.values()}) != len(gui_app.RUN_STATES):
        sys.exit('FAILED: two states share a color, so the color says nothing')

    # Press it. The bot is faked in afterwards, because start() would go looking for Tarkov.
    runner = FakeRunner()
    app.bot = runner
    app.thread = threading.Thread(target=runner.start, daemon=True)
    app.thread.start()
    app._set_run('stop')
    root.update()
    expect(app, 'stop', 'a running bot offers to stop')

    # F5 and the button are the same call, so pressing either while running asks it to stop and
    # leaves the button amber until the thread actually comes back.
    app.toggle()
    root.update()
    expect(app, 'stopping', 'the ask is with the bot')
    if not runner.event.is_set():
        sys.exit('FAILED: the toggle did not reach the bot')

    # Pressing again while it is unwinding must be a no-op rather than a second start.
    app.toggle()
    expect(app, 'stopping', 'a second press changes nothing')

    app.thread.join(timeout=5)
    app.tick()  # what normally clears it, once a second
    root.update()
    expect(app, 'start', 'the thread came back, so it offers to start again')

    # Stop with nothing running at all, which is what the X button and a tab switch both do.
    # This is the one that used to strand it amber, since tick() only clears a thread it saw die.
    app.bot = None
    app.stop()
    expect(app, 'start', 'stopping nothing leaves it startable')

    # And the countdown is cancellable: the button is live through it, not only once the bot is.
    app.pending = root.after(10_000, lambda: None)
    app._set_run('stop')
    app.toggle()
    if app.pending is not None:
        sys.exit('FAILED: the countdown survived a stop')
    expect(app, 'start', 'a cancelled countdown is back to stopped')

    if theme.lighter(theme.RUNNING) == theme.RUNNING:
        sys.exit('FAILED: the hover face is the same color as the rest, so hover does nothing')

    root.destroy()
    print('ok')
