# Craft soak report: hideout tab never active: wedged Handover modal left by a prior Blind

| | |
|---|---|
| **Timestamp** | 2026-09-05 14:08:12 |
| **Revision** | c9881be (dirty: 8 files uncommitted) |
| **Session log** | `tarkbot-20260905-140545.log` |
| **Craft / station** | run start (first `_ensure_on`), navigating to the first station |
| **Restarted game?** | yes - seasonal. A leftover Handover modal was wedged over everything and no run could get past it; only a client restart clears it |

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 497, in start
    self._ensure_on(self.jobs[self.index])
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 137, in _ensure_on
    craft.get_to_station(job.craft, self.region)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 631, in get_to_station
    raise LookupError('hideout tab did not become active after clicking it')
LookupError: hideout tab did not become active after clicking it
```

Last narration before the crash (the same line ~20 times over ~18s):

```
[14:06:31.277]   hideout tab mean 50 vs 90: inactive
...
[14:06:48.731]   hideout tab mean 50 vs 90: inactive
LookupError: hideout tab did not become active after clicking it
```

## Diagnosis

**This is the aftermath of the handover `Blind`, and it also disproves that Blind's first
assumption.** The prior lap (lap 3) clicked START on the cordura craft, raised
`Blind: no handover dialog appeared`, and ended. But the dialog *had* appeared, or appeared right
after the single look: the frame captured at run start of this lap,
`1788631608246-find-hideout_hideout_tab.png`, shows a **"Handover" dialog wide open** over the
lavatory - titled "Handover", "Stash items selected:" with two sling bags and two Krasavchik
(sewing kit) icons staged, and a full-width **HANDOVER** confirm button at the bottom. So the
handover dialog is real for these crafts; the `Blind` was a false negative from
`_confirm_handover` looking exactly once, `HANDOVER_DELAY = 1.0 s` after the click
(`craft_bot.py:178, 213-221`), before this dialog - which has to fetch and draw the staged stash
items - had finished rendering a matchable button.

The knock-on failure this report is filed under:

- That `Blind` ended lap 3 with the Handover modal still open.
- Lap 4 started, `craft_bot.start` called `_ensure_on(jobs[0])` -> `get_to_station`
  (`craft_bot.py:497`, `craft.py:609`).
- `get_to_station` reads `is_hideout_tab_active`; the Handover modal dims the whole screen behind
  it, so the hideout tab reads `mean 50 vs 90: inactive`. It clicked the tab and polled
  `wait_hideout_tab_active` for `TAB_TIMEOUT` (`craft.py:630`), but the tab stayed dimmed under
  the modal the entire time, so it never crossed 90.
- After the timeout it raised `LookupError: hideout tab did not become active after clicking it`
  (`craft.py:631`).
- Every fresh run repeats this immediately: the modal is still up, the tab still reads dim, the
  poll still times out. The bot has no path that dismisses a leftover Handover modal at startup,
  so it is wedged - the skill's "a modal the bot cannot clear is in front of everything." Hence
  the game restart.

Root of the whole chain is still the single-look handover confirm (see
[[20260905-134426_wires-start-blind-no-handover-dialog-appeared]]): had it polled for the button
instead of looking once, it would have confirmed this very dialog, started the craft, and never
left a modal to wedge the next run.

## Proposed solution

Two fixes, the first being the real one:

1. **Poll for the handover button instead of looking once** (the fix already proposed in the
   wires `Blind` report). This dialog is slow because it stages stash items; a single look 1.0 s
   after START is simply too early. Polling `HANDOVER_TARGET` over ~2-3 s before concluding "no
   dialog" would have caught it, confirmed the handover, and prevented both the false `Blind` and
   this wedged-modal aftermath. Also worth checking that `HANDOVER_TARGET`
   (`hideout/handover_button`) actually matches this dialog's full-width **HANDOVER** button and
   not some earlier variant, since a stale crop would defeat even a poll.

2. **Defensive startup recovery** (belt and braces, like the flea bot's `_recover`): before the
   first navigation, dismiss any leftover modal (press esc / click a close X) so a run started
   into a wedged state can dig itself out instead of timing out on the hideout tab and needing a
   client restart. Without fix 1 this only papers over the symptom, but it removes the one
   failure that forces a manual/automated game restart mid-soak.

Do **not** apply during the soak.

## Recurrences

_(Append `- <timestamp> - <craft/station>` lines here if this same signature happens again,
instead of writing a new report.)_
