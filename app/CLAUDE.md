# Tarkbot-2

Screen-reading bot for Escape From Tarkov on Windows. Finds UI elements by template-matching
reference screenshots against the live game window, clicks them, reads the suggested price off
the screen, undercuts it, and lists the item on the flea market. Loops until told to stop.

## Lay of the land

```
bot.py               Tarkbot: the bot itself.
                     sell_one() is one full pass, start() repeats it until stop().
                     stop() sets a threading.Event; _pause() is the checkpoint every wait and
                     step boundary goes through, so a stop lands mid pass rather than at the
                     end of one. Raises Stopped internally to unwind, Retry to abandon a pass
                     and start a fresh one. Keeps the stats dict the GUI polls, keyed by
                     STAT_LABELS, which the GUI also builds its labels from.
tarkov_window.py     Locates the Tarkov window via ctypes/user32. Load bearing: bot, gui and
                     every test import it. handle() -> hwnd, position() -> (x,y), size() -> (w,h).
                     Raises WindowError if the window is missing or ambiguous.
                     Run directly to print the window's hwnd/pos/size.
main.py              Entry point for the frozen build only, and where stdout gets pointed at
                     %APPDATA%/tarkbot/tarkbot.log, since a windowed exe has no console and
                     bot.py's first print() would otherwise kill the run. From source, still
                     run python -m gui.app.
version.py           The version string. Read from the __version__ file the build writes from
                     the git tag; 'dev' when there is no build. python -m version prints it.
scripts/setup_msi.py cx_Freeze build and MSI, see docs/build_and_release.md at the repo root.
                     python scripts/setup_msi.py bdist_msi --target-version v0.0.0-local
scripts/make_icon.py Renders gui/tarkbot.svg into gui/tarkbot.ico at 7 sizes. Only needed
                     after editing the svg; the ico is committed. Wants cairosvg.
gui/app.py           The control panel. Start/Stop, a 3s countdown, a coloured state lamp, the
                     stats, a background picker and an item-source picker. Run: python -m gui.app
                     Everything is drawn as canvas items over one pre-composited backdrop,
                     because tk widgets cannot be translucent and would punch opaque holes in
                     the glass; the two dropdowns are the only real widgets. The system title
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
interact/sell.py     Everything the bot does to a screen. See the section below.
                     Geometry self-check, no game needed: python -m interact.sell
interact/ocr.py      Reads the numbers Tarkov prints. Not an OCR engine: the prices are a fixed
                     bitmap font, so it cuts the crop into glyphs and pixel-matches each against
                     a reference. read_number() is all or nothing, None if any glyph is
                     unreadable, because a partly read price is a wrong price.
interact/reference_images/<target>/*.png
                     Cropped screenshots of the thing to find, one folder per target. Any png
                     in the folder counts as a match candidate, so multiple angles/states can
                     live side by side. Filenames mean nothing.
                     price_digits/ is the exception: it is generated, and <digit>__<n>.png
                     names are the answer key.
```

## What sell.py does

- **Geometry** `infer_inventory_region` (derived from the All / autoselect-similar / auto-sort
  buttons framing the grid), `infer_scav_case_region`, `grab_price_region` (fixed window
  fractions, because the number inside changes and there is nothing stable to match).
- **State reads** `is_flea_open` and `more_offers_available` work off pixel brightness rather
  than a second template, because those elements only change colour: the flea taskbar icon
  inverts (mean channel 57 closed, 117 open, threshold 90) and the add offer button greys out
  (brightest channel 255 lit, 123 greyed, threshold 190). Also `is_item_selected` and
  `is_autoselect_similar_ticked`, which widens the button's box 30% first because the tick
  sits just outside it.
- **Finding items** `find_sell_pixels` masks out empty slots using a 256³ boolean cube built
  from every colour in `reference_images/dead_pixels/`, ±5 per channel. Scav case boxes are
  expanded 15% and excluded.
- **Acting** `click_all_button`, `click_add_offer`, `wait_for_offer_slot` (no timeout by
  design; pass a threading.Event as `stop` to make it interruptible),
  `disable_autoselect_similar`, `enter_price` (ctrl+A first, the field arrives prefilled),
  `click_place_offer`, `select_item_from_inventory`, `select_item_from_random_scav_case`,
  `open_scav_case`, `orientate_offer_creation` / `orientate_scav_box` (drag to the corner).
- **Pricing** `get_price` reads the suggested price, `undercut_price` returns the higher of
  `price * 0.85` and `price - 2000`, so the flat cut wins on expensive items and the percentage
  wins on cheap ones without ever going negative. They cross at `flat / (1 - fraction)`.

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
