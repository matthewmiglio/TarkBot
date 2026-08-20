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
snipe_bot.py         FleaSniper: the flea run backwards. Walks a watchlist of item names,
                     searches each on the flea, reads the cheapest offer, and buys it when the
                     asking price is far enough under what a trader pays. Selling to the trader
                     afterwards is done by hand; nothing here goes near a trader screen.
                     check_one is one item: type its name into the flea's search box, wait
                     SEARCH_DELAY for the suggestion list, and if a padlock is showing in that
                     quarter of the window leave the item alone. Otherwise click the suggestion,
                     click back into the box and empty it, wait BOARD_DELAY for the board, read
                     the price on the topmost offer row, and buy that row if it is far enough
                     under trader value.
                     sweep_once walks the whole watchlist, start() repeats it. The order is
                     reshuffled every sweep: a sweep is the same work whatever order it runs in,
                     and the csv's own order would mean the top of the list is read every few
                     minutes on the dot while the bottom always waits longest.
                     The filters go on once per sweep, not once per item: they survive a search,
                     and that window costs four matches and three menu waits. A filter-by-item is
                     cleared straight after them and not only at Start, because the filter
                     window's reset can bring a saved filter set back with it, and a board still
                     filtered to one item answers every search with that item: 77 checks that are
                     really one.
                     The board is read through the topmost PURCHASE button rather than through a
                     region of its own. That button is the only thing on an offer row with a
                     reference crop, the price sits at a fixed offset from it, and the match is
                     needed anyway to click it, so one match does both jobs.
                     MARGINS is the GUI's MARGIN dropdown: how many roubles under trader value an
                     offer has to be listed before it is bought, 500/1k/2k/5k. Flat roubles and
                     not a percentage, because what makes a flip worth the clicks is the profit
                     and not the ratio: 10% off a 2000 rouble barter item is 200 roubles for the
                     same six actions that clear 9000 on a scope.
                     trader_choices/for_trader are the GUI's TRADER dropdown: buy only what one
                     trader buys back, or everything. Not about the money, about the selling
                     afterwards being done by hand. A run bringing home 26 Therapist items and 2
                     Jaeger ones is a run where the two get missed, and an item sold to the wrong
                     trader pays less: on 2026-08-17 two Jaeger scopes worth 54,894 went to a
                     trader that was not Jaeger and took most of that run's missing profit with
                     them. The choices come off the csv rather than a list here, busiest trader
                     first, so a regenerated watchlist offers the right ones on its own.
                     DEFAULT_TRADER is Therapist, not ALL_TRADERS: 70 of the 77 items are
                     Therapist's, so the default gives up 7 and removes the whole class of
                     mistake. It is a trader's name, so it can go missing from a regenerated
                     watchlist the same way a saved one can, and gui/app.py falls back through it
                     to ALL_TRADERS rather than onto it.
                     SANITY_FLOOR is the other half of worth_buying and is not an optimisation.
                     Every way a price read goes wrong drops digits rather than adding them, so
                     every misread looks like a bargain, which is the one direction that spends
                     money on its own. A listing under a quarter of trader value is refused.
                     interact/snipe.read_price refuses a clipped crop outright; this catches the
                     reads that come back looking sane.
                     Same shape as the other two modes (stats dict, _pause checkpoint,
                     start/stop, build). Its _pause is the third copy of Tarkbot._pause, which
                     is the third mode gym_bot.py's note said would settle it: hoist _pause,
                     _stop and stop() into a Runner before any of the three grows a checkpoint
                     the other two do not have.
                     Self-check, no game needed: python -m snipe_bot
