"""Find the Tarkov window and print its position/size. Run: python tests/find_tarkov_window.py"""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
TITLE = "EscapeFromTarkov"  # ponytail: exact title; pass a substring as argv[1] if BSG renames it


def find(title=TITLE):
    hwnd = user32.FindWindowW(None, title)
    return hwnd or None


def rect(hwnd):
    r = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        raise ctypes.WinError()
    return r.left, r.top, r.right - r.left, r.bottom - r.top


if __name__ == "__main__":
    import sys
    hwnd = find(sys.argv[1] if len(sys.argv) > 1 else TITLE)
    if not hwnd:
        sys.exit("Tarkov window not found (is the game running?)")
    x, y, w, h = rect(hwnd)
    print(f"hwnd={hwnd} pos=({x},{y}) size={w}x{h}")
