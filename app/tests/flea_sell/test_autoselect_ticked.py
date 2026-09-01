"""Check whether the autoselect similar checkbox is ticked on the live screen.

Exercises interact/sell.py's autoselect_similar_region and is_autoselect_similar_ticked. The
checkbox sits at the right end of every reference crop of the button, so the region is that
button's box grown by CHECKMARK_MARGIN and the checkmark searched for inside it; sizing off the
whole box, as it once did, gave a region too small to hold the needle when a short crop won.
Prints the button box, the grown region and the verdict, and writes that crop to
tests/flea_sell/output/autoselect_ticked.png so it can be judged by eye.

Read-only, it never clicks. Pass true or false to also assert the state. Needs the live game,
flea open with the offer creation window up.

Run:  python tests/flea_sell/test_autoselect_ticked.py         (just report)
      python tests/flea_sell/test_autoselect_ticked.py true    (also fail unless it is ticked)
      python tests/flea_sell/test_autoselect_ticked.py false   (also fail unless it is not)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parents[1] / 'output'

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
