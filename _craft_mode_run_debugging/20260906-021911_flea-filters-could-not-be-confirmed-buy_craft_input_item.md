# Craft soak report: flea filters could not be confirmed buy_craft_input_item

| | |
|---|---|
| **Timestamp** | 2026-09-06 02:19:11 |
| **Revision** | c9881be (dirty: 12 files uncommitted) |
| **Session log** | `tarkbot-20260906-014710.log` |
| **Craft / station** | red_gunpowder, buying its green_gunpowder input on the flea |
| **Restarted game?** | No. Game up; a stuck purchase dialog is transient, cleared by the next run. Re-ran. |

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 1329, in buy_craft_input_item
    raise Blind('the flea filters could not be confirmed, so no price on this board can be '
interact.craft.Blind: the flea filters could not be confirmed, so no price on this board can be trusted
```

Last narration before the crash:

```
[02:18:34.048] buying 1 green_gunpowder at up to 50000 from players
[02:18:35.342]   clicking filter by item at (1744, 1084)
[02:18:39.731]   44888 is at or under 50000 before filtering, buying
[02:18:41.153]   the screen is 0.50 of its old brightness, so the purchase dialog is still up and nothing has been bought
[02:18:42.104]   still nothing, answering 'n' so the dialog cannot block the next item
[02:18:42.957]   lost that offer before filtering; setting the filters and reading the board properly
[02:18:43.166]   opening the filter window at (643, 113)
[02:18:47.647]   the filter window did not open. Something else is in front of the flea: check the frame saved around that click
(then Blind)
```

## Diagnosis

A purchase confirmation dialog got stuck open, and the code proceeded as if it had closed, so the
next thing it tried to do (open the filter window) was blocked by that modal and it raised `Blind`.

The flow: red_gunpowder needed green_gunpowder, so `buy_craft_input_item` right-clicked the input,
narrowed the board by item, and saw a top offer (44888) at or under the 50000 ceiling, so it went
to buy it "before filtering" (the fast path for an already-cheap board). The buy pressed its
confirm, then checked the balance: the screen was still 0.50 of its pre-click brightness, which is
the purchase dialog still being up with nothing bought (the offer was lost to another buyer, the
common flea race). It logged that, then "answering 'n' so the dialog cannot block the next item"
and moved to the fallback: set the filters properly and re-read the board.

But the 'n' did not close the dialog. The frame the log points to (`1788675523325-post.png`, taken
around the filter-gear click at (643, 113)) shows the **Item purchase dialog still open** over a
dimmed board - "Are you sure you want to buy Eagle (1) for 44888 P? YES (Y) / NO (N)" - with the
gear click landing on that dimmed, modal-blocked screen. Tarkov ignored the 'n', the same way it
sometimes ignores the 'y' (documented in sell.py's `buy`/`purchase_landed`: "Tarkov's confirmation
sometimes does not take the 'y' at all"). With the modal still up, the filter gear click did
nothing, the filter window never opened, and `buy_craft_input_item` (craft.py:1329) treated an
unconfirmable filter set as `Blind` - correctly, since a board it cannot filter cannot be trusted.
The real fault is upstream: the code assumed one 'n' dismissed the dialog and never verified.

## Proposed solution

Verify the purchase dialog actually closed before moving on, the same poll-to-confirm pattern used
for the handover and panel-close fixes. After answering 'n' (or 'y'), re-check the dimming/dialog
and, if it is still up, press again (Escape as well as 'n') until the screen brightness returns or
a small retry budget is spent. Only once the dialog is confirmed gone should the fallback go on to
open the filter window. That turns "sometimes the key is dropped" from a run-ending `Blind` into a
one-retry recovery. The shared flea `dismiss_error_popup`/brightness helpers in sell.py already
have the pieces (a brightness read is what detected the stuck dialog here); the buy path just needs
to loop on it rather than fire once. Keep the `Blind` as the final give-up if the dialog truly will
not clear, so a genuinely wedged flea still stops loudly.

Do not apply during the soak.

## Recurrences

_(Append `- <timestamp> - <craft/station>` lines here if this same signature happens again,
instead of writing a new report.)_
