"""Scroll the scav case list to the 95,000-rouble roll and report whether it was found and in how
many scrolls.

App layer: craft.find_scav_case_95k_craft's constants and target (SCAV_CASE_DEADSPACE_COORD,
SCAV_CASE_SCROLL_DOWN, FIND_95K_CRAFT_TIMEOUT, NINETY_FIVE_K_TARGET) over find.find. This runs the
same click-then-wheel-down hunt the shipping method does, but counts the scrolls and narrates each
one, so the scroll amount can be tuned live: too few scrolls overshoots, too many is slow.

**This drives the real game.** Tarkov has to be running with the Scav Case panel open. It clicks
the panel dead spot and scrolls the list for real; it buys and starts nothing.

Run:  python tests/hideout_craft_actions/test_find_95k_scav.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import craft_bot  # noqa: E402
import screen  # noqa: E402
from gui import settings  # noqa: E402
from interact import craft, find  # noqa: E402
from PIL import ImageDraw  # noqa: E402

# A crop must exist, or find raises deep in the loop with a less obvious message.
crop_dir = Path(craft.find.REFS) / craft.NINETY_FIVE_K_TARGET
if not any(crop_dir.glob('*.png')):
    sys.exit(f'no reference crop in {crop_dir} yet - add a crop of the 95k roll input first')

find.VERBOSE = True  # so a near-miss shows its score, same as a real craft run
runner = craft_bot.build(settings.load(), None)  # real region/window/monitor
region = runner.region

# Fail fast if the scav case panel is not actually open, or the hunt runs against the wrong screen
# and every look is a meaningless miss (seen once against the Customization panel).
if not find.find(craft.SCAV_CASE_ACTIVE_TARGET, region):
    sys.exit('the Scav Case panel is not open - open it (scrolled to the top) and re-run')

coord = craft.SCAV_CASE_DEADSPACE_COORD
print(f'clicking deadspace at {coord} for wheel focus, then wheeling down by '
      f'{craft.SCAV_CASE_SCROLL_DOWN} up to {craft.FIND_95K_CRAFT_TIMEOUT:.0f}s')
pyautogui.click(*coord)

deadline = time.time() + craft.FIND_95K_CRAFT_TIMEOUT
scrolls = 0
found_box = None
while time.time() < deadline:
    found_box = find.find(craft.NINETY_FIVE_K_TARGET, region)
    if found_box:
        break
    pyautogui.scroll(-craft.SCAV_CASE_SCROLL_DOWN)  # negative wheels down
    scrolls += 1
    print(f'  scroll #{scrolls}')
    time.sleep(0.3)

print()
if found_box:
    print(f'FOUND the 95k roll after {scrolls} scroll(s) at {tuple(found_box)}')
    # Write the frame it was found on: the full-width row band (yellow) derived from the input
    # match, plus the input match itself (green). The band is what a caller would read START /
    # GET ITEMS off, so this shows whether the thinner text-only crop still frames the row.
    band = craft.scav_case_95k_row_band(found_box, region)  # 95k exception band, absolute screen coords
    print(f'row band {tuple(band)}')
    out_dir = Path(__file__).resolve().parents[1] / 'output' / 'find_95k_scav'
    out_dir.mkdir(parents=True, exist_ok=True)
    shot = screen.grab(region).convert('RGB')
    d = ImageDraw.Draw(shot)
    bl, bt, bw, bh = band
    d.rectangle([bl - region[0], bt - region[1], bl - region[0] + bw, bt - region[1] + bh],
                outline=(255, 200, 0), width=3)
    x0, y0 = found_box.left - region[0], found_box.top - region[1]
    d.rectangle([x0, y0, x0 + found_box.width, y0 + found_box.height], outline=(0, 255, 0), width=4)
    out = out_dir / 'found.png'
    shot.save(out)
    print(f'wrote {out}')
else:
    print(f'NOT FOUND within {craft.FIND_95K_CRAFT_TIMEOUT:.0f}s ({scrolls} scrolls)')
sys.exit(0 if found_box else 1)
