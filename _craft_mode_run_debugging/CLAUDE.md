# Craft-mode soak debugging

Bug reports from soak-testing hideout craft mode (the `pressure-test-crafting` skill). One
`<timestamp>_<signature>.md` per distinct error, recurrences appended to the report they match.

## The log ledger — keep it current

Every craft run writes one session log to `%APPDATA%/tarkbot/logs/` (a soak run's log is the one
that appears after the run starts; see the skill). The table below tracks every soak log and
whether its outcome has been dealt with.

**Any agent ingesting these logs and handling the errors in them MUST keep this ledger up to
date.** Specifically:

- When a run finishes, add its log filename here as **new**.
- Once you have triaged it, move it to **handled** or **unhandled**:
  - **handled** — its error is diagnosed and written into a report (or appended as a recurrence to
    an existing one), OR it ended benignly (a clean Stop, or a StashFull that is the user's to
    clear) and needs no report. Say which report, or "benign".
  - **unhandled** — reviewed and it contains an error that is not yet documented, or not yet
    reviewed at all. Come back to it.
- Never delete rows. Logs age out of `%APPDATA%` (only the 10 newest survive), but their ledger
  row stays as the record that they were handled.

### Status legend

| Status | Meaning |
|---|---|
| new | just generated, not yet triaged |
| unhandled | has an error not yet diagnosed/documented, or not yet reviewed |
| handled | documented in a report / recurrence, or benign (no report needed) |

### Ledger

Session 1 (2026-09-05 soak, scav_case enabled through log `141305`, disabled from `142911` on):

