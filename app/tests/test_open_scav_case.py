"""Right-click a random scav case and choose open from its menu.

Run:  python tests/test_open_scav_case.py        (countdown, then really clicks)
      python tests/test_open_scav_case.py --dry  (show the case it would pick, no clicking)

Writes tests/output/open_scav_case_before.png (every case boxed, the pick in magenta)
and _after.png. Exits non-zero if nothing was opened. Tarkov must be the visible window.
"""
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'
DELAY = 3  # ponytail: seconds to alt-tab into Tarkov; the clicks land nowhere useful otherwise

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    cases = find.find_all('scav_case', region)
    print(f'{len(cases)} scav case(s): {[tuple(int(v) for v in c) for c in cases]}')
    if not cases:
        sys.exit('no scav case on screen')

    OUT.mkdir(exist_ok=True)
    pick = random.choice(cases)
    before = pyautogui.screenshot(region=region)
    draw = ImageDraw.Draw(before)
    for case in cases:
        color = 'magenta' if case == pick else 'lime'
        x, y = case.left - region[0], case.top - region[1]
        draw.rectangle([x, y, x + case.width, y + case.height], outline=color, width=3)
    before.save(OUT / 'open_scav_case_before.png')

    if dry:
        print(f'would right-click {pyautogui.center(pick)}, then look for open_scav_case')
        sys.exit(0)

    for n in range(DELAY, 0, -1):
        print(f'opening in {n}...')
        time.sleep(1)

    point = sell.open_scav_case(region)  # picks its own case, not necessarily the one boxed above
    time.sleep(0.5)  # let the window draw
    pyautogui.screenshot(region=region).save(OUT / 'open_scav_case_after.png')
    print(f'clicked open at {point}' if point else 'no menu entry found, nothing opened')
    print(f'wrote {OUT / "open_scav_case_before.png"} and _after.png')
    sys.exit(0 if point else 1)
