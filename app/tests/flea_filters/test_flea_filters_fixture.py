"""Every flea filter reference image, matched against a real screenshot from a 1440p player.

App layer under test: interact/find.py against the filter targets interact/sell.py's
apply_flea_filters reads (the currency and offers-from state pairs, the gear, the FILTERS title
bar and OK). Verifies each visible target is found at find.CONFIDENCE and, for the two-state
settings, that the state actually on screen scores higher than its opposite so a looser
confidence could not pick the wrong one (non-zero exit on a miss or an inverted pair).

No-game fixture test: it matches against a saved 2560x1440 screenshot, no live game or window.

Run:  python tests/flea_filters/test_flea_filters_fixture.py
      python tests/flea_filters/test_flea_filters_fixture.py --verbose   (name the png that matched)

tests/fixtures/2560x1440/flea-filters-open.png is that player's screen with the
filter window open, which is exactly where his runs die with "could not apply the flea filters".
The fixture's own height drives find.scale(), so the needles are resized here the same way they
are on his machine, and a miss here is the miss he gets.

Two different things are checked, and the second is the one that matters:

1. Can each target that is visible in the fixture be found at find.CONFIDENCE. Pass/fail comes
   from find.find() itself, so it is the real code path and not a reimplementation of it.
2. For the three settings that exist in two states, does the state actually on screen score
   HIGHER than its opposite. apply_flea_filters reads these states to decide whether to click,
   so a pair that scores the wrong way round is worse than a miss: dropping CONFIDENCE far
   enough to find anything would then find the wrong one, and the bot would skip a setting it
   never applied instead of reporting that it could not.

The peak score printed beside each target is cv2's TM_CCOEFF_NORMED, the same measure pyscreeze
compares against confidence, computed here only so a miss says how far off it was.

Exits non-zero if a visible target is not found, or if a pair scores the wrong way round.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from interact import find, sell  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / '2560x1440' / 'flea-filters-open.png'
OUT = Path(__file__).resolve().parents[1] / 'output'

# What the fixture shows. Currency and offers-from both read 'any', so for each pair the first
# is on screen and the second is not. The remember-selected-filter pair used to be checked here
# too; apply_flea_filters no longer touches that box, because the tick never survives the OK.
PAIRS = ((sell.CURRENCY_ANY_TARGET, sell.CURRENCY_RUB_TARGET, 'currency'),
         (sell.OFFERS_FROM_ANY_TARGET, sell.OFFERS_FROM_PLAYERS_TARGET, 'display offers from'))
# Visible, and with no opposite state to confuse them with.
SINGLES = ((sell.FILTER_BUTTON_TARGET, 'the gear that opens the window'),
           (sell.FILTERS_WINDOW_TARGET, 'the FILTERS title bar'),
           (sell.FILTERS_OK_TARGET, 'the OK button'))
# Only ever on screen while a dropdown is hanging open, so it should be nowhere in this shot.
OPEN_LIST_ONLY = (sell.CURRENCY_RUBLES_OPTION, sell.OFFERS_FROM_PLAYERS_OPTION)


def references(name):
    """`name`'s reference pngs, or [] if that folder is empty or gone.

    Empty is a real state here: a folder gets cleared out on purpose when its crops turn out to
    be wrong, and the test has to keep reporting on everything else until new ones are cut.
    """
    try:
        return find.images(name)
    except FileNotFoundError:
        return []


def peak(name, haystack_bgr):
    """The best TM_CCOEFF_NORMED any of `name`'s references scores against the fixture."""
    best = 0.0
    for path in references(name):
        needle = find.needle(path)
        array = (cv2.cvtColor(np.array(needle.convert('RGB')), cv2.COLOR_RGB2BGR)
                 if hasattr(needle, 'convert') else cv2.imread(needle))
        if array.shape[0] > haystack_bgr.shape[0] or array.shape[1] > haystack_bgr.shape[1]:
            continue  # needle grown past the screen, which is its own bug
        best = max(best, float(cv2.matchTemplate(haystack_bgr, array, cv2.TM_CCOEFF_NORMED).max()))
    return best


def report(name, what, haystack, haystack_bgr, draw, expected):
    """Print one target's line and draw its box. Returns (found_at_confidence, peak score)."""
    if not references(name):
        print(f'  ----  {name:46} {"no reference images yet":>21}')
        print(f'          {what}')
        return False, 0.0
    box = find.find(name, haystack=haystack)
    score = peak(name, haystack_bgr)
    ok = bool(box) == expected
    where = f'({int(box.left)}, {int(box.top)}) {int(box.width)}x{int(box.height)}' if box else ''
    print(f'  {"ok  " if ok else "FAIL"}  {name:46} {score:.4f}  {where}')
    print(f'          {what}')
    if box:
        draw.rectangle((box.left, box.top, box.left + box.width, box.top + box.height),
                       outline=(90, 200, 90) if ok else (220, 70, 70), width=3)
    return bool(box), score


if __name__ == '__main__':
    if not FIXTURE.exists():
        sys.exit(f'no fixture at {FIXTURE}')
    find.VERBOSE = '--verbose' in sys.argv
    haystack = Image.open(FIXTURE).convert('RGB')
    haystack_bgr = cv2.cvtColor(np.array(haystack), cv2.COLOR_RGB2BGR)
    factor = haystack.height / find.REFERENCE_HEIGHT
    find.scale = lambda: factor  # his screen, without his screen

    print(f'{FIXTURE.name}  {haystack.size}, references resized {factor:.4f}x, '
          f'pass mark {find.CONFIDENCE}\n')
    canvas = haystack.copy()
    draw = ImageDraw.Draw(canvas)
    missing, inverted = [], []

    print('on screen, and there is a second state it must not be confused with:')
    for on_screen, opposite, what in PAIRS:
        found, score = report(on_screen, f'{what}, the state this shot is in',
                              haystack, haystack_bgr, draw, expected=True)
        _, other = report(opposite, f'{what}, the state it is not in',
                          haystack, haystack_bgr, draw, expected=False)
        if not found:
            missing.append((on_screen, score))
        if score and other >= score:  # an empty folder scores 0 and is not an inversion
            inverted.append((what, on_screen, score, opposite, other))
            print(f'          ^ WRONG WAY ROUND: the state that is not on screen scores '
                  f'{other:.4f} against {score:.4f}')
    print()

    print('on screen, no opposite state:')
    for name, what in SINGLES:
        found, score = report(name, what, haystack, haystack_bgr, draw, expected=True)
        if not found:
            missing.append((name, score))
    print()

    print('should be nowhere in this shot:')
    for name in OPEN_LIST_ONLY:
        report(name, 'only drawn while the dropdown is open', haystack, haystack_bgr, draw,
               expected=False)
    print()

    OUT.mkdir(exist_ok=True)
    path = OUT / 'flea_filters_fixture.png'
    canvas.save(path)
    print(f'boxes drawn on {path}')

    if inverted:
        for what, on_screen, score, opposite, other in inverted:
            print(f'INVERTED PAIR: {what} reads {opposite} ({other:.4f}) over {on_screen} '
                  f'({score:.4f}), so a lower confidence would pick the wrong state')
    if missing:
        print(f'NOT FOUND at {find.CONFIDENCE}: '
              + ', '.join(f'{n} (peak {s:.4f})' for n, s in missing))
    if missing or inverted:
        sys.exit(f'FAILED: {len(missing)} missing, {len(inverted)} inverted')
    print(f'ok, every visible target found at {find.CONFIDENCE} and every pair the right way up')
