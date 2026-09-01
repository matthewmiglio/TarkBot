"""Can find() locate each craft's items on a real hideout frame, and only on the right station.

App layer under test: interact/find.py's per-target confidence thresholds, find.CONFIDENCES (the
input-icon numbers behind interact/craft.py's ingredient reads: crafting/wires 0.70,
crafting/power_cord 0.65, crafting/crackers 0.80, and why crafting/sewing_kit stays at the 0.9
default). It is the READ half of the craft mode: whether an ingredient icon is seen on the row so
the bot knows to go and buy it. Not navigation, not buying.

What it verifies: each craft's input icons are found on the station they belong to and NOT on the
other station (each frame is the other's negative), exiting non-zero on any miss or false match.

No game needed: it runs entirely off two saved, labelled 1080p fixture frames.

Run:  python tests/hideout_craft_reads/test_craft_input_confidence.py

Two labelled 1080p frames from one session, each the negative for the other:
the lavatory frame holds the fleece craft's inputs and none of the slickers craft's, and the
nutrition unit frame holds the slickers craft's and none of the fleece craft's.

Why this exists. Two failures on 2026-08-27, one loud and one silent.
The loud one: a crafts run spent 151s at the lavatory logging 'could not find sewing_kit on the
craft row to buy it', 22 times, and started 0 crafts, while crafting/start matched the whole time
so the craft was startable and only the input read was wrong.
The silent one: the wires craft was skipped on every single pass without an error, because
find_all('crafting/wires') came back empty at the workbench, so find_craft had no output row, so
get_craft_state returned its then-reading for an output it cannot see, which was 'producing'.
That reading is now a LookupError that ends the run, so this class of blindness cannot be silent
again: tests/test_craft_state_unreadable.py.

The cause behind both is one picture. Tarkov draws a white circular-arrows badge in an item's
bottom left corner when the stash is short of it, and that is exactly the state the bot has to
read in order to go and buy the thing. The badge sits inside the crop, so every reference image
taken from a stocked hideout is the wrong picture of the case that matters.

What made it hard to see is that find.best_score used to measure in colour while pyscreeze
matches in grey (GRAYSCALE_DEFAULT is True), so every 'best 0.xxx' line in the logs was
optimistic. crafting/wires is the clearest case: 0.917 in colour, 0.8955 in grey, refused by the
0.9 default by four thousandths while the log called it a comfortable pass.

Measured over the 241 frames of that session, in grey, present against absent:
  wires        0.8753+ on 104 frames   0.5346 and down on the other 137   -> 0.70
  power_cord   0.7135+ on 102 frames   0.5602 and down on the other 139   -> 0.65
  crackers     0.8852+ on  22 frames   0.7514 and down on the other 219   -> 0.80
  sewing_kit   0.7943 peak             0.65 or better on 235 of 241       -> a fourth crop
The sewing kit is a plain blue rectangle with almost no structure, so in grey it scores high
everywhere and there is no gap to put a threshold in. It got a badged reference crop instead,
which is why it is the one target here still judged at the 0.9 default.

Exits non-zero if an item is not found where it is, or is found where it is not.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image  # noqa: E402

from interact import find  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / '1920x1080'
# frame -> what is on it, and what makes it worth keeping.
FRAMES = (
    ('craft-lavatory-fleece-inputs.png',
     {'crafting/fleece': True, 'crafting/sewing_kit': True, 'crafting/ux_pro_beanie': True,
      'crafting/slickers': False, 'crafting/crackers': False, 'crafting/alyonka': False,
      'crafting/wires': False, 'crafting/power_cord': False},
     'the reported run: the fleece craft open, its sewing kit wearing the badge that broke it'),
    ('craft-nutrition-slickers-inputs.png',
     {'crafting/slickers': True, 'crafting/crackers': True, 'crafting/alyonka': True,
      'crafting/fleece': False, 'crafting/sewing_kit': False, 'crafting/ux_pro_beanie': False,
      'crafting/wires': False, 'crafting/power_cord': False},
     'the other station from the same session, so each frame is the other one\'s negative'),
)

failures = []
for name, wants, why in FRAMES:
    path = FIXTURES / name
    if not path.exists():
        failures.append(f'{name}: missing from {FIXTURES}')
        print(f'MISSING {name}')
        continue
    fixture = Image.open(path).convert('RGB')
    find.scale = lambda height=fixture.height: height / find.REFERENCE_HEIGHT  # the frame's screen
    print(f'\n{name}  {fixture.width}x{fixture.height}')
    print(f'  {why}')
    for target, want in sorted(wants.items()):
        box = find.find(target, haystack=fixture)
        peak, crop = find.best_score(target, haystack=fixture)
        ok = bool(box) == want
        if not ok:
            failures.append(
                f'{name}: {target} {"not found where it is" if want else "found where it is not"}'
                f' (grey peak {peak:.4f} against confidence {find.confidence_for(target)})')
        print(f'  {"ok  " if ok else "FAIL"} {target:24} want {"present" if want else "absent ":7}'
              f'  grey peak {peak:.4f}  at {find.confidence_for(target)}  {crop}')

print(f'\n{len(failures)} failure(s)')
for line in failures:
    print(f'  {line}')
sys.exit(1 if failures else 0)
