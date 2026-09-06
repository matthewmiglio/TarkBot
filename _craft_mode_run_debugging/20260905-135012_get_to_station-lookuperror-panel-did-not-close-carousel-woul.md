# Craft soak report: get_to_station: LookupError, panel did not close, carousel would not scroll

| | |
|---|---|
| **Timestamp** | 2026-09-05 13:50:12 |
| **Revision** | c9881be (dirty: 8 files uncommitted) |
| **Session log** | `tarkbot-20260905-134540.log` |
| **Craft / station** | navigating from workbench to the medstation (ai2 craft) |
| **Restarted game?** | no - game healthy (workbench panel just left open); re-ran the loop |

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 443, in step
    self._swap()
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 160, in _swap
    self._ensure_on(job)
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 137, in _ensure_on
    craft.get_to_station(job.craft, self.region)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 647, in get_to_station
    raise LookupError(f'{craft.station} never appeared sweeping the whole carousel both ways')
LookupError: medstation never appeared sweeping the whole carousel both ways
```

Last narration before the crash:

```
[13:47:22.226]   red_gunpowder craft state: producing
[13:47:22.226] red_gunpowder is producing, swapping to the next craft
[13:47:22.226] swapping to the ai2 craft
[13:47:23.054]   not on the medstation, navigating there
[13:47:23.604]   already on the hideout tab, skipping to the module search
[13:47:23.780]   a station panel is open; clicking its close button before navigating
[13:47:23.995]     frames 1788630443780-pre.png / 1788630443919-post.png around click(2504, 131)
[13:47:31.070]   module row grab point (1596, 1333) off 3 icons
[13:47:31.070]   sweeping the carousel for the medstation
[13:47:32.766]     frames ... around dragTo(2263, 1333)
[13:47:34.346]     hideout tab strip changed by 1.7 vs 8.0: hit the end of the list
[13:47:35.068]     frames ... around dragTo(929, 1333)
[13:47:36.630]     hideout tab strip changed by 0.0 vs 8.0: hit the end of the list
LookupError: medstation never appeared sweeping the whole carousel both ways
```

## Diagnosis

The workbench station panel never closed, so the carousel underneath it could not scroll, and the
sweep gave up with a message that blames the wrong thing ("station never appeared").

- After red_gunpowder went to `producing`, `_swap` moved to the ai2 craft and called
  `get_to_station(medstation)` (`craft.py:609`).
- `get_to_station` calls `close_open_station_panel` (`craft.py:635`, defined `craft.py:445-461`)
  to clear the leftover workbench panel that "covers part of the module row and eats the drag".
  It found the close (X) button in `CLOSE_BUTTON_REGION_FRACTIONS` (the far-right strip,
  `craft.py:152`), clicked it at `(2504, 131)`, slept `PANEL_CLOSE_SETTLE`, and **returned True
  without checking the panel actually closed** (`craft.py:459-461`).
- The click did not take. Both frames after it (`1788630443919-post.png`, and the swipe frames
  `1788630452681-post.png` onward) show the **Workbench panel still fully open**, "Items ready",
  red_gunpowder now `Producing (00:58:22)`.
- With the panel still covering the row, `_scroll_to_module` (`craft.py:646, 529`) swiped right,
  measured `did_scroll_mode_hideout_tab` diff `1.7 < 8.0` -> "hit the end of the list", turned
  around, swiped left, diff `0.0` -> "hit the end of the list" again. The row never moved because
  the open panel ate both drags, exactly the case the close was meant to prevent.
- Having swept both ways with no movement, `get_to_station` raised
  `LookupError: medstation never appeared ...` (`craft.py:647`). The medstation was never the
  problem; the panel that would not close was.

This is the same failure shape as the wires `Blind` report from the previous lap
([[20260905-134426_wires-start-blind-no-handover-dialog-appeared]]): a single click is fired and
trusted with no poll to confirm it landed, and one ineffective click on a busy client ends the run.
`close_open_station_panel` clicks the X once and assumes closure; `_confirm_handover` looks once
and assumes absence. Both need to verify.

## Proposed solution

Make `close_open_station_panel` verify the panel actually closed instead of trusting one click.
After clicking the X, poll `close_open_station_panel`'s own `find` (the close button is gone once
the panel is) over a short window and re-click up to a few times, the same shape as `_open_station`'s
`PANEL_TIMEOUT` poll and the handover fix proposed in the sibling report. Only give up (and let the
caller raise) if the panel is still there after the retries. That turns a one-off missed click into
a re-click rather than a whole-run `LookupError`.

Secondary, cheaper guard: if `get_to_station`'s sweep finds the row will not move in *either*
direction (both swipes at ~0 diff on the very first try), that is far more likely a covered/eaten
row than a genuine both-ends-at-once, so it could re-run the close and retry once before raising,
and the raise message could name "row would not scroll (panel still open?)" rather than blaming the
target station. Do **not** apply during the soak.

## Recurrences

_(Append `- <timestamp> - <craft/station>` lines here if this same signature happens again,
instead of writing a new report.)_
