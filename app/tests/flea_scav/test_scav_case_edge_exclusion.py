"""A scav case at the inventory grid's left edge is still excluded from the sell pixels.

App layer under test: interact/sell.py find_sell_pixels / scav_case_regions, the read that
decides which stash pixels are items worth listing. find_sell_pixels drops pixels inside any
scav case, because a case is not ours to sell. This pins that it drops them even when the case
sits half a column outside the inferred grid.

No-game fixture test: it runs against a saved 2560x1440 screenshot, no live game or window.

Run:  python tests/flea_scav/test_scav_case_edge_exclusion.py

Why this exists. On 2026-09-03 a player (a YouTuber, roman) reported the bot "trying to sell the
scav case" and looping. His stash had sold down to one scav case, which Tarkov draws dimmed in
the offer creation window because a case cannot be listed. The case matched fine at 0.891 on the
whole screen, but find_sell_pixels searched for cases *inside* the inferred grid region, and his
grid's left edge came out at x=66 while the case's own left edge sat at x=52. A template cannot
be placed partly outside its search region, so the best in-grid placement was shifted ~14px right
and the score fell to 0.765, under scav_case's 0.8 gate. The case went unexcluded, its ~47 live
edge pixels were the only "sellable" pixels on the screen, and the stash path clicked them ten
times a pass forever, selecting nothing. The fix is to search for cases in the full region and
let _pixels_in clamp the exclusion rect into the grid, so a case at the very edge is still found.

The clip is marginal by a few pixels of grid inference (his 66 misses; a 61 would just catch it),
which is exactly why the wider search is the fix rather than a nudged constant.

Exits non-zero if the edge case is not excluded.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image  # noqa: E402

import screen  # noqa: E402
from interact import find, sell  # noqa: E402

FIXTURE = (Path(__file__).resolve().parents[1] / 'fixtures' / '2560x1440'
           / 'scav-case-at-grid-left-edge.png')
GRID_AS_LOGGED = (66, 293, 791, 1113)  # the grid his machine inferred, which clips the case
FULL = (0, 0, 2560, 1440)

img = Image.open(FIXTURE).convert('RGB')
screen.size = lambda: (img.width, img.height)
screen.grab = lambda rect: img.crop((rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]))
find.scale = lambda: img.height / find.REFERENCE_HEIGHT  # his 1440p screen, not ours

failures = []

# The mechanism: searching only the clipped grid loses the case; searching the full region keeps it.
clipped = find.find_all('scav_case', GRID_AS_LOGGED)
whole = find.find_all('scav_case', FULL)
print(f'scav_case in the as-logged grid {GRID_AS_LOGGED}: {len(clipped)}')
print(f'scav_case in the full region:              {len(whole)}')
if len(clipped) != 0:
    failures.append(f'expected the clipped grid to miss the edge case, found {len(clipped)}')
if len(whole) != 1:
    failures.append(f'expected the full region to find 1 case, found {len(whole)}')

# The shipped path: find_sell_pixels excludes the case, so an all-but-empty stash reads empty
# rather than handing the caller the case's edge pixels to click.
pixels = sell.find_sell_pixels(FULL)
print(f'find_sell_pixels live pixels: {len(pixels)}')
if pixels:
    failures.append(f'expected 0 sellable pixels (only the excluded case is on screen), '
                    f'got {len(pixels)}')

print(f'\n{len(failures)} failure(s)')
for line in failures:
    print(f'  {line}')
sys.exit(1 if failures else 0)
