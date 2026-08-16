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
gym_bot.py           HideoutGym: the other mode, hitting the workout skill check at the hideout
                     gym. Same shape as sell_bot.py (stats dict, _pause checkpoint, start/stop)
                     and named to pair with it, and so it cannot be mistaken for
                     interact/gym.py. Nothing to do with the flea.
                     do_one_rep() is one look at the screen: match the hexagon icon, and only
                     if it is there read the strip and click when the two hexagons have met.
                     No icon means wait IDLE_POLL and look again. start() repeats it until
                     stop(). It navigates nowhere: start it with the workout already running.
                     CLICK_GAP is the tuning knob, in ROI columns, 0 today.
                     The icon gates every look, and must. An earlier version read the strip
                     first and only checked the icon when the strip came back empty, to save
                     the match. It clicked fifteen times at a character standing still: a
                     bright scene fills the whole strip, and one run across all 201 columns is
                     what two lines that have met also look like. The strip cannot tell a skill
                     check from a wall. A look costs ~50ms, 45 of which is the one screenshot
                     it takes of gym.look_region and slices into the icon box and the strip.
                     The press is aimed, not reacted to. _predict() takes the ring's speed from
                     the last two readings and, once the overlap is nearer than one look period,
                     sleeps to it and presses. It has to: the ring closes at ~75 columns a
                     second on a set's first rep and ~235 by its fifteenth, and a look plus the
                     ~45ms the pixels are already stale by means waiting to *see* the lines meet
                     presses 7 to 25 columns past them. That is exactly why reps 1-9 of every
                     set used to land and 10 onwards did not. CLICK_LEAD is the trim; CLICK_GAP
                     is only the fallback for a rep whose overlap happened inside one look.
                     Tarkov scores the rep on the press, not the release, and pyautogui presses
                     immediately, so its 0.1s PAUSE costs throughput and not accuracy. Do not
                     turn PAUSE off: sell.py depends on those pauses between its own clicks.
                     It aims at the two centres lining up, trimmed by AIM_COLUMNS (a spatial
                     offset, for a miss that looks the same at every speed) and CLICK_LEAD (a
                     time one, for reps that land early in a set and miss late in it). Aiming
                     at gym.Lines.touch, where the lines first meet 4-8 columns sooner, was
                     tried because every fallback press had landed there, and it pressed too
                     early on every rep.
                     CLICK_LEAD is 0, and three sessions differing only in it say to leave it
                     there: +15ms landed reps to ~165 columns a second, 0 to ~205, -30ms to
                     ~190. Worse both ways, so there is no systematic offset left to cancel and
                     what limits the last reps of a set is the spread of the error. Do not
                     reach for either trim again without a measurement saying the misses are
                     lopsided. An aim can legitimately fall after the two lines merge, which is
                     why the merged branch honours a pending aim instead of pressing on sight.
                     Attacking the spread instead: the loop reads through screen.fast_grab, a
                     BitBlt of just the look box, which took a look from ~60ms to ~17ms. That
                     shortens the blind extrapolation past the merge from 24-44ms to 8-17ms and
                     triples the sample rate. Speed is measured across SPEED_SAMPLES readings
                     end to end rather than the last two, so the faster reads do not turn half
                     a column of reading error into a large fraction of the speed.
                     Two Windows clock traps, both measured, both load bearing here. Every
                     reading is perf_counter, never monotonic, which ticks every 15.6ms and put
                     30% error in the speed. And the aimed wait is time.sleep via _sleep(), not
                     Event.wait via _pause(): Event.wait rounds up to that same tick, 45ms for
                     a 31ms ask, which is a press landing 4 columns late at speed.
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
frames.py            The picture half of that log: %APPDATA%/tarkbot/frames/, sister of logs/.
                     start() wraps pyautogui's input calls in place, so every click, drag and
                     keypress leaves a full screen png before it and another after it, named
                     for the millisecond (1754702835123-pre.png) and logged by name, which is
                     what lines a frame up against the narration. Not a recording: only
                     changes are captured. 250 frames across all sessions, oldest deleted as
                     new ones arrive. Whole screen, native resolution, lossless.
                     Self-check: python -m frames
