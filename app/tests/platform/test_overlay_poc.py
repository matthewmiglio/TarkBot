"""Can a see-through, always-on-top overlay let clicks through and stay out of the bot's screenshots.

WHAT LAYER THIS TESTS
    The proof of concept for a click visualiser: a borderless tkinter window over the monitor
    with a magenta background made invisible (-transparentcolor), the WS_EX_TRANSPARENT style so
    the mouse goes through even its painted pixels, and SetWindowDisplayAffinity(EXCLUDEFROMCAPTURE)
    so screen captures skip it. The capture side is checked through the bot's own three grabs:
    screen.grab, screen.fast_grab and pyautogui.screenshot.

WHAT IT DOES  (NO GAME NEEDED: paints its own target window, clicks only that)
    Puts a green target window in the middle of the primary monitor and the overlay over the whole
    monitor, with a red square painted on the overlay right over the target. Then:
      1. control: a grab of the square reads red, so the overlay really is on screen
      2. control: a click on the square does NOT reach the target, so the overlay really is in the way
      3. click-through on: the same click reaches the target
      4. capture exclusion on: all three grabs of the square read the target's green underneath
      5. the app's own overlay.Overlay has both settings on, and marks where a real click landed
    Steps 1 and 2 are there so 3 and 4 cannot pass by accident. It moves the real mouse (and puts
    it back), and steals focus to the target window for a moment.

    After a pass the overlay (still click-through and hidden from capture) demos the chosen click
    marker on fake clicks at random spots: a dashed arrow from the last click, brackets closing in
    on the new one, and its screen coordinates beside it.

Run:  python tests/platform/test_overlay_poc.py            then the demo runs 20s
      python tests/platform/test_overlay_poc.py --hold 60
      python tests/platform/test_overlay_poc.py --hold 0   test only, no demo
"""
import argparse
import ctypes
import ctypes.wintypes
import os
import random
import sys
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402
import overlay  # noqa: E402
import screen  # noqa: E402

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
RED, GREEN = (255, 0, 0), (0, 200, 0)
SQUARE = 120
PERIOD = 1.2  # seconds between fake clicks in the demo

parser = argparse.ArgumentParser()
parser.add_argument('--hold', type=float, default=20, help='seconds to demo the click marker')
args = parser.parse_args()


def settle(root, seconds=0.25):
    """Pump tk for a moment, so the compositor paints and queued clicks get handled."""
    end = time.time() + seconds
    while time.time() < end:
        root.update()
        time.sleep(0.01)


def top_hwnd(window):
    """The real top-level handle; winfo_id is tk's inner child window."""
    return user32.GetParent(window.winfo_id())


def fail(message):
    sys.exit(f'FAILED: {message}')


left, top, width, height = screen.monitors()[0].rect  # the primary
cx, cy = left + width // 2, top + height // 2

root = tk.Tk()  # the target, a plain window that counts the clicks it gets
root.overrideredirect(True)
root.geometry(f'300x300+{cx - 150}+{cy - 150}')
root.configure(bg='#00c800')
root.attributes('-topmost', True)  # over a fullscreen game too; the overlays go on above it
clicks = []
root.bind('<Button-1>', lambda e: clicks.append((e.x_root, e.y_root)))

