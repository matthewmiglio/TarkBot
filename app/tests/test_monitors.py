"""Does a grab land on the monitor that was picked, on every monitor this machine has.

Run:  python tests/test_monitors.py

No game needed. For each monitor in turn it selects that one, puts a window of a known colour
in its top left corner, and reads those pixels back through the same path the bot uses. A grab
that comes back the wrong colour is a grab of the wrong screen, which is the failure this whole
module exists to stop: pyscreeze only ever photographs the primary monitor, so before screen.py
a Tarkov on the second one was invisible no matter what region it was handed.

Exits non-zero on the first monitor that reads back wrong.
"""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import screen  # noqa: E402
from interact import find  # noqa: E402
from narrate import log  # noqa: E402

PATCH = 160  # px square of known colour to put on each monitor, big enough to see in a picture
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
