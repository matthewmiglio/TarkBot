"""
Reroll Ragman's operational 'Find and transfer' daily until it asks for WD-40 (100ml).

Open the game on TRADERS > TASKS with Ragman selected, then run:
    python _sudak_daily_resetter/daily_resetter.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))  # interact/ is a namespace package

import pyautogui

import screen
from interact import find
from narrate import log

OFFER = 'tasks/find_and_transfer_daily_offer'
REPLACE = 'tasks/replace_daily_button'
WD_40 = 'tasks/wd_40_100ml'

# Where the objective row sits, as fractions of the screen (left, top, width, height), so it lands
# in the same place at any resolution. Measured off fixtures/wd_40_100ml_example_offer_daily_frame.png
# (2560x1440) with region_picker.html: the 'Hand over the found in raid item' bar. Retune there.
OBJECTIVE_FRACTIONS = (0.251, 0.550, 0.745, 0.106)

# The crop is '(100ml)' alone. A crop of the whole objective line is mostly text every offer shares,
# which let 'Ripstop fabric' (0.836) and then 'WD-40 (400ml)' (0.987) through. The '(100ml)' crop
# reads 0.991 on 100ml, 0.872 on 400ml, 0.566 on Ripstop; 0.95 sits in that gap. Center subcrops
# of it were dropped: smaller is mostly the shared '00ml', and the 70% one read 0.945 on 400ml.
WD_40_CONFIDENCE = 0.95

SETTLE = 0.5  # after clicking the offer, before reading its objective. ponytail: a guess, tune it
REPLACE_SETTLE = 1.0


def objective_region():
    left, top, width, height = screen.rect()
    fl, ft, fw, fh = OBJECTIVE_FRACTIONS
    return (left + round(width * fl), top + round(height * ft), round(width * fw), round(height * fh))


def _find_or_raise(name):
    point = find.find_center(name, region=screen.rect())
    if point is None:
        raise LookupError(f'{name} is not on screen')
    return point


def find_find_and_transfer_daily_offer():
    """(x, y) of the 'Find and transfer' row in the task list."""
    return _find_or_raise(OFFER)


def find_replace_daily_button():
    """(x, y) of the REPLACE button."""
    return _find_or_raise(REPLACE)


def check_if_wd_40_100ml_offer():
    """Is the selected task's objective asking for WD-40 (100ml)."""
    return find.find(WD_40, region=objective_region(), confidence=WD_40_CONFIDENCE) is not None


def click_daily_offer():
    pyautogui.click(*find_find_and_transfer_daily_offer())
    time.sleep(SETTLE)


def reset_daily_task():
    """Replace the task, then reopen it: the panel keeps showing the old offer until it is clicked."""
    pyautogui.click(*find_replace_daily_button())
    pyautogui.press('y')
    time.sleep(REPLACE_SETTLE)
    click_daily_offer()


def main():
    rerolls = 0
    click_daily_offer()
    while True:
        if check_if_wd_40_100ml_offer():
            log(f'WD-40 (100ml) offer up after {rerolls} rerolls')
            break
        reset_daily_task()
        rerolls += 1
        log(f'rerolled ({rerolls})', 1)


if __name__ == '__main__':
    main()
