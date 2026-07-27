"""Check whether there is still a free offer slot, by the add offer button's brightness.

Run:  python tests/test_more_offers.py          (just report)
      python tests/test_more_offers.py true     (also fail unless a slot is free)
      python tests/test_more_offers.py false    (also fail unless the button is greyed out)

Read-only, it never clicks. Writes tests/output/more_offers.png, the button crop it measured.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import tarkov_window  # noqa: E402
from interact import find, sell  # noqa: E402

OUT = Path(__file__).parent / 'output'

if __name__ == '__main__':
    hwnd = tarkov_window.handle()
    region = tarkov_window.position(hwnd) + tarkov_window.size(hwnd)

    box = find.find(sell.ADD_OFFER_TARGET, region)
    if not box:
        sys.exit('add offer button not on screen')
    rect = (int(box.left), int(box.top), int(box.width), int(box.height))
    OUT.mkdir(exist_ok=True)
    path = OUT / 'more_offers.png'
    pyautogui.screenshot(region=rect).save(path)

    brightness = sell.add_offer_brightness(region)
    available = sell.more_offers_available(region)
    print(f'button:     {rect}')
    print(f'brightness: {brightness}  (threshold {sell.MORE_OFFERS_BRIGHTNESS}, lit 255, greyed 123)')
    print(f'more offers available -> {available}')
    print(f'wrote {path}')

    want = sys.argv[1].lower() == 'true' if len(sys.argv) > 1 else None
    if want is not None and available != want:
        sys.exit(f'FAILED: expected {want}, got {available}')
