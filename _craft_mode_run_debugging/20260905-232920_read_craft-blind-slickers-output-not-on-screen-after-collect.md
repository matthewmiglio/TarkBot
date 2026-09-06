# Craft soak report: read_craft blind slickers output not on screen after collect

| | |
|---|---|
| **Timestamp** | 2026-09-05 23:29:20 |
| **Revision** | c9881be (dirty: 12 files uncommitted) |
| **Session log** | `tarkbot-20260905-232745.log` |
| **Craft / station** | Slickers craft (nutrition unit), the re-read right after collecting it |
| **Restarted game?** | No. The game is up; this and Report 7 are the same environmental screen-capture degradation, which a game restart does not touch. Re-ran. |

> **Correction (post-restart):** the root here was the **Tarkov client crashing/closing**, not a
> Windows/GPU capture glitch - the next launch (`tarkbot-20260905-233134.log`) found no Tarkov
> window (`--game status` -> running False). The 16.9s/blank grabs were the fullscreen client
> going down. See the ledger's Session 2 correction note. Restarted onto seasonal.

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 534, in step
    read = craft.read_craft(job.craft, self.region)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 957, in read_craft
    raise Blind(f'{craft.name} output not on screen, cannot read the craft row')
interact.craft.Blind: slickers output not on screen, cannot read the craft row
```

Last narration before the crash:

```
[23:28:00.380]   slickers craft state: done
[23:28:00.380]   collecting the slickers craft, clicking GET ITEMS at (2119, 882)
[23:28:00.603]     frames 1788665280380-pre.png / 1788665280517-post.png around click(2119, 882)
[23:28:22.558]     find errors/stash_full: none of 5 reference images matched ... best 0.000 from None ... in 16.91s
[23:28:27.638]     find hideout/hideout_station_titles/nutrition_unit: ... matched at (1430, 155) 307x16 in 3.06s
[23:28:29.125]     find_all crafting/slickers: 0 raw matches, 0 after dedupe, 0.69s
(then read_craft raised Blind)
```

## Diagnosis

The slickers output was on screen; the read that could not find it got a bad grab. This is the
same environmental screen-capture degradation as Report 7 (`OSError: screen grab failed`), which
happened ~1 minute earlier in the previous run, not a slickers-specific or scav-case bug.

Sequence: slickers read `done`, the runner collected it (GET ITEMS at 23:28:00), and the very next
`step` re-read the row and found no slickers output, so `read_craft` raised `Blind` (craft.py:957,
via craft_bot.py:534). The post-collect frame `1788665280517-post.png` shows the panel fully drawn
with the slickers output bar and its lit GET ITEMS still on the top production row - the output was
there.

What was wrong was the capture, and the timings in the 27-second gap between the collect and the
failed read are the evidence:

- `find errors/stash_full` (part of the collect path) took **16.91s** for what is normally ~1s, and
  logged `best 0.000 from None` - a best-score of exactly 0 against a `None` crop, i.e. the match
  had no usable haystack to score. A healthy grab never scores a flat 0.000.
- The nutrition-unit title find then took **3.06s** (normally sub-second).
- Only then did `find_all crafting/slickers` come back with **0 raw matches** and `read_craft`
  raised.

Grabs going from ~17ms to 17 seconds, plus a `None`/0.000 score, is `screen.grab`
(`ImageGrab.grab`) failing or returning garbage under whatever was stressing the desktop capture -
the same condition that raised `OSError: screen grab failed` outright a minute before. There it
threw; here it returned a frame degraded enough that a real, on-screen output matched nothing. Two
consecutive runs died to the display/capture subsystem, not to game state or bot logic.

## Proposed solution

Two layers, neither applied during the soak:

1. The `screen.grab` retry from Report 7 is the primary fix and covers this too: a grab that fails
   or comes back unusable should be retried a couple of times with a short sleep before the result
   is trusted, so a transient capture stall does not turn into a false "nothing on screen".
2. Defence in depth for `read_craft`: an empty output read is currently `Blind` immediately. Since
   an empty read is exactly what a degraded grab produces, `read_craft` (or its caller) could look
   once more after a short pause before raising, the same poll-before-concluding-failure pattern
   used for the handover and panel-close fixes. A genuinely absent output still raises after the
   retry.

Underlying all of it is that the machine's screen capture was unhealthy for this ~1-minute window
(grabs failing, then taking 16s). If that recurs across restarts it is an environment problem
(display sleep/mode change, GPU/driver, or system load) to chase outside the bot, not more code.

## Recurrences

- Shares a root cause with Report 7 (`screen grab failed`), 20260905-232648. If capture degradation
  keeps ending runs, treat it as one environmental issue across both reports.

## Recurrences

_(Append `- <timestamp> - <craft/station>` lines here if this same signature happens again,
instead of writing a new report.)_
