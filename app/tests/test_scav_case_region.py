"""Infer the opened scav case region on the live Tarkov screen and save an annotated screenshot.

Run:  python tests/test_scav_case_region.py

Writes tests/output/scav_case_region.png: the title bar and close buttons boxed in lime,
the close button actually used in cyan, the inferred region in magenta. Read-only, it
never clicks. The scav case window must already be open.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402
from PIL import ImageDraw  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'


def box(draw, rect, origin, color, label, width=2):
    """Outline a screen-coord (left, top, w, h) on a screenshot that starts at origin."""
    left, top = rect[0] - origin[0], rect[1] - origin[1]
    draw.rectangle([left, top, left + rect[2], top + rect[3]], outline=color, width=width)
    draw.text((left + 2, max(0, top - 10)), label, fill=color)


if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    print(f'searching window {region}')

    shot = pyautogui.screenshot(region=region)
    draw = ImageDraw.Draw(shot)

    title = find.find(sell.SCAV_WINDOW_TARGET, region=region)
    print(f'{sell.SCAV_WINDOW_TARGET}: {title or "NOT FOUND"}')
    if title:
        box(draw, title, region, 'lime', sell.SCAV_WINDOW_TARGET)

    closes = find.find_all(sell.CLOSE_BUTTON_TARGET, region=region)
    used = min(closes, key=lambda b: b.left) if closes else None
    print(f'{sell.CLOSE_BUTTON_TARGET}: {len(closes)} found, using leftmost {used or "NOT FOUND"}')
    for found in closes:
        chosen = found == used
        box(draw, found, region, 'cyan' if chosen else 'lime',
            'close (used)' if chosen else 'close (ignored)')

    scav = sell.infer_scav_case_region(region)  # raises LookupError if a piece is missing
    print(f'scav case region: {scav}')
    box(draw, scav, region, 'magenta', 'scav case', width=3)

    OUT.mkdir(exist_ok=True)
    path = OUT / 'scav_case_region.png'
    shot.save(path)
    print(f'wrote {path}')
