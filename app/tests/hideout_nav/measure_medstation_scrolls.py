"""Scroll the hideout module row toward the medstation (the leftmost tab) and count the swipes.

Run:  python tests/hideout_nav/measure_medstation_scrolls.py

Real swipes against the live game, so it needs Tarkov up on the hideout screen with the module
row visible. Start it with the WORKBENCH (the rightmost tab) on screen to measure the full
left-to-right span: the number it prints is CAROUSEL_SPAN_SWIPES for the new get_to_station.

Each swipe drags the row toward the left end (dx = +dist, the direction the crash log's +667
swipes moved toward Weapon Rack). Stops the moment medstation matches and reports the count, or
gives up after MAX_SCROLLS and prints the best score seen so the crops can be blamed if it never
matched.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import window  # noqa: E402
from interact import craft, find  # noqa: E402

MAX_SCROLLS = 40  # a hard ceiling: the whole carousel is well under this, so a run this long is a miss
COUNTDOWN = 3  # seconds to alt-tab back into Tarkov before it starts clicking


if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    for n in range(COUNTDOWN, 0, -1):
        print(f'focus Tarkov... {n}')
        time.sleep(1)

    icons = craft.hideout_icons(region)
    if not icons:
        print('no hideout module icons on screen to grab the row by; open the hideout first')
        raise SystemExit(1)
    x = round(sum(craft._center(b)[0] for b in icons) / len(icons))
    y = round(sum(craft._center(b)[1] for b in icons) / len(icons))
    dist = round(craft.SWIPE_DISTANCE * find.scale())
    print(f'grabbing the row at ({x}, {y}), swiping by +{dist} toward the medstation\n')

    for scrolls in range(MAX_SCROLLS + 1):
        if find.find(craft.MEDSTATION_TARGET, region):
            print(f'\nmedstation reached after {scrolls} scrolls')
            print(f'-> CAROUSEL_SPAN_SWIPES = {scrolls} (measured at {find.scale():.3f}x scale)')
            break
        peak, crop = find.best_score(craft.MEDSTATION_TARGET, region)
        print(f'scroll {scrolls:2d}: medstation not up (best {peak:.3f} from {crop}), swiping')
        craft._swipe(x, y, dist)
        time.sleep(craft.SWIPE_SETTLE)
    else:
        print(f'\nmedstation never matched in {MAX_SCROLLS} scrolls. Either the crops under '
              f'{craft.MEDSTATION_TARGET} are stale for this build, or the row hit its end short '
              f'of it. Check the last frames in %APPDATA%/tarkbot/frames.')
        raise SystemExit(1)
