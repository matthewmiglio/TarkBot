"""Drag the offer creation window round all four corners and time each leg.

App layer under test: interact/sell.py, sell.orientate_offer_creation (and _drag_to_corner under
it). Starting from the bottom left, it drags the window to the bottom right, top left, top right
and back to the bottom left, and prints how long each leg took, split into template matching,
sleeping (the drag itself, pyautogui's pause, settles) and the rest, plus whether the window
actually reached that corner. Non-zero exit if any leg lost the window, or did not arrive at a
corner that has a measured parking spot (ORIENTATED_OFFSETS) for this window.

Needs the live game: the flea open with the offer creation window up, parked bottom left. It
drags the real mouse, so do not touch it while it runs.

Frame capture is on, the way production runs it (gui/app.py, cli.py and main.py all call
frames.start()), into a scratch folder so the real frames pool is left alone. Every drag input
takes a full-screen frame either side of it, so this is the shipping cost, frames included.

--scav runs the same tour on the opened scav case window (sell.orientate_scav_box) instead, from
the same bottom-left start.

Run:  python tests/flea_sell/test_orientate_offer_tour.py
      python tests/flea_sell/test_orientate_offer_tour.py --scav
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import frames  # noqa: E402
import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the drags land nowhere useful otherwise
LEGS = ('bottom right', 'top left', 'top right', 'bottom left')

# perf_counter, not monotonic: monotonic ticks every 15.6ms on Windows.
COST = {'find': 0.0, 'find_n': 0, 'sleep': 0.0, 'frame': 0.0, 'frame_n': 0}


def _tally(kind, fn):
    def wrapped(*a, **k):
        t = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            COST[kind] += time.perf_counter() - t
            if kind != 'sleep':
                COST[f'{kind}_n'] += 1
    return wrapped


if __name__ == '__main__':
    # --scav: the same tour for the opened scav case window, through orientate_scav_box.
    if '--scav' in sys.argv:
        target, orientate, name = sell.SCAV_WINDOW_TARGET, sell.orientate_scav_box, 'scav'
    else:
        target, orientate, name = sell.OFFER_TARGET, sell.orientate_offer_creation, 'offer'
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    if not find.find(target, region):
        sys.exit(f'{target} not on screen: open the {name} window first, parked bottom left')

    for n in range(DELAY, 0, -1):
        print(f'starting in {n}...')
        time.sleep(1)

    frames.start(OUT / f'orientate_{name}_tour_frames', keep=60)
    # Only the leaf finds, after the countdown so its own sleeps are not counted. pyautogui's
    # drag tween and PAUSE both go through time.sleep, so they land in 'sleep' too.
    find.find = _tally('find', find.find)
    time.sleep = _tally('sleep', time.sleep)
    frames.capture = _tally('frame', frames.capture)

    rows, failed = [], []
    for corner in LEGS:
        before = dict(COST)
        t = time.perf_counter()
        point = orientate(region, corner)
        wall = time.perf_counter() - t
        box = find.find(target, region)  # outside the timing: the check, not the leg
        # A corner with no ORIENTATED_OFFSETS entry for this window has nothing to check against,
        # so it says where the title landed instead of guessing (and the drag runs all
        # DRAG_REPEATS passes there, since nothing can tell it it has arrived).
        if not box:
            arrived = 'LOST'
        elif (target, corner) in sell.ORIENTATED_OFFSETS:
            arrived = 'yes' if sell.is_window_orientated(target, corner, box) else 'NO'
        else:
            arrived = f'unmeasured, title at ({int(box.left)}, {int(box.top)})'
        spent = {k: COST[k] - before[k] for k in COST}
        rows.append((corner, wall, spent, arrived))
        if not point or arrived in ('LOST', 'NO'):
            failed.append(corner)

    print(f'\n{"leg":<26} {"total":>6}  {"find":>12}  {"sleep":>6}  {"frames":>12}  {"rest":>6}  arrived')
    for corner, wall, s, arrived in rows:
        rest = wall - s['find'] - s['sleep'] - s['frame']
        print(f'{"-> " + corner:<26} {wall:5.2f}s  {s["find"]:5.2f}s ({s["find_n"]:2d})  '
              f'{s["sleep"]:5.2f}s  {s["frame"]:5.2f}s ({s["frame_n"]:2d})  {rest:5.2f}s  '
              f'{arrived}')
    print(f'{"all four":<26} {sum(r[1] for r in rows):5.2f}s')
    frames.flush()

    if failed:
        sys.exit(f'FAILED: the window did not reach {failed}')
    print(f'ok, the {name} window went round all four corners and is back bottom left')