snipe_targets.csv    That watchlist: name, trader, trader price, 24h flea average, gap, category.
                     Generated, not hand written. _price_scraper/rouble_flips.py writes it from
                     the pages _price_scraper/scrape_prices.py pulls off tarkov-market.com, and
                     the scraper module is gitignored while this file is committed and shipped,
                     so a build has the list without needing the network.
                     Roubles only, both legs: rows whose trader pays in dollars are dropped at
                     scrape time. The file is ranked by how far under trader value each item's
                     flea price usually sits, which is worth reading but is not the order the bot
                     uses: sweep_once reshuffles every pass.
                     The Name column comes from the site's span.name, not from the name cell's
                     text, which runs the item name into its required level and its category
                     breadcrumbs. That name is typed into the flea's search box, so a breadcrumb
                     left on the end of one is an item silently never checked.
                     scripts/setup_msi.py copies it to lib/snipe_targets.csv, and snipe_bot's
                     TARGETS_PATH resolves to lib/ off sys.executable when frozen rather than off
                     __file__. It has to: snipe_bot is a top-level module and cx_Freeze packs
                     those into lib/library.zip, so __file__ points inside the zip and the plain
                     form looked for the csv one level too deep. interact/find.py gets away with
                     the plain form only because interact/ is a package and stays a real folder.
                     v1.1.0 shipped the csv and could not read it, and since targets() answers a
                     missing file with an empty list rather than a crash, the only symptom was a
                     TRADER dropdown with nothing on it but 'All traders'.
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
                     check from a wall. A look costs ~17ms, nearly all of it the one screenshot
                     it takes of gym.look_region and slices into the icon box and the strip.
                     The press is aimed, not reacted to. _predict() takes the ring's speed from
                     the readings so far and, once either the press falls due or the two lines
                     are about to merge, sleeps to the aimed moment and presses. It has to: the
                     ring closes at ~100 columns a second on a set's first rep and ~320 by its
                     fifteenth, so waiting to *see* the lines meet presses past them.
                     A reading is anchored to when its pixels were grabbed, not to when the look
                     began. Measured, not assumed: the ring's speed inside a rep is constant, so
                     the right clock is the one that makes gap against time straightest, and
                     over 453 looks that was 0.62 columns of residual for grabbed against 0.72
                     for started. A grab is 8-22ms, so anchoring to the start of it was pressing
                     a whole grab early, which is 4 columns at rep 15 into a window about 2.5
                     wide. That one argument was most of what stopped a set finishing 15 of 15.
                     CLICK_LEAD is the trim; CLICK_GAP is only the fallback for a rep whose
                     overlap happened inside one look.
                     Tarkov scores the rep on the press, not the release, and pyautogui presses
                     immediately, so its 0.1s PAUSE costs throughput and not accuracy. Do not
                     turn PAUSE off: sell.py depends on those pauses between its own clicks.
                     It aims at the two centres lining up, trimmed by AIM_COLUMNS (a spatial
                     offset, for a miss that looks the same at every speed) and CLICK_LEAD (a
                     time one, for reps that land early in a set and miss late in it). Aiming
                     at gym.Lines.touch, where the lines first meet 4-8 columns sooner, was
                     tried because every fallback press had landed there, and it pressed too
                     early on every rep.
                     CLICK_LEAD is 20ms, and the aim point is therefore about 20ms before the
                     two centres line up rather than on them. It was 0 on the strength of three
                     sessions that found a lead worse both ways; those predate fast_grab and the
                     grabbed anchor below, and with a reading anchored a whole grab early a lead
                     was being stacked on an error that already pressed early, so they measured
                     the wrong thing. Scored against the flash the game gives each rep, over
                     reps 11-15 of six sets: 0 of 2 landed when the press was late, about half
                     landed under 12ms early, and it is a flat plateau of three quarters to all
                     from 12ms out to 40ms. Aiming dead on scored 11 of 15.
                     An aim can legitimately fall after the two lines merge, which is why the
                     merged branch honours a pending aim instead of pressing on sight, and it
                     can now fall before the merge too, which is why _predict commits on
                     whichever of those comes first rather than on the merge alone.
                     Attacking the spread: the loop reads through screen.fast_grab, a BitBlt of
                     just the look box, which took a look from ~60ms to ~17ms. Speed is measured
                     across SPEED_SAMPLES readings end to end rather than the last two, so half
                     a column of reading error does not become a large fraction of the speed.
                     What is left is not fixable by aiming. A grab costs ~16.7ms whatever size
                     it is (measured from 10,000 pixels to 250,000: all 16.7), because it waits
                     for the display's next frame, so a look is one 60Hz frame and the ring
                     moves ~5 columns per frame by rep 15. The scoring window there is about
                     that wide, so the last rep is bounded by frame quantisation and not by the
                     bot. Shrinking the look box to read faster would gain nothing.
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
                     tab per mode (FLEA SELL / FLEA SNIPE / HIDEOUT GYM) and the pickers each
                     mode needs. FLEA SNIPE's MARGIN and TRADER dropdowns sit in the same two
                     header slots as FLEA SELL's UNDERCUT and SOURCE: a tab's dropdowns are never
                     on screen with another tab's, so they share the positions rather than each
                     taking one.
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
                     DISABLED_TABS are drawn greyed and cannot be switched to at all. It is
                     empty today, so all three modes are selectable; put a key back in it to
                     grey one out.
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
                     (flea.png, gym.png, snipe.png), swapped by repainting the backdrop on tab
                     switch. The filename is the whole wiring: a new mode drops a png in here
                     named for its tab and theme.py needs no change.
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
interact/snipe.py    The same for the flea sniper. sell.is_flea_open and sell.return_to_browse
                     are used as they are, rather than copied: they are the shipping versions and
                     a second copy would be a second thing to keep in step with the game's UI.
                     open_flea is the exception and wraps sell.open_flea: open, escape, open
                     again. Reopening puts the filter chips back at the front of the header,
                     which is what makes a leftover filter-by-item visible to
                     remove_filter_by_item_filter. Escape rather than clicking the taskbar icon
                     a second time, since that icon toggles on brightness and sell.open_flea
                     would read it as already open and not click.
                     open_clean_board is the whole opening and what snipe_bot.start() calls:
                     open_flea, FILTER_SETTLE for the header to draw its chips, then clear a
                     leftover filter-by-item if one is there and give the board BOARD_DELAY to
                     reload. The reload wait only happens when something was cleared, since a run
                     that starts clean has nothing to wait for. apply_flea_filters is one line:
                     sell.apply_flea_filters(region, reset=True). It was a copy for a while, on
                     the grounds that a buyer's filters would diverge from a seller's, and they
                     never did. The reset was the only difference, so it is a flag on the
                     seller's function now, and the name survives here as the sniper's seam for
                     the filters it will want that a seller never will.
                     Both modes open that window through sell.open_filters, which clicks the
                     gear and then waits FILTERS_WINDOW_TIMEOUT for flea_filters_window_title
                     before anything reads a control inside it. A click on the gear is not the
                     same as the window opening: the game can put a plain Error dialog over the
                     flea, and without the check the first thing to notice was the currency
                     dropdown read, which blamed a missing reference crop for a window that was
                     never on screen.
                     reset=True clicks flea_filters_reset_button and reopens the window (the
                     reset closes it) before the seller's flow runs. Without it a dropdown is
                     only ever touched while it still says 'any', so a board somebody already
                     filtered is left exactly as it was found. Right for a mode that lists
                     items, wrong for one that buys them: a filter we did not set is a board we
                     are not reading all of, and an offer missed is invisible in a way a wrong
                     price is not.
                     search_for finds flea_enter_item_name_input *before* typing and aims
                     everything after that from where the box was then. It has to: once a name
                     is in the field no crop of the empty box matches it any more, and the
                     suggestion list that drops has no reference image at all. SUGGESTION_DROP
                     is 1.5 box heights under the box's bottom edge, in the box's own height
                     rather than pixels so it scales like everything else here.
                     clear_search takes that same box rather than looking for it again, for the
                     same reason, and runs last rather than first. Emptying the field before
                     typing would work just as well for the field and would leave the previous
                     name in it through the whole price read that follows, with the board
                     underneath filtered by it.
                     PRICE_LEFT/TOP/WIDTH/HEIGHT are the price's offsets from its row's PURCHASE
                     button, 1080p pixels like every other measurement. Measured off 250 recorded
                     frames of a real 1440p board: the button at (2284, 226) 161x32 and the price
                     spanning x 1819-1960 on rows y 214-247. All 1957 rows across those frames
                     read back the price the board was showing.
                     read_price refuses a crop with anything lit in its left gutter. A price
                     wider than its box has had its leading digits cut off, and a cut price reads
                     low, which is the direction that makes the sniper buy.
                     buy() checks that the money left rather than that the click went out, by
                     photographing ruble_region either side of itself and handing the pair to
                     purchase_landed. It has to: Tarkov's confirmation sometimes does not take
                     the 'y' at all, and on 2026-08-17 that cost 55,000 roubles of purchases
                     counted and never made, with every rouble stat downstream inheriting it. A
                     second 'y' is sent if the first did not land, which cannot double buy since
                     the key does nothing with no dialog up, and a 'n' after that, so a
                     confirmation nobody answered cannot swallow the next item's clicks.
                     purchase_landed tests brightness before pixels, and needs both. Tarkov dims
                     everything behind that dialog, and the dimming alone moves 12.8% of the
                     balance box, against the 13.6% a real purchase moves: a pixel count on its
                     own says yes to both. Brightness separates them, 0.95 of the old mean for a
                     real purchase and 0.50 for a live dialog, hence BALANCE_DIM at 0.75.
                     BALANCE_MOVED is 2%, between a real purchase's 13.6% and the 0.000% two
                     grabs of an unchanged balance move.
                     RUBLE_ROI_FRACTIONS is that box, measured on a 2560x1440 flea where the
                     balance sits at x 1943-2112, y 93-131. Tune it with
                     tests/test_ruble_region.py, which draws the box on the screen it cut it
                     from.
                     remove_filter_by_item_filter clears a filter-by-item chip: check the board
                     reads as filtered (filter_by_item_filter_applied), find every
                     clear_filter_button, click the leftmost. Not wired into the loop yet.
                     The applied check first is the whole design. clear_filter_button is a 12 to
                     14 pixel crop of a small plain glyph, the shape of target that has no
                     false-positive headroom, and every other filter chip carries the same x: on
                     a board filtered only by currency and condition, the leftmost x found is the
                     *currency* one, and clicking it would quietly unfilter roubles. Something
                     bigger has to say the item chip is there before its x is trusted.
                     is_locked looks for flea_item_locked_icon over top_left_quadrant of the
                     window, which is where the suggestion list drops. The whole window would
                     find a padlock anywhere in the UI, and a box around one row is not needed:
                     the list has exactly one row in it, because every watchlist name was typed
                     into a real flea first and the fourteen that brought back several rows or
                     none were dropped. One row means one padlock and no question of whose it is.
                     That is a real coupling: put an ambiguous name back on the list and this
                     reads the wrong row's lock. _price_scraper/rouble_flips.py's AMBIGUOUS set
                     is what holds it. It is read while the list is still up,
                     the only moment it can be: the list closes the instant a suggestion is
                     clicked, so a locked item is never clicked at all.
                     Those crops read 2 padlocks in the quadrant of a frame that visibly has 2,
                     and 0 on a frame with no list up, which is the present-and-absent pair this
                     repo wants behind any target. An empty flea_item_locked_icon/ raises out of
                     find and is meant to: this is what stands between the sniper and clicking
                     purchase on something it cannot buy, so failing quietly is worse than the
                     run stopping and naming the folder.
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
  fractions, because the number inside changes and there is nothing stable to match),
  `grab_first_offer_region` (the same trick and the same scaling, for the topmost comparable
  offer; `FIRST_OFFER_FRACTIONS` was measured at 2560x1440 rather than 1080p, since that is
  what was on screen, and `tests/test_first_offer_region.py` is where to retune it).
