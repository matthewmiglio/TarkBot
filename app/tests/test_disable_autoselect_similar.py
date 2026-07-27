"""Switch autoselect similar off on the live screen, whatever state it starts in.

Run:  python tests/test_disable_autoselect_similar.py

Clicks, but only the one checkbox, and only if it is ticked. Already off means no click at
all, which is the case worth watching: a blind click there would switch it on. Writes
tests/output/disable_autoselect_before.png and _after.png. Exits non-zero if it is still on.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import tarkov_window  # noqa: E402
from interact import sell  # noqa: E402

OUT = Path(__file__).parent / 'output'

if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)
    crop = sell.autoselect_similar_region(region)  # raises LookupError if the button is gone

    OUT.mkdir(exist_ok=True)
    before = sell.is_autoselect_similar_ticked(region)
    pyautogui.screenshot(region=crop).save(OUT / 'disable_autoselect_before.png')
    print(f'before: ticked={before}  ({"will click" if before else "no click needed"})')

    ok = sell.disable_autoselect_similar(region)

    after = sell.is_autoselect_similar_ticked(region)
    pyautogui.screenshot(region=crop).save(OUT / 'disable_autoselect_after.png')
    print(f'after:  ticked={after}')
    print(f'wrote {OUT / "disable_autoselect_before.png"} and _after.png')

    if not ok or after:
        sys.exit(f'FAILED: autoselect similar is still on (returned {ok})')
    print('autoselect similar is off')
