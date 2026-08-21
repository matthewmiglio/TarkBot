"""Locate the Tarkov window. Raises WindowError if missing or ambiguous."""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
TITLE = "EscapeFromTarkov"  # ponytail: exact title match; widen to substring if BSG renames it


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


if __name__ == "__main__":
    h = handle()
    print(f"hwnd={h} pos={position(h)} size={size(h)}")
