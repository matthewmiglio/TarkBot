"""Scroll the scav case list to a named roll and report whether it was found, and in how many steps.

App layer: craft.find_scav_case_row and its constants (SCAV_CASE_DEADSPACE_COORD,
SCAV_CASE_SCROLL_DOWN, SCAV_CASE_SCROLL_STEPS, SCAV_CASE_SCROLL_SETTLE) over find.find. This is the
live tuning loop for the scroll amount: too few notches per step overshoots the row, too many is
slow, and too few steps gives up before a list left scrolled the wrong way can be swept back.

Was test_find_95k_scav.py, which only ever hunted the 95k roll, because the shipping code only ever
scrolled for that one. Either roll can be the one below the fold, so this takes the roll as an
argument and defaults to running both.

**This drives the real game.** Tarkov has to be running with the Scav Case panel open. It clicks
the panel dead spot and scrolls the list for real; it buys and starts nothing.

Run:  python tests/hideout_craft_actions/test_scav_case_scroll.py            # both rolls
      python tests/hideout_craft_actions/test_scav_case_scroll.py moonshine  # just the one
      python tests/hideout_craft_actions/test_scav_case_scroll.py 95k
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
import screen  # noqa: E402
from gui import settings  # noqa: E402
from interact import craft, find  # noqa: E402
from PIL import ImageDraw  # noqa: E402

ROLLS = {'moonshine': craft.MOONSHINE_TARGET, '95k': craft.NINETY_FIVE_K_TARGET}

wanted = sys.argv[1:] or list(ROLLS)
unknown = [r for r in wanted if r not in ROLLS]
if unknown:
    sys.exit(f'unknown roll(s) {unknown}; pick from {list(ROLLS)}')

# A crop must exist, or find raises deep in the loop with a less obvious message.
for roll in wanted:
    crop_dir = Path(find.REFS) / ROLLS[roll]
    if not any(crop_dir.glob('*.png')):
        sys.exit(f'no reference crop in {crop_dir} yet - add a crop of the {roll} roll input first')

find.VERBOSE = True  # so a near-miss shows its score, same as a real craft run
runner = craft_bot.build(settings.load(), None)  # real region/window/monitor
region = runner.region

# Fail fast if the scav case panel is not actually open, or the hunt runs against the wrong screen
# and every look is a meaningless miss (seen once against the Customization panel).
if not find.find(craft.SCAV_CASE_ACTIVE_TARGET, region):
    sys.exit('the Scav Case panel is not open - open it and re-run')

print(f'dead space at {craft.SCAV_CASE_DEADSPACE_COORD}, {craft.SCAV_CASE_SCROLL_DOWN} notches per '
      f'step, {craft.SCAV_CASE_SCROLL_STEPS} steps down then {craft.SCAV_CASE_SCROLL_STEPS * 2} back up')
out_dir = Path(__file__).resolve().parents[1] / 'output' / 'scav_case_scroll'
out_dir.mkdir(parents=True, exist_ok=True)

results = {}
for roll in wanted:
    print(f'\n--- hunting the {roll} roll ({ROLLS[roll]}) ---')
    box = craft.find_scav_case_row(ROLLS[roll], region)
    results[roll] = box
    if not box:
        print(f'NOT FOUND: the {roll} roll never came into view')
        continue
    print(f'FOUND the {roll} roll at {tuple(box)}')

    # Write the frame it was found on: the row band (yellow) a caller would read START / GET ITEMS
    # off, plus the anchor match itself (green), so a band that frames the wrong row is visible
    # rather than showing up later as a state read that makes no sense.
    band = (craft.scav_case_95k_row_band(box, region) if roll == '95k'
            else craft.craft_row_band(craft.SCAV_CASE, region))
    print(f'row band {tuple(band) if band else None}')
    shot = screen.grab(region).convert('RGB')
    d = ImageDraw.Draw(shot)
    if band:
        bl, bt, bw, bh = band
        d.rectangle([bl - region[0], bt - region[1], bl - region[0] + bw, bt - region[1] + bh],
                    outline=(255, 200, 0), width=3)
    x0, y0 = box.left - region[0], box.top - region[1]
    d.rectangle([x0, y0, x0 + box.width, y0 + box.height], outline=(0, 255, 0), width=4)
    out = out_dir / f'{roll}.png'
    shot.save(out)
    print(f'wrote {out}')

print()
for roll, box in results.items():
    print(f'{roll:>10}: {"found" if box else "NOT FOUND"}')
sys.exit(0 if all(results.values()) else 1)
