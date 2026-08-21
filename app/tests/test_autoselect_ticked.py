"""Check whether the autoselect similar checkbox is ticked on the live screen.

Run:  python tests/test_autoselect_ticked.py         (just report)
      python tests/test_autoselect_ticked.py true    (also fail unless it is ticked)
      python tests/test_autoselect_ticked.py false   (also fail unless it is not)

Read-only, it never clicks. Writes tests/output/autoselect_ticked.png, the widened crop it
searched, so you can see for yourself what it was looking at.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    box = find.find('autoselect_similar', region)
    crop = sell.autoselect_similar_region(region)  # raises LookupError if the button is gone
    print(f'button {box}')
    print(f'grown by {sell.CHECKMARK_MARGIN:.0%} -> {crop}')

    OUT.mkdir(exist_ok=True)
    path = OUT / 'autoselect_ticked.png'
    pyautogui.screenshot(region=crop).save(path)

    ticked = sell.is_autoselect_similar_ticked(region)
    print(f'checkmark {find.find(sell.CHECKMARK_TARGET, crop) or "not in the crop"}')
    print(f'ticked -> {ticked}')
    print(f'wrote {path}')

    want = sys.argv[1].lower() == 'true' if len(sys.argv) > 1 else None
    if want is not None and ticked != want:
        sys.exit(f'FAILED: expected {want}, got {ticked}')
