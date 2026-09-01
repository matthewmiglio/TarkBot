"""What snipe.remove_filter_by_item_filter can see, and optionally what it does.

App layer under test: interact/snipe.py's remove_filter_by_item_filter, the read that finds a
filter-by-item chip narrowing the board to one item and clicks the leftmost clear button. The
flea BUYER (snipe_bot) calls it at Start and after every filter pass.

Run:  python tests/flea_snipe/test_remove_item_filter.py                looks only, live game
      python tests/flea_snipe/test_remove_item_filter.py frame.png      looks only, a saved screenshot
      python tests/flea_snipe/test_remove_item_filter.py --click        actually clears the filter

Bare with a saved frame it needs no game; bare with no frame and --click both drive the live
game (--click is the only mode that changes your screen).

Bare, it clicks nothing. It reports whether the board says it is filtered by item, how many
clear-filter buttons are on screen, which one is leftmost, and writes an annotated picture to
tests/output/remove_item_filter/: the chip in blue, every clear button in yellow, the leftmost
one in green. Look at that before believing any of the three numbers.

Look at it especially closely when the count is high. clear_filter_button is a 12 to 14 pixel
crop of a small plain glyph, and CLAUDE.md is explicit that a target that shape has no
false-positive headroom: a handful of matches scattered across the window means the crops are
finding punctuation, not buttons, and the leftmost of those is a click into nowhere.

--click needs the live game and does the real thing, so it is the one that changes your screen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw  # noqa: E402

import screen  # noqa: E402  patches pyautogui.screenshot, so import it before grabbing
import window  # noqa: E402
from interact import find, snipe  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'output' / 'remove_item_filter'


def look(shot, region, origin, haystack):
    """Report and draw what the function would find. Returns (chip, leftmost clear button).

    haystack is the picture to search when it came off disk, or None to search the live screen
    the way the shipping code does.
    """
    chips = {target: find.find(target, region, haystack=haystack)
             for target in snipe.APPLIED_TARGETS}
    chip = next((box for box in chips.values() if box), None)
    buttons = find.find_all(snipe.CLEAR_FILTER_TARGET, region, haystack=haystack)
    leftmost = min(buttons, key=lambda box: box.left) if buttons else None

    for target, box in chips.items():
        print(f'{target}: ' + (f'found at {tuple(box)}' if box else 'not found'))
    print(f'{snipe.CLEAR_FILTER_TARGET}: {len(buttons)} found')
    for box in sorted(buttons, key=lambda b: b.left):
        mark = ' <- leftmost, the one that would be clicked' if box is leftmost else ''
        print(f'  {tuple(box)}{mark}')
    if not chip:
        print('\nthe function would stop at step 1 and click nothing')
    elif not buttons:
        print('\nthe function would stop at step 2 and click nothing')

    OUT.mkdir(parents=True, exist_ok=True)
    marked = shot.copy()
    draw = ImageDraw.Draw(marked)
    # Back into the picture's coordinates: a live window does not start at (0, 0).
    shift = lambda b: (b.left - origin[0], b.top - origin[1],
                       b.left - origin[0] + b.width - 1, b.top - origin[1] + b.height - 1)
    if chip:
        draw.rectangle(shift(chip), outline='#4a90d0', width=3)
    for box in buttons:
        colour = '#5ec26a' if box is leftmost else '#e0c040'
        draw.rectangle(shift(box), outline=colour, width=2)
    marked.save(OUT / 'window.png')
    print(f'\nwrote {OUT / "window.png"}: chip blue, clear buttons yellow, leftmost green')
    return chip, leftmost


if __name__ == '__main__':
    paths = [a for a in sys.argv[1:] if not a.startswith('--')]
    clicking = '--click' in sys.argv

    if paths:
        if clicking:
            sys.exit('--click needs the live game, not a saved frame')
        shot = Image.open(paths[0]).convert('RGB')
        region, origin, haystack = (0, 0, shot.width, shot.height), (0, 0), shot
        print(f'{Path(paths[0]).name}: {shot.width}x{shot.height}')
    else:
        hwnd = window.handle()  # raises WindowError if Tarkov is missing or duplicated
        rect = window.position(hwnd) + window.size(hwnd)
        region = screen.overlap(rect, screen.current().rect) or rect
        shot, origin, haystack = screen.grab(region), region[:2], None
        print(f'the live window at {region}')

    chip, leftmost = look(shot, region, origin, haystack)

    if clicking:
        print('\n--click: doing it for real')
        cleared = snipe.remove_filter_by_item_filter(region)
        print('cleared' if cleared else 'nothing to clear, or no button to clear it with')
        after = next((box for box in (find.find(t, region) for t in snipe.APPLIED_TARGETS)
                      if box), None)
        print('the chip is gone' if not after else f'the chip is still there at {tuple(after)}')
        sys.exit(0 if cleared and not after else 1)

    if chip and leftmost:
        print('\nthis board would be cleared. Re-run with --click to actually do it.')
