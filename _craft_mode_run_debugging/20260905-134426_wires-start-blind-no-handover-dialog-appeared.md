# Craft soak report: wires START: Blind, no handover dialog appeared

| | |
|---|---|
| **Timestamp** | 2026-09-05 13:44:26 |
| **Revision** | c9881be (dirty: 7 files uncommitted) |
| **Session log** | `tarkbot-20260905-123832.log` |
| **Craft / station** | wires craft, workbench |
| **Restarted game?** | no - the game was fine (workbench panel still open), just re-ran the craft loop |

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 456, in step
    self.start_craft(job, read)
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 179, in start_craft
    if not self._confirm_handover():
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 218, in _confirm_handover
    raise craft.Blind(
interact.craft.Blind: no handover dialog appeared after clicking START, so there is no way to tell whether the craft began
```

Last narration before the crash:

```
[13:42:47.434]   collecting the wires craft, clicking GET ITEMS at (2067, 874)
[13:42:56.001]   workbench panel open
[13:42:56.001]   already on the workbench
[13:42:58.167]   wires craft state: ready
[13:42:58.627]   power_cord: ready
[13:42:58.627]   starting the wires craft, clicking START at (2071, 1016)
[13:42:58.841]     frames 1788630178627-pre.png / 1788630178760-post.png around click(2071, 1016)
Traceback (most recent call last): ... interact.craft.Blind
```

## Diagnosis

A slow (or dropped) handover dialog was read once, too early, and turned into a run-ending
`Blind`. The click itself was correct.

- The wires craft had just been collected: `collect_craft` clicked GET ITEMS at 13:42:47 and
  eight bundles landed. Both frames around the START click (`1788630178627-pre.png` and
  `1788630178760-post.png`, 150 ms apart) show the workbench with eight stacked "Items have been
  put in the stash: Bundle of wires" notifications still animating down the right edge. The game
  was busy digesting that collect.
- The START click landed where it should. `(2071, 1016)` sits on the wires row's START button in
  both frames (the row reads `2/2` with a checkmark, i.e. ready), so this is not a mis-aimed
  click or a wrong-row read.
- `start_craft` (`craft_bot.py:174-179`) then clicks START, sleeps `HANDOVER_DELAY = 1.0 s`
  (`craft_bot.py:37, 178`), and calls `_confirm_handover()`.
- `_confirm_handover` (`craft_bot.py:213-221`) looks for the handover button **exactly once** at
  `loops == 0`. Finding nothing on that single look, with `required=True`, it raises `Blind`
  immediately (`craft_bot.py:216-220`).
- So the whole "did the dialog appear?" decision rests on one screen read taken 1.0 s after a
  click that was fired while the game was mid notification-storm. If the dialog was even slightly
  late to draw (or the click was swallowed by the busy client), that one look misses and the
  entire run ends. This is the only place in the craft path that still does flat-sleep-then-
  single-look instead of polling; everywhere else (`_open_station`'s `PANEL_TIMEOUT` poll,
  `sell.wait_for`, the snipe board waits) polls for a target over a window.
- Whether the craft actually started is unknowable from these two pre-dialog frames. If it did,
  the `Blind` ended a healthy run for nothing; if it did not, a single retry would have caught it.
  Either way, one missed look should not be a run-ender.

## Proposed solution

Poll for the handover button instead of looking once. In `_confirm_handover`, replace the
`loops == 0` single-shot check with a short poll (e.g. `find.find_center` retried over ~2-3 s,
the same shape as `_open_station`'s `PANEL_TIMEOUT` loop or `sell.wait_for`) before concluding
"no dialog". Only raise `Blind` if the button never appears across the whole poll. That keeps the
genuine "START missed, nothing came up" case as a `Blind` while no longer ending a run over a
dialog that was one frame slow after a heavy collect.

Cheaper, alternative framing: raise the single `HANDOVER_DELAY` and/or give `_confirm_handover`
one or two extra looks spaced by a short settle before the `loops == 0` raise. A poll is the
tidier fix and matches the rest of the module. Do **not** apply during the soak.

## Recurrences

**Update (proof the dialog is real):** the frame `1788631608246-find-hideout_hideout_tab.png`,
captured at the start of lap 4, shows the cordura handover dialog from lap 3 still open - titled
"Handover", sling bags and Krasavchik/sewing kits staged, full-width HANDOVER button. So this
`Blind` is a **false negative**, not a missing dialog: the dialog appears but is slow to render
(it stages stash items), and the single look 1.0 s after START fires before the button is
matchable. The proposed poll fix is correct and, unfixed, the abandoned modal wedges the next run
(see [[20260905-140812_hideout-tab-never-active-wedged-handover-modal-left-by-a-pri]]).

- 2026-09-05 14:05:06 - cordura craft, lavatory (lap 3, log `tarkbot-20260905-135055.log`). Same
  traceback and line (`craft_bot.py:218`). This lap navigated cleanly and bought a sling_bag first,
  so it is not tied to the wires post-collect notification storm; confirms the single-look handover
  check is a general run-ender across crafts, not a wires-only quirk. Second sighting of this
  signature in three laps.
