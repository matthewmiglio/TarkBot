"""End-to-end smoke test of hideout navigation: enter the hideout and reach every station.

WHAT LAYER THIS TESTS
    interact/craft.py's navigation stack, exercised against the live game rather than a fixture:
    get_to_station (the anchor-left-then-scroll-right carousel walk), close_open_station_panel
    (click the panel's X so it stops covering the module row), _open_station (click a tab and
    confirm its panel drew), _scroll_until, hideout_icons and is_hideout_tab_active. This is the
    top of the craft mode's "where on the hideout am I and how do I get to station X" problem; the
    per-craft state reads and buying live in other craft tests. Nothing here touches the flea.

WHY IT EXISTS
    Navigation is the slowest, least reliable thing craft mode does, and its misses (a sweep that
    turned around one swipe short of the medstation on 2026-08-31; a station panel left open that
    swallowed every drag) only reproduce against a real hideout with a real carousel and a real
    camera-fly animation. This walks the whole carousel end to end so a regression in the walk
    surfaces as a failed station here rather than as a dead craft run.

WHAT IT DOES  (real clicks and swipes; START IT OFF THE HIDEOUT: flea, character, traders, any
    screen with the bottom nav bar showing the HIDEOUT button)
    1. confirms it is not on the hideout (so step 2 actually navigates),
    2. enters the hideout (clicks the HIDEOUT button, waits for it to read active),
    3. for each station that has a panel-title crop (the six craft stations), drives the real
       craft.get_to_station: close any open panel, anchor on the medstation, scroll right, click
       the tab, and confirm the panel opened,
    4. for each tab-only station (bitcoin_farm, cultist_circle, intelligence_center, scav_case:
       tab crop but no title crop, so an open cannot be confirmed), scrolls to its tab and confirms
       the tab appears.

TIGHT TIMEOUTS
    Each step runs on its own thread with a hard STEP_TIMEOUT wall-clock cap, and the craft timing
    constants (SWIPE_SETTLE, NAV_SETTLE, PANEL_TIMEOUT, PANEL_CLOSE_SETTLE, TAB_TIMEOUT) are
    overridden small for the run so a stuck step surfaces fast instead of dragging out the sweep.
    craft._swipe is wrapped so a timed-out step's leftover thread raises out of its next swipe
    instead of fighting the next step for the mouse; a timed-out step also releases the mouse button
    in case it died mid-drag. A step that fails or times out is recorded and the sweep continues.

READING THE RESULT
    One PASS / FAIL / TIMEOUT line per step with seconds, then a tally and a list of the
    non-passing steps. Known-open questions this test surfaces rather than answers: whether the
    tab-only reaches stall on scrolling itself (see tests/test_scroll_progress.py) vs. on the tab
    crops not matching. Exits non-zero unless every step passed.

Run:  python tests/hideout_nav/test_nav_all_stations.py
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402
import window  # noqa: E402
from interact import craft, find, sell  # noqa: E402

# Tight budgets for this run so a stuck step surfaces fast instead of dragging out the whole sweep.
craft.SWIPE_SETTLE = 0.4
craft.NAV_SETTLE = 1.0
craft.PANEL_TIMEOUT = 5.0
craft.PANEL_CLOSE_SETTLE = 0.8
craft.TAB_TIMEOUT = 10.0
STEP_TIMEOUT = 30  # hard wall-clock cap per step, seconds

_abort = threading.Event()
_real_swipe = craft._swipe


class _Aborted(Exception):
    """Raised inside a timed-out step's thread to unwind it rather than leave it swiping."""


def _guarded_swipe(*args, **kwargs):
    if _abort.is_set():
        raise _Aborted('step timed out')
    return _real_swipe(*args, **kwargs)


craft._swipe = _guarded_swipe  # every scroll goes through this, so a timeout can stop it mid-loop


def run_step(label, fn, timeout=STEP_TIMEOUT):
    """Run fn on a thread, cap it at `timeout`. Returns (status, detail): PASS / FAIL / TIMEOUT."""
    result = {}

    def worker():
        try:
            result['value'] = fn()
        except Exception as exc:  # noqa: BLE001  the point is to report whatever it was
            result['error'] = exc

    _abort.clear()
    thread = threading.Thread(target=worker, daemon=True)
    start = time.monotonic()
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        _abort.set()  # neuter further swipes so the worker unwinds at its next one
        thread.join(5)
        try:
            pyautogui.mouseUp()  # release a drag button left held if it died mid-drag
        except Exception:
            pass
        return 'TIMEOUT', f'exceeded {timeout}s'
    if 'error' in result:
        exc = result['error']
        return 'FAIL', f'{type(exc).__name__}: {exc}'
    return 'PASS', f'{time.monotonic() - start:.1f}s'