| Log file | Outcome | Status | Report / note |
|---|---|---|---|
| `tarkbot-20260905-123832.log` | wires craft `Blind`, no handover dialog seen after START | handled | [Report 1](20260905-134426_wires-start-blind-no-handover-dialog-appeared.md) |
| `tarkbot-20260905-134540.log` | `LookupError: medstation never appeared` (panel would not close, ate the swipes) | handled | [Report 2](20260905-135012_get_to_station-lookuperror-panel-did-not-close-carousel-woul.md) |
| `tarkbot-20260905-135055.log` | cordura craft `Blind`, same handover single-look | handled | Report 1 (recurrence) |
| `tarkbot-20260905-140545.log` | `hideout tab did not become active` — wedged handover modal from the prior Blind | handled | [Report 3](20260905-140812_hideout-tab-never-active-wedged-handover-modal-left-by-a-pri.md) |
| `tarkbot-20260905-141305.log` | scav case collect left LOOT FROM SCAVS / RECEIVE modal open, wedged nav | handled | [Report 4](20260905-142427_scav-case-collect-loot-from-scavs-receive-modal-not-handled-.md) |
| `tarkbot-20260905-142911.log` | StashFull after ~12 min (3 crafts started, ~92k profit) — clean stop | handled | benign (stash is the user's to empty) |
| `tarkbot-20260905-144152.log` | StashFull after 54 s (0 crafts) — clean stop, stash saturated | handled | benign (soak paused pending stash clear) |

Pre-soak logs (`120313`, `113325`, `113302`, and older) are out of scope: not craft-soak runs.

Session 2 (2026-09-05 evening soak, scav_case re-enabled to exercise the new moonshine -> 95k ->
leave sequence; water_collector disabled from log `222107` on, see the row below):

| Log file | Outcome | Status | Report / note |
|---|---|---|---|
| `tarkbot-20260905-222107.log` | water collector `Blind`: `water_filter_state` matched both a fitted filter (0.853 false positive on dropdown chrome) and the empty-slot X (0.956) | handled | [Report 5](20260905-223118_water_filter_state-blind-both-fitted-and-empty-matched.md); water_collector disabled in settings.json afterwards so the soak continues |
| `tarkbot-20260905-223531.log` | 95k scav case sequence validated live (moonshine started, scrolled to 95k, read ready, START clicked); then `LookupError: clicked the scav case but its panel never opened within 15s` on the 4th scav visit (`_open_station`, transient nav miss) | handled | [Report 6](20260905-225436_open_station-scav-case-panel-never-opened-within-15s.md); also noted the non-fatal 95k re-read anchor bug (started roll misreported as "did not start"), fix pending |
| `tarkbot-20260905-225640.log` | ran clean ~30 min (both scav rolls producing, all crafts cycling), then `OSError: screen grab failed` during a fleece flea buy - a transient Windows desktop-capture failure, not bot logic | handled | [Report 7](20260905-232648_screen-grab-failed-oserror-during-flea-buy.md) |
| `tarkbot-20260905-232745.log` | died ~40s in: `Blind: slickers output not on screen` right after collecting slickers - grabs in that window took 16.9s / returned blank (same capture degradation as Report 7, ~1 min later) | handled | [Report 8](20260905-232920_read_craft-blind-slickers-output-not-on-screen-after-collect.md) (shares root with Report 7) |
| `tarkbot-20260905-233134.log` | run aborted at startup: "Tarkov window not found" - the game client had crashed/closed | handled | benign (no soak error); the true root of the two rows above |

Session 2 continued (post-restart onto seasonal):

| Log file | Outcome | Status | Report / note |
|---|---|---|---|
| `tarkbot-20260905-233518.log` | ran clean ~23 min post-restart (crafts cycling, both scav rolls producing), then `LookupError: clicked the scav case but its panel never opened within 15s` - 2nd sighting, game still up | handled | [Report 6](20260905-225436_open_station-scav-case-panel-never-opened-within-15s.md) (recurrence) |
| `tarkbot-20260906-010140.log` | failed on the first scav visit right after the memory-reclaim restart: `LookupError: clicked the scav case but its panel never opened within 15s` - 3rd sighting, game up | handled | [Report 6](20260905-225436_open_station-scav-case-panel-never-opened-within-15s.md) (recurrence); dominant failure this session |
| `tarkbot-20260906-010848.log` | worked several crafts, then died at the scav case again (4th sighting): `LookupError: clicked the scav case but its panel never opened within 15s` | handled | [Report 6](20260905-225436_open_station-scav-case-panel-never-opened-within-15s.md) (recurrence); **scav_case disabled in settings.json afterwards** - 95k already validated (log `235854`), and re-hitting this every lap blocks finding other errors |
| `tarkbot-20260906-011639.log` | ~15 min in (scav case off) died at the **nutrition unit**: `LookupError: clicked the nutrition unit but its panel never opened within 15s` - proves `_open_station` is station-agnostic; client at 17.82 GB (leak-bloated, sluggish) | handled | [Report 6](20260905-225436_open_station-scav-case-panel-never-opened-within-15s.md) (recurrence + Update: ties `_open_station` to the memory leak) |
| `tarkbot-20260906-013623.log` | started then killed by the operator seconds in (launched detached by mistake, relaunched tracked) | handled | benign (operational, no soak content) |
| `tarkbot-20260906-013700.log` | ran ~7 min, died at nutrition unit `_open_station` at only 9.44 GB - frame shows selected-but-not-entered (ENTER prompt, empty viewport) | handled | [Report 6](20260905-225436_open_station-scav-case-panel-never-opened-within-15s.md) (recurrence; **corrects the memory theory** - the driver is the select-without-enter click, not the leak) |
| `tarkbot-20260906-014710.log` | ran ~31 min (longest clean stretch), then a **new** error: `Blind: the flea filters could not be confirmed` buying green_gunpowder - a purchase dialog stuck open (Tarkov ignored the 'n'), modal-blocked the filter window | handled | [Report 9](20260906-021911_flea-filters-could-not-be-confirmed-buy_craft_input_item.md) (new signature) |
| `tarkbot-20260906-022115.log` | nutrition unit `_open_station` again (7th sighting), game up | handled | [Report 6](20260905-225436_open_station-scav-case-panel-never-opened-within-15s.md) (recurrence) |
| `tarkbot-20260906-022639.log` | ran ~3 min, clean **StashFull** stop (exit 0): "the stash is full... empty the stash and start again" (0 started, est. profit 52305) | handled | benign (stash is the user's to empty); **soak paused pending stash clear** |

**Soak paused (2026-09-06 ~02:29): stash full.** Every run now StashFulls immediately until the
stash is emptied (the user's to do). Session 2 findings are complete: Reports 5-9 plus the memory
leak, and the 95k feature validated end-to-end (log `235854`). Resume by emptying the stash and
re-running `python -m cli --mode craft` (re-enable water_collector and scav_case in settings.json
first if their fixes have landed; both are disabled now).
| `tarkbot-20260905-235854.log` | ran clean ~56 min - both scav rolls finished and were being collected (first scav collect this session, incl. the 95k roll full lifecycle: started -> produced -> done -> collect) - when the bot process was **OOM-killed by Windows**, not a bot error | handled | benign to the bot; root cause = Tarkov memory leak (below) |

**Session root cause - Tarkov memory leak.** When lap 6 was OOM-killed, `Win32_OperatingSystem`
showed **5.34 GB free of 63.91 GB (8.4%)**, with **EscapeFromTarkov.exe alone at 34.97 GB** (next
was chrome at 3.25 GB; each bot process ~0.5 GB). Tarkov's working set grows the longer it runs, so
over a multi-hour soak it exhausts RAM and Windows kills whatever it can - the bot process here,
and almost certainly the **client itself at laps 3-4** (Report 7/8's "screen grab failed" and
16.9s/blank grabs were the leaked-out client being taken down, which is why the next launch found
no window). This is the real root of every environmental failure this session. Mitigation: restart
Tarkov periodically to reclaim the memory (a fresh client is a few GB); the soak's restart step
does this on a crash, but a proactive time- or memory-based restart would avoid losing the run.
Restarted onto seasonal after lap 6 to reclaim the 35 GB.

**Correction (post-restart):** the "screen-capture degradation" blamed in Reports 7 and 8 was
actually the **Tarkov client crashing/closing**. Proven by the next launch (`233134`) finding no
Tarkov window at all (`--game status` -> running False). Lap 3's `screen grab failed` and lap 4's
16.9s/blank grabs were the fullscreen client going down and taking the desktop capture with it, not
a Windows/GPU glitch. Restarted the game onto the **seasonal** profile and resumed. The
`screen.grab` retry proposed in those reports is still worth having (it would turn a client-death
mid-grab into a clean stop rather than an `OSError`), but it would not have kept these runs alive:
once the client is gone there is nothing to read.

## Reports in this folder

Fixes for reports 1-4 were implemented after session 1 (poll for the handover dialog; verify the
station panel actually closed; handle the scav case RECEIVE reveal). Re-open the ledger for the
next soak session to confirm they hold.
