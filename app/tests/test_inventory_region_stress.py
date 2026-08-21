"""Shove the offer creation window around at random until an inventory edge button stops matching.

Run:  python tests/test_inventory_region_stress.py [rounds]

One round drags the offer creation window to a random point, then looks for all three buttons
infer_inventory_region needs. First round that misses one prints which, writes
tests/output/inventory_region_stress.png of that screen, and exits 1. Needs the flea open with
the offer creation window on screen, since that is the thing being dragged.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'
ROUNDS = 50
MARGIN = 200  # px kept clear of every screen edge, so the dragged window lands somewhere usable


def drag_somewhere_random(region):
    """Drag the offer creation window to a random point. Returns (grabbed, dropped) or None."""
    point = find.find_center(sell.OFFER_TARGET, region)
    if not point:
        return None
    width, height = pyautogui.size()
    destination = (random.randint(MARGIN, width - MARGIN), random.randint(MARGIN, height - MARGIN))
    failsafe = pyautogui.FAILSAFE  # the drag can pass through a corner; see sell._drag_to_corner
    pyautogui.FAILSAFE = False
    try:
        pyautogui.moveTo(*point)
        pyautogui.dragTo(*destination, duration=sell.DRAG_SECONDS, button='left')
        pyautogui.moveTo(width // 2, height // 2)
    finally:
        pyautogui.FAILSAFE = failsafe
    return point, destination


if __name__ == '__main__':
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else ROUNDS
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    print(f'searching window {region}, {rounds} rounds')

    for i in range(1, rounds + 1):
        dragged = drag_somewhere_random(region)
        if not dragged:
            sys.exit(f'round {i}: {sell.OFFER_TARGET} not on screen to drag, is the flea open?')
        print(f'round {i}: dragged from {dragged[0]} to {dragged[1]}')

        missing = [name for name in sell.EDGES if find.find(name, region) is None]
        if missing:
            OUT.mkdir(exist_ok=True)
            path = OUT / 'inventory_region_stress.png'
            pyautogui.screenshot(region=region).save(path)
            print(f'  NOT FOUND: {", ".join(missing)}')
            sys.exit(f'round {i}: lost {len(missing)} of {len(sell.EDGES)} edge buttons, wrote {path}')
        print(f'  all {len(sell.EDGES)} edge buttons found')

    print(f'{rounds} rounds, never lost a button')
