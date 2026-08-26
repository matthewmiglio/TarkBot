"""Report which hideout_tab reference crops read as active vs inactive.

Run:  python tests/test_hideout_tab_active.py                 (every crop in hideout_tab/)
      python tests/test_hideout_tab_active.py <img.png ...>    (specific images)

Applies craft.HIDEOUT_TAB_ACTIVE_BRIGHTNESS (the same threshold is_hideout_tab_active uses) to
each image's mean brightness and prints active/inactive. No game needed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
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