def enter_hideout(region):
    """Click into the hideout from another screen; True once its tab reads active. Mirrors get_to_station."""
    if craft.is_hideout_tab_active(region):
        return True
    tab = find.find(craft.HIDEOUT_TAB_TARGET, region)
    if not tab:
        raise LookupError('HIDEOUT button not on screen to enter the hideout')
    pyautogui.click(*sell.jitter(pyautogui.center(tab)))
    time.sleep(craft.SWIPE_SETTLE)
    if sell.wait_for(craft.HIDEOUT_TAB_TARGET, region, timeout=craft.TAB_TIMEOUT) is None:
        raise LookupError('HIDEOUT tab never came back after clicking it')
    if not craft.is_hideout_tab_active(region):
        raise LookupError('HIDEOUT tab did not become active after clicking it')
    return True


def reach_tab(target, region):
    """Anchor on the medstation, then scroll right until `target`'s tab shows. (ok, swipes)."""
    craft.close_open_station_panel(region)  # an open panel covers the row and eats the drag
    icons = craft.hideout_icons(region)
    if not icons:
        raise LookupError('no hideout module icons on screen to grab the row by')
    x = round(sum(craft._center(b)[0] for b in icons) / len(icons))
    y = round(sum(craft._center(b)[1] for b in icons) / len(icons))
    dist = round(craft.SWIPE_DISTANCE * find.scale())
    limit = craft.CAROUSEL_SPAN_SWIPES + 2
    if not craft._scroll_until(craft.LEFTMOST_TARGET, x, y, dist, limit, region):
        raise LookupError('could not anchor on the medstation (leftmost tab)')
    for swipes in range(limit + 1):
        if find.find(target, region):
            return True, swipes
        craft._swipe(x, y, -dist)
        time.sleep(craft.SWIPE_SETTLE)
    return False, limit


def distinct_craft_stations():
    """One Craft per station (deduped by module tab), in CRAFTS order. These have panel-title crops."""
    seen, out = set(), []
    for c in craft.CRAFTS.values():
        if c.module_target not in seen:
            seen.add(c.module_target)
            out.append(c)
    return out


if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    for n in range(3, 0, -1):
        print(f'START OFF THE HIDEOUT. Beginning in {n}...')
        time.sleep(1)

    results = []  # (label, status)

    def record(label, status, detail):
        results.append((label, status))
        print(f'[{status}] {label}: {detail}')

    # 1. starting state (instant)
    off = not craft.is_hideout_tab_active(region)
    record('start off the hideout', 'PASS' if off else 'FAIL',
           'confirmed off the hideout' if off else 'already on the hideout (start elsewhere)')

    # 2. enter the hideout (nothing downstream can run without it)
    status, detail = run_step('enter the hideout', lambda: enter_hideout(region))
    record('enter the hideout', status, detail)
    if status != 'PASS':
        print('\ncannot navigate stations without the hideout; stopping')
        raise SystemExit(1)

    # 3. openable stations: the real get_to_station (nav + open + confirm panel)
    craft_targets = {c.module_target for c in craft.CRAFTS.values()}
    for c in distinct_craft_stations():
        status, detail = run_step(f'{c.station} (open panel)',
                                  lambda c=c: craft.get_to_station(c, region))
        record(f'{c.station} (open panel)', status, detail)

    # 4. tab-only stations: reach the tab (no panel crop to open-confirm)
    for target in craft.hideout_module_targets():
        if target in craft_targets:
            continue
        name = target.rsplit('/', 1)[-1]

        def reach(target=target):
            ok, swipes = reach_tab(target, region)
            if not ok:
                raise LookupError('tab never appeared')
            return swipes

        status, detail = run_step(f'{name} (reach tab)', reach)
        record(f'{name} (reach tab)', status, detail)

    passed = sum(1 for _, s in results if s == 'PASS')
    print(f'\n{passed}/{len(results)} steps passed')
    for label, s in results:
        if s != 'PASS':
            print(f'  {s}: {label}')
    raise SystemExit(0 if passed == len(results) else 1)
