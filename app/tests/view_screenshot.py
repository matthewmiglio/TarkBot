"""Open a Tarkov screenshot in matplotlib with a grid, coordinates and pixel colours.

Run:  python tests/view_screenshot.py            (grab the live Tarkov window)
      python tests/view_screenshot.py shot.png   (open a saved image instead)

Hover anywhere and the status bar shows that pixel's window coords, the screen
coords to click, and its colour. Use the magnifier to zoom in on a button, then
read the corners off the grid to know what to crop as a reference image.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyautogui  # noqa: E402
from PIL import Image  # noqa: E402

import tarkov_window  # noqa: E402

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
        hwnd = tarkov_window.handle()
        region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
        print(f'capturing window {region}')
        show(pyautogui.screenshot(region=region), origin=region[:2], title='Tarkov')
