"""Check whether a free offer slot is left, by the add offer button's brightness.

Exercises interact/sell.py's add_offer_brightness and more_offers_available. The button keeps
its dark plate whether or not a slot is free and only its label lights, so availability is read
as a brightest-channel threshold (MORE_OFFERS_BRIGHTNESS, lit 255 vs greyed 123) rather than a
second template. Prints the measured brightness and the verdict, and writes the button crop to
tests/flea_sell/output/more_offers.png so the number can be checked against what is on screen.

Read-only, it never clicks. Pass true or false to also assert the expected state, which is how
this doubles as a regression check on the threshold. Needs the live game, flea open with the
offer creation window up.

Run:  python tests/flea_sell/test_more_offers.py          (just report)
      python tests/flea_sell/test_more_offers.py true     (also fail unless a slot is free)
      python tests/flea_sell/test_more_offers.py false    (also fail unless the button is greyed out)
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
