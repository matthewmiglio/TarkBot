"""Tarkbot GUI. Run: python -m gui.app

The whole interface is drawn onto one canvas over a pre-composited backdrop (see theme.py),
because tk widgets cannot be translucent and would punch opaque rectangles through the glass.
Canvas text and rectangles can sit over it, so the only real widgets are the dropdowns, which
sit in two header rows (see DROP_ROW).
"""
import ctypes
import ctypes.wintypes
import os
import sys
import threading
import time
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import font as tkfont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crash_report  # noqa: E402
import frames  # noqa: E402
import gym_bot  # noqa: E402
import screen  # noqa: E402
import sell_bot  # noqa: E402
import session_log  # noqa: E402
import snipe_bot  # noqa: E402
import window  # noqa: E402
import narrate  # noqa: E402  the module, not the function: narrate.LAST has to be read live
from sell_bot import DEFAULT_STALE, DEFAULT_UNDERCUT, MODES, STALE_THRESHOLDS, UNDERCUTS  # noqa: E402
from snipe_bot import DEFAULT_MARGIN, MARGINS  # noqa: E402
from gui import settings, theme  # noqa: E402

JOIN_TIMEOUT = 10  # seconds to give the bot to unwind before the window goes anyway
COUNTDOWN = 3  # seconds to alt-tab into Tarkov before the clicking starts

# One mode per tab. Each module supplies the same four things and nothing else, so adding a
# third mode is a row here plus a module, not a new branch through the drawing code:
#   STAT_LABELS  the rows to draw, (key, label)
#   TINT_STAT    the row that goes green once it is non-zero, or None
#   build(prefs, stats)  a runner with .start(), .stop() and .stats
TABS = (('flea', 'FLEA SELL', sell_bot), ('snipe', 'FLEA SNIPE', snipe_bot),
        ('gym', 'HIDEOUT GYM', gym_bot))
DEFAULT_TAB = 'flea'
# Tabs drawn but not selectable, greyed rather than deleted so a mode being built can still be
# seen. Empty today: all three modes are selectable. Put a key back in here to grey one out.
DISABLED_TABS = set()

DROP_ROW = (29, 63)  # centre lines of the header's two dropdown rows
TAB_ROW = 138  # the tab strip's centre line, inside the status panel
TAB_WIDTH = 132
TAB_GAP = 8
ROW_TOP = 222  # first stat row's baseline, below the tab strip
ROW_STEP = 32  # tuned to the row count: ten rows have to fit between ROW_TOP and the panel foot
PAD = 24  # panel inset used for every label and value
LOG_DROP = 40  # px below the status row for the activity line, in the band under the buttons
LOG_BOX = 17  # half the height of the box drawn round that line, and its inset from the text
TIP_DELAY = 400  # ms of hover before a tooltip appears, so passing over one does not flash it
BUTTON = (130, 34)  # every footer plate, so the run button and LOGS cannot drift apart
BUTTON_GAP = 16
# What the run button can be bound to: the name shown, and its Windows virtual key. F1 is 0x70
# and they run in order, so the codes are worked out rather than listed.
#
# Function keys only, and that is a safety rail rather than laziness. RegisterHotKey takes the
# key system wide and *eats* it, so binding W would stop the key walking in Tarkov. F5 is left
# out because sell_bot presses it itself to refresh the flea after every offer, and the bot's
# own refresh came straight back here as a press of its own Stop.
HOTKEYS = {f'F{n}': 0x6F + n for n in range(1, 13) if n != 5}
DEFAULT_HOTKEY = 'F4'
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
# The run button's three states: label, face color, and whether it can be pressed. Green to go,
# red to stop, and amber while the ask is with the bot and there is nothing useful to press.
# {key} is filled in with whatever the key is bound to now; 'Stopping...' has none to fill.
RUN_STATES = {'start': ('Start ({key})', theme.RUNNING, True),
              'stop': ('Stop ({key})', theme.ERROR, True),
              'stopping': ('Stopping...', theme.WARNING, False)}


def hotkey(fire):
    """Global start/stop key. Returns bind(name), which claims a key and drops the last one.

    A Windows hotkey registration rather than a tk key binding, because tk only sees keys while
    its own window has focus and the entire point of this one is to stop the bot while the game
    is in front of it.

    It is not a poll of the keyboard either. The thread sits blocked inside GetMessageW until
    Windows pushes the press into its queue, so a press registers the moment it happens rather
    than having to be held down until something comes round to look at the key.

    Rebinding is one thread per key rather than a message the running one understands: the
    registration belongs to the thread that made it, so the old key can only be given back by
    the thread holding it. WM_QUIT ends its GetMessageW loop and it unregisters on the way out.
    """
    live = {}  # the pump thread's id, so the next bind can tell it to let its key go

    def pump(name, key):
        user32 = ctypes.windll.user32
        live['thread'] = ctypes.windll.kernel32.GetCurrentThreadId()  # kernel32, not user32
        if not user32.RegisterHotKey(None, 1, 0, key):
            narrate.log(f'{name} is already claimed by another program, so the hotkey is off. '
                        f'The button still works.')
            return
        narrate.log(f'{name} will start and stop the bot, from inside the game too')
        message = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            if message.message == WM_HOTKEY:
                fire()
        user32.UnregisterHotKey(None, 1)  # WM_QUIT: a rebind is waiting on this key coming free

    def bind(name):
        old = live.pop('thread', None)
        if old:
            ctypes.windll.user32.PostThreadMessageW(old, WM_QUIT, 0, 0)
        threading.Thread(target=pump, args=(name, HOTKEYS[name]), daemon=True).start()

    return bind