- **State reads** `is_flea_open` and `more_offers_available` work off pixel brightness rather
  than a second template, because those elements only change color: the flea taskbar icon
  inverts (mean channel 57 closed, 117 open, threshold 90; the cursor is parked before the
  read, since hovering the entry inverts it the same way and a pointer left sitting on it
  after a click reads as open whatever the flea is doing) and the add offer button greys out
  (brightest channel 255 lit, 123 greyed, threshold 190). `is_item_selected` is three template
  reads that all have to agree, not one: `item_is_selected` and `place_offer_button` present,
  `no_items_selected` absent, because any single match that fails for its own reasons reads as
  a selection and the pass then prices an item it never picked. `is_autoselect_similar_ticked`
  looks inside the *right half* of that button's box grown 15% (`_checkmark_region_from`),
  because the checkbox is at that end of every reference crop of it. Sizing the region off the
  whole box, as it used to, made it depend on which crop won: a short crop matching gave a
  region too small to hold the checkmark needle, and pyscreeze raises rather than missing.
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
- **Pricing** `get_price` reads the suggested price, but only after `first_offer_is_a_pack` has
  said the top comparable offer is a single item. A pack offer's title ends '- pack' and the
  price quoted under it is the whole pack's, so undercutting it lists one item at twenty items'
  money. Nothing later in the pass can catch that: the number in the box is perfectly readable,
  and every counter in the run's totals agrees it went well. A pack reads as None, which is
  already the answer `sell_bot` handles correctly, by skipping the item and starting a fresh
  pass, so no new failure mode had to be threaded through. `undercut_price(price, fraction, flat)`
  returns the higher of `price * fraction` and `price - flat`, so the flat cut wins on expensive
  items and the percentage wins on cheap ones without ever going negative. They cross at
  `flat / (1 - fraction)`. Which pair to use is the GUI's UNDERCUT dropdown, `sell_bot.UNDERCUTS`:
  2k, 3k or 5k, all at 90%, so the choice only moves the price where the flat cut takes over.
  `sell.py`'s own constants are only the defaults.

