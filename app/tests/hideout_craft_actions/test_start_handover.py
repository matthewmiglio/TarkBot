"""Start one craft against the live game, checking each of the four steps it takes.

Run:  python tests/hideout_craft_actions/test_start_handover.py            (the wires craft)
      python tests/hideout_craft_actions/test_start_handover.py moonshine  (any name in craft.CRAFTS)

App layer: craft_bot.HideoutCraft's two-step START action, craft_bot.start_craft and its
_confirm_handover (over interact/craft.py's read_craft), which is where clicking START then
confirming the handover dialog actually begins a craft. A craft-actions test, and the one that
does the acting for real.

**This drives the real game.** Tarkov has to be running and sat in the hideout, and this will
navigate to the station and click START for real, so it starts an actual craft when it works.
There is no dry mode: the thing being tested is whether the clicks land.

Why it exists. On 2026-08-30 the wires craft bought its power cord, clicked START, and never
began producing. START on its own does not start anything: it opens a handover dialog that hands
the ingredients over from the stash, and the craft only runs once that dialog's button is
clicked. Any of four things can go wrong and the run's log looks much the same either way, so
this walks them one at a time and says which one broke:

  1. the ingredients are in the stash   (a checkmark under each input icon)
  2. a START button is on the craft's own row
  3. START is clicked
  4. the handover button appears and is clicked

Then it reads the craft state back. That last read is the only real proof: a handover that was
found and clicked but did not take leaves the row exactly as it was, so the four steps can all
report fine while nothing was started. Prints PASS or FAIL per step and exits 0 only if every
one passed, so it is usable from a script.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pyautogui  # noqa: E402

import craft_bot  # noqa: E402
import frames  # noqa: E402
from gui import settings  # noqa: E402
from interact import craft, find, sell  # noqa: E402

DEFAULT_CRAFT = 'wires'


def check(ok, label, detail=''):
    """Print one PASS/FAIL line. detail explains a failure, so it is only printed on one."""
    print(f'  {"PASS" if ok else "FAIL"}  {label}{"" if ok or not detail else " - " + detail}')
    return ok


def start_craft_checked(runner, job):
    """Walk the four steps of starting this craft, then confirm the row actually flipped. bool.

    Uses the same reads and constants craft_bot.start_craft does rather than a copy of them, so a
    threshold or a target changed there changes what this checks.
    """
    name = job.craft.name

    # 0. Be at the station, or none of the reads below mean anything.
    if not craft.station_active(job.craft, runner.region):
        print(f'  ....  not on the {job.craft.station}, navigating there')
        craft.get_to_station(job.craft, runner.region)  # raises LookupError if it cannot
    if not check(craft.station_active(job.craft, runner.region),
                 f'on the {job.craft.station}'):
        return False

    # One read of the row, the same one a real pass makes: it answers the state, frames the row,
    # and hands back the START box and the input queue together. Raises craft.Blind if the row or
    # an input icon will not read, which is the failure this test most wants to see loudly.
    read = craft.read_craft(job.craft, runner.region)
    if read.state != 'ready':
        print(f'  ....  the {name} craft is {read.state!r}, not "ready", so there is nothing to '
              f'start')
        print(f'        wait for it to finish, collect it, or pick a craft that is ready')
        return False

    # 1. The ingredients are in the stash: a checkmark, not an X, under every input icon.
    missing = [n for n, ingredient_ready, _ in read.inputs if not ingredient_ready]
    if not check(not missing, 'ingredients in the stash',
                 f'missing {missing}' if missing else ''):
        return False

    # 2. A START button, on this craft's own row. read_craft scopes that to the output's own row,
    # since the band is tall enough to overlap the row below.
    if not check(read.start is not None, 'START button on that row'):
        frames.capture(f'{name}-no-start')
        return False

    # 3. Click it.
    point = sell.jitter(pyautogui.center(read.start))
    pyautogui.click(*point)
    check(True, f'clicked START at {point}')

    # 4. The handover dialog, which is the step that went missing. The runner's own
    # _confirm_handover does this, rather than a copy of it here, so the retry count and the
    # waits under test are the ones a real craft run uses. It clicks until the dialog is gone,
    # and False means it was never there or would not go away.
    time.sleep(craft_bot.HANDOVER_DELAY)
    if not check(runner._confirm_handover(), 'handover confirmed',
                 f'the dialog was never there, or survived '
                 f'{craft_bot.MAX_HANDOVER_LOOPS + 1} clicks'):
        frames.capture(f'{name}-no-handover')
        return False

    # The proof. A craft that started is no longer ready: it has no START and no GET ITEMS, which
    # is what get_craft_state calls 'producing'.
    time.sleep(craft_bot.START_SETTLE)
    after = craft.read_craft(job.craft, runner.region).state
    if not check(after == 'producing', 'the craft is now producing',
                 f'state is {after!r}, so the handover did not take'):
        frames.capture(f'{name}-not-producing')
        return False
    return True


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CRAFT
    if name not in craft.CRAFTS:
        sys.exit(f'no such craft {name!r}. one of: {", ".join(craft.CRAFTS)}')
    if name == craft.WATER_COLLECTOR_NAME:
        sys.exit('the water collector has no START button and no handover; it is not this test')

    find.VERBOSE = True  # the same narration a real craft run prints, so a miss shows its score
    frames.start()
    # A real runner, off the saved settings, so the monitor, the window rect and the search
    # region are exactly the ones a craft run would use.
    runner = craft_bot.build(settings.load(), None)
    job = next(j for j in runner.jobs if j.craft.name == name)

    print(f'starting the {name} craft at the {job.craft.station}, against the live game')
    ok = start_craft_checked(runner, job)
    frames.flush()
    print(f'\n{"ok" if ok else "FAILED"}: the {name} craft '
          f'{"started" if ok else "did not start"}')
    sys.exit(0 if ok else 1)
