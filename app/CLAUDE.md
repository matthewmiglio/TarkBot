# Tarkbot-2

Screen-reading bot for Escape From Tarkov on Windows. Finds UI elements by template-matching
reference screenshots against the live game window, clicks them, reads the suggested price off
the screen, undercuts it, and lists the item on the flea market. Loops until told to stop.

## Lay of the land

```
sell_bot.py          Tarkbot: the flea selling mode.
                     sell_one() is one full pass, start() repeats it until stop().
                     stop() sets a threading.Event; _pause() is the checkpoint every wait and
                     step boundary goes through, so a stop lands mid pass rather than at the
                     end of one. Raises Stopped internally to unwind, Retry to abandon a pass
                     and start a fresh one. Counts into a stats dict keyed by STAT_LABELS,
                     which the GUI also builds its labels from. The GUI passes its own dict
                     in, so the counters span the session rather than one Start; a Tarkbot
                     built without one keeps its own.
gym_bot.py           HideoutGym: the other mode, training at the hideout gym. Same shape as
                     sell_bot.py (stats dict, _pause checkpoint, Stopped/Retry, start/stop) and
                     named to pair with it, and so it cannot be mistaken for interact/gym.py.
                     nothing to do with the flea. SKELETON: train_once() calls into
                     interact/gym.py, which raises NotImplementedError until its reference
                     images exist, so starting this mode fails loudly rather than no-opping.
tarkov_window.py     Locates the Tarkov window via ctypes/user32. Load bearing: bot, gui and
                     every test import it. handle() -> hwnd, position() -> (x,y), size() -> (w,h).
                     Raises WindowError if the window is missing or ambiguous.
                     Run directly to print the window's hwnd/pos/size.
main.py              Entry point for the frozen build only. Calls session_log.start() before
                     anything else, since a windowed exe has no console and sell_bot.py's first
                     print() would otherwise kill the run. From source, still run
                     python -m gui.app, which starts a session log the same way.
session_log.py       One log file per session in %APPDATA%/tarkbot/logs/, where a session is
                     one app boot to one app close, not one Start to one Stop. Tees stdout and
                     stderr, so running from source still narrates to the console. Keeps the
                     10 newest and deletes the rest as each session opens.
                     Self-check: python -m session_log
narrate.py           log(message, indent): one timestamped print. Everything in the selling
                     path narrates through it rather than print(), so a run reads back as a
                     flow with a clock on each line. indent 0 is a step in the pass, 1 is what
                     a screen read or click did, 2 is one attempt inside a retry loop.
                     Not named trace.py: that shadows the stdlib module.
version.py           The version string. Read from the __version__ file the build writes from
                     the git tag; 'dev' when there is no build. python -m version prints it.
scripts/setup_msi.py cx_Freeze build and MSI, see docs/build_and_release.md at the repo root.
                     python scripts/setup_msi.py bdist_msi --target-version v0.0.0-local
scripts/make_icon.py Renders gui/tarkbot.svg into gui/tarkbot.ico at 7 sizes. Only needed
                     after editing the svg; the ico is committed. Wants cairosvg.
gui/app.py           The control panel. Start/Stop, a 3s countdown, a coloured state lamp, one
                     tab per mode (FLEA SELL / HIDEOUT GYM) and the pickers each mode needs.
                     Run: python -m gui.app
                     Modes are rows in TABS, and each mode's module supplies exactly three
                     things: STAT_LABELS (rows to draw), TINT_STAT (the row that goes green,
                     or None) and build(prefs, stats) -> a runner with start/stop/stats. A
                     third mode is a row in TABS plus a module, not a new branch through the
                     drawing code. Per-tab canvas items carry a 'tab:<key>' tag and switching
                     is itemconfigure(state=hidden/normal), so nothing is redrawn and the item
                     ids stay stable for tick(). Tabs refuse to switch while a runner is
                     alive, or Stop would point at a mode the window is no longer showing.
                     Everything is drawn as canvas items over one pre-composited backdrop,
                     because tk widgets cannot be translucent and would punch opaque holes in
                     the glass; the dropdowns are the only real widgets, and they sit in the
                     two header rows DROP_ROW names. The system title
                     bar is off (overrideredirect) and replaced by one of our own, which is
                     what drags the window and carries the close X; WS_EX_APPWINDOW is put
                     back by hand or the window would vanish from the taskbar and alt-tab and
                     be unreachable behind fullscreen Tarkov. The bot runs on a
                     daemon thread so the window stays responsive, the X button stops it and
                     joins before destroying, and a pass that dies on a wrong screen turns the
                     lamp red instead of vanishing.
gui/theme.py         Palette, font stack and backdrop(): the chosen photo blurred and dimmed,
                     glass panels composited on, character trimmed and feathered in.
                     Preview it without opening the GUI: python -m gui.theme [name.png]
gui/settings.py      Preferences in %APPDATA%/tarkbot/settings.json. Never raises: a corrupt
                     file is ignored so the GUI always opens. Self-check: python -m gui.settings
gui/backgrounds/     The photos the picker offers. Drop a png in and it appears in the list.
gui/poster_character.png   The figure on the left panel.
gui/tarkbot.svg, gui/tarkbot.ico   Window, taskbar and exe icon. The svg is the source; the
                     ico is generated from it and committed.
interact/find.py     Locating things on screen. find(), find_all(), find_center() take a target
                     name and an optional region, return pyscreeze Boxes / (x,y) / None.
                     images() resolves a name to reference pngs; dedupe()/iou() collapse
                     overlapping matches.
interact/sell.py     Everything the flea bot does to a screen. See the section below.
                     Geometry self-check, no game needed: python -m interact.sell
interact/gym.py      The same for the hideout gym. Separate module on purpose: the two share
                     find.py and narrate.py and nothing else. All stubs for now; the gym_*
                     reference folders it names do not exist yet.
interact/ocr.py      Reads the numbers Tarkov prints. Not an OCR engine: the prices are a fixed
                     bitmap font, so it cuts the crop into glyphs and pixel-matches each against
                     a reference. read_number() is all or nothing, None if any glyph is
                     unreadable, because a partly read price is a wrong price.
interact/reference_images/<target>/*.png
                     Cropped screenshots of the thing to find, one folder per target. Any png
                     in the folder counts as a match candidate, so multiple angles/states can
                     live side by side. Filenames mean nothing and are uuids, so a new crop is
                     never a name to think about and never collides.
                     price_digits/ is the exception: it is generated, and <digit>__<n>.png
                     names are the answer key, so leave that folder's names alone.
                     Where two states of one element have to be told apart, they get a folder
                     each rather than sharing one (browse_button_selected /
                     browse_button_unselected), because find() cannot say which png matched.
```

