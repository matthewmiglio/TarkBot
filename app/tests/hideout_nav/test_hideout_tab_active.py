"""Report which hideout_tab reference crops read as active vs inactive under the brightness gate.

WHAT LAYER THIS TESTS
    interact/craft.py's is_hideout_tab_active read, in isolation from any screen grab: it applies
    craft.HIDEOUT_TAB_ACTIVE_BRIGHTNESS (the exact threshold is_hideout_tab_active uses) to each
    reference crop's mean brightness and calls it active or inactive. is_hideout_tab_active is the
    gate every hideout navigation starts from, so this pins the threshold that decides whether the
    hideout is already open before get_to_station scrolls anywhere.

WHAT IT DOES  (NO GAME NEEDED: reads reference png crops off disk, grabs nothing)
    Runs over every crop in interact/reference_images/hideout/hideout_tab/ (or the image paths
    given on the command line), printing each crop's mean brightness, its active/inactive verdict,
    and a final active count.

Run:  python tests/hideout_nav/test_hideout_tab_active.py                 (every crop in hideout_tab/)
      python tests/hideout_nav/test_hideout_tab_active.py <img.png ...>    (specific images)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from interact import craft, find  # noqa: E402

FOLDER = find.REFS / 'hideout' / 'hideout_tab'


def report(path):
    mean = float(np.asarray(Image.open(path).convert('RGB')).mean())
    active = mean >= craft.HIDEOUT_TAB_ACTIVE_BRIGHTNESS
    print(f'  {"ACTIVE  " if active else "inactive"}  mean={mean:5.1f}  {path.name}')
    return active


if __name__ == '__main__':
    paths = [Path(p) for p in sys.argv[1:]] or sorted(FOLDER.glob('*.png'))
    print(f'threshold {craft.HIDEOUT_TAB_ACTIVE_BRIGHTNESS}')
    actives = sum(report(p) for p in paths)
    print(f'{actives}/{len(paths)} active')
