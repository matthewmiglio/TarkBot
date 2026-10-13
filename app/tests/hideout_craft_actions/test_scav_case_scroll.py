"""Wheel the scav case list once, the way the pass does on entry, and report whether both rolls are on screen.

App layer: craft.scroll_scav_case_list and its constants (SCAV_CASE_DEADSPACE_COORD,
SCAV_CASE_SCROLL_NOTCHES, SCAV_CASE_SCROLL_SETTLE) over find.find. This is the live tuning loop for
the scroll: the pass wheels exactly once and then only reads, so one wheel has to leave both the
moonshine and the intelligence rows on screen together.

**This drives the real game.** Tarkov has to be running with the Scav Case panel open. It clicks
the panel dead spot and scrolls the list for real; it buys and starts nothing.

Run:  python tests/hideout_craft_actions/test_scav_case_scroll.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import craft_bot  # noqa: E402
import screen  # noqa: E402
from gui import settings  # noqa: E402
from interact import craft, find  # noqa: E402
from PIL import ImageDraw  # noqa: E402

ROLLS = (craft.SCAV_CASE, craft.SCAV_CASE_INTEL)

find.VERBOSE = True  # so a near-miss shows its score, same as a real craft run
region = craft_bot.build(settings.load(), None).region  # real region/window/monitor

# Fail fast if the scav case panel is not actually open, or the reads run against the wrong screen
# and every look is a meaningless miss (seen once against the Customization panel).
if not find.find(craft.SCAV_CASE_ACTIVE_TARGET, region):
    sys.exit('the Scav Case panel is not open - open it and re-run')

print(f'dead space at {craft.SCAV_CASE_DEADSPACE_COORD} (1080p), '
      f'{craft.SCAV_CASE_SCROLL_NOTCHES} notches down')
craft.scroll_scav_case_list(region)

out_dir = Path(__file__).resolve().parents[1] / 'output' / 'scav_case_scroll'
out_dir.mkdir(parents=True, exist_ok=True)
shot = screen.grab(region).convert('RGB')
d = ImageDraw.Draw(shot)
found = {}
for c in ROLLS:
    box = find.find(c.output_target, region)
    found[c.name] = box
    print(f'{c.name:>16}: {"on screen at " + str(tuple(box)) if box else "NOT ON SCREEN"}')
    if box:
        band = craft.craft_row_band(c, region)  # the band a read takes START / GET ITEMS off (yellow)
        bl, bt, bw, bh = band
        d.rectangle([bl - region[0], bt - region[1], bl - region[0] + bw, bt - region[1] + bh],
                    outline=(255, 200, 0), width=3)
        x0, y0 = box.left - region[0], box.top - region[1]
        d.rectangle([x0, y0, x0 + box.width, y0 + box.height], outline=(0, 255, 0), width=4)
out = out_dir / 'after_scroll.png'
shot.save(out)
print(f'wrote {out}')
sys.exit(0 if all(found.values()) else 1)
