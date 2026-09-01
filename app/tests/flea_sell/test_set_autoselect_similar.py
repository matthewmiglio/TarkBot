"""Switch autoselect similar on or off on the live screen, whatever state it starts in.

Exercises interact/sell.py's set_autoselect_similar, checked through is_autoselect_similar_ticked
before and after. AUTOSELECT ON leaves the offer window's checkbox ticked, so one pick lists
the whole matching stack as one offer. The behaviour under test is that the click is conditional:
set_autoselect_similar reads the current state and clicks only when it differs from the ask, so
a box already right is left untouched. That is the case worth watching, since a blind click
would flip it the wrong way. Writes the before/after crops to tests/flea_sell/output/.

This one clicks, but only the single checkbox. Needs the live game, flea open with the offer
creation window up. Exits non-zero if the checkbox did not end up in the asked-for state.

Run:  python tests/flea_sell/test_set_autoselect_similar.py [on|off]      (off by default)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import sell  # noqa: E402

OUT = Path(__file__).parents[1] / 'output'

if __name__ == '__main__':
    want = (sys.argv[1].lower() if len(sys.argv) > 1 else 'off')
    if want not in ('on', 'off'):
        sys.exit(f'say on or off, not {want!r}')
    on = want == 'on'

    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    crop = sell.autoselect_similar_region(region)  # raises LookupError if the button is gone

    OUT.mkdir(exist_ok=True)
    before = sell.is_autoselect_similar_ticked(region)
    pyautogui.screenshot(region=crop).save(OUT / 'autoselect_before.png')
    print(f'before: ticked={before}  ({"no click needed" if before == on else "will click"})')

    ok = sell.set_autoselect_similar(on, region)

    after = sell.is_autoselect_similar_ticked(region)
    pyautogui.screenshot(region=crop).save(OUT / 'autoselect_after.png')
    print(f'after:  ticked={after}')
    print(f'wrote {OUT / "autoselect_before.png"} and _after.png')

    if not ok or after != on:
        sys.exit(f'FAILED: wanted autoselect similar {want}, it is ticked={after} (returned {ok})')
    print(f'autoselect similar is {want}')