report.py            Sends a crash to tarkbot.org: the traceback, plus the frame from before the
                     last click and the screen as it is now. Hooked into the one catch in
                     gui/app.py's _run, on a daemon thread, so a slow or dead site cannot hold
                     up the red lamp or raise on top of the error it is reporting. Off with
                     send_error_reports false in settings.json.
                     Ships no key: it posts to a route on our own site, which holds the Supabase
                     service key server side, the same way the download counter does. The
                     screenshots do not go through that route. A lossless png of a 1440p screen
                     is 4.5MB and Vercel rejects bodies at 4.5MB before route code runs, so the
                     endpoint answers with two single-use upload urls and the bytes go straight
                     to storage, where the bucket's own 25MB limit caps them.
                     Png, never lossy: these exist to be cropped into reference images, and
                     while find() survives even JPEG q10, ocr.py's digit templates and sell.py's
                     dead pixel colors (±5 a channel) do not.
                     machine_id() is a uuid5 of the Windows build, the account name and the
                     monitor size, so it is stable without anything being stored.
screen.py            Which monitor the bot works on, and grabbing pixels off it. Exists because
                     pyscreeze photographs the primary monitor and nothing else, and
                     locateOnScreen throws the caller's region away before grabbing, so a
                     Tarkov on the second screen was invisible however good the region was.
                     grab(region) takes the whole virtual desktop and cuts the rectangle out
                     itself, subtracting the virtual origin, which is negative on the very
                     common layout of a second monitor placed left of the primary; Pillow and
                     pyscreeze both crop the wrong place there. monitors() enumerates them,
                     use(name) picks one and everything else measures against it, overlap()
                     clips the Tarkov window to it. Importing the module patches
                     pyautogui.screenshot, so the test scripts get the same fix without
                     knowing about any of it. The GUI's MONITOR dropdown is what calls use().
                     fast_grab(region) is the other capture path, a ctypes BitBlt of just that
                     rectangle: ~17ms against grab()'s ~45ms, because Pillow photographs the
                     whole virtual desktop and crops however small the ask. Only gym_bot uses
                     it, and only because it is pressing a button at an instant. Its pixels
                     come back 1-2 levels a channel off Pillow's on about half of them, which
                     is nothing to a brightness threshold and a real problem for ocr.py's digit
                     bitmaps and sell.py's dead pixel colors at ±5. Those stay on grab().
                     Self-check: python -m screen
narrate.py           log(message, indent): one timestamped print. Everything in the selling
                     path narrates through it rather than print(), so a run reads back as a
                     flow with a clock on each line. indent 0 is a step in the pass, 1 is what
                     a screen read or click did, 2 is one attempt inside a retry loop.
                     narrate.LAST is that line kept as a string, which is what the GUI's footer
                     shows. Written on the bot thread, read on the GUI thread, no lock needed.
                     Not named trace.py: that shadows the stdlib module.
version.py           The version string. Read from the __version__ file the build writes from
                     the git tag; 'dev' when there is no build. python -m version prints it.
scripts/setup_msi.py cx_Freeze build and MSI, see docs/build_and_release.md at the repo root.
                     python scripts/setup_msi.py bdist_msi --target-version v0.0.0-local
scripts/make_icon.py Renders gui/tarkbot.svg into gui/tarkbot.ico at 7 sizes. Only needed
                     after editing the svg; the ico is committed. Wants cairosvg.
