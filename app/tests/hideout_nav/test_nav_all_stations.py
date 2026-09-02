"""End-to-end test of hideout navigation: enter the hideout and reach every station in turn.

WHAT LAYER THIS TESTS
    interact/craft.py's navigation pieces, against the live game: is_hideout_tab_active /
    wait_hideout_tab_active (enter the hideout), hideout_icons and _swipe / _row_strip (scroll the
    module carousel), close_open_station_panel (click a panel's X), and check_if_station_active (is a
    station panel open, read off close_window_button in the top-right). Nothing here touches the flea.

    Unlike craft.get_to_station, this test does its own scrolling: it sweeps the carousel until the
    target tab is actually on screen, both directions, rather than anchoring on the medstation and
    trusting a swipe-count span. That span is exactly what has been failing to reach the far stations
    (nutrition unit, workbench, water collector), so the test must not depend on it to prove a tab is
    reachable. A tab this cannot reach by sweeping the whole row both ways is genuinely unreachable.

WHAT IT DOES  (real clicks and swipes; start on or off the hideout, either works)
    1. enters the hideout, testing the full enter flow: if it starts on the hideout it clicks the
       FLEA MARKET tab to leave first (so clicking HIDEOUT genuinely navigates), then clicks HIDEOUT
       and waits for its tab to read active,
    2. for every station in craft.hideout_module_targets(), one cycle:
         - close any open panel, then scroll the carousel until the station's tab shows,
         - click the tab, wait CLICK_SETTLE, and assert check_if_station_active is True (a close X is
           up: a panel opened),
         - click the close X (close_open_station_panel) to leave, and assert check_if_station_active
           is now False.
       All three have to hold for the station to pass.

SCREENSHOTS  (tests/output/nav_all_stations, wiped at the start of every run)
    A full game-screen shot is dropped at each sub-step, numbered in run order and stamped HH-MM-SS
    so it lines up with the log:
      hideout before / after; then per station: before-scroll, scrolled-found|missing, before-click,
      on-station-True|False, off-station-left|stuck.
    So a failure's frame is right there next to the log line that recorded it. Full game screen, not
    the tiny searched region (repo convention), grabbed by window region so it is right on any monitor.

READING THE RESULT
    A live PASS / FAIL line per step, then a results table: one row per step (index, name, time,
    pass/fail) and a totals footer with the run's time and pass rate (e.g. 11/13 = 85%). Exits
    non-zero unless every step passed.

Run:  python tests/hideout_nav/test_nav_all_stations.py
"""
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402
import screen  # noqa: E402  (also patches pyautogui.screenshot; imported for the full-screen grab)
import window  # noqa: E402
from interact import craft, find, sell  # noqa: E402

# Timing. Small settles keep the run brisk; TAB_TIMEOUT stays long because the hideout can be slow to
# draw its tab as active after clicking in. CLICK_SETTLE is the spec's "wait 2s" for a station panel
# to fly in before it is read. SWEEP_LIMIT is a backstop cap per direction; the sweep normally stops
# earlier when the row hits its end (stops moving).
craft.SWIPE_SETTLE = 0.4
craft.PANEL_CLOSE_SETTLE = 1.0
craft.TAB_TIMEOUT = 60.0
CLICK_SETTLE = 2.0
FOUND_SETTLE = 0.5  # after the tab first matches, the row is still gliding; let it stop before clicking
SWEEP_LIMIT = 30  # more than the whole carousel is wide, so it only bites if end-detection fails
FLEA_TAB_TARGET = 'flea_icon'  # the menu's FLEA MARKET tab, clicked to leave the hideout when we start on it

# One full game-screen shot per sub-step. Saved here, numbered in run order, wiped each run.
OUTPUT = Path(__file__).resolve().parents[1] / 'output' / 'nav_all_stations'
_seq = 0  # global shot counter, so filenames sort in the order they were taken


def reset_output():
    """Empty the screenshot folder and reset the counter so a run only holds its own frames."""
    global _seq
    _seq = 0
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT.glob('*.png'):
        old.unlink()


