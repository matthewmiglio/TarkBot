# Tarkbot tests: lay of the land

Every test here is a **standalone script, not pytest**. Each one runs against the live game or a
stubbed/fixture screen, prints what it saw, sometimes writes an annotated picture to `output/`, and
exits non-zero on failure. There is no runner, no `conftest`, no fixtures-as-arguments. You run one
by naming it:

```
python tests/<folder>/<file>.py            # from the app/ directory
```

For the mapping of what each *app* module does, see `app/CLAUDE.md` (the deep reference). This file
is the opposite view: given a test, what is it for and which layer does it exercise.

## The two kinds of test

- **no-game** — the mouse, clock, matcher, window and screen are stubbed, or the input is a saved
  frame/fixture. These are pure logic/geometry checks and safe to run anywhere, anytime. They are
  the regression net.
- **game** — real clicks, drags and screen grabs against a running Tarkov on the hideout or flea.
  These drive the actual UI. **Prefer to let a human run the game tests** (they move the real mouse
  and can act on the real account); when you must, know that one wrong crop drives a real click.

Some tests are **game or with-a-frame**: bare, they grab the live window (game); handed a saved
frame path, they need nothing (no-game). Those are noted below.

## Conventions

- **sys.path.** A test bootstraps the repo's `app/` onto `sys.path` so it can `import window`,
  `from interact import sell`, etc. At this depth (one folder under `tests/`) that is
  `sys.path.insert(0, str(Path(__file__).resolve().parents[2]))`. The `gym/` folder is the canonical
  example.
- **fixtures / output.** Static inputs live in `tests/fixtures/`, annotated pictures are written to
  `tests/output/`. From a subfolder those are `Path(__file__).resolve().parents[1] / 'fixtures'`
  (resp. `'output'`). Do not recreate them per-subfolder; they stay at the `tests/` root.
- **reference images** are under `app/interact/reference_images/`, cropped at 1080p and resized to
  the live screen by `find.scale()`. Many game tests exist to prove a crop still matches after a
  game update, or to retune a region/threshold constant that lives at the top of an app module.
- **new test → put it in the folder for the layer it drives** (below), match the neighbours' style,
  and give it a heavy module docstring: one-line purpose, which app module/function it tests, what
  it verifies, and game vs no-game.

## The folders

Thirteen folders, grouped by the app layer each drives. Format below is
`file — app layer/function — what it verifies — game|no-game`.

### `flea_sell/` — the flea seller's screen reads and actions (`interact/sell.py`, `sell_bot.py`)
- `test_get_price.py` — sell.grab_price_region/get_price — read the suggested price off the live offer window — game
- `test_grab_price_window.py` — sell.grab_price_region + ocr.read_number — crop the price readout and read each digit — game
- `test_more_offers.py` — sell.more_offers_available — is a free offer slot left, by button brightness — game
- `test_autoselect_ticked.py` — sell.is_autoselect_similar_ticked — does the autoselect-similar checkbox read ticked — game
- `test_set_autoselect_similar.py` — sell.set_autoselect_similar — toggle, clicking only when the state differs — game
- `test_click_all_button.py` — sell.click_all_button — click the inventory All button, before/after shot — game
- `test_pack_offer.py` — sell.get_price + first_offer_is_a_pack — a pack-priced top offer reads None before OCR — no-game
- `test_sell_pixels.py` — sell.infer_inventory_region/find_sell_pixels — paint every stash pixel that counts as an item — game
- `test_select_item.py` — sell.select_item_from_inventory — pick a stash item and right-click to filter by it — game
- `test_orientate_offer.py` — sell.orientate_offer_creation — drag the offer window to a corner, measure travel — game
- `test_inventory_region.py` — sell.infer_inventory_region — draw the inferred stash region and its framing buttons — game
- `test_inventory_region_stress.py` — sell.infer_inventory_region — drag the offer window randomly until a framing button drops — game
- `add_offer_color.py` — sell add-offer brightness threshold — measure the button colour to pick the lit/greyed threshold — game
- `flea_icon_color.py` — sell.is_flea_open threshold — measure the flea icon colour to set the open/closed threshold — game
- `test_flea_open.py` — sell.is_flea_open — print whether the flea reads open, with the brightness — game
- `test_remove_offers.py` — sell.remove_stale_offers/return_to_browse — run the whole stale-offer sweep, land back on browse — game
- `test_bot_loop.py` — sell_bot.FleaSeller sell_one/start/stop — drive the whole flea sell loop, incl. the GUI stop path — game
- `test_checkmark_region.py` — sell._checkmark_region_from — the autoselect checkmark search region fits the needle over saved frames — no-game

