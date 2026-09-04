"""Measure where each window's title lands when it is jammed in its orientation corner.

The data behind sell.ORIENTATED_OFFSETS and the early-quit in sell._drag_to_corner. For every
window we orientate (offer creation, opened scav case, filter modal) at every corner it is parked
in, this opens it, drags it there with the shipping functions, and then matches EACH reference
crop of its title bar one at a time, recording where that crop's corner-nearest edge sits as an
offset from the screen corner, in 1080p pixels (so the number is the same at any resolution).

Why per crop, not one find(): the crops of one title bar are very different widths (the filter
title runs 92 to 367px), so which one wins the match moves the box. The early-quit keys off the
corner-nearest edge precisely because that edge is the same title-bar edge whichever crop matched;
this is the tool that checks that claim holds, and prints a paste-ready ORIENTATED_OFFSETS plus a
tolerance wide enough to cover the spread across crops.

Drives the real mouse on the live account: opens the flea, an offer, a scav case and the filter
window, and drags them around. Game must be logged in and at the stash/flea. Do not touch the
mouse while it runs. Mr. President runs it; the bot does not run itself.

    python tests/gather_orientation.py

Each window is independent and wrapped: one that will not open (no free offer slot, no scav case
in the stash) is reported skipped and the rest still measure.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
sys.path.insert(0, APP)

import pyautogui  # noqa: E402
import screen  # noqa: E402
from interact import find, sell  # noqa: E402
from sell_bot import FleaSeller  # noqa: E402

# (label, target, opener, [corners to measure]). The opener leaves the window open and parked in
# its home (first) corner; the extra corners are the filtering positions it moves to mid-pass.
# Filters first: its gear sits on the flea board, and the offer and scav windows are drawn over
# that corner, so opening it last found no gear to click.
PLAN = [
    ('filter window', sell.FILTERS_WINDOW_TARGET,
     'filters', [sell.FILTERS_CORNER]),
    ('offer creation', sell.OFFER_TARGET,
     'offer', [sell.OFFER_CORNER, sell.FILTERING_OFFER_CORNER]),
    ('scav case', sell.SCAV_WINDOW_TARGET,
     'scav', [sell.SCAV_CORNER, sell.FILTERING_SCAV_CORNER]),
]


def match_each_crop(target, region):
    """[(crop name, Box or None)] for every reference image of target, matched one at a time."""
    image = screen.grab(region)
    off = (region[0], region[1])
    conf = find.confidence_for(target)
    out = []
    for path in find.images(target):
        try:
            box = pyautogui.locate(find.needle(path), image, confidence=conf)
        except Exception:  # pyscreeze raises ImageNotFoundException on a clean miss
            box = None
        out.append((path.name, find._shift(box, off) if box else None))
    return out


def edge_offset(corner, box):
    """(dx, dy) in 1080p px: the box's top-left minus the screen corner point.

    Top-left, not the corner-nearest edge: the crops of one title share their top-left (only their
    width and height differ), so box.left/box.top is the anchor that agrees across crops.
    """
    cx, cy = sell._corner_point(corner, screen.rect())
    s = find.scale()
    return ((box.left - cx) / s, (box.top - cy) / s)


def measure(label, target, corner, results):
    """Match every crop with the window already at corner; print and record the edge offsets."""
    print(f'\n  {label} at the {corner}:')
    rows = match_each_crop(target, sell.SELLER_REGION)
    offs = []
    for name, box in rows:
        if box is None:
            print(f'    {name[:8]}  no match')
            continue
        dx, dy = edge_offset(corner, box)
        offs.append((dx, dy))
        print(f'    {name[:8]}  box ({int(box.left)},{int(box.top)}) {int(box.width)}x{int(box.height)}'
              f'  edge offset ({dx:+.1f}, {dy:+.1f})')
    if offs:
        results[(target, corner)] = offs


def orientate(which, corner):
    """Drag one already-open window to corner with the shipping orientate function."""
    if which == 'offer':
        return sell.orientate_offer_creation(sell.SELLER_REGION, corner=corner)
    if which == 'scav':
        return sell.orientate_scav_box(sell.SELLER_REGION, corner=corner)
    if which == 'filters':
        return sell.orientate_filters_window(sell.SELLER_REGION, corner=corner)
    raise ValueError(which)


def open_window(seller, which):
    """Open one window, parked in its home corner. True on success."""
    if which == 'offer':
        seller.open_offer_creation()  # opens flea, offer window, parks it bottom left
        return True
    if which == 'scav':
        return sell.open_scav_case(sell.SELLER_REGION) is not None  # opens and parks top left
    if which == 'filters':
        return sell.open_filters(sell.SELLER_REGION)  # opens and parks top left
    raise ValueError(which)


def report(results):
    print('\n' + '=' * 70)
    print('Paste into interact/sell.py ORIENTATED_OFFSETS (offsets are 1080p px):\n')
    print('ORIENTATED_OFFSETS = {')
    worst_spread = 0.0
    for (target, corner), offs in results.items():
        xs = [o[0] for o in offs]
        ys = [o[1] for o in offs]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        spread = max(max(xs) - min(xs), max(ys) - min(ys))
        worst_spread = max(worst_spread, spread)
        print(f"    ({target!r}, {corner!r}): ({mx:.0f}, {my:.0f}),"
              f"  # {len(offs)} crops, spread {spread:.1f}px")
    print('}')
    # tol must cover half the spread across crops (they land either side of the mean) plus a
    # little for the window settling a pixel or two differently each open.
    suggested = math.ceil(worst_spread / 2) + 4
    print(f'\nWidest crop spread: {worst_spread:.1f}px  ->  suggested ORIENTATED_TOL = {suggested}')
    print('If a spread is large, those crops do NOT share an edge when jammed and the early-quit '
          'for that window wants a second look before trusting it.')


def main():
    print('building a seller and recovering to the flea (no jitter)')
    seller = FleaSeller(target_scav_cases=True, scav_chance=1.0)
    sell.SELLER_REGION = seller.region  # module global so the helpers above need no plumbing
    seller._recover()

    results = {}
    for label, target, which, corners in PLAN:
        print(f'\n=== {label} ===')
        try:
            if not open_window(seller, which):
                print(f'  could not open the {label}, skipping')
                continue
        except Exception as e:
            print(f'  opening the {label} failed ({e!r}), skipping')
            continue
        for corner in corners:
            try:
                if orientate(which, corner) is None:
                    print(f'  could not drag the {label} to the {corner}, skipping that corner')
                    continue
                measure(label, target, corner, results)
            except Exception as e:
                print(f'  measuring the {label} at the {corner} failed ({e!r})')
        # leave it in its home corner for the next window to open over
        try:
            orientate(which, corners[0])
        except Exception:
            pass

    if results:
        report(results)
    else:
        print('\nnothing measured: no window opened. Is the flea reachable, with a scav case in '
              'the stash?')


if __name__ == '__main__':
    main()
