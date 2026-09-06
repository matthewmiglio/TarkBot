# Craft soak report: water_filter_state blind both fitted and empty matched

| | |
|---|---|
| **Timestamp** | 2026-09-05 22:31:18 |
| **Revision** | c9881be (dirty: 12 files uncommitted) |
| **Session log** | `tarkbot-20260905-222107.log` |
| **Craft / station** | Water collector (`tend_water_collector`, reading the filter slot) |
| **Restarted game?** | No. Not a wedged modal or a dead client, so a restart fixes nothing; it is a detection bug that reproduces on any empty-slot pass. Water collector disabled in `settings.json` (config, not code) so the soak keeps exercising the other crafts and the scav case; noted in the ledger. |

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 345, in tend_water_collector
    if craft.water_filter_state(self.region) == 'fitted':
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 1478, in water_filter_state
    raise Blind('the water collector slot matched both a fitted filter and the empty-slot '
interact.craft.Blind: the water collector slot matched both a fitted filter and the empty-slot icon, so one of those two crop sets is too loose to tell them apart
```

Last narration before the crash:

```
[22:30:39.714]   already on the water collector
[22:30:41.394]     find crafting/water_filter: a51230f7-...-55249a20bddc.png (6/8) matched at (1796, 805) 83x59 in 0.80s
[22:30:41.678]     find crafting/missing_water_filter: 92ed18da-...-554887ed5a7a.png (1/4) matched at (1732, 835) 59x87 in 0.28s
```

## Diagnosis

The water collector's slot is **empty**, and `water_filter_state` (craft.py:1462) misread it as
being both empty and fitted at once, which it treats as unreadable (`Blind`, craft.py:1477).

`water_filter_state` asks two positive questions over the same region and requires exactly one to
answer yes: `find(WATER_FILTER_TARGET)` for a filter fitted in the slot, and
`find(MISSING_WATER_FILTER_TARGET)` for the empty-slot X. Both came back truthy, so it cannot say
which state the slot is in and raises rather than guess (craft.py:1475-1479).

Running both crop sets against the crash frame (`1788661840680-find-crafting_water_filter.png`)
shows which read is the false one:

- `crafting/missing_water_filter` matched at **0.956**, box (1732, 835, 59, 87). The zoom crop is
  the big **X** empty-slot icon. This is the true state: the slot is empty.
- `crafting/water_filter` matched at **0.853**, box (1796, 805, 83, 59). The zoom crop is **not a
  filter in the slot** - it is the panel's filter dropdown chrome (the "Item name" strip and its
  down-arrow), which sits just up and to the right of the slot. This is a false positive.

So the fitted-filter crop is the loose one. Two things line up to make it fire:

1. **Whole-window region.** `tend_water_collector` passes `self.region` (the entire game window),
   not a box around the slot (craft_bot.py:345). That lets the fitted-filter crop match UI chrome
   64px away from the slot it is meant to read - the dropdown control is nowhere near the slot's X,
   but it is well within the window.
2. **A loose crop.** The winning crop is `a51230f7-...bddc.png`, the 6th of the 8 in
   `reference_images/crafting/water_filter/`, and it scores 0.853 on that dropdown chrome - only
   0.023 over the 0.83 default (`find.CONFIDENCE`). One of the eight fitted crops generalises to a
   grey rounded control with an arrow on it.

The empty-slot read is strong and correct (0.956); the failure is entirely the fitted read hitting
chrome the region should never have included.

## Proposed solution

Scope both reads to the slot, not the whole window. Give `water_filter_state` a slot region built
from window fractions (the panel is fixed-layout, so the slot sits at a stable fraction), the way
`close_open_station_panel` already scopes its close-button find with `_region_from_fractions`, and
pass it to both `find` calls. A box tight to the slot (~(1720, 800)-(1800, 925) at 2560x1440)
contains the X and a genuinely-fitted filter but excludes the dropdown chrome at (1796, 805), so
the 0.853 false positive can no longer be seen and only the true state matches. This is more robust
than a threshold bump: the present-state fitted score is unknown here (the slot is empty), so there
is no measured gap to place a `find.CONFIDENCES['crafting/water_filter']` entry in without risking
the real fitted read. Region-scoping needs no such number and matches the repo's existing pattern
for exactly this class of "a loose crop matches lookalike chrome elsewhere in the window" bug.

A cheaper, additive option if the slot region is awkward to pin: drop or re-crop the one loose
fitted image (`a51230f7-...bddc.png`) so no fitted crop generalises to the dropdown arrow. That
removes this specific false positive but leaves the whole-window search able to find the next
lookalike, so the region fix is the real one.

Do not apply during the soak.

## Recurrences

_(Append `- <timestamp> - <craft/station>` lines here if this same signature happens again,
instead of writing a new report.)_