def shot(label, region):
    """Save a shot of the whole game screen. NN_label_HH-MM-SS.png, sortable and matchable to the log."""
    global _seq
    _seq += 1
    slug = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')
    path = OUTPUT / f'{_seq:02d}_{slug}_{datetime.now():%H-%M-%S}.png'
    try:
        screen.grab(region).save(path)
        print(f'  saved {path.name}')
    except Exception as exc:  # noqa: BLE001  a lost screenshot must never fail the step it documents
        print(f'  screenshot failed: {exc}')


def leave_hideout(region):
    """Click the FLEA MARKET tab to get off the hideout, so the enter flow below can be tested.

    Only called when we start on the hideout. flea_icon is that tab in the menu bottom bar. True once
    the hideout tab no longer reads active.
    """
    flea = find.find(FLEA_TAB_TARGET, region)
    if not flea:
        raise LookupError('on the hideout but no FLEA MARKET tab found to leave it')
    pyautogui.click(*sell.jitter(pyautogui.center(flea)))
    time.sleep(craft.SWIPE_SETTLE)
    if craft.is_hideout_tab_active(region):
        raise LookupError('clicked FLEA MARKET but the hideout tab still reads active')
    return True


def enter_hideout(region):
    """Enter the hideout, testing the full flow whether we start on it or off it.

    If we start on the hideout, leave first (click FLEA MARKET) so clicking HIDEOUT genuinely
    navigates. Then click HIDEOUT and wait for its tab to read active. Ends on the hideout, or raises.
    """
    if craft.is_hideout_tab_active(region):
        leave_hideout(region)
        shot('hideout_left', region)
    tab = find.find(craft.HIDEOUT_TAB_TARGET, region)
    if not tab:
        raise LookupError('HIDEOUT button not on screen to enter the hideout')
    pyautogui.click(*sell.jitter(pyautogui.center(tab)))
    time.sleep(craft.SWIPE_SETTLE)
    if not craft.wait_hideout_tab_active(region, craft.TAB_TIMEOUT):
        raise LookupError('HIDEOUT tab never became active after clicking it')
    return True


def row_grab_point(region):
    """The (x, y) to drag the module row by: the centre of the row of module icons on screen."""
    icons = craft.hideout_icons(region)
    if not icons:
        raise LookupError('no hideout module icons on screen to grab the row by')
    x = round(sum(craft._center(b)[0] for b in icons) / len(icons))
    y = round(sum(craft._center(b)[1] for b in icons) / len(icons))
    return x, y


def scroll_to_tab(target, region, x, y, dist):
    """Sweep the module row until `target`'s tab is on screen. True if it showed.

    Tries one direction to its end, then the other to its end, so the tab is found whichever side of
    the carousel it is on without trusting a swipe-count span. 'End' is the row no longer moving
    (craft._row_moved off a strip diff) for two swipes running, since the hideout is never perfectly
    still; SWEEP_LIMIT is only a backstop if that never trips.
    """
    if find.find(target, region):
        return True
    for step in (dist, -dist):  # right to the wall, then left to the wall
        stuck = 0
        for _ in range(SWEEP_LIMIT):
            before = craft._row_strip(y, region)
            craft._swipe(x, y, step)
            time.sleep(craft.SWIPE_SETTLE)
            if find.find(target, region):
                return True
            if craft._row_moved(before, craft._row_strip(y, region)):
                stuck = 0
            else:
                stuck += 1
                if stuck >= 2:
                    break  # this end reached; try the other direction
    return False


