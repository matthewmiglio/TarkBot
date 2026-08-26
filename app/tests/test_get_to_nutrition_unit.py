"""Drive craft.get_to_nutrition_unit against the live game and report the outcome.

Run:  python tests/test_get_to_nutrition_unit.py

This performs real clicks and swipes and navigates the hideout, so it needs the game up on the
hideout screen. Prints 'reached the nutrition unit' on success, or the error it raised.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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
