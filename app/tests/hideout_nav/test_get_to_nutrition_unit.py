"""Drive interact/craft.py's get_to_nutrition_unit against the live game and report the outcome.

WHAT LAYER THIS TESTS
    interact/craft.py's navigation, specifically get_to_nutrition_unit (the slickers-era
    back-compat wrapper over the generic get_to_station carousel walk): make the hideout tab
    active, treat the module row as a horizontal carousel, scroll until the nutrition unit's tab
    appears, click it, and confirm its panel drew. This is the single-station smoke test that
    sits under the full carousel sweep in test_nav_all_stations; nothing here touches the flea.

WHAT IT DOES  (LIVE GAME: real clicks and swipes, so it needs Tarkov up on the hideout screen
    with the module row visible)
    Grabs the window rect, calls craft.get_to_nutrition_unit(region), and prints 'reached the
    nutrition unit' on success or the error it raised on failure. Exits non-zero on failure.

Run:  python tests/hideout_nav/test_get_to_nutrition_unit.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import window  # noqa: E402
from interact import craft  # noqa: E402

if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)
    try:
        craft.get_to_nutrition_unit(region)
        print('reached the nutrition unit')
    except Exception as exc:
        print(f'failed: {type(exc).__name__}: {exc}')
        raise SystemExit(1)