## Tests

Nothing here is pytest. Each script runs against the live game, prints what it saw, writes a
picture to `tests/output/`, and exits non-zero on failure. These run with no game open:
`test_price_corpus.py`, `test_activity_line.py`, `test_flea_filters_fixture.py`,
`test_checkmark_region.py`, `test_snipe_loop.py`, `test_snipe_watchlist.py`,
`test_cheap_offer_popup.py`, `test_totals_line.py`, `test_recover_on_start.py`,
`test_drag_failsafe.py`, `test_click_jitter.py`, `test_dropdown_no_retry.py`,
`test_recover_loop.py`, `test_tab_switch.py`, `test_run_button.py`, `test_monitors.py`,
`test_window_gone.py`, `test_pack_offer.py`,
`gym/test_generate_roi.py`,
`gym/test_line_reads.py`, `gym/test_gym_loop.py`,
`python -m interact.sell`, `python -m interact.gym`, `python -m interact.snipe`,
`python -m interact.find`, `python -m snipe_bot`,
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
test_window_gone.py          A game closed mid-run stops the pass before the add offer click
                             rather than clicking where the button used to be, and an open one
                             still goes through. No game needed.
test_pack_offer.py           A suggested price quoted against a pack is refused before the OCR
                             is ever reached, and a normal offer still reads. No game needed.
