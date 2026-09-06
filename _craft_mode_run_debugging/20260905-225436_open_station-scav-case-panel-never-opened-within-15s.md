# Craft soak report: open_station scav case panel never opened within 15s

| | |
|---|---|
| **Timestamp** | 2026-09-05 22:54:36 |
| **Revision** | c9881be (dirty: 12 files uncommitted) |
| **Session log** | `tarkbot-20260905-223531.log` |
| **Craft / station** | Navigating to the scav case (`_open_station`), between craft passes |
| **Restarted game?** | No. Window is up, no wedged modal; the scav case panel opened cleanly three times earlier in this same run (22:39, 22:44, 22:48). A transient nav miss, recovered by re-running. |

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 539, in step
    self._swap()
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 169, in _swap
    self._ensure_on(job)  # raises if it cannot get there
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 677, in get_to_station
    return _open_station(craft, region)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 712, in _open_station
    raise LookupError(f'clicked the {craft.station} but its panel never opened '
LookupError: clicked the scav case but its panel never opened within 15.0s
```

Last narration before the crash:

```
[22:53:51.637]   scav case found
[22:53:52.133]   clicked the scav case, waiting up to 15.0s for its panel
[22:53:52.133]     frames 1788663231910-pre.png / 1788663232048-post.png around click(1621, 1329)
[22:53:53.188]   scav case panel not open      (x10, once per poll, over the full 15s)
...
LookupError: clicked the scav case but its panel never opened within 15.0s
```

## Diagnosis

The carousel sweep found and clicked the scav case, but the station room never flew in, so
`_open_station` (craft.py:698-712) polled `station_active` for the full 15s and gave up. This is
navigation, not the scav-case craft code: it failed on `_swap` -> `_ensure_on` ->
`get_to_station` before any roll was read.

The post-click frame (`1788663232048-post.png`, 0.1s after the click at (1621, 1329)) shows what
went wrong. The click **did** land on the Scav Case carousel tab and **selected** it - the tab is
highlighted and its gear/settings icon is now drawn above it - but the main viewport is still the
empty hideout overview, with `ENTER` / `BACK` prompts across the top. The station was selected but
not *entered*: the camera never flew into the room, so the room title crop `_open_station` waits on
(`SCAV_CASE_ACTIVE_TARGET`, `station_active`) never appeared, and every one of the ten polls read
"panel not open" correctly.

Why the single click selected without entering is not certain from one frame, but the shape fits a
transient: the same code entered the scav case three times earlier this run on the same single
click. `_open_station` deliberately clicks exactly once, because a second click on an
already-selected tab navigates back *out* of the room (see the craft.py note and Report 2's
lineage), so the one click it is allowed to make occasionally only selects when the game is mid
camera-transition or drops the click's follow-through.

This is the inverse failure to the double-click hazard `_open_station` was written to avoid: one
click is safe against navigating out, but has no recovery when a click selects yet does not enter.

## Update - not scav-case-specific, correlates with the Tarkov memory leak

Lap 9 (log `tarkbot-20260906-011639.log`) raised the identical error on the **nutrition unit**, so
this is a general `_open_station` failure, not a scav-case quirk - the scav case was just where it
showed first and most. Disabling the scav case did not stop it; it moved to the next station.

It also correlates with the Tarkov memory leak (the session root cause, see the ledger). When lap 9
failed, `EscapeFromTarkov.exe` was already back to **17.82 GB** (from 3.62 GB at the fresh restart
~15 min earlier, ~1 GB/min), with the game up and 23 GB system RAM still free - so this was not an
OOM, it was the *bloated-but-alive* client being sluggish. A heavier client is slower to fly the
hideout camera to the room and draw the panel, and `_open_station`'s 15s poll (`PANEL_TIMEOUT`)
starts missing that deadline. This fits the whole arc: fresh client enters fast; a client grown
over ~15-30 min starts failing `_open_station`; a client at ~35 GB OOMs/crashes outright (Reports
7/8). The single-click-selects-but-does-not-enter case from the frame in the original diagnosis is
still real, but client sluggishness from the leak is what turned an occasional miss into the
session's dominant failure.

This means the two real fixes are: (a) keep the client responsive - proactive periodic restarts to
reclaim memory before it bloats, which also prevents the OOM; and/or (b) make `_open_station`
tolerate a slow draw - a longer or adaptive `PANEL_TIMEOUT`, plus the selected-but-not-entered
recovery below. Fix (a) addresses the root; (b) is the local hardening.

### Correction to the memory theory - it is the selected-but-not-entered click, not the leak

A later sighting (lap 10, log `013700`) fails this down. It raised the same error on the nutrition
unit with `EscapeFromTarkov.exe` at only **9.44 GB** - a barely-grown client ~7 min after a fresh
restart, nowhere near bloated - and the failed-poll frame
(`1788673475191-find-hideout_hideout_station_titles_nutrition_unit.png`) shows the decisive state:
the Nutrition Unit carousel tab is **selected** (its settings gear is drawn above it), the main
viewport is the **empty hideout overview**, and the **`ENTER` prompt is up top**. Identical to the
scav-case frame in the original diagnosis. So the room was never entered - the station was only
selected - and this happens independent of memory. The memory leak is a real and separate problem
(it OOMs the run and crashed the client, Reports 7/8), but it is **not** what drives this error;
the driver is `_open_station`'s single click landing as a *select* without the *enter*. Memory
bloat may raise the rate, but a lightly-loaded client hits it too.

So the primary fix is (b), specifically the **selected-but-not-entered recovery**: when the panel
has not appeared and the `ENTER` prompt / selected-tab state is present, press Enter (or click the
ENTER control) once rather than re-clicking the carousel tab. That is the real fix; the longer
`PANEL_TIMEOUT` and the proactive restarts are secondary hardening.

## Proposed solution

Nothing during the soak; re-running recovers it, and it is rare (1 in 4 scav visits this run, 0 in
the other three). If it recurs enough to matter, the fix is a middle path between "click once" and
the forbidden "click twice": have `_open_station`, when the panel has not appeared partway through
its poll, distinguish *selected-but-not-entered* from *not-selected* and act only on the former -
e.g. detect the `ENTER` prompt (or the tab's own selected/gear state) and press Enter / click the
ENTER control once, rather than re-clicking the carousel tab (which would navigate out). That keeps
the single-click safety while adding a recovery for the "selected, camera did not fly" state. Needs
its own crop (`ENTER` prompt or the selected-tab marker) and a test, so it is a deliberate change,
not a soak edit.

Do not apply during the soak.

## Recurrences

- 2026-09-05 23:58 - scav case (`_open_station`), log `tarkbot-20260905-233518.log`. Second sighting,
  post-restart run, game still up (running True) so not a client crash. Same signature: clicked the
  scav case, 15s of "scav case panel not open", `LookupError`. Two occurrences now on the scav case
  specifically - the selected-but-not-entered recovery in Proposed solution is looking necessary
  rather than optional.
- 2026-09-06 01:01 - scav case (`_open_station`), log `tarkbot-20260906-010140.log`. Third sighting,
  and the first on the **very first scav visit right after a fresh restart** (game up, running True).
  This is now the session's dominant failure mode (laps 2, 5, 7). Worth noting the post-restart
  timing: the fresh client may drop or mis-time the first entry click while the hideout camera is
  still settling. The selected-but-not-entered recovery should be prioritised.
- 2026-09-06 01:08 - scav case (`_open_station`), log `tarkbot-20260906-010848.log`. Fourth sighting.
  This lap first worked nutrition/fleece/cordura/wires normally, then died at the scav case, so the
  failure is per-scav-visit, not tied to a fresh boot. Four laps (2, 5, 7, 8) have now ended here.
  Two restarts did not change it (expected: it is a code/nav bug, not game state), so re-running
  just re-hits it. Decision: `scav_case` disabled in settings.json (config, reversible - same call
  as the water collector) so the soak keeps finding *other* errors instead of ending here every lap.
  The 95k feature this session was built to validate is already proven end-to-end (log
  `235854.log`: both rolls started -> produced -> done -> collected). Re-enable once the
  selected-but-not-entered recovery lands.
- 2026-09-06 01:31 - **nutrition unit** (`_open_station`), log `tarkbot-20260906-011639.log`. Fifth
  sighting and the one that proves it is not scav-case-specific (scav case was disabled this lap).
  Client at 17.82 GB when it failed, ~15 min after a fresh restart.
- 2026-09-06 01:44 - **nutrition unit** (`_open_station`), log `tarkbot-20260906-013700.log`. Sixth
  sighting, and the one that corrects the memory theory: client at only **9.44 GB**, and the failed
  frame shows the selected-but-not-entered state (tab selected, empty viewport, `ENTER` prompt). See
  the Correction section above - the driver is the select-without-enter click, not the leak. Game
  stayed up, so re-ran (no restart needed).
- 2026-09-06 02:xx - nutrition unit (`_open_station`), log `tarkbot-20260906-022115.log`. Seventh
  sighting, same select-without-enter. Game up, re-ran. No new information; logged for the count.
