# Craft soak report: scav case collect: LOOT FROM SCAVS RECEIVE modal not handled, wedges nav

| | |
|---|---|
| **Timestamp** | 2026-09-05 14:24:27 |
| **Revision** | c9881be (dirty: 8 files uncommitted) |
| **Session log** | `tarkbot-20260905-141305.log` |
| **Craft / station** | scav_case (the new, uncommitted moonshine scav-case craft) |
| **Restarted game?** | yes - seasonal, to clear the wedged LOOT FROM SCAVS modal. Also disabled scav_case in the live settings.json from lap 6 on so the soak keeps testing the other 8 crafts (see Proposed solution / note below) |

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 435, in step
    self.tend_scav_case(job)
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 413, in tend_scav_case
    self._swap()
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 160, in _swap
    self._ensure_on(job)
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 137, in _ensure_on
    craft.get_to_station(job.craft, self.region)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 631, in get_to_station
    raise LookupError('hideout tab did not become active after clicking it')
LookupError: hideout tab did not become active after clicking it
```

Last narration before the crash (scav-case tending, log `tarkbot-20260905-141305.log`):

```
[14:19:45.117]   scav_case craft state: done
[14:19:45.117]   collecting the scav_case craft, clicking GET ITEMS at (2084, 751)
[14:19:55.677]   scav_case craft state: ready
[14:19:56.194]   moonshine: ready
[14:19:56.194]   starting the scav case moonshine craft, clicking START at (2083, 806)
[14:19:58.174]   find hideout/handover_button: none of 3 reference images matched (best 0.401)
[14:20:03.073]   scav_case craft state: ready
[14:20:03.611] scav case did not start, so the moonshine input is missing; buying one at up to 230000 from players
[14:20:08.452]   moonshine: no filter by item in the menu, cannot narrow the board to this item, swapping to the next craft
[14:20:56 .. 14:21:12]  hideout tab mean 50 vs 90: inactive   (x20)
LookupError: hideout tab did not become active after clicking it
```

## Diagnosis

The scav case's collect opens a loot-reveal modal that ordinary crafts do not have, nothing
confirms it, and that one un-dismissed modal poisons everything after it. Frame
`1788632472135-find-hideout_hideout_tab.png` shows it: a **"LOOT FROM SCAVS"** dialog, "Scavs have
brought you:" (Xenomorph sealing foam, Smoke balaclava, Ops-Core FAST Visor, Eagle Industries
plate carrier...), with a full-width **RECEIVE** button.

Step by step:

1. The moonshine scav case read `done`, so `tend_scav_case` called `collect_craft`
   (`craft_bot.py:373-374`), which clicked GET ITEMS at `(2084, 751)`. For a normal craft that
   just drops loot into the stash; for a scav case it opens the LOOT FROM SCAVS reveal, which
   waits on a **RECEIVE** click. `collect_craft` (`craft_bot.py:232-249`) knows nothing about
   RECEIVE, so it booked profit and returned with the modal still open.
2. The next scav-case pass re-read the row *through* the modal and got `ready`
   (`14:19:55.677`), because the moonshine bottle is still drawn on the row behind the dim. It
   clicked START `(2083, 806)` (`craft_bot.py:384-385`), which the modal ate.
3. `_confirm_handover(required=False)` correctly found no handover (`best 0.401`, expected for a
   scav case) and shrugged (`craft_bot.py:387`).
4. The re-read still said `ready` (`14:20:03.073`), so the code took the "START did nothing ->
   moonshine must be missing -> buy one" branch (`craft_bot.py:391-408`). But the moonshine was
   never missing; the START was eaten by the modal. This is the blind-spot the method's own
   ponytail comment (`craft_bot.py:359-364`) worried about, reached by a different route: the
   re-read cannot tell "did not start" from "cannot start, modal in the way".
5. `buy_craft_input_item` right-clicked the moonshine bottle for its "filter by item" menu, but
   the right-click landed on the LOOT FROM SCAVS modal, so no menu appeared:
   `no filter by item in the menu ... swapping` (`14:20:08.452`), caught as `LookupError`
   (`craft_bot.py:411-412`).
6. `_swap` (`craft_bot.py:413`) then navigated, and `get_to_station` could not activate the
   hideout tab behind the still-open modal (`mean 50 vs 90` x20) -> the run-ending `LookupError`
   (`craft.py:631`), the same terminal symptom as the wedged-handover report
   ([[20260905-140812_hideout-tab-never-active-wedged-handover-modal-left-by-a-pri]]) but a
   completely different cause.

So this is a genuine gap in the new scav-case feature, exactly what smoke-testing it was meant to
surface: **collecting a scav case is a two-step action (GET ITEMS, then RECEIVE), and only the
first step is implemented.**

## Proposed solution

Handle the LOOT FROM SCAVS / RECEIVE modal as part of the scav case collect. After GET ITEMS on a
scav case, click the **RECEIVE** button (crop it as a new target, e.g.
`hideout/scav_case_receive_button`, and poll for it the way the handover fix polls, since the loot
list takes a moment to populate) before returning. Only the scav case needs this, so it belongs in
`tend_scav_case`'s `done` branch (or a scav-case-specific collect) rather than in the shared
`collect_craft`.

Two supporting changes worth making at the same time:

- **Do not trust the ready-after-START re-read while a modal could be up.** The "still ready ->
  buy moonshine" branch fired on a phantom-missing input purely because a modal ate the START.
  Once RECEIVE is handled this specific path closes, but the re-read remains the only start signal
  and is fragile; a check that the screen is actually clear (no modal) before concluding "did not
  start" would harden it.
- Nothing here is a code fix to apply during the soak.

**Soak note (config change, not a code change):** because this bug re-wedges the game every time a
scav case finishes and forces a restart, scav_case has been disabled in the live
`%APPDATA%/tarkbot/settings.json` (`scav_case_enabled: false`) from lap 6 onward, so the soak can
keep exercising the other eight crafts and the still-open handover bug for hours instead of
looping on this one. The source tree (and its `DEFAULTS`) is untouched; re-enable scav_case in the
GUI once RECEIVE is handled. Mr. President should decide whether to re-enable sooner.

## Recurrences

_(none while scav_case is disabled; if re-enabled and it recurs, note here.)_

## Recurrences

_(Append `- <timestamp> - <craft/station>` lines here if this same signature happens again,
instead of writing a new report.)_