def claim_taskbar_identity(app_id='tarkbot'):
    """Make the taskbar show our icon instead of the host exe's.

    Windows groups taskbar buttons by AppUserModelID, and from source that id is python.exe,
    so the button shows the Python logo no matter what the window icon says. Frozen it is
    already tarkbot.exe, but setting it explicitly costs nothing and keeps the two the same.
    """
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        pass  # not Windows, or an old shell32. A wrong icon is not worth failing to open over.


def strip_titlebar(root):
    """Drop the system title bar but keep the taskbar button and alt-tab entry.

    overrideredirect takes the frame and the taskbar button with it, which would strand the
    window behind fullscreen Tarkov with no way back. Clearing WS_EX_TOOLWINDOW and setting
    WS_EX_APPWINDOW puts the button back, and the window has to be hidden and reshown for
    Windows to notice the new style at all.
    """
    GWL_EXSTYLE, WS_EX_TOOLWINDOW, WS_EX_APPWINDOW = -20, 0x00000080, 0x00040000
    root.overrideredirect(True)
    root.update_idletasks()
    user32 = ctypes.windll.user32
    hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TOOLWINDOW | WS_EX_APPWINDOW)
    root.withdraw()
    root.after(10, root.deiconify)


def spaced(text):
    """Letter-spacing, which tk fonts do not do, faked for the few headings that want it."""
    return ' '.join(text)


def clock(seconds):
    """Seconds as hh:mm:ss."""
    seconds = int(seconds)
    return f'{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}'


def one_line(text, font, width):
    """`text` as a single line, tail-trimmed with an ellipsis until it fits `width` pixels.

    First line only: a canvas text item draws every newline it is given, and the one message
    that is many lines long is the crash traceback, which would run straight off the bottom of
    the window. Measured in the real font rather than cut at a character count, because the
    family is whatever the machine has and a count that fits here overflows there.
    """
    text = text.splitlines()[0] if text else ''
    measure = tkfont.Font(font=font).measure
    if measure(text) <= width:
        return text
    while text and measure(text + '…') > width:
        text = text[:-1]
    return text + '…' if text else ''