def visit_station(target, region):
    """Scroll to a station's tab, open it, validate the close X is up, close it, validate it is gone.

    Every screenshot the spec asks for is taken here, so a failure leaves the exact frame behind.
    Raises on the first thing that does not hold; the caller turns that into a FAIL row.
    """
    name = target.rsplit('/', 1)[-1]
    craft.close_open_station_panel(region)  # a leftover panel covers the row and eats the drag
    shot(f'{name}_before-scroll', region)

    x, y = row_grab_point(region)
    dist = round(craft.SWIPE_DISTANCE * find.scale())
    found = scroll_to_tab(target, region, x, y, dist)
    if not found:
        shot(f'{name}_scrolled-missing', region)
        raise LookupError('tab never appeared sweeping the whole carousel both ways')
    time.sleep(FOUND_SETTLE)  # the row is still coasting when the tab first matches; let it come to rest
    shot(f'{name}_scrolled-found', region)

    box = find.find(target, region)  # re-find at rest, so the click is not aimed at a stale position
    if box is None:  # matched a moment ago in scroll_to_tab; a flaky miss now
        raise LookupError('tab vanished between finding it and clicking it')
    shot(f'{name}_before-click', region)
    pyautogui.click(*sell.jitter(pyautogui.center(box)))
    time.sleep(CLICK_SETTLE)  # the spec's 2s wait for the panel to fly in before reading it

    active = craft.check_if_station_active(region)
    shot(f'{name}_on-station-{active}', region)
    if not active:
        raise AssertionError('check_if_station_active False after clicking the tab (no close X found)')

    craft.close_open_station_panel(region)  # leave by clicking the close (X)
    left = not craft.check_if_station_active(region)
    shot(f'{name}_off-station-{"left" if left else "stuck"}', region)
    if not left:
        raise AssertionError('check_if_station_active still True after clicking close')


def print_table(rows, total_seconds):
    """rows is [(name, seconds, status)]. Print the results table with a totals footer row."""
    passed = sum(1 for _, _, s in rows if s == 'PASS')
    total = len(rows)
    pct = round(100 * passed / total) if total else 0
    header = ('#', 'step', 'time', 'result')
    body = [(str(i + 1), name, f'{sec:.1f}s', status) for i, (name, sec, status) in enumerate(rows)]
    footer = ('totals', f'{total} steps', f'{total_seconds:.1f}s', f'{passed}/{total} = {pct}%')
    widths = [max(len(r[c]) for r in (header, footer, *body)) for c in range(4)]

    def line(cells):
        return '| ' + ' | '.join(cells[c].ljust(widths[c]) for c in range(4)) + ' |'

    rule = '|' + '|'.join('-' * (widths[c] + 2) for c in range(4)) + '|'
    print()
    print(line(header))
    print(rule)
    for r in body:
        print(line(r))
    print(rule)
    print(line(footer))


def timed(fn):
    """Run fn, return (status, seconds, detail). PASS/ok, or FAIL with the exception's message."""
    start = time.monotonic()
    try:
        fn()
        return 'PASS', time.monotonic() - start, 'ok'
    except Exception as exc:  # noqa: BLE001  the point is to report whatever went wrong
        return 'FAIL', time.monotonic() - start, f'{type(exc).__name__}: {exc}'


if __name__ == '__main__':
    hwnd = window.handle()
    region = window.position(hwnd) + window.size(hwnd)

    for n in range(3, 0, -1):
        print(f'Focus Tarkov (on or off the hideout). Beginning in {n}...')
        time.sleep(1)

    reset_output()  # clear last run's frames before saving this run's
    rows = []  # (name, seconds, status), one per step, in run order
    run_start = time.monotonic()

    def record(name, status, seconds, detail):
        rows.append((name, seconds, status))
        print(f'[{status}] {name} ({seconds:.1f}s): {detail}')

    # 1. enter the hideout (leaving first if we start on it, so the enter flow is really exercised).
    #    Nothing downstream can run without it. Screenshot before and after.
    shot('hideout_before', region)
    status, seconds, detail = timed(lambda: enter_hideout(region))
    shot('hideout_after', region)
    record('enter the hideout', status, seconds, detail)
    if status != 'PASS':
        print('\ncannot navigate stations without the hideout; stopping')
        print_table(rows, time.monotonic() - run_start)
        raise SystemExit(1)

    # 2. every station: scroll to its tab, open it, validate the close X, close it, validate it is gone.
    for target in craft.hideout_module_targets():
        name = target.rsplit('/', 1)[-1]
        status, seconds, detail = timed(lambda t=target: visit_station(t, region))
        record(name, status, seconds, detail)

    print_table(rows, time.monotonic() - run_start)
    passed = sum(1 for _, _, s in rows if s == 'PASS')
    raise SystemExit(0 if passed == len(rows) else 1)