### `flea_scav/` — scav-case selling (`interact/sell.py` scav paths, `sell_bot.py` fallback)
- `test_open_scav_case.py` — sell.open_scav_case — right-click a random scav case and pick 'open' — game
- `test_scav_case_region.py` — sell.infer_scav_case_region — infer the open case window's box and draw it — game
- `test_scav_case_fixture.py` — find.find_all('scav_case') @0.8 — count cases correctly on labelled 1440p frames — no-game
- `test_scav_only_fallback.py` — sell_bot scav-only fallback — refuse the stash when no case is on screen — no-game
- `test_select_scav_item.py` — sell.select_item_from_random_scav_case — pick a live pixel in the case and filter by it — game

### `flea_filters/` — the flea filter pass and its guards (`interact/sell.py`)
- `test_apply_flea_filters.py` — sell.apply_flea_filters — run the whole filter pass live, verify it sticks, time the phases — game
- `test_flea_filters_fixture.py` — find vs sell filter targets — every filter target found and each state pairs the right way — no-game
- `test_filter_window_guard.py` — sell.open_filters — no control is read until the filter window actually opens — no-game
- `test_dropdown_no_retry.py` — sell._pick_from_dropdown — a missing option fails at once (no escape); a missed click still retries — no-game
- `speed_test_apply_filters.py` — sell.apply_flea_filters (timing) — fastest pacing across all call shapes still sets filters that stick — game

### `flea_recovery/` — failure and recovery paths (`interact/sell.py`, `sell_bot.py`)
- `test_recover_loop.py` — sell_bot._recover — Start unwinds a stack of leftover windows one layer per round, honours Stop — no-game
- `test_recover_targets.py` — sell_bot._recover + recovery crops — real FleaSeller vs the live window, the shipping recovery crops still match — game
- `test_recover_on_start.py` — sell.close_leftover_windows — which leftover windows Start backs out of, leaving the plain inventory alone — no-game
- `test_cheap_offer_popup.py` — sell_bot.sell_one — a refused or unpriced pass counts no sale and unwinds by the right escape count — no-game
- `test_error_popup.py` — sell.dismiss_error_popup — where OK is clicked on the Error/0 dialog, and a clean screen is untouched — no-game
- `test_flea_open_error_dialog.py` — sell_bot.open_offer_creation + _past_error_dialog — a failed step gets exactly one retry once the Error dialog is cleared — no-game
- `test_window_gone.py` — sell_bot.open_offer_creation (window guard) — a game closed mid-run raises and clicks nothing before the add-offer click — no-game
- `test_drag_failsafe.py` — sell._drag_to_corner — a drag that raises still parks the cursor off the corner before the fail-safe comes back on — no-game

### `flea_snipe/` — the flea buyer (`interact/snipe.py`, `snipe_bot.py`)
- `test_snipe_loop.py` — snipe_bot.sweep_once/check_one — buy/skip decisions vs a fake board: cheap bought, dear left, unreadable never acted on, locked skipped, Stop lands mid-sweep — no-game
- `test_snipe_watchlist.py` — snipe_bot.targets/TARGETS_PATH — the watchlist csv loads, TRADER dropdown has traders, frozen build looks in lib/ — no-game
- `test_remove_item_filter.py` — snipe.remove_filter_by_item_filter — what the filter-by-item chip clear sees, and with --click what it clicks — game or with a frame
- `test_ruble_region.py` — snipe.ruble_region — where the purchase-confirm balance box lands, drawn on the frame it was cut from — game or with a frame
- `test_top_offer_price.py` — snipe.read_price/price_region — read the topmost offer's price and draw the price/currency/gutter boxes — game
- `test_dear_board.py` — craft.buy_craft_input_item reading snipe.read_price — dear/unreadable offers waited out then Unbuyable, cheap bought, retry counters stay separate — no-game
- `test_price_gutter.py` — snipe.first_lit_column/_clipped — a six-figure price reads, a clipped one (leading digit outside the box) is refused — no-game
- `test_first_offer_region.py` — sell.grab_first_offer_region — where the topmost comparable-offer box lands, drawn on the frame — game or with a frame
- `test_find_first_offer_dollar.py` — sell.grab_first_item_price_region + dollar check — is the top comparable offer in dollars and where the glyph landed — game or with a frame
- `test_filter_by_item_backout.py` — sell pick loops + sell_bot.sell_one reset — a menu with no 'filter by item' ends the pass pressing nothing — no-game

