"""Does find_all('scav_case') read the right number of cases off real 1440p screenshots.

Run:  python tests/test_scav_case_fixture.py

No game needed. Each fixture's own height drives find.scale(), so the reference crops are
resized here exactly as they are on a 1440p player's machine, and a miss here is his miss.

Why this exists. On 2026-08-20 a player running SCAV CASES ONLY watched the bot log
"scav cases on screen: 0" and then sell his stash. The case was on screen the whole time: it
sits dimmed in the offer creation window and peaked at 0.852, under the 0.9 default. Adding
another reference crop would not have helped, because a crop taken from that very frame and put
through the 1080p convention still only scores 0.896 once needle() grows it back. The threshold
was the problem, so find.CONFIDENCES now holds scav_case at 0.8, and this is the evidence.

Measured over 105 labelled frames from two 1440p players before that number was picked:
  true peaks    0.852 (dimmed and cross-hatched) to 0.960 (dimmed, no hatch)
  false peaks   0.752 across 81 frames with no case on screen
So anything from 0.76 to 0.85 is clean on all of them, and 0.8 is the middle of that.

Exits non-zero if a fixture reads the wrong number of cases.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image  # noqa: E402

from interact import find  # noqa: E402

FIXTURES = Path(__file__).parent / 'fixtures' / '2560x1440'
# file -> how many scav cases are actually in it, and what makes it worth keeping.
CASES = (
    ('scav-case-in-offer-window.png', 1,
     'the reported player, one case dimmed and cross-hatched behind the offer creation window'),
    ('two-scav-cases-in-offer-window.png', 2,
     'two cases side by side, dimmed but unhatched, which is the other way they are drawn'),
    # The negative already in the tree for the filter test: the flea with no stash on screen.
    ('flea-filters-open.png', 0, 'the flea with the filter window open, no stash and no case'),
)

TARGET = 'scav_case'
failures = []

print(f'{TARGET} at confidence {find.confidence_for(TARGET)}\n')
for name, want, why in CASES:
    path = FIXTURES / name
    if not path.exists():
        failures.append(f'{name}: missing from {FIXTURES}')
        print(f'MISSING {name}')
        continue
    fixture = Image.open(path).convert('RGB')
    find.scale = lambda height=fixture.height: height / find.REFERENCE_HEIGHT  # his screen, not ours
    boxes = find.find_all(TARGET, haystack=fixture)
    ok = len(boxes) == want
    if not ok:
        failures.append(f'{name}: found {len(boxes)}, there are {want}')
    print(f'{"ok  " if ok else "FAIL"} {name:36} {len(boxes)}/{want}  '
          f'{[(int(b.left), int(b.top)) for b in boxes]}')
    print(f'     {why}')

print(f'\n{len(failures)} failure(s)')
for line in failures:
    print(f'  {line}')
sys.exit(1 if failures else 0)
