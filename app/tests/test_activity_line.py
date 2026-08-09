"""The footer's activity line: does the bot's last narrated line land inside the window.

Run:  python tests/test_activity_line.py

No game needed, but it does open the GUI for a moment. Checks the three ways this can go
wrong: the line showing something other than the newest log line, the text sitting outside the
window or on top of the buttons, and a long line running off the right edge instead of being
trimmed. Exits non-zero on the first one that fails.
"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import narrate  # noqa: E402
from gui import theme  # noqa: E402
from gui.app import PAD, App, one_line  # noqa: E402

BUTTON_BOTTOM = theme.FOOTER_RULE + 34 + 17  # the START/STOP plates end here


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    # After the window is built, not before: opening it narrates too (which monitor it settled
    # on, for one), and the whole point here is that the footer shows the *newest* line.
    narrate.log('reading the suggested price', 1)
    root.update()
    app.tick()
    root.update()

    text = app.canvas.itemcget(app.activity, 'text')
    left, top, right, bottom = app.canvas.bbox(app.activity)
    print(f'showing {text!r}')
    print(f'at {(left, top, right, bottom)} in a {theme.WINDOW} window')
    if not text.endswith('reading the suggested price'):
        sys.exit(f'the footer is not showing the newest log line, it has {text!r}')
    if bottom > theme.WINDOW[1]:
        sys.exit(f'the line runs {bottom - theme.WINDOW[1]}px past the bottom of the window')
    if top <= BUTTON_BOTTOM:
        sys.exit(f'the line starts at {top}, on top of the buttons that end at {BUTTON_BOTTOM}')

    narrate.log('x' * 400)  # nothing logs this much, but a traceback line gets close
    app.tick()
    root.update()
    right = app.canvas.bbox(app.activity)[2]
    print(f'a 400 character line trims to {right}px, margin is at {theme.WINDOW[0] - PAD}')
    if right > theme.WINDOW[0] - PAD + 1:  # +1: bbox rounds a pixel out
        sys.exit(f'a long line reaches {right}, past the {theme.WINDOW[0] - PAD} margin')

    # A traceback is the one message with newlines in it, and a canvas draws every one of them.
    if '\n' in one_line('first\nsecond\nthird', app.fonts['small'], 10_000):
        sys.exit('a multi-line message must be cut down to its first line')

    root.destroy()
    print('ok')
