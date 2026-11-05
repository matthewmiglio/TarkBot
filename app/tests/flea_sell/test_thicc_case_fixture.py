"""Does find_all('flea/thicc_case') see the thicc case where the sell flow actually looks for it.

App layer under test: interact/find.py, find.find_all('flea/thicc_case') at its threshold (the
default CONFIDENCE, 0.83). This is the detection behind "picking an item, trying a thicc case
first" in sell_bot.py: the bot only sells out of the thicc case if this finds it. Verifies each
labelled fixture reports the exact number of cases it holds (non-zero exit on a wrong count).

No-game fixture test: it matches against saved screenshots, no live game or window. Each fixture's
own height drives find.scale(), so the 1080p reference crops are resized exactly as they are on
that machine, and a miss here is a miss there.

Why this exists. The thicc case is picked while the offer creation window is open, where the stash
sits DIMMED behind it, not on the bright gear screen. Every thicc_case crop was cut from the bright
screen, so none cleared 0.83 against the dimmed case (the best reached 0.803), and on 2026-11-05 a
1080p player watched the bot log "thicc cases on screen: 0" and never sell from the case, pass after
pass, while scav cases (whose crops include the dimmed state) were found fine. The fix was a crop of
the case as it looks dimmed in that window (flea/thicc_case/11b33d22...), which matches at 0.9966 at
1080p and 0.96 at a simulated 1440p. This fixture is that very frame, kept so the dimmed state is
never dropped from the corpus again.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image  # noqa: E402

from interact import find  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / '1920x1080'
# file -> how many thicc cases are in it, and what makes it worth keeping.
CASES = (
    ('thicc-case-in-offer-window.png', 1,
     'the reported 1080p player: the case dimmed behind the offer creation window, where the '
     'sell flow picks it. Two scav cases are also on screen and must not be miscounted as thicc.'),
)

TARGET = 'flea/thicc_case'
failures = []

print(f'{TARGET} at confidence {find.confidence_for(TARGET)}\n')
for name, want, why in CASES:
    path = FIXTURES / name
    if not path.exists():
        failures.append(f'{name}: missing from {FIXTURES}')
        print(f'MISSING {name}')
        continue
    fixture = Image.open(path).convert('RGB')
    find.scale = lambda height=fixture.height: height / find.REFERENCE_HEIGHT  # that screen, not ours
    boxes = find.find_all(TARGET, haystack=fixture)
    ok = len(boxes) == want
    if not ok:
        failures.append(f'{name}: found {len(boxes)}, there are {want}')
    print(f'{"ok  " if ok else "FAIL"} {name:34} {len(boxes)}/{want}  '
          f'{[(int(b.left), int(b.top)) for b in boxes]}')
    print(f'     {why}')

print(f'\n{len(failures)} failure(s)')
for line in failures:
    print(f'  {line}')
sys.exit(1 if failures else 0)
