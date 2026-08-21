"""Does window.state() tell the three positions apart. No game and no GUI needed.

Run:  python tests/test_window_overlap.py          the decision, against made up rectangles
      python tests/test_window_overlap.py --live   print what the real two windows are doing

The decision is what is worth a test: the win32 lookups either find a window or raise, and
--live is there to eyeball them. The rectangles below are a 1920x1080 game at the origin with
a 420x600 panel put in various places against it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import window  # noqa: E402

GAME = (0, 0, 1920, 1080)
failures = []


def check(want, gui, focus, why):
    got = window.state(gui, GAME, focus)
    ok = got == want
    print(f'{"ok  " if ok else "FAIL"} {why}: {got}')
    if not ok:
        failures.append(f'{why}: wanted {want}, got {got}')


# The three the caller asked for.
check(window.GUI_ON_TOP, (700, 200, 1120, 800), True, 'panel over the game, panel focused')
check(window.GAME_ON_TOP, (700, 200, 1120, 800), False, 'panel over the game, game focused')
check(window.CLEAR, (2000, 200, 2420, 800), True, 'panel on the second monitor, panel focused')
check(window.CLEAR, (2000, 200, 2420, 800), False, 'panel on the second monitor, game focused')

# The edges.
check(window.CLEAR, (1920, 0, 2340, 600), True, 'panel starting exactly where the game ends')
check(window.GUI_ON_TOP, (1919, 0, 2339, 600), True, 'panel one pixel into the game')
check(window.GUI_ON_TOP, (0, 0, 1920, 1080), True, 'panel exactly over the game')
check(window.GUI_ON_TOP, (-100, -100, 300, 500), False, 'panel off the top left, still overlapping')
check(window.CLEAR, (-32000, -32000, -31580, -31400), True, 'minimised panel (windows parks it here)')
# A monitor left of the primary has negative coords, and nothing here may assume otherwise.
check(window.GUI_ON_TOP, (-500, 100, 100, 700), True, 'panel from the left monitor spilling in')
check(window.CLEAR, (-500, 100, -80, 700), False, 'panel wholly on the left monitor')

if '--live' in sys.argv:
    print()
    try:
        game, gui = window.handle(), window.gui_handle()
        print(f'game {window.bounds(game)}')
        print(f'gui  {window.bounds(gui)}')
        print(f'->   {window.overlap_state(gui, game)}')
    except window.WindowError as e:
        print(f'nothing to read: {e}')

if failures:
    sys.exit('\n'.join(failures))
print('\nok: overlap, no overlap, and which of the two is in front all read correctly')
