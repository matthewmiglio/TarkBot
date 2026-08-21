"""Locate the Tarkov window and our own control panel. Raises WindowError if missing/ambiguous."""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
TITLE = "EscapeFromTarkov"  # ponytail: exact title match; widen to substring if BSG renames it
GUI_TITLE = "Tarkbot"  # what gui/app.py passes to root.title()

# The three ways the control panel and the game can be sitting. Anything that grabs pixels off
# the game has to know: the GUI in front of a fullscreen Tarkov is a hole in every screenshot.
CLEAR = "clear"  # they do not share a pixel
GUI_ON_TOP = "gui_on_top"  # they overlap and the GUI has focus, so the GUI is what is drawn
GAME_ON_TOP = "game_on_top"  # they overlap and the GUI does not have focus


class WindowError(RuntimeError):
    pass


def _handles(title=TITLE):
    found = []
    cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        if buf.value == title and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(cb(visit), 0)
    return found


def handle(title=TITLE):
    """The one Tarkov window. Raises if there are zero or several."""
    hwnds = _handles(title)
    if not hwnds:
        raise WindowError(f"No window titled {title!r} (is the game running?)")
    if len(hwnds) > 1:
        raise WindowError(f"{len(hwnds)} windows titled {title!r}: {hwnds}")
    return hwnds[0]


def gui_handle():
    """Our own control panel's window. Raises WindowError if it is not open."""
    return handle(GUI_TITLE)


def _rect(hwnd):
    r = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        raise ctypes.WinError()
    return r


def position(hwnd=None):
    """(x, y) of the window's top-left corner."""
    r = _rect(hwnd if hwnd is not None else handle())
    return r.left, r.top


def size(hwnd=None):
    """(width, height) including borders. ponytail: window rect, not client rect."""
    r = _rect(hwnd if hwnd is not None else handle())
    return r.right - r.left, r.bottom - r.top


def bounds(hwnd=None):
    """(left, top, right, bottom), the form the overlap maths wants."""
    r = _rect(hwnd if hwnd is not None else handle())
    return r.left, r.top, r.right, r.bottom


def overlaps(a, b):
    """Do two (left, top, right, bottom) rectangles share a pixel. Touching edges do not."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def state(gui, game, gui_has_focus):
    """CLEAR / GUI_ON_TOP / GAME_ON_TOP from two rects and who has focus.

    Split out from overlap_state so the decision can be checked without either window being
    open: tests/test_window_overlap.py.

    A minimised window is at (-32000, -32000) on Windows, which reads as CLEAR on its own with
    no special case, and correctly: a minimised GUI covers nothing.

    ponytail: only the GUI's focus is asked about. Anything else being in front (Explorer, a
    browser) reports GAME_ON_TOP, which is a lie about the game and the truth about the thing
    the caller cares about, that the GUI is not what is drawn there. Ask about the game's hwnd
    too if a caller ever needs the difference.
    """
    if not overlaps(gui, game):
        return CLEAR
    return GUI_ON_TOP if gui_has_focus else GAME_ON_TOP


def overlap_state(gui=None, game=None):
    """The live answer. Pass hwnds to skip the lookups; raises WindowError if either is missing."""
    gui = gui if gui is not None else gui_handle()
    game = game if game is not None else handle()
    return state(bounds(gui), bounds(game), user32.GetForegroundWindow() == gui)


if __name__ == "__main__":
    h = handle()
    print(f"tarkov  hwnd={h} pos={position(h)} size={size(h)}")
    try:
        g = gui_handle()
        print(f"gui     hwnd={g} pos={position(g)} size={size(g)}")
        print(f"state   {overlap_state(g, h)}")
    except WindowError as e:
        print(f"gui     {e}")