### `hideout_craft_reads/` — craft screen reads (`interact/craft.py`)
- `test_find_slickers_craft_region.py` — craft.find_craft/output_box — draw the found craft-output band on a crafting screen — game or with a frame
- `test_get_slickers_craft_state.py` — craft.get_craft_state — print not-started/done/ready/producing for a craft row — game or with a frame
- `test_slickers_requisites_check.py` — craft.craft_plan/validate_craftable — draw and print the (all_ready, missing) verdict for a craft's ingredients — game or with a frame
- `test_start_ready.py` — craft.START_READY_BRIGHTNESS — outline each START button green/red by its ready brightness — game or with a frame
- `test_craft_input_confidence.py` — find.CONFIDENCES input-icon thresholds — input icons found on the right station and not the wrong one — no-game
- `test_craft_blind.py` — craft.read_craft/Blind + craft_bot.step — a missing-icon read raises Blind; step swaps on LookupError but stops on Blind — no-game
- `test_craft_state_unreadable.py` — craft.get_craft_state raising Blind — a missing output raises (not 'producing') and the raise escapes start() — no-game
- `test_new_crafts.py` — craft.CRAFTS descriptor set — workbench wires and medstation ai2 crafts wired end to end — no-game
- `test_more_crafts.py` — craft.CRAFTS + craft_bot water-collector branch — moonshine/cordura/red_gunpowder/water_collector wired end to end — no-game

### `hideout_craft_actions/` — craft actions: open, start, buy (`interact/craft.py`, `craft_bot.py`)
- `test_station_open_retry.py` — craft._open_station — the station tab is clicked once then waited on, never twice — no-game
- `test_craft_menu_retry.py` — craft._open_item_menu + craft_bot.step — a right-click menu miss hovers-then-retries; a no-menu slot swaps craft, never raises — no-game
- `test_start_handover.py` — craft_bot.start_craft/_confirm_handover — the four-step START-then-handover actually starts a craft — game
- `test_craft_station_grouping.py` — craft_bot.build/_swap — the cycle is grouped by station and a same-station swap does not navigate — no-game
- `test_water_collector.py` — craft_bot.tend_water_collector — the collector pass fits/collects/buys, finishing on its own panel — game
- `test_booze_generator.py` — craft_bot.step — the moonshine craft state machine collects/starts/buys — game
- `test_water_buy_race.py` — craft.buy_water_filter — a lost water-filter race is retried (no refresh), capped, then False — no-game
- `test_craft_buy_retry.py` — craft.buy_craft_input_item — a lost-race refresh-in-place retry, capped at BUY_ATTEMPTS, with four distinct Unbuyable messages — no-game

### `hideout_nav/` — hideout carousel navigation (`interact/craft.py`)
- `test_get_to_nutrition_unit.py` — craft.get_to_nutrition_unit (get_to_station wrapper) — drive nutrition-unit navigation and report the outcome — game
- `test_hideout_tab_active.py` — craft.is_hideout_tab_active — which hideout_tab crops read active vs inactive, by brightness — no-game
- `measure_medstation_scrolls.py` — craft carousel span (CAROUSEL_SPAN_SWIPES) — count the swipes to reach the medstation (the left wall) — game
- `test_scroll_progress.py` — craft._row_strip diff — measure whether each swipe actually moves the module row — game
- `test_check_station_active.py` — craft.check_if_station_active — is a station panel open, read off its close (X) button — game
- `test_nav_all_stations.py` — craft.get_to_station + the full nav stack — enter the hideout and reach every station end to end, with per-step timeouts — game