poc = tk.Toplevel(root)  # a bare overlay, so steps 1 and 2 can run before the settings go on
poc.overrideredirect(True)
poc.geometry(f'{width}x{height}+{left}+{top}')
poc.attributes('-topmost', True)
poc.attributes('-transparentcolor', overlay.KEY)
canvas = tk.Canvas(poc, bg=overlay.KEY, highlightthickness=0)
canvas.pack(fill='both', expand=True)
half = SQUARE // 2
canvas.create_rectangle(width // 2 - half, height // 2 - half, width // 2 + half,
                        height // 2 + half, fill='#ff0000', outline='')
canvas.create_text(width // 2, height // 2 - half - 20, text='overlay PoC', fill='#ff0000',
                   font=('Segoe UI', 16, 'bold'))
settle(root, 0.1)
poc.lift()  # both are topmost, so which is on top is whichever was raised last
settle(root, 0.5)
hwnd = top_hwnd(poc)
probe = (cx - 2, cy - 2, 4, 4)
mouse_was = pyautogui.position()


def grabs():
    """The centre pixel of the square through each of the bot's three capture paths."""
    return {'screen.grab': screen.grab(probe).convert('RGB').getpixel((2, 2)),
            'screen.fast_grab': screen.fast_grab(probe).convert('RGB').getpixel((2, 2)),
            'pyautogui.screenshot': pyautogui.screenshot(region=probe).convert('RGB').getpixel((2, 2))}


def ours_at(x, y):
    """True if the window the mouse would hit at (x, y) is one of this script's."""
    user32.WindowFromPoint.restype = user32.GetAncestor.restype = ctypes.c_void_p
    user32.WindowFromPoint.argtypes = [ctypes.wintypes.POINT]
    hit = user32.GetAncestor(user32.WindowFromPoint(ctypes.wintypes.POINT(x, y)), 2)
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(ctypes.c_void_p(hit), ctypes.byref(pid))
    return pid.value == os.getpid()


def click_square():
    # Through a click-through overlay the click lands on whatever is under it. If that is not the
    # target (a fullscreen game came up over it), refuse rather than click someone else's window.
    if not ours_at(cx, cy):
        fail(f'something else is on top at {(cx, cy)}, so the test will not click there')
    clicks.clear()
    pyautogui.click(cx, cy)
    settle(root)
    return bool(clicks)


def demo(app_overlay, seconds):
    """Fake clicks at random spots, fed to the real overlay's queue, one every PERIOD."""
    end = time.time() + seconds
    while time.time() < end:
        overlay._clicks.put((left + random.randint(160, width - 160),
                             top + random.randint(160, height - 160)))
        settle(root, min(PERIOD, end - time.time()))


try:
    seen = grabs()
    print(f'1. overlay up, no exclusion: {seen}')
    if seen['screen.grab'] != RED:
        fail(f'screen.grab read {seen["screen.grab"]} on the red square, so the overlay never '
             'painted and nothing after this would mean anything')

    got = click_square()
    print(f'2. click on the square, click-through off: target got it = {got}')
    if got:
        fail('the target got the click through a plain overlay, so step 3 would prove nothing')

    overlay.click_through(hwnd)
    settle(root)
    got = click_square()
    print(f'3. click on the square, click-through on:  target got it = {got} {clicks}')
    if not got:
        fail('WS_EX_TRANSPARENT did not pass the click through to the window underneath')

    if not overlay.hide_from_capture(hwnd):
        fail(f'SetWindowDisplayAffinity refused, error {ctypes.GetLastError()} (needs Windows 10 2004+)')
    settle(root, 0.5)
    seen = grabs()
    print(f'4. capture exclusion on: {seen}')
    wrong = {name: px for name, px in seen.items() if px != GREEN}
    if wrong:
        fail(f'these grabs did not see the green target under the overlay: {wrong}')
    if not user32.IsWindowVisible(hwnd):
        fail('the overlay is no longer a visible window')
    poc.destroy()

    # 5. The app's own overlay, as the GUI builds it: same two settings, and its click hook.
    screen.use(screen.monitors()[0].name)
    app_overlay = overlay.Overlay(root)
    affinity = ctypes.c_uint()
    user32.GetWindowDisplayAffinity(app_overlay.hwnd, ctypes.byref(affinity))
    through = bool(user32.GetWindowLongW(app_overlay.hwnd, GWL_EXSTYLE) & overlay.WS_EX_TRANSPARENT)
    got = click_square()
    print(f'5. app overlay: hidden from capture = {affinity.value == overlay.WDA_EXCLUDEFROMCAPTURE}, '
          f'click-through = {through}, target got the click = {got}, marked at {app_overlay.point}')
    if affinity.value != overlay.WDA_EXCLUDEFROMCAPTURE or not through:
        fail('overlay.Overlay did not put both settings on its window')
    if not got:
        fail('a click did not get through overlay.Overlay')
    if app_overlay.point != (cx, cy):
        fail(f'the click hook marked {app_overlay.point}, not where it clicked, {(cx, cy)}')

    print('PASSED: clicks go through the overlay and all three grabs ignore it.')
    if args.hold:
        print(f'Demoing the click marker for {args.hold:g}s.')
        pyautogui.moveTo(*mouse_was)
        root.geometry('1x1+-100+-100')  # the green target is done; get it out of the way
        demo(app_overlay, args.hold)
finally:
    pyautogui.moveTo(*mouse_was)
    root.destroy()
