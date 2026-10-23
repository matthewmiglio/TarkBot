"""Grid the sell region on saved frames, and check what the bot would click is sellable.

App layer under test: interact/grid.py (cells, lines, SELLABLE_BRIGHTNESS) and the shipped pick
reads built on it in interact/sell.py: find_sell_pixels for the stash (sellable cell centres,
less any under a scav or thicc case) and find_scav_case_pixels for an opened scav or thicc case.

For each fixture in tests/fixtures/sell/ (inventory.png, thicc.png, scav_case.png, full 2560x1440
frames with the offer creation window open and, for the two cases, the case parked top left):
infer the region the bot sells from, grid it, and write the frame to tests/output/sell_grid/
with the region in magenta, every cell green (sellable) or red (not), and a white dot on each
point the shipped read returned, which is what a pass picks its click from. Look at those: a
count in the summary cannot say whether the grid sits on the lines.

screen.grab, rect and size are swapped for the fixture, so every find and the grid read the
saved frame. Patching find.find would not reach the region inference: sell._scoped binds the
real one at import.

scav_case_empty.png is a case holding only greyed items (a Bas-Relief whose name reads 98, just
under the cutoff), where the read must offer nothing at all.

Fails if a region cannot be inferred, a frame grids to no sellable cell or no unsellable one
(each of the other frames has both), the empty case offers anything, or the shipped read offers a point that is not the centre of a
sellable cell.

No game needed.
Run:  python tests/flea_sell/test_sell_grid.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import screen  # noqa: E402
from interact import grid, sell  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'sell'
OUT = Path(__file__).resolve().parents[1] / 'output' / 'sell_grid'
# fixture -> (the region the bot sells from on that screen, the shipped read of its clicks)
CASES = {'inventory': (sell.infer_inventory_region, sell.find_sell_pixels),
         'thicc': (lambda whole: sell.infer_scav_case_region(whole, 'thicc'),
                   lambda whole: sell.find_scav_case_pixels(whole, 'thicc')),
         'scav_case': (lambda whole: sell.infer_scav_case_region(whole, 'scav'),
                       lambda whole: sell.find_scav_case_pixels(whole, 'scav'))}
CASES['scav_case_empty'] = CASES['scav_case']
EMPTY = {'scav_case_empty'}  # nothing in it can be listed, so nothing may be offered

failures = []
OUT.mkdir(parents=True, exist_ok=True)
real = screen.grab, screen.rect, screen.size
for name, (infer, shipped) in CASES.items():
    frame = Image.open(FIXTURES / f'{name}.png').convert('RGB')
    whole = (0, 0) + frame.size
    screen.grab = lambda rect=None, frame=frame: (
        frame if rect is None else frame.crop((rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])))
    screen.rect, screen.size = (lambda whole=whole: whole), (lambda frame=frame: frame.size)
    try:
        region = infer(whole)
        points = shipped(whole)
    except LookupError as e:
        failures.append(f'{name}: {e}')
        print(f'FAIL {name}: {e}')
        continue
    finally:
        screen.grab, screen.rect, screen.size = real

    bgr = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
    found = grid.cells(bgr, region, frame.size[1] / 1080)
    sellable = sum(c.sellable for c in found)
    centres = {(c.box[0] + c.box[2] // 2, c.box[1] + c.box[3] // 2) for c in found if c.sellable}
    stray = [p for p in points if p not in centres]

    out = bgr.copy()
    l, t, w, h = region
    cv2.rectangle(out, (l, t), (l + w, t + h), (255, 0, 255), 2)
    for c in found:
        x, y, s, _ = c.box
        cv2.rectangle(out, (x + 2, y + 2), (x + s - 2, y + s - 2),
                      (60, 220, 60) if c.sellable else (60, 60, 230), 2)
    for p in points:
        cv2.circle(out, p, 5, (255, 255, 255), -1)
    cv2.imwrite(str(OUT / f'{name}.png'), out)

    if name in EMPTY:
        ok = found and not sellable and not points
    else:
        ok = found and 0 < sellable < len(found) and points and not stray
    print(f'{"ok  " if ok else "FAIL"} {name}: region {region}, {len(found)} cells, '
          f'{sellable} sellable, {len(points)} offered to click'
          + (f', {len(stray)} not on a sellable cell' if stray else '')
          + f' -> {OUT / (name + ".png")}')
    if not ok:
        failures.append(f'{name}: {len(found)} cells, {sellable} sellable, '
                        f'{len(points)} offered, {len(stray)} stray')

print(f'\n{len(failures)} failure(s)')
for line in failures:
    print(f'  {line}')
sys.exit(1 if failures else 0)