## What sell.py does

- **Geometry** `infer_inventory_region` (derived from the All / autoselect-similar / auto-sort
  buttons framing the grid), `infer_scav_case_region`, `grab_price_region` (fixed window
  fractions, because the number inside changes and there is nothing stable to match).
- **State reads** `is_flea_open` and `more_offers_available` work off pixel brightness rather
  than a second template, because those elements only change colour: the flea taskbar icon
  inverts (mean channel 57 closed, 117 open, threshold 90) and the add offer button greys out
  (brightest channel 255 lit, 123 greyed, threshold 190). `is_item_selected` is three template
  reads that all have to agree, not one: `item_is_selected` and `place_offer_button` present,
  `no_items_selected` absent, because any single match that fails for its own reasons reads as
  a selection and the pass then prices an item it never picked. `is_autoselect_similar_ticked`
  widens the button's box 30% first because the tick sits just outside it.
- **Finding items** `find_sell_pixels` masks out empty slots using a 256³ boolean cube built
  from every colour in `reference_images/dead_pixels/`, ±5 per channel. Scav case boxes are
  expanded 15% and excluded.
- **Acting** `click_all_button`, `click_add_offer`, `wait_for_offer_slot` (no timeout unless
  asked for one; pass a threading.Event as `stop` to make it interruptible),
  `remove_stale_offers` (my-offers tab, walk `stale_offer_rows` bottom upwards clicking every
  remove button found, lowest first, so a cancelled offer cannot shift a point still to be
  clicked; settle, back to browse; returns how many it cancelled). Both ends of that go
  through `is_on_browse_page`, which reads the browse tab's own two states
  (`browse_button_selected` / `browse_button_unselected`) and is the only thing on screen that
  says which flea page we are on: it bails before walking the rows if the my-offers click
  missed, and `return_to_browse` clicks up to `TAB_ATTEMPTS` times until browse reads active,
  `wait_for` (poll for a target until it shows, rather than sleeping a guess at the worst
  case; `open_scav_case` uses it for the case window, which loads for seconds and used to be
  missed by a flat `WINDOW_DELAY`),
  `disable_autoselect_similar`, `enter_price` (ctrl+A first, the field arrives prefilled),
  `click_place_offer`, `select_item_from_inventory`, `select_item_from_random_scav_case`,
  `open_scav_case`, `orientate_offer_creation` / `orientate_scav_box` (drag to the corner).
