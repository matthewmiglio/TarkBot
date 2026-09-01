"""Open a Tarkov screenshot in matplotlib with a grid, coordinates and pixel colors.

WHAT LAYER THIS IS
    Not a pass/fail test but an authoring utility for the screen layer: it opens an image (a live
    screen.grab of the game window, or a saved png) in matplotlib with a 100px grid, and a
    format_coord readout mapping every hovered pixel to its window coords, the screen coords to
    click there, and its rgb/hex color. It sits over screen.py (importing it patches
    pyautogui.screenshot onto the right monitor) and window.py; it reads no interact/ code.

HOW IT IS USED
    This is how reference-image crops are measured: hover a button, zoom with the magnifier, read
    the corners off the grid, and you have the box to crop at 1080p. It is a tool, so it exits only
    when the matplotlib window is closed rather than reporting a result.

NEEDS THE LIVE GAME only when run with no argument (it grabs the live Tarkov window); given a
    saved image path it needs no game.

Run:  python tests/platform/view_screenshot.py            (grab the live Tarkov window)
      python tests/platform/view_screenshot.py shot.png   (open a saved image instead)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402
from PIL import Image  # noqa: E402

import screen  # noqa: E402,F401  importing it patches pyautogui.screenshot onto the right monitor
import window  # noqa: E402

GRID = 100  # px between grid lines


def show(img, origin=(0, 0), title=''):
    """Display img with a pixel grid. origin is its top-left in screen coords."""
    a = np.asarray(img.convert('RGB'))
    h, w = a.shape[:2]
    fig, ax = plt.subplots()
    fig.canvas.manager.set_window_title(title or 'screenshot')
    ax.imshow(a)
    ax.set_xticks(range(0, w, GRID))
    ax.set_yticks(range(0, h, GRID))
    ax.grid(color='lime', alpha=0.35, lw=0.5)
    ax.tick_params(labelsize=6)
    plt.setp(ax.get_xticklabels(), rotation=90)
    ax.set_title(f'{title}  {w}x{h}')

    def coord(x, y):
        c, r = int(x), int(y)
        if not (0 <= c < w and 0 <= r < h):
            return ''
        rgb = tuple(int(v) for v in a[r, c])
        return (f'image ({c}, {r})   screen ({c + origin[0]}, {r + origin[1]})   '
                f'rgb {rgb}  #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}')

    ax.format_coord = coord  # ponytail: replaces the default readout, which has no screen coords
    plt.show()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        show(Image.open(path), title=path.name)
    else:
        hwnd = window.handle()
        region = window.position(hwnd) + window.size(hwnd)
        print(f'capturing window {region}')
        show(pyautogui.screenshot(region=region), origin=region[:2], title='Tarkov')
