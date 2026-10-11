"""A see-through window over the game that marks every click the bot makes, for watching a run.

Borderless and always on top, over the working monitor. Three Windows settings make it safe to
leave over the game while the bot plays it:
    -transparentcolor     the KEY background is never drawn, so only the marks show
    WS_EX_TRANSPARENT     the mouse goes straight through it, the bot's clicks and yours alike
    EXCLUDEFROMCAPTURE    screenshots skip it, so the bot's matching, the frames and crash
                          reports all see the game as if it were not there (Windows 10 2004+)
tests/platform/test_overlay_poc.py proves all three on a real screen.

Each mark is a dashed arrow from the last click, brackets closing in on the new one, and its
screen coordinates beside it. pyautogui's button functions are wrapped in place, as frames.py
wraps them, and the wrapper only drops where the mouse landed onto a queue: the bot thread never
waits on tk. The tk thread polls that queue and draws.

ponytail: GUI only, a Toplevel on the app's root. cli.py has no tk root; give the overlay its own
in a thread here the day a headless run wants watching.

Self-check, no screen needed:  python -m overlay
"""
import ctypes
import queue
import time
import tkinter as tk

import pyautogui

import screen
from narrate import log

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x80000, 0x20
WDA_EXCLUDEFROMCAPTURE = 0x11
KEY = '#ff00ff'  # the background colour, made invisible; nothing in a mark may use it
COLOUR = '#00ffff'
LIFE = 1.2  # seconds a mark animates for: the arrow draws in over the first third
IDLE = 8  # seconds without a click before the last mark is cleared away
POLL_MS = 30
# The pyautogui calls that press a button. dragTo is marked where the drag ends.
WATCHED = ('click', 'doubleClick', 'tripleClick', 'rightClick', 'middleClick', 'mouseDown',
           'dragTo')

_clicks = queue.Queue()  # (x, y) screen points, put by the bot thread, taken by tk's
# True while a wrapped call is in flight: doubleClick and rightClick are written in terms of the
# module's own click(), which is wrapped too, and one press should leave one mark.
# ponytail: one flag, not threading.local, because only ever one bot thread clicks at a time.
_busy = False


def click_through(hwnd):
    """Let every click on `hwnd` fall through to whatever is under it."""
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)


def hide_from_capture(hwnd):
    """Keep `hwnd` out of every screenshot while still drawing it on screen. False if refused."""
    return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE))


def marker(c, prev, point, t, origin):
    """One frame of a click mark on canvas `c` at `point`, arriving from `prev` (None for the
    first). Both are canvas coordinates; `origin` is the canvas's screen position, for the label.
    t runs 0 to 1 over the mark's life. Tk has no per-item transparency, so nothing fades: the
    mark holds at t=1 until the next one."""
    x, y = point
    if prev:
        grow = min(1, t * 3)
        tip = prev[0] + (x - prev[0]) * grow, prev[1] + (y - prev[1]) * grow
        c.create_line(*prev, *tip, fill=COLOUR, width=2, arrow='last', dash=(6, 4), tags='g')
    s, k = 40 - 20 * min(1, t * 2), 10  # closes in on the point, then holds
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        bx, by = x + dx * s, y + dy * s
        c.create_line(bx - dx * k, by, bx, by, bx, by - dy * k, fill=COLOUR, width=3, tags='g')
    c.create_text(x + 26, y + 26, anchor='nw', fill=COLOUR, font=('Consolas', 11),
                  text=f'({x + origin[0]:.0f}, {y + origin[1]:.0f})', tags='g')


def _wrap(func):
    """`func`, reporting where the mouse is once it returns. Nested watched calls pass through."""
    def marked(*args, **kwargs):
        global _busy
        if _busy:
            return func(*args, **kwargs)
        _busy = True
        try:
            return func(*args, **kwargs)
        finally:
            _busy = False
            _clicks.put(tuple(pyautogui.position()))
    marked._marked = True
    # Carried over so frames.watch(), if it runs again, still sees its own wrapper underneath
    # and does not add a second one, which would take every frame twice.
    marked._framed = getattr(func, '_framed', False)
    return marked


def watch(module=pyautogui, names=WATCHED):
    """Wrap `module`'s button functions so each press is queued for marking. Idempotent."""
    for name in names:
        func = getattr(module, name, None)
        if func is not None and not getattr(func, '_marked', False):
            setattr(module, name, _wrap(func))


class Overlay:
    """The window, on `root`'s tk thread. Build it once; it lives as long as root does."""

    def __init__(self, root):
        self.root = root
        self.rect = None
        self.prev = self.point = None
        self.at = 0.0  # monotonic time of the newest click
        self.window = tk.Toplevel(root)
        # Not 'Tarkbot': window.gui_handle() finds the control panel by that exact title.
        self.window.title('Tarkbot click overlay')
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-transparentcolor', KEY)
        self.canvas = tk.Canvas(self.window, bg=KEY, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self._fit()
        self.window.update()  # the real top-level handle only exists once it is mapped
        self.window.lift()  # among topmost windows, the one raised last is on top
        self.hwnd = user32.GetParent(self.window.winfo_id())  # winfo_id is tk's inner child
        click_through(self.hwnd)
        if not hide_from_capture(self.hwnd):
            # Shown anyway, the marks would sit in the bot's own screenshots and break its matches.
            log('click overlay off: this Windows cannot keep a window out of screenshots')
            self.window.destroy()
            return
        watch()
        log('click overlay on')
        self._poll()

    def _fit(self):
        """Cover the working monitor, which the MONITOR dropdown can change at any time."""
        rect = screen.rect()
        if rect != self.rect:
            self.rect = rect
            left, top, width, height = rect
            self.window.geometry(f'{width}x{height}+{left}+{top}')

    def _poll(self):
        fresh = False
        while not _clicks.empty():
            self.prev, self.point = self.point, _clicks.get_nowait()
            self.at, fresh = time.monotonic(), True
        if fresh:
            self._fit()
        age = time.monotonic() - self.at
        if self.point and age > IDLE:
            self.canvas.delete('g')
            self.prev = self.point = None
        elif self.point and (fresh or age < LIFE + 0.1):  # animating; afterwards it just holds
            left, top = self.rect[:2]
            local = lambda p: p and (p[0] - left, p[1] - top)  # noqa: E731
            self.canvas.delete('g')
            marker(self.canvas, local(self.prev), local(self.point), min(1, age / LIFE),
                   (left, top))
        self.root.after(POLL_MS, self._poll)


if __name__ == '__main__':
    calls = []

    class _Fake:
        def click(self, *args):
            calls.append(args)

        def doubleClick(self):
            fake.click()  # the module's own click, wrapper and all, as pyautogui's is
            fake.click()

    fake = _Fake()
    watch(fake, ('click', 'doubleClick'))
    watch(fake, ('click', 'doubleClick'))  # a second watch must not double wrap
    fake.click(7, 9)
    assert calls == [(7, 9)], f'the real click still ran with its arguments, {calls}'
    assert _clicks.qsize() == 1, 'one click, one mark'
    _clicks.get_nowait()
    fake.doubleClick()
    assert len(calls) == 3 and _clicks.qsize() == 1, 'a double click is one mark, not three'
    _clicks.get_nowait()

    def framed():
        pass
    framed._framed = True
    assert _wrap(framed)._framed, 'frames.watch() still sees its wrapper under ours'
    print('ok')
