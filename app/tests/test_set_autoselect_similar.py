"""Switch autoselect similar on or off on the live screen, whatever state it starts in.

Run:  python tests/test_set_autoselect_similar.py [on|off]      (off by default)

Clicks, but only the one checkbox, and only if it is not already the way it was asked for.
Already there means no click at all, which is the case worth watching: a blind click would
flip it the wrong way. Writes tests/output/autoselect_before.png and _after.png. Exits
non-zero if the checkbox did not end up in the asked-for state.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pyautogui  # noqa: E402

import window  # noqa: E402
from interact import sell  # noqa: E402

OUT = Path(__file__).parent / 'output'

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