gui/app.py           The control panel. Start/Stop, a 3s countdown, a colored state lamp, one
                     tab per mode (FLEA SELL / HIDEOUT GYM) and the pickers each mode needs.
                     Run: python -m gui.app
                     Under the buttons, one boxed line of narrate.LAST, repainted by tick()
                     once a second: the lamp says which state the run is in, this says what it
                     is doing right now, which is how a working pass is told from a stuck one.
                     one_line() trims it to the inside of that box measured in the real font,
                     and to its first line, since a canvas draws every newline a traceback has
                     in it. LOGS, left of the run button, opens %APPDATA%/tarkbot in Explorer,
                     which is where the session logs and the frames are.
                     One run button, not a START beside a STOP: RUN_STATES holds its three
                     states, each a label, a face color and whether it can be pressed, and
                     _set_run() is the only thing that writes it so the two cannot disagree.
                     Green 'Start (F4)', red 'Stop (F4)', amber 'Stopping...' while the ask is
                     with the bot, cleared by tick() when the thread comes back. stop() only
                     goes amber if a thread is actually alive, since tick() is what clears it
                     and it only fires on a thread it watched die.
                     F4 does the same as pressing it, through hotkey(): a RegisterHotKey on its
                     own thread blocked in GetMessageW, not a tk binding (tk sees no keys while
                     Tarkov has focus) and not a keyboard poll (nothing has to be held down).
                     The press is handed back to the tk thread with after(0), because tk is
                     only safe from the thread that built it.
                     Modes are rows in TABS, and each mode's module supplies exactly three
                     things: STAT_LABELS (rows to draw), TINT_STAT (the row that goes green,
                     or None) and build(prefs, stats) -> a runner with start/stop/stats. A
                     third mode is a row in TABS plus a module, not a new branch through the
                     drawing code. Per-tab canvas items carry a 'tab:<key>' tag and switching
                     is itemconfigure(state=hidden/normal), so nothing is redrawn and the item
                     ids stay stable for tick(). Switching tabs stops whatever the tab being
                     left was running and waits for it, rather than refusing the switch: the
                     window must never show one mode while another is still clicking. Tabs in
                     DISABLED_TABS are drawn greyed and cannot be switched to at all, which is
                     where HIDEOUT GYM sits: it hits reps, but the last few of every set still
                     miss, so it is off until that is fixed. Empty that set to switch it on.
                     Everything is drawn as canvas items over one pre-composited backdrop,
                     because tk widgets cannot be translucent and would punch opaque holes in
                     the glass; the dropdowns are the only real widgets, and they sit in the
                     two header rows DROP_ROW names. The system title
                     bar is off (overrideredirect) and replaced by one of our own, which is
                     what drags the window and carries the close X and the minimise beside it;
                     WS_EX_APPWINDOW is put back by hand or the window would vanish from the
                     taskbar and alt-tab and be unreachable behind fullscreen Tarkov. An
                     overrideredirect window cannot be iconified, so minimise() puts the system
                     frame back for the length of the minimise and the <Map> binding strips it
                     again on the way back, restoring the position by hand because the
                     re-measure against a frame that is gone walks the window down the screen.
                     The bot runs on a
                     daemon thread so the window stays responsive, the X button stops it and
                     joins before destroying, and a pass that dies on a wrong screen turns the
                     lamp red instead of vanishing.
gui/theme.py         Palette, font stack and backdrop(background, tab): the chosen photo blurred
                     and dimmed, glass panels composited on, that tab's character trimmed and
                     feathered in.
                     Preview it without opening the GUI: python -m gui.theme [name.png] [tab]
gui/settings.py      Preferences in %APPDATA%/tarkbot/settings.json. Never raises: a corrupt
                     file is ignored so the GUI always opens. Self-check: python -m gui.settings
gui/backgrounds/     The photos the picker offers. Drop a png in and it appears in the list.
gui/characters/      The figure on the left panel, one png per mode named for its tab key
                     (flea.png, gym.png), swapped by repainting the backdrop on tab switch.
gui/tarkbot.svg, gui/tarkbot.ico   Window, taskbar and exe icon. The svg is the source; the
                     ico is generated from it and committed.
interact/find.py     Locating things on screen. find(), find_all(), find_center() take a target
                     name and an optional region, return pyscreeze Boxes / (x,y) / None.
                     images() resolves a name to reference pngs; dedupe()/iou() collapse
                     overlapping matches. scale() is the screen height over 1080 and needle()
                     resizes a reference by it before matching, because the matcher does not
                     scale and a 1440p button never matches the 1080p crop of it. At 1080p
                     needle() hands over the file itself, so that path is unchanged.
                     find.VERBOSE = True narrates every reference image tried, matched or not,
                     with timings. Off by default: the selling loop would drown in it. The
                     test scripts turn it on, since which crop stopped matching is the answer
                     they exist to give.
                     Self-check, no game needed: python -m interact.find
interact/sell.py     Everything the flea bot does to a screen. See the section below.
                     Geometry self-check, no game needed: python -m interact.sell
