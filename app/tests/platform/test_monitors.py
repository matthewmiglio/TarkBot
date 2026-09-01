"""Does a grab land on the monitor that was picked, on every monitor this machine has.

WHAT LAYER THIS TESTS
    screen.py's monitor selection and pixel grab: monitors(), use(name), rect(), grab(region)
    and the bare whole-monitor grab(), plus interact/find.scale() reading its height off the
    chosen monitor rather than the primary. This is the OS/screen layer the bot photographs the
    game through; nothing here matches a reference crop or touches the game.

WHY IT EXISTS
    pyscreeze only ever photographs the primary monitor, so before screen.py a Tarkov on the
    second screen was invisible however good the region handed to it. A grab that comes back the
    wrong color is a grab of the wrong screen, which is exactly the failure this module exists to
    stop, and it surfaces here rather than as the bot mysteriously finding nothing on the game.

WHAT IT DOES  (NO GAME NEEDED: paints its own tkinter color patches, grabs those)
    For each monitor in turn it use()s that one, asserts rect() and find.scale() follow the pick,
    paints a known-color borderless square in that monitor's top-left corner, and reads the pixels
    back through screen.grab() (middle, whole-rect corner, and a bare whole-monitor grab). Exits
    non-zero on the first monitor that reads back the wrong color, offset, or size.

Run:  python tests/platform/test_monitors.py
"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import screen  # noqa: E402
from interact import find  # noqa: E402
from narrate import log  # noqa: E402

PATCH = 160  # px square of known color to put on each monitor, big enough to see in a picture
COLOUR = '#00ff88'  # nothing in the theme or on a desktop is this, so a match cannot be luck
RGB = (0, 255, 136)


def show_patch(root, monitor):
    """A borderless COLOUR square in that monitor's top left corner. Returns its screen rect."""
    left, top, _, _ = monitor.rect
    root.overrideredirect(True)
    root.geometry(f'{PATCH}x{PATCH}+{left}+{top}')
    root.configure(bg=COLOUR)
    root.attributes('-topmost', True)
    root.update()
    root.after(120, root.quit)  # let the compositor actually paint it before anything is read
    root.mainloop()
    return (left, top, PATCH, PATCH)


if __name__ == '__main__':
    found = screen.monitors()
    log(f'{len(found)} monitor(s), virtual desktop {screen.virtual_rect()}')
    for monitor in found:
        log(f'{monitor.label:22} {monitor.name:14} at {monitor.rect}'
            + ('  primary' if monitor.primary else ''), 1)
    if len(found) == 1:
        log('only one monitor here, so this checks that one and the maths but not the switch')

    for monitor in found:
        screen.use(monitor.name)
        assert screen.rect() == monitor.rect, f'use() did not select {monitor.label}'
        assert find.scale() == monitor.rect[3] / find.REFERENCE_HEIGHT, \
            'reference images scale off the chosen monitor, not the primary'

        root = tk.Tk()
        rect = show_patch(root, monitor)
        middle = screen.grab((rect[0] + PATCH // 2, rect[1] + PATCH // 2, 4, 4))
        corner = screen.grab(rect).getpixel((2, 2))
        root.destroy()

        log(f'{monitor.label}: grabbed {rect}, middle pixel {middle.getpixel((0, 0))}, '
            f'corner pixel {corner}', 1)
        if middle.getpixel((0, 0)) != RGB:
            sys.exit(f'FAILED: the patch on {monitor.label} at {rect} read back as '
                     f'{middle.getpixel((0, 0))}, not {RGB}. That grab came off another screen.')
        if corner != RGB:
            sys.exit(f'FAILED: a whole-rect grab of {monitor.label} read {corner} at its corner, '
                     f'so the crop is offset even though the middle landed.')

        # The bare grab is the whole monitor, which is what a frame capture saves.
        whole = screen.grab()
        if whole.size != monitor.rect[2:]:
            sys.exit(f'FAILED: a bare grab of {monitor.label} came back {whole.size}, '
                     f'not {monitor.rect[2:]}')

    screen.use(screen.AUTO)
    log(f'PASSED: {len(found)} monitor(s), each one grabbed its own pixels')