- **Pricing** `get_price` reads the suggested price, `undercut_price(price, fraction, flat)`
  returns the higher of `price * fraction` and `price - flat`, so the flat cut wins on expensive
  items and the percentage wins on cheap ones without ever going negative. They cross at
  `flat / (1 - fraction)`. Which pair to use is the GUI's UNDERCUT dropdown, `sell_bot.UNDERCUTS`:
  2k, 3k or 5k, all at 90%, so the choice only moves the price where the flat cut takes over.
  `sell.py`'s own constants are only the defaults.

## Tests

Nothing here is pytest. Each script runs against the live game, prints what it saw, writes a
picture to `tests/output/`, and exits non-zero on failure. Two run with no game open:
`test_price_corpus.py` and `python -m interact.sell`.

```
test_bot_loop.py             The whole thing. --loop runs pass after pass until ctrl+c, and
                             stops it from another thread, which is the same path the GUI's
                             Stop button and X button use. --scav / --scav-only pick the item
                             source. --dry reports what it would find and clicks nothing.
test_price_corpus.py         Reads every fixture in tests/fixtures/prices/ and checks it against
                             its own filename. No game needed. The regression net for ocr.py.
capture_price.py <value>     Grab the price region now, save it as fixtures/prices/<value>.png,
                             report whether the reader agrees. How the corpus grows.
build_digit_templates.py     Cut every fixture into glyphs and file them under the digit each
                             one is, rebuilding interact/reference_images/price_digits/ from
                             scratch. Rerun whenever the corpus grows.
test_find.py [target]        find() over every reference folder, match box drawn on screen.
test_more_offers.py          [true|false] is the add offer button lit or greyed out.
test_autoselect_ticked.py    [true|false] is the similar-items checkbox ticked.
test_disable_autoselect_similar.py   Untick it, no-op if it is already off.
test_remove_offers.py        The whole stale-offer sweep, flea already open. Cancels real
                             offers, so it counts down first. --settle N shortens the wait.
test_flea_open.py            Is the flea market open.
test_get_price.py            Read the price region right now.
test_grab_price_window.py    Crop the price region and show what was cropped.
test_inventory_region.py, test_scav_case_region.py, test_sell_pixels.py, test_select_item.py,
test_select_scav_item.py, test_open_scav_case.py, test_orientate_offer.py,
test_click_all_button.py     The individual steps, one script each.
add_offer_colour.py, flea_icon_colour.py    Measure a UI element's colour in one state, so a
                             brightness threshold can be picked. Run once per state.
view_screenshot.py           matplotlib viewer with grid, coordinates and colours.
find_tarkov_window.py        Dead: a standalone spike that predates tarkov_window.py.
```

## Conventions

- Regions are `(left, top, width, height)` in screen coords. The Tarkov window rect comes from
  `tarkov_window.position(hwnd) + tarkov_window.size(hwnd)` and gets passed into `find` so
  matching stays inside the game window. The game runs fullscreen, so image coords == screen
  coords.
- Matching uses `confidence=0.9` (`find.CONFIDENCE`), which requires opencv-python.
- Thresholds, pads and delays are module constants at the top of `sell.py`, each carrying the
  measurement that produced it in its comment. Tune there, not inline.
- `interact/` has no `__init__.py`. It works as a namespace package, so imports need the repo
  root on `sys.path` (scripts under `gui/` and `tests/` insert it themselves).
- `(0, 0)` is pyautogui's panic corner. Any drag ending there sets `FAILSAFE = False` first and
  moves the cursor back to centre screen *before* restoring it.
- Windows-only: `tarkov_window.py` calls user32 directly.
- `ponytail:` comments mark deliberate shortcuts and name the upgrade path.

## Deps

`pip install -r requirements.txt` (pyautogui, pyscreeze, opencv-python, numpy, pillow, matplotlib).
No OCR engine on purpose: one was tried and read 999 as 666 and 777 as 7777, both at full
confidence. Everything else is stdlib.