interact/gym.py      The same for the hideout gym. Separate module on purpose: the two share
                     find.py and narrate.py and nothing else.
                     rep_region() is the strip the skill check is read from, held as fractions
                     of the window (REP_ROI_FRACTIONS) so it lands in the same place at any
                     resolution, the way sell.grab_price_region does. It is a slice off the
                     right of both hexagons at the height where their edges are vertical, not a
                     box around them. icon_region() is the same trick for the hexagon icon: a
                     145x155 box around where it was measured to land, because the gate reads
                     it before every look and matching it over the whole window costs 287ms
                     against 49ms inside that box.
                     read_lines() collapses that strip to one brightness per column, calls each
                     run over LINE_BRIGHT a line, and returns Lines(target, moving, gap): the
                     leftmost is the fixed hexagon's edge, the rightmost the closing ring, each
                     a sub-pixel column. One run means they have met, so gap is 0. No template
                     matching, because the ring is a different size in every frame. The target
                     drifts between reps, so neither line may be measured once and cached.
                     Getting to the hideout, opening the gym and reading fatigue are still
                     stubs that raise NotImplementedError, and their gym_* reference folders do
                     not exist yet.
                     Self-check, no game needed: python -m interact.gym
interact/ocr.py      Reads the numbers Tarkov prints. Not an OCR engine: the prices are a fixed
                     bitmap font, so it cuts the crop into glyphs and pixel-matches each against
                     a reference. read_number() is all or nothing, None if any glyph is
                     unreadable, because a partly read price is a wrong price. read_region()
                     shrinks the crop by find.scale() first: the digit references are 1080p
                     bitmaps compared inside a fixed 16x24 box, so a bigger glyph has to come
                     down to them rather than them growing to it.
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
  than a second template, because those elements only change color: the flea taskbar icon
  inverts (mean channel 57 closed, 117 open, threshold 90) and the add offer button greys out
  (brightest channel 255 lit, 123 greyed, threshold 190). `is_item_selected` is three template
  reads that all have to agree, not one: `item_is_selected` and `place_offer_button` present,
  `no_items_selected` absent, because any single match that fails for its own reasons reads as
  a selection and the pass then prices an item it never picked. `is_autoselect_similar_ticked`
  widens the button's box 30% first because the tick sits just outside it.
- **Finding items** `find_sell_pixels` masks out empty slots using a 256³ boolean cube built
  from every color in `reference_images/dead_pixels/`, ±5 per channel. Scav case boxes are
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
picture to `tests/output/`, and exits non-zero on failure. These run with no game open:
`test_price_corpus.py`, `test_activity_line.py`, `test_flea_filters_fixture.py`,
`test_cheap_offer_popup.py`, `test_totals_line.py`, `test_recover_on_start.py`,
`test_drag_failsafe.py`, `test_click_jitter.py`, `test_dropdown_no_retry.py`,
`test_recover_loop.py`, `test_tab_switch.py`, `test_run_button.py`, `test_monitors.py`,
`gym/test_generate_roi.py`,
`gym/test_line_reads.py`, `gym/test_gym_loop.py`,
`python -m interact.sell`, `python -m interact.gym`, `python -m interact.find`,
`python -m frames` and `python -m screen`.

```
gym/test_generate_roi.py     Cut gym.rep_region out of a saved frame and write the crop plus
                             the whole frame with the box drawn on it. Where to check a change
                             to REP_ROI_FRACTIONS. Takes any frame path.
gym/test_line_reads.py       gym.read_lines over every crop in fixtures/gym/line_reads/, each
                             one written back out with a green line down the target and a red
                             one down the closing ring. Takes a file or a folder.
gym/test_gym_loop.py         The gym loop's decisions against a drawn screen: clicks when the
                             lines meet and not before, one click per rep, Stop lands mid loop,
                             and a missing icon crop is a log line rather than the end of the
                             run.
```