class Tip:
    """Hover text for one widget. tk has no tooltip and a library for one string is silly.

    A Toplevel rather than a canvas item, because it has to be able to draw outside the
    window, and it is built on show rather than kept hidden so nothing lingers if the widget
    goes away underneath it.
    """

    def __init__(self, widget, text, font, delay=TIP_DELAY):
        self.widget, self.text, self.font, self.delay = widget, text, font, delay
        self.window = self.pending = None
        widget.bind('<Enter>', self._enter, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<Button-1>', self._hide, add='+')  # or it sits over the opened menu

    def _enter(self, _event):
        self.pending = self.widget.after(self.delay, self._show)

    def _hide(self, _event=None):
        if self.pending:
            self.widget.after_cancel(self.pending)
            self.pending = None
        if self.window:
            self.window.destroy()
            self.window = None

    def _show(self):
        self.pending = None
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        tk.Label(self.window, text=self.text, bg=theme.PLATE, fg=theme.INK, font=self.font,
                 bd=1, relief='solid', padx=8, pady=4).pack()
        self.window.geometry(f'+{self.widget.winfo_rootx()}'
                             f'+{self.widget.winfo_rooty() + self.widget.winfo_height() + 6}')


class Plate:
    """A flat rectangle that behaves like a button. tk.Button cannot sit over the backdrop."""

    def __init__(self, canvas, box, text, command, font):
        self.canvas, self.command, self.enabled = canvas, command, True
        self.fill, self.hot = theme.PLATE, theme.PLATE_HOT
        self.rect = canvas.create_rectangle(*box, fill=theme.PLATE, outline=theme.LINE, width=1)
        self.label = canvas.create_text((box[0] + box[2]) // 2, (box[1] + box[3]) // 2,
                                        text=spaced(text), fill=theme.INK, font=font)
        for item in (self.rect, self.label):
            canvas.tag_bind(item, '<Button-1>', self._click)
            canvas.tag_bind(item, '<Enter>', lambda _: self._hover(True))
            canvas.tag_bind(item, '<Leave>', lambda _: self._hover(False))

    def _click(self, _event):
        if self.enabled:
            self.command()

    def paint(self, text, fill):
        """Recolor the face and rewrite the label, for a button whose color carries its state.

        The text is written as given, not letter-spaced like the ones set in the constructor:
        spacing suits an all caps word and turns 'Stop (F4)' into something unreadable.
        """
        self.fill, self.hot = fill, theme.lighter(fill)
        self.canvas.itemconfig(self.label, text=text)
        self.config(self.enabled)  # so the face and the outline are painted in one place

    def _hover(self, over):
        if self.enabled:
            self.canvas.itemconfig(self.rect, fill=self.hot if over else self.fill)
            self.canvas.config(cursor='hand2' if over else '')

    def config(self, enabled):
        self.enabled = enabled
        self.canvas.itemconfig(self.rect, fill=self.fill,
                               outline=theme.LINE if enabled else theme.INK_FAINT)
        self.canvas.itemconfig(self.label, fill=theme.INK if enabled else theme.INK_FAINT)


class Tab(Plate):
    """A Plate whose selected state is lit rather than dimmed.

    Plate.config() dims what it disables, which is right for a button you cannot press and
    backwards for the tab you are already on. select() inverts both halves: the active tab is
    the bright one, and it is unclickable because clicking it would do nothing.
    """

    def select(self, active):
        self.enabled = not active
        self.canvas.itemconfig(self.rect, fill=theme.PLATE_HOT if active else theme.PLATE,
                               outline=theme.INK_FAINT if active else theme.LINE)
        self.canvas.itemconfig(self.label, fill=theme.INK if active else theme.INK_DIM)


class App:
    def __init__(self, root):
        self.root = root
        self.bot = None
        self.thread = None
        self.error = None
        self.started_at = None
        self.pending = None  # the after() id of a running countdown, so Stop can cancel it
        self.prefs = settings.load()
        self.modules = {key: module for key, _, module in TABS}
        self.tabs = {}  # key -> Tab, filled by _draw_tabs
        self.values = {}  # tab key -> {stat key -> canvas item}, filled by _draw_stats
        # An edited settings file must not wedge it, and neither must one saved back when the
        # tab it was left on was still selectable.
        if self.prefs['tab'] not in self.modules or self.prefs['tab'] in DISABLED_TABS:
            self.prefs['tab'] = DEFAULT_TAB
        self.tab = self.prefs['tab']
        # Owned here rather than by the runner, and handed to every one we build, so the
        # counters run for the whole session instead of restarting with each Start. One dict
        # per mode: selling counts and gym counts have nothing to say to each other.
        self.stats = {key: {k: 0 for k, _ in module.STAT_LABELS}
                      for key, _, module in TABS}
        self.drag_from = None  # where in the header a window drag started, None when not dragging
        self.restore_to = None  # where to put the window back when it comes up off the taskbar

        claim_taskbar_identity()
        root.title('Tarkbot')
        if theme.ICON.is_file():
            root.iconbitmap(default=theme.ICON)  # default= so dialogs inherit it, not just this window
        root.configure(bg='#101110')
        root.resizable(False, False)
        root.protocol('WM_DELETE_WINDOW', self.close)  # the X button must kill the bot too
        root.bind('<Map>', self._restored)  # coming back off the taskbar, see minimise()

        family = theme.font_family(root)
        self.fonts = {'title': (family, 19), 'heading': (family, 11),
                      'label': (family, 10), 'value': (family, 15),
                      'status': (family, 12), 'plate': (family, 11), 'small': (family, 9),
                      # The activity line, a quarter up on 'small' so the one thing that
                      # changes second to second is not the smallest text in the window.
                      'activity': (family, 11)}

        self._build_titlebar(root)  # packed first, so it sits above the main canvas
        self.canvas = tk.Canvas(root, width=theme.WINDOW[0], height=theme.WINDOW[1],
                                highlightthickness=0, bd=0)
        self.canvas.pack()
        self.backdrop_id = self.canvas.create_image(0, 0, anchor='nw')
        self._draw_chrome()
        self._draw_tabs()
        for key, _, module in TABS:
            self._draw_stats(key, module)
        self._draw_footer()
        self._draw_controls()
        self._show_tab(self.tab)  # paints the backdrop, hides the other tab's rows and dropdowns

        # Once the dropdown has resolved 'auto' to a real screen, so anything grabbing pixels
        # before Start is ever pressed (frame capture, the tests) already has the right one.
        screen.use(self.prefs['monitor'])
        settings.save(self.prefs)

        self._set_status('Stopped', theme.STOPPED)
        self.tick()

        # The press arrives on the hotkey's own thread, and tk is only safe to touch from the
        # thread that built it, so the work is handed back over with after(0) rather than done
        # there. That is a queue jump, not a wait: the tk loop is idle between ticks and picks
        # it up on the next pass through, which is the same instant from a person's point of
        # view. The stop itself is a threading.Event the bot is already watching.
        self.bind_hotkey = hotkey(lambda: self.root.after(0, self.toggle))
        self.bind_hotkey(self.prefs['hotkey'])

        # Last, so the window only appears once it has something to show.
        strip_titlebar(root)

    # ------------------------------------------------------------------ window chrome

    def _build_titlebar(self, root):
        """Our own title bar. It has to *look* draggable, not just be draggable.

        A bare header the user has to discover by accident is the same as no title bar at all,
        so this carries the three things people already read as one: the app mark on the left,
        the close on the right, and a move cursor the moment you hover it.
        """
        width = theme.WINDOW[0]
        bar = tk.Canvas(root, width=width, height=theme.TITLEBAR, bg=theme.TITLEBAR_BG,
                        highlightthickness=0, bd=0, cursor='fleur')
        bar.pack()
        bar.create_line(0, theme.TITLEBAR - 1, width, theme.TITLEBAR - 1, fill=theme.LINE)

        left = PAD
        if theme.ICON.is_file():
            from PIL import Image, ImageTk

            # Held on self or tk collects it and the bar comes up blank.
            self.bar_icon = ImageTk.PhotoImage(
                Image.open(theme.ICON).resize((16, 16), Image.LANCZOS))
            bar.create_image(left, theme.TITLEBAR // 2, image=self.bar_icon, anchor='w')
            left += 24
        bar.create_text(left, theme.TITLEBAR // 2 + 1, anchor='w', text=spaced('TARKBOT'),
                        fill=theme.INK_FAINT, font=self.fonts['small'])

        # Close on the corner, minimise inboard of it, in the order Windows puts them. Same
        # font as each other so they read as one pair of controls, and the minimise is grey
        # rather than red: closing kills a running bot, minimising is the harmless one.
        for glyph, offset, command, rest, hot in (
                ('✕', 0, self.close, theme.CLOSE, theme.CLOSE_HOT),
                ('−', 26, self.minimise, theme.STOPPED, theme.INK)):
            tag = f'chrome{offset}'
            item = bar.create_text(width - PAD - offset, theme.TITLEBAR // 2, text=glyph,
                                   fill=rest, font=self.fonts['status'], tags=tag)
            bar.tag_bind(tag, '<Button-1>', lambda _, c=command: c())
            # Canvas items have no cursor of their own, so the bar's own is swapped on the way
            # in and put back on the way out. Without it these read as more drag handle, and a
            # move cursor over a button says the click will not do anything.
            for event, color, cursor in (('<Enter>', hot, 'hand2'), ('<Leave>', rest, 'fleur')):
                bar.tag_bind(tag, event, lambda _, i=item, c=color, k=cursor: (
                    bar.itemconfig(i, fill=c), bar.config(cursor=k)))

        bar.bind('<Button-1>', self._drag_start, add='+')
        bar.bind('<B1-Motion>', self._drag, add='+')
        self.titlebar = bar

    def _drag_start(self, event):
        self.drag_from = (event.x, event.y)

    def _drag(self, event):
        if self.drag_from is None:
            return
        # Canvas coords, so the offset is measured against the window that just moved and the
        # pointer lands back on the same pixel. Screen coords would compound the delta.
        x = self.root.winfo_x() + event.x - self.drag_from[0]
        y = self.root.winfo_y() + event.y - self.drag_from[1]
        self.root.geometry(f'+{x}+{y}')

    # ------------------------------------------------------------------ drawing

    def _paint_backdrop(self):
        """Recomposite and swap in the backdrop. Held on self, or tk garbage collects it."""
        from PIL import ImageTk

        self.backdrop = ImageTk.PhotoImage(theme.backdrop(self.prefs['background'], self.tab))
        self.canvas.itemconfig(self.backdrop_id, image=self.backdrop)

    def _draw_chrome(self):
        # The subtitle that used to sit beside the title is gone: three dropdowns need the
        # width more than 'FLEA MARKET OPERATOR' does.
        self.canvas.create_text(PAD, 29, anchor='w', text=spaced('TARKBOT'),
                                fill=theme.INK, font=self.fonts['title'])

        if self.prefs['stale'] not in STALE_THRESHOLDS:  # an edited settings file must not wedge it
            self.prefs['stale'] = DEFAULT_STALE
        self.stale_var = self._dropdown(
            'STALE OFFER THRESHOLD', 452, list(STALE_THRESHOLDS), self.prefs['stale'],
            self._pick_stale, 62, tag='tab:flea',
            tip='How long to wait for offers to sell before removing stale offers')
        names = theme.backgrounds()
        if self.prefs['background'] not in names and names:  # a deleted png must not wedge it
            self.prefs['background'] = names[0]
        # Untagged, so it stays put across tabs: the backdrop is the window's, not a mode's.
        self.background_var = self._dropdown('BACKGROUND', 684, names or ['none'],
                                             self.prefs['background'], self._pick_background, 112)

        # Tagged tab:flea, so it is on screen only on that tab. Gym mode has nothing of its own
        # to pick: it watches for the skill check and clicks it, and the only thing it needs
        # told is which monitor, which the row below asks once for both modes.
        labels = [label for label, _, _ in MODES.values()]
        current = MODES.get(self.prefs['mode'], MODES['inventory'])[0]
        self.mode_var = self._dropdown('SOURCE', 916, labels, current, self._pick_mode, 150,
                                       tag='tab:flea')

        # Snipe mode's own pick, in the slot SOURCE uses on the flea tab. The two are never on
        # screen together, the same arrangement as UNDERCUT and MARGIN on the row below.
        traders = snipe_bot.trader_choices()
        if self.prefs['trader'] not in traders:  # a regenerated watchlist can drop a trader
            # And the default is a trader's name now, so it can go missing the same way.
            self.prefs['trader'] = (snipe_bot.DEFAULT_TRADER
                                    if snipe_bot.DEFAULT_TRADER in traders
                                    else snipe_bot.ALL_TRADERS)
        self.trader_var = self._dropdown(
            'TRADER', 916, traders, self.prefs['trader'], self._pick_trader, 150, tag='tab:snipe',
            tip='Only buy items this trader will buy back, so everything bought goes to one '
                'trader when you sell it on')

        # Second row. Untagged like the background: which screen the game is on belongs to the
        # window, not to a mode, so both tabs see it.
        self.monitors = {m.label: m for m in screen.monitors()}
        chosen = next((m for m in self.monitors.values() if m.name == self.prefs['monitor']),
                      None) or self._monitor_now()
        self.prefs['monitor'] = chosen.name  # 'auto', or an unplugged screen, resolves to a real one
        self.monitor_var = self._dropdown(
            'MONITOR', 452, list(self.monitors), chosen.label, self._pick_monitor, 150, row=1,
            tip='Which screen to watch and click on. Defaults to the one Tarkov is on')
        # Untagged too, in the slot BACKGROUND uses on the row above: the key starts and stops
        # whichever mode the tab is on, so it is the window's setting rather than a mode's.
        if self.prefs['hotkey'] not in HOTKEYS:  # an edited settings file must not wedge it
            self.prefs['hotkey'] = DEFAULT_HOTKEY
        self.hotkey_var = self._dropdown(
            'START KEY', 684, list(HOTKEYS), self.prefs['hotkey'], self._pick_hotkey, 112, row=1,
            tip='The key that starts and stops the bot from inside the game. Function keys '
                'only: the key is taken system wide, so a letter would stop working in Tarkov')
        if self.prefs['undercut'] not in UNDERCUTS:  # an edited settings file must not wedge it
            self.prefs['undercut'] = DEFAULT_UNDERCUT
        self.undercut_var = self._dropdown(
            'UNDERCUT', 916, list(UNDERCUTS), self.prefs['undercut'], self._pick_undercut, 150,
            tag='tab:flea', row=1,
            tip='How far under the suggested price to list: the higher of the flat cut and the '
                'percentage, so the flat one wins on expensive items')
        # Snipe mode's one pick, in the slot UNDERCUT uses on the flea tab. They are never on
        # screen together, so the two share the position rather than each getting their own.
        if self.prefs['margin'] not in MARGINS:  # an edited settings file must not wedge it
            self.prefs['margin'] = DEFAULT_MARGIN
        self.margin_var = self._dropdown(
            'MARGIN', 916, list(MARGINS), self.prefs['margin'], self._pick_margin, 150,
            tag='tab:snipe', row=1,
            tip='How many roubles under trader value an offer has to be listed before it is '
                'bought')

    def _draw_tabs(self):
        """The mode strip along the top of the status panel.

        It sits where the STATUS heading used to: with two modes the tab labels say what the
        panel is showing better than the word STATUS did, so that heading is gone rather than
        squeezed in above these.
        """
        left, top, right, _ = theme.STATUS_PANEL
        x = left + PAD
        for key, label, _ in TABS:
            self.tabs[key] = Tab(self.canvas, (x, TAB_ROW - 13, x + TAB_WIDTH, TAB_ROW + 13),
                                 label, lambda k=key: self._show_tab(k), self.fonts['plate'])
            if key in DISABLED_TABS:
                self.tabs[key].config(False)  # greyed and unclickable, see DISABLED_TABS
            x += TAB_WIDTH + TAB_GAP
        self.canvas.create_line(left + PAD, TAB_ROW + 32, right - PAD, TAB_ROW + 32,
                                fill=theme.LINE)

    def _dropdown(self, caption, right, values, current, command, width, tip=None, tag=None,
                  row=0):
        """A caption and a tk OptionMenu, right-aligned to x. The one real widget style here.

        tag: a canvas tag, so _show_tab can hide the whole thing. Canvas window items take
        state='hidden' like any other item, which is why the dropdowns can be tabbed at all.
        row: which header row, indexing DROP_ROW.
        """
        var = tk.StringVar(value=current)
        menu = tk.OptionMenu(self.canvas, var, *values, command=command)
        menu.config(bg=theme.PLATE, fg=theme.INK, activebackground=theme.PLATE_HOT,
                    activeforeground=theme.INK, highlightthickness=1, bd=0, relief='flat',
                    highlightbackground=theme.LINE, highlightcolor=theme.LINE,
                    font=self.fonts['label'], anchor='w', width=1, padx=8, pady=2,
                    indicatoron=False, direction='below')
        menu['menu'].config(bg=theme.PLATE, fg=theme.INK, activebackground=theme.PLATE_HOT,
                            activeforeground=theme.INK, bd=0, relief='flat',
                            font=self.fonts['label'])
        tags = (tag,) if tag else ()
        y = DROP_ROW[row]
        self.canvas.create_window(right, y, anchor='e', window=menu, width=width, height=24,
                                  tags=tags)
        self.canvas.create_text(right - width - 10, y + 1, anchor='e', text=spaced(caption),
                                fill=theme.INK_FAINT, font=self.fonts['small'], tags=tags)
        if tip:
            Tip(menu, tip, self.fonts['label'])  # held by the widget's own bindings, not by us
        return var

    def _draw_stats(self, tab, module):
        """One mode's stat rows, tagged so _show_tab can hide them as a set.

        Every tab's rows are drawn once at startup and then shown or hidden, rather than being
        torn down and redrawn on each switch. Canvas items are cheap to hide and the ids stay
        stable, so tick() can keep writing into whichever set it likes.
        """
        left, top, right, _ = theme.STATUS_PANEL
        self.values[tab] = {}
        rows = [*module.STAT_LABELS, ('runtime', 'Run time')]
        for index, (key, label) in enumerate(rows):
            y = ROW_TOP + index * ROW_STEP
            indent = 12 if label.startswith(' ') else 0  # the two "from ..." rows sit inset
            self.canvas.create_text(left + PAD + indent, y, anchor='w',
                                    text=spaced(label.strip().upper()),
                                    fill=theme.INK_FAINT if indent else theme.INK_DIM,
                                    font=self.fonts['label'], tags=f'tab:{tab}')
            self.values[tab][key] = self.canvas.create_text(
                right - PAD, y, anchor='e', text='-', fill=theme.INK,
                font=self.fonts['value'], tags=f'tab:{tab}')
            if index < len(rows) - 1:
                self.canvas.create_line(left + PAD, y + 20, right - PAD, y + 20,
                                        fill='#2a2c2a', tags=f'tab:{tab}')

    def _show_tab(self, tab):
        """Switch modes: stop whatever was running, then light that tab and show its rows.

        Switching used to be refused outright while a runner was alive, which meant the only
        way across was Stop and then the tab. The switch now does the stopping itself, because
        the thing that must never happen is the window showing one mode while another is still
        clicking: Stop would point at a panel that is no longer up, the counters would move
        behind a hidden one, and Start on the new tab would put a second bot on top of a live
        one.

        The wait is on the tk thread, so the window sits still until the pass unwinds, the same
        way the X button does. A stop lands at the next sell.* checkpoint, so that is a second
        or two, not a whole listing. The lamp is left to tick() rather than tidied here, which
        keeps the one place that decides what "the runner ended" looks like.
        """
        if tab in DISABLED_TABS:
            return
        # tab != self.tab: __init__ calls this with the tab already set, to do the first draw.
        if tab != self.tab and (self.pending or (self.thread and self.thread.is_alive())):
            narrate.log(f'switching to the {tab} tab, so stopping the {self.tab} one first')
            self.stop()  # cancels a countdown outright, or asks a live runner to unwind
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=JOIN_TIMEOUT)
                narrate.log('stopped' if not self.thread.is_alive()
                            else f'still running after {JOIN_TIMEOUT}s, switching anyway', 1)
        self.tab = tab
        self.prefs['tab'] = tab
        settings.save(self.prefs)
        self._paint_backdrop()  # each mode has its own figure in the character panel
        for key in self.modules:
            self.canvas.itemconfigure(f'tab:{key}', state='normal' if key == tab else 'hidden')
            if key not in DISABLED_TABS:  # select() would light a tab that cannot be used
                self.tabs[key].select(key == tab)

    def _draw_footer(self):
        y = theme.FOOTER_RULE + 34
        self.dot = self.canvas.create_oval(PAD, y - 5, PAD + 10, y + 5,
                                           fill=theme.STOPPED, outline='')
        self.status = self.canvas.create_text(PAD + 22, y, anchor='w', text='',
                                              fill=theme.INK_DIM, font=self.fonts['status'])
        # The bot's most recent narrated line, under the buttons and across the full width. The
        # lamp says what state the run is in; this says what it is doing right now, which is the
        # difference between a pass that is working and one that is stuck on the same step. The
        # session log keeps the history, so this is only ever the newest line.
        #
        # Boxed, because unboxed it read as a caption drifting under the buttons rather than as
        # its own readout. Outline only, no fill: the backdrop behind it is a photo composited
        # into one image (see theme.py) and a canvas rectangle cannot be translucent over it.
        line = y + LOG_DROP
        self.canvas.create_rectangle(PAD, line - LOG_BOX, theme.WINDOW[0] - PAD, line + LOG_BOX,
                                     outline=theme.LINE, fill='')
        self.activity = self.canvas.create_text(PAD + LOG_BOX // 2, line, anchor='w', text='',
                                                fill=theme.INK_DIM, font=self.fonts['activity'])

    def _draw_controls(self):
        """The run button and LOGS, against the right edge, widest thing on the footer.

        One run button rather than a START beside a STOP: one of that pair was always greyed
        out, so only ever one of them was really there. Its color and its label say which of
        the two it is at the moment, which the greying was a poorer way of saying.
        """
        y = theme.FOOTER_RULE + 34
        width, height = BUTTON

        def box(slot):
            """The slot'th button in from the right edge, as (left, top, right, bottom)."""
            edge = theme.WINDOW[0] - PAD - slot * (width + BUTTON_GAP)
            return (edge - width, y - height // 2, edge, y + height // 2)

        self.run_plate = Plate(self.canvas, box(0), '', self.toggle, self.fonts['plate'])
        self.logs_plate = Plate(self.canvas, box(1), 'LOGS', self.open_logs, self.fonts['plate'])
        self._set_run('start')

    def _set_run(self, state):
        """The one place the run button is written, so its label and color cannot disagree."""
        label, color, live = RUN_STATES[state]
        self.run_state = state
        self.run_plate.paint(label.format(key=self.prefs['hotkey']), color)
        self.run_plate.config(live)

    def toggle(self):
        """The run button, and the hotkey: start when stopped, stop when running.

        'stopping' does nothing on purpose. The ask is already with the bot, and a second one
        would not reach it any sooner.
        """
        if self.run_state == 'start':
            self.start()
        elif self.run_state == 'stop':
            self.stop()

    def _set_status(self, text, color):
        """The one place the state indicator is written, so lamp and words cannot disagree."""
        self.canvas.itemconfig(self.dot, fill=color)
        self.canvas.itemconfig(self.status, text=spaced(text.upper()), fill=color)

    # ------------------------------------------------------------------ preferences

    def _monitor_now(self):
        """The monitor to start on: the one Tarkov is on, or the primary if it is not running.

        Read off the window's middle rather than its top left corner, which on a maximised
        window can sit a pixel over the edge onto the screen next door.
        """
        try:
            hwnd = window.handle()
            (x, y), (width, height) = window.position(hwnd), window.size(hwnd)
            found = screen.containing((x + width // 2, y + height // 2))
            narrate.log(f'Tarkov is on monitor {found.label}, starting there')
            return found
        except window.WindowError:
            return screen.current()  # the game is not running, so there is nothing to follow

    def _pick_monitor(self, label):
        self.prefs['monitor'] = self.monitors[label].name  # the label is for reading, not saving
        settings.save(self.prefs)
        screen.use(self.prefs['monitor'])

    def _pick_background(self, name):
        self.prefs['background'] = name
        settings.save(self.prefs)
        self._paint_backdrop()

    def _pick_mode(self, label):
        for key, (text, _, _) in MODES.items():
            if text == label:
                self.prefs['mode'] = key
                break
        settings.save(self.prefs)

    def _pick_hotkey(self, name):
        """Claim the new key, give the old one back, and relabel the button that names it."""
        if name == self.prefs['hotkey']:
            return  # binding it again would fight the registration we already hold
        self.prefs['hotkey'] = name
        settings.save(self.prefs)
        self.bind_hotkey(name)
        self._set_run(self.run_state)

    def _pick_undercut(self, label):
        self.prefs['undercut'] = label  # the dropdown's labels are the keys, so no lookup
        settings.save(self.prefs)

    def _pick_stale(self, label):
        self.prefs['stale'] = label  # the dropdown's labels are the keys, so no lookup
        settings.save(self.prefs)

    def _pick_margin(self, label):
        self.prefs['margin'] = label  # the dropdown's labels are the keys, so no lookup
        settings.save(self.prefs)

    def _pick_trader(self, label):
        self.prefs['trader'] = label  # a trader's name, or snipe_bot.ALL_TRADERS
        settings.save(self.prefs)

    # ------------------------------------------------------------------ running

    def _run(self):
        """The bot's whole life, off the tk thread so the window keeps painting and responding."""
        try:
            self.bot.start()
        except Exception as e:  # a wrong screen raises RuntimeError or LookupError mid pass
            # The lamp only has room for 60 characters, so the log is the only place the whole
            # message and the line that raised it survive. Without this a crash just stops the
            # log dead mid pass, with no reason on the last line.
            narrate.log(f'run ended on {type(e).__name__}: {e}')
            narrate.log(traceback.format_exc().rstrip(), 1)
            self.error = e
            # Off to the website too, on its own thread, so a crash on someone else's setup can
            # be looked at here. Opt out by setting send_telemetry false in settings.json,
            # which also stops snipe mode reporting what it buys. See gui/settings.py.
            if self.prefs.get('send_telemetry'):
                crash_report.report_later(e)

    def start(self):
        # ponytail: the start lock is "is it running, or about to be?"
        if self.pending or (self.thread and self.thread.is_alive()):
            return
        # Whichever mode the tab is on. Both modules expose build(prefs, stats), so there is no
        # branch here on which one it is.
        try:
            self.bot = self.modules[self.tab].build(self.prefs, self.stats[self.tab])
        except window.WindowError as e:
            self.bot = None
            self._set_status(str(e), theme.ERROR)
            return
        self.error = None
        self._set_run('stop')  # pressable through the countdown, so that can be cancelled too
        self._countdown(COUNTDOWN)

    def _countdown(self, left):
        """Tick down to launch, on tk's event loop. A sleep here would freeze the window."""
        self.pending = None
        if left > 0:
            self._set_status(f'Starting in {left}', theme.WARNING)
            self.pending = self.root.after(1000, self._countdown, left - 1)
            return
        self.started_at = time.monotonic()  # after the countdown, uptime is running time
        # daemon so a wedged bot can never outlive the window, on top of the join in close()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._set_status('Running', theme.RUNNING)

    def stop(self):
        """Ask it to stop. tick() does the tidying once the thread actually ends."""
        if self.pending:  # still counting down, so there is nothing running to ask
            self.root.after_cancel(self.pending)
            self.pending = None
            self.bot = None
            self._set_run('start')
            self._set_status('Stopped', theme.STOPPED)
            return
        if self.bot:
            self.bot.stop()
        # 'Stopping' only while something is actually unwinding. tick() is what clears it, and
        # tick() only fires on a thread it watched die, so setting it with nothing running
        # would leave the button amber and unpressable with no way back.
        if self.thread and self.thread.is_alive():
            self._set_run('stopping')
            self._set_status('Stopping', theme.WARNING)
        else:
            self._set_run('start')
            self._set_status('Stopped', theme.STOPPED)

    def open_logs(self):
        """Open %APPDATA%/tarkbot in Explorer: the session logs, the frames and settings.json.

        Made first if it is not there yet, so a fresh install opens an empty folder rather than
        failing with nothing on screen to say why.
        """
        try:
            settings.APP_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(settings.APP_DIR)  # Windows only, like the rest of this app
        except OSError as e:  # no Explorer, or the folder is somewhere unreachable
            narrate.log(f'could not open {settings.APP_DIR}: {e}')
            self._set_status(f'Cannot open {settings.APP_DIR}', theme.ERROR)

    def minimise(self):
        """Send the window to the taskbar.

        overrideredirect windows cannot be iconified, so the system frame goes back on for as
        long as it takes to minimise and comes straight off again on the way back (see the
        <Map> binding). The geometry is put back by hand afterwards: restoring re-measures the
        window against a frame that is no longer there, and without this it walks a title bar's
        height down the screen every time.
        """
        where = (self.root.winfo_x(), self.root.winfo_y())
        narrate.log(f'minimising, window at {where} to be put back there')
        self.root.overrideredirect(False)
        # Putting the frame back remaps the window, which queues a <Map> of its own. Drained
        # here while restore_to is still None, so _restored ignores it; arming afterwards is
        # what makes the next <Map> mean "the user brought us back" and nothing else.
        self.root.update()
        narrate.log('system frame back on, since an overrideredirect window cannot iconify, '
                    'and its own <Map> drained so it does not read as a restore', 1)
        self.restore_to = where
        self.root.iconify()
        narrate.log(f'iconified, tk calls that state {self.root.state()!r}; '
                    f'the taskbar button is the way back', 1)

    def _restored(self, event=None):
        """Take the system frame back off once Windows has finished restoring the window."""
        if event is not None and event.widget is not self.root:
            return  # a child canvas being mapped; those reach the toplevel's bindings too
        if self.restore_to is None:
            return  # a Map we did not ask for: the first show, or strip_titlebar's own redisplay
        x, y = self.restore_to
        self.restore_to = None  # cleared first, or strip_titlebar's deiconify lands back in here
        narrate.log(f'restored from the taskbar at {(self.root.winfo_x(), self.root.winfo_y())}, '
                    f'taking the system frame back off')
        strip_titlebar(self.root)
        self.root.geometry(f'+{x}+{y}')
        narrate.log(f'window put back at {(x, y)}, which the restore had moved it off', 1)

    def close(self):
        """Window closed: stop the bot and wait for it, so nothing keeps clicking after the GUI."""
        settings.save(self.prefs)
        self.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=JOIN_TIMEOUT)
        self.root.destroy()

    def tick(self):
        # Every tab's rows, not just the visible one: a mode left running is not the only way a
        # counter moves, and writing to a hidden item is free.
        for tab, items in self.values.items():
            stats = self.stats[tab]
            for key, item in items.items():  # no runner needed, the dict is ours and always there
                if key in stats:
                    self.canvas.itemconfig(item, text=f'{stats[key]:,}')
            # Green only once that mode's headline counter has moved; zero stays the same ink
            # as the rest, so the color means "it has actually done something" not "this row".
            tint = self.modules[tab].TINT_STAT
            if tint:
                self.canvas.itemconfig(items[tint],
                                       fill=theme.RUNNING if stats[tint] else theme.INK)
            self.canvas.itemconfig(items['runtime'],
                                   text=clock(time.monotonic() - self.started_at)
                                   if self.started_at and tab == self.tab else '-')
        # Trimmed to the inside of the box, not to the window, or a long line runs through its
        # right edge instead of stopping at it.
        self.canvas.itemconfig(self.activity,
                               text=one_line(narrate.LAST, self.fonts['activity'],
                                             theme.WINDOW[0] - 2 * PAD - LOG_BOX))
        if self.thread and not self.thread.is_alive():  # stopped, or died on a wrong screen
            self.thread = None
            self.started_at = None
            self._set_run('start')
            if self.error:
                self._set_status(f'Error: {self.error}'[:60], theme.ERROR)
            else:
                self._set_status('Stopped', theme.STOPPED)
        self.root.after(1000, self.tick)


if __name__ == '__main__':
    session_log.start()  # one file per boot, same as the frozen build. See session_log.py.
    frames.start()  # and a screenshot either side of every click, to read beside that log
    root = tk.Tk()
    App(root)
    root.mainloop()
