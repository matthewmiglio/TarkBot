# Craft soak report: screen grab failed OSError during flea buy

| | |
|---|---|
| **Timestamp** | 2026-09-05 23:26:48 |
| **Revision** | c9881be (dirty: 12 files uncommitted) |
| **Session log** | `tarkbot-20260905-225640.log` |
| **Craft / station** | Fleece craft, buying its `ux_pro_beanie` input on the flea |
| **Restarted game?** | No. The game is up and this is not a game state - it is a Windows desktop-capture failure, which restarting Tarkov does not touch. Re-ran instead. |

> **Correction (post-restart):** the root here was not a generic Windows capture glitch but the
> **Tarkov client crashing/closing** - the next launch (`tarkbot-20260905-233134.log`) found no
> Tarkov window (`--game status` -> running False). The fullscreen client going down took the
> desktop capture with it. See the ledger's Session 2 correction note. Restarted onto seasonal.

## Error

```
File "C:\My_Files\my_programs\Tarkbot-2\app\craft_bot.py", line 311, in buy_input
    return craft.buy_craft_input_item(location, ceiling, self.region, source=source, ...)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 1295, in buy_craft_input_item
    top = _top_offer(region)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\craft.py", line 1454, in _top_offer
    buttons = snipe.purchase_buttons(region)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\snipe.py", line 416, in purchase_buttons
    return sorted(find.find_all(PURCHASE_TARGET, region), key=lambda box: box.top)
File "C:\My_Files\my_programs\Tarkbot-2\app\interact\find.py", line 382, in find_all
    image, offset = _haystack(region, haystack)
File "C:\My_Files\my_programs\Tarkbot-2\app\screen.py", line 206, in grab
    return _crop(ImageGrab.grab(all_screens=True), ...)
File "...\PIL\ImageGrab.py", line 93, in grab
    offset, size, data = Image.core.grabscreen_win32(...)
OSError: screen grab failed
```

Last narration before the crash:

```
[23:26:19.572]   fleece craft state: ready
[23:26:20.506] fleece missing ['ux_pro_beanie'], buying each
[23:26:20.611]   buying 2 ux_pro_beanie at up to 3500 from traders
[23:26:20.611] buying 2 craft input(s) at (1727.5, 1014.0), ceiling 3500
[23:26:21.920]   clicking filter by item at (1850, 1058)
Traceback (most recent call last):
...
OSError: screen grab failed
```

## Diagnosis

Not a bot-logic failure and nothing to do with the scav case. The fleece craft was ready but short
its `ux_pro_beanie` input, so the runner went to the flea to buy two: it right-clicked the input to
open the filter-by-item menu (last log line, 23:26:21.920) and then went to read the board's
PURCHASE buttons, and the read's screenshot itself failed at the Windows API level.

The exception is `OSError: screen grab failed`, raised by Pillow's `Image.core.grabscreen_win32`
inside `ImageGrab.grab(all_screens=True)`, which `screen.grab` (screen.py:206) calls for every
capture. That is the Win32 GDI desktop-capture (BitBlt of the virtual screen) returning failure -
the process could not photograph the desktop at that instant. It is an environmental/transient
condition, not a pixel or region problem: the usual triggers are the session locking or the
lock/secure desktop (a UAC prompt) coming to the foreground, the display going to sleep or changing
mode, or a momentary GPU/driver/DWM hiccup. The bot had done thousands of successful grabs in the
~30 minutes before this one and the game was still running afterwards, so nothing about this call
site was special; a grab that had worked all run failed once.

It surfaced on a flea read only because that is what the bot happened to be doing; any `find`,
`find_all`, brightness read or frame capture goes through the same `screen.grab`, so the same
one-off could land on any screen-reading line.

## Proposed solution

Make `screen.grab` survive a single transient capture failure instead of letting it end a
multi-hour run. Wrap the `ImageGrab.grab` call in a small retry: on `OSError`, sleep briefly
(~100-250ms) and try again once or twice before giving up, then raise if it still fails. Grabs are
idempotent and side-effect-free, so a retry cannot double anything, and the failure's typical
causes (a lock screen flashing up, a mode switch, a driver blip) clear within a frame or two. This
is the same "poll/retry rather than conclude failure on the first look" pattern the handover and
panel-close fixes used. A retry that exhausts still raises, so a genuinely gone display (monitor
unplugged, session logged out) still stops the run loudly rather than spinning.

Do not apply during the soak.

## Recurrences

_(Append `- <timestamp> - <craft/station>` lines here if this same signature happens again,
instead of writing a new report.)_