```
test_bot_loop.py             The whole thing. --loop runs pass after pass until ctrl+c, and
                             stops it from another thread, which is the same path the GUI's
                             Stop button and X button use. --scav / --scav-only pick the item
                             source. --dry reports what it would find and clicks nothing.
test_price_corpus.py         Reads every fixture in tests/fixtures/prices/ and checks it against
                             its own filename. No game needed. The regression net for ocr.py.
test_tab_switch.py           Switching tabs stops the mode being left, and a disabled tab
                             refuses the switch. A stand-in runner, no game needed.
test_run_button.py           The run button's state machine: start -> stop -> stopping -> start,
                             the label and color agreeing at each step, and the two ways it
                             used to strand amber (stopping nothing, cancelling a countdown).
                             Opens the GUI for a moment, no game needed.
test_monitors.py             Puts a known color on each monitor in turn and reads it back
                             through screen.grab(), so a grab off the wrong screen fails here
                             rather than as the bot finding nothing. No game needed.
test_activity_line.py        The footer's activity line: is it showing the newest log line, and
                             does it stay inside the window when that line is long. Opens the
                             GUI for a moment, no game needed.
test_cheap_offer_popup.py    The below-market-value confirmation means no sale: sell_one must
                             not count posted or money, must count a price failure, and must
                             escape one more time than the pass otherwise would. No game needed.
test_totals_line.py          The end-of-run totals still get logged when a pass raises, for
                             both bots. No game needed.
test_recover_on_start.py     What Start backs out of before it looks for the flea. The case that
                             matters is the plain inventory, which must be left alone. No game
                             needed.
test_drag_failsafe.py        A drag that raises still parks the cursor off the corner before the
                             fail-safe comes back on. No game needed.
test_click_jitter.py         Clicks land off centre but stay inside the smallest reference crop
                             of the control they are aimed at. No game needed.
test_recover_loop.py         Start unwinds a stack of leftover windows a layer per round, gives
                             up on one it cannot clear rather than spinning, and returns when
                             Stop is pressed part way. No game needed.
test_recover_targets.py      The other half of that, and the half the fakes cannot cover: a real
                             Tarkbot against the real window, so the region, the crops and the
                             loop are all the shipping ones. Bare, it reports which of the three
                             windows it can see and presses nothing, so it is safe to point at a
                             live mess. --run calls that bot's own _recover, clicks and all, and
                             times it. Wants the game up.
test_dropdown_no_retry.py    A filter dropdown missing its option gives up on the first attempt
                             and never presses escape, while a pick that did not take still
                             retries. No game needed.
test_error_report.py         Crash reporting end to end. The machine id depends on all three of
                             its inputs, a real screenshot round trips byte for byte, an image
                             past the bucket cap is refused, and a crash through App._run both
                             sets the lamp and reports itself. No game needed, but it wants a
                             screen and the site running (npx next dev in website/); point it
                             at the deploy with TARKBOT_ERROR_URL. Writes real rows under a
                             test machine id and deletes them again.
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
add_offer_color.py, flea_icon_color.py    Measure a UI element's color in one state, so a
                             brightness threshold can be picked. Run once per state.
view_screenshot.py           matplotlib viewer with grid, coordinates and colors.
find_tarkov_window.py        Dead: a standalone spike that predates tarkov_window.py.
```

## Conventions

- Regions are `(left, top, width, height)` in screen coords. The Tarkov window rect comes from
  `tarkov_window.position(hwnd) + tarkov_window.size(hwnd)`, gets clipped to the chosen monitor
  by `screen.overlap()`, and is passed into `find` so matching stays inside the game window.
  The game runs fullscreen, so image coords == screen coords.
- Screen coords are the whole desktop's, not one monitor's, so `left` and `top` are negative on
  a monitor sitting left of or above the primary. Nothing may assume a screen starts at (0, 0):
  clip against `screen.rect()`, and grab through `screen.grab()` rather than
  `pyautogui.screenshot` (which is patched to it anyway) or `ImageGrab` directly.
- Matching uses `confidence=0.9` (`find.CONFIDENCE`), which requires opencv-python. A target that
  cannot meet it gets its own number in `find.CONFIDENCES`, which every call goes through, so a
  looser threshold does not have to be threaded down to one call site. Only add one with both
  readings behind it, the score with the thing on screen and the score with it gone, so the
  number can be seen to sit in the gap. Today that is `offer_creation_window_title` at 0.8:
  its title is a thin strip of small text that scores 0.88 on a 1440p screen once `needle()`
  has grown it, and 0.58 when the window is not there.
- Every reference image was cropped at 1920x1080 fullscreen. That is the one resolution the
  files themselves are matched at; every other screen gets them resized at match time by
  `find.scale()`, and the price crop scaled the other way to meet them. Crop new references at
  1080p so there is still a single size everything is derived from.
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