test_first_offer_region.py   Where sell.grab_first_offer_region lands, drawn on the screen it was
                             cut from: the window with the box on it in yellow and the crop at
                             2x, both to tests/output/first_offer_region/. The tuning loop for
                             FIRST_OFFER_FRACTIONS. Takes a saved frame, or grabs the live
                             window.
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
test_checkmark_region.py     Where the tick is looked for and whether it is found there, over
                             whole frames rather than a live screen. Each frame is run at its
                             own size and again at 1920x1080, since this only goes wrong on a
                             screen that is not 1080p. Writes an annotated png and a 4x zoom per
                             frame to tests/output/checkmark_region/: button blue, region
                             yellow, tick green. Look at those before believing an 'unticked',
                             since a region drawn in the wrong place reads the same in the
                             summary as a checkbox that is genuinely empty. Defaults to the
                             frame recorder's folder, or takes frame paths. No game needed.
test_remove_item_filter.py   What snipe.remove_filter_by_item_filter can see, and with --click
                             what it does. Bare it clicks nothing: it says whether the board
                             reads as filtered by item, how many clear-filter buttons are up and
                             which is leftmost, and draws all of it to
                             tests/output/remove_item_filter/ (chip blue, buttons yellow,
                             leftmost green). Takes a saved frame or the live window; --click
                             wants the game and clears the filter for real.
test_ruble_region.py         Where snipe.ruble_region lands, drawn on the screen it was cut
                             from: the whole window with the box on it in yellow, and the crop
                             at 4x, both to tests/output/ruble_region/. The tuning loop for
                             RUBLE_ROI_FRACTIONS. Takes a saved frame, or grabs the live window.
test_snipe_loop.py           The snipe loop's decisions against a stand-in screen: a cheap top
                             offer is bought, a dear one is left, an unreadable price is never
                             acted on, a price under SANITY_FLOOR reads as a misread rather than
                             a bargain, an empty board and a missing search box end the item and
                             not the run, a filter-by-item that survived the filter window is
                             cleared before any searching, a purchase whose balance never moved
                             is counted nowhere but in "buys that missed", a locked item is
                             skipped before the board is ever read,
                             filters that will not go on stop the sweep before it reads anything,
                             a shuffled sweep still covers every item exactly once and two sweeps
                             do not walk the same order, and Stop lands mid sweep. No game needed.
test_snipe_watchlist.py      The watchlist loads and the TRADER dropdown has traders on it,
                             plus where the frozen build looks for the csv, checked by pretending
                             to be frozen rather than by freezing. No game needed.
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
  number can be seen to sit in the gap. Two entries today. `offer_creation_window_title` at 0.8:
  its title is a thin strip of small text that scores 0.88 on a 1440p screen once `needle()`
  has grown it, and 0.58 when the window is not there. `autoselect_similar` at 0.85: 0.889 to
  0.944 across every frame it is in at either resolution, and never above 0.413 across 134
  frames it is not in, so the old flat 0.9 ran through the middle of the real matches and lost
  the button on a 1440p screen by 0.011.
- Do not "fix" one of these by lowering `CONFIDENCE` itself. How low a target can safely go is a
  property of that target: a wide element full of structure has a low false-positive ceiling
  (the button, 0.413), a small plain one does not (`checkmark`, which scores 0.69 against an
  *empty* checkbox, because empty and ticked are the same square). A global 0.42 would fix the
  button and make the tick read ticked on a box that is not.
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