### `hideout_gym/` (folder `gym/`) — the hideout gym skill check (`interact/gym.py`, `gym_bot.py`)
- `gym/test_generate_roi.py` — gym.rep_region — cut the rep strip out of a saved frame and draw the box — no-game
- `gym/test_line_reads.py` — gym.read_lines — the target/closing-ring lines over the line-read fixtures — no-game
- `gym/test_gym_loop.py` — gym_bot.do_one_rep — the loop clicks when the lines meet and not before, and Stop lands mid-loop — no-game

### `detection/` — the matching and reading primitives (`interact/find.py`, `interact/ocr.py`, `sell.jitter`)
- `test_find.py` — find.find_all + scale — box every reference target on the live screen, save the annotated shot — game
- `test_price_corpus.py` — ocr.read_number vs fixtures/prices — the ocr regression net: every price fixture reads back its filename — no-game
- `capture_price.py` — sell.grab_price_region + ocr.read_number — grab the live price box as a new labelled corpus fixture — game
- `build_digit_templates.py` — ocr digit templates — rebuild the price-digit templates from the fixture corpus — no-game
- `test_click_jitter.py` — sell.jitter — clicks land off-centre but never off the smallest reference crop — no-game
- `test_flea_jitter.py` — sell._human_jitter — pads the sell code's waits/clicks, leaves pyautogui's exact, restores on the way out — no-game *(pre-existing assertion failure, see below)*

### `platform/` — the OS/screen/window/launcher layer
- `test_monitors.py` — screen.py grab (use/rect/grab) — a colour put on each monitor reads back through the picked one — no-game
- `test_window_overlap.py` — window.state()/overlap_state() — tell the three panel-vs-game overlap cases apart — no-game *(one pre-existing FAIL, see below)*
- `test_game_client.py` — game_client launcher start_tarkov/close_game — pin the boot/close step order and which profile card is clicked — no-game
- `view_screenshot.py` — screen/window pixel inspector — matplotlib grid/coord/colour viewer for cropping references — game (live grab) or with a saved image

### `gui/` — the control panel (`gui/app.py`)
- `test_activity_line.py` — gui footer activity line (tick/one_line) — the newest log line shows and stays inside the window — no-game
- `test_run_button.py` — gui run-button state machine (RUN_STATES) — start→stop→stopping→start, label and colour agree, no amber strand — no-game
- `test_tab_switch.py` — gui tab switch over TABS/DISABLED_TABS — switching stops the mode being left; a disabled tab is refused — no-game
- `test_hotkey_bind.py` — gui hotkey RegisterHotKey rebind (HOTKEYS) — a rebind claims the new key and hands the old one back — no-game
- `test_totals_line.py` — mode runners' start() totals logging — the totals line survives a pass that raises, for both bots — no-game

### `telemetry/` — crash and purchase reporting (`crash_report.py`, `snipe_report.py`)
- `test_error_report.py` — crash_report + gui App._run → /api/error — crash reporting end to end plus the opt-out gate — no-game, **needs the website running**
- `test_snipe_report.py` — snipe_report + snipe_bot.build gate → /api/snipe — a buy reaches the site, and the opt-out sends nothing — no-game, **needs the website running**

## Known pre-existing failures (predate the reorg, not path bugs)

- `detection/test_flea_jitter.py` asserts "click not restored" — reproduces on the original,
  untouched committed file. A real test-logic issue in the jitter restore path, unrelated to the move.
- `platform/test_window_overlap.py` prints one `FAIL` ("panel off the top left") from `window.state`
  logic; also pre-existing.

## Deleted in this reorg (deprecated / superseded)

- `find_tarkov_window.py` — a standalone ctypes spike that predated `window.py`.
- `test_hideout_swipe_limits.py` — pinned `get_to_station`'s old bounded bidirectional sweep, replaced
  by the anchor-left/scroll-right walk (see `hideout_nav/`).
- `test_craft_nav_permutations.py` — pinned the old `_preferred_first_dx`/`STATION_ORDER` direction
  guessing, removed from `get_to_station`.
