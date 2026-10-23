"""The stash grid: where its cell lines sit inside a region, and which cells hold something to sell.

The cell is a fixed size, 63px at 1080p (84 at 1440p, measured on 2026-10-23 and exactly 63 x
1440/1080), so only where the lines start has to be found. That is a comb over a thin-line
profile, picked over autocorrelation, FFT and Hough lines on 9 hand-annotated stash frames in
_sellable_unsellable_testing/:
  1. a thin-line response per pixel, the pixel minus the mean of its neighbours 2px either side,
     which a 1-2px grid line answers strongly and a broad item edge much less;
  2. the median of that down each column (and along each row), so a column lit only where some
     item has an edge does not count, while a grid line, lit along most of its length, does;
  3. for each offset, the profile's mean on the lines minus its mean halfway between them.

Sellable is the brightest pixel inside the cell, past a margin that keeps the grid lines out.
Tarkov draws what cannot be listed (and what is not ours, like a case's own contents behind the
offer window) dimmed and greyed: across 500 hand-labelled cells the brightest unsellable one
peaked at 95, against 100 and up for sellable cells with anything bright in them. Live, a greyed
Bas-Relief's name peaked at 98 (tests/fixtures/sell/scav_case_empty.png), and at a cutoff of 98
the bot clicked it ten times over, so the line sits at 100, as high as the labels allow. The only
sellable cells under it were the plain middles of a larger item, whose name and outline are in
its other cells, so the item is still found through those.
"""
from collections import namedtuple

import cv2
import numpy as np

CELL_1080 = 63.0  # px, one stash cell on a 1080p screen
SELLABLE_BRIGHTNESS = 100  # brightest pixel in a cell at or above this is sellable, see below
CELL_MARGIN = 0.12  # of the cell, trimmed off each side before reading it, to drop the grid lines

Cell = namedtuple('Cell', 'row col box brightness sellable')  # box is (left, top, width, height)


def _profile(gray, axis):
    """Median thin-line response down each column (axis=0) or along each row (axis=1)."""
    k = np.array([[-0.5, 0, 1, 0, -0.5]], np.float32)
    lines = np.abs(cv2.filter2D(gray, -1, k if axis == 0 else k.T))
    p = np.median(lines, axis=axis)
    return p - cv2.blur(p.reshape(1, -1).astype(np.float32), (31, 1)).ravel()  # detrend


def _sample(p, pos):
    pos = pos[(pos >= 0) & (pos <= len(p) - 1)]
    lo = np.floor(pos).astype(int)
    f = pos - lo
    return p[lo] * (1 - f) + p[np.minimum(lo + 1, len(p) - 1)] * f


def _offset(p, cell, step=0.25):
    """Where the comb of lines `cell` apart best fits the profile, 0 <= offset < cell."""
    best, best_score = 0.0, -np.inf
    k = np.arange(-1, len(p) / cell + 1)
    for o in np.arange(0, cell, step):
        on, off = _sample(p, o + k * cell), _sample(p, o + k * cell + cell / 2)
        score = on.mean() - off.mean() if len(on) and len(off) else -np.inf
        if score > best_score:
            best, best_score = o, score
    return float(best)


def lines(image, cell):
    """(x, y): where the first vertical and horizontal grid lines sit in an RGB/BGR array."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return _offset(_profile(gray, 0), cell), _offset(_profile(gray, 1), cell)


def cells(frame, region, scale):
    """Every cell of the grid in `region` of `frame`, as Cells in screen coords, top row first.

    frame: the whole screen as a BGR array, screen.grab() of the monitor (so frame coords are
    screen coords less its origin; pass a frame whose top left is the screen's).
    region: (left, top, width, height), the grid as sell.py infers it.
    scale: screen height / 1080, find.scale() on a live screen.

    A cell counts when its centre is inside the region, not only when all of it is. The regions
    are drawn short of the grid's edge on purpose (infer_inventory_region pads 30px in from the
    buttons it measures off), so a whole-cell rule dropped the outer column on every side. The
    grid is found in the region grown by half a cell, which is what lets those edge cells be read.
    """
    frame = np.asarray(frame)
    cell = CELL_1080 * scale
    left, top, width, height = region
    pad = round(cell / 2)
    gl, gt = max(0, left - pad), max(0, top - pad)
    gr, gb = min(frame.shape[1], left + width + pad), min(frame.shape[0], top + height + pad)
    crop = frame[gt:gb, gl:gr]
    x0, y0 = lines(crop, cell)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    m = max(2, round(cell * CELL_MARGIN))
    size = round(cell)
    out = []
    for r in range(int((h - y0) // cell)):
        for c in range(int((w - x0) // cell)):
            cl, ct = round(x0 + c * cell), round(y0 + r * cell)
            cx, cy = gl + cl + cell / 2, gt + ct + cell / 2
            if not (left <= cx < left + width and top <= cy < top + height):
                continue
            inner = gray[ct + m:ct + size - m, cl + m:cl + size - m]
            peak = int(inner.max()) if inner.size else 0
            out.append(Cell(r, c, (gl + cl, gt + ct, size, size), peak, peak >= SELLABLE_BRIGHTNESS))
    return out


if __name__ == '__main__':  # the geometry on a drawn grid, no game needed
    scale = 1440 / 1080
    cell = CELL_1080 * scale
    img = np.full((600, 700, 3), 30, np.uint8)
    for k in range(10):  # lines 84px apart starting at 17, 40
        cv2.line(img, (round(17 + k * cell), 0), (round(17 + k * cell), 599), (90, 90, 90), 1)
        cv2.line(img, (0, round(40 + k * cell)), (699, round(40 + k * cell)), (90, 90, 90), 1)
    cv2.putText(img, 'AK', (17 + 20, 40 + 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (240, 240, 240), 2)
    x, y = lines(img, cell)
    assert abs(x - 17) <= 1 and abs(y - 40) <= 1, (x, y)
    # A region drawn 30px inside the grid on the left and top still gets the first cell.
    found = cells(img, (47, 70, 600, 500), scale)
    assert found[0].box[:2] == (17, 40), found[0]
    assert found[0].sellable and not found[1].sellable, found[:2]
    print(f'ok: lines at ({x:.1f}, {y:.1f}), {len(found)} cells, one bright one sellable')
