"""Tarkbot GUI. Run: python -m gui.app

The whole interface is drawn onto one canvas over a pre-composited backdrop (see theme.py),
because tk widgets cannot be translucent and would punch opaque rectangles through the glass.
Canvas text and rectangles can sit over it, so the only real widgets are the dropdowns, which
sit in two header rows (see DROP_ROW).
"""
import ctypes
import sys
import threading
import time
import tkinter as tk
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gym_bot  # noqa: E402
import sell_bot  # noqa: E402
import session_log  # noqa: E402
import tarkov_window  # noqa: E402
from narrate import log  # noqa: E402
from sell_bot import DEFAULT_STALE, DEFAULT_UNDERCUT, MODES, STALE_THRESHOLDS, UNDERCUTS  # noqa: E402
from gui import settings, theme  # noqa: E402

JOIN_TIMEOUT = 10  # seconds to give the bot to unwind before the window goes anyway
COUNTDOWN = 3  # seconds to alt-tab into Tarkov before the clicking starts

# One mode per tab. Each module supplies the same four things and nothing else, so adding a
# third mode is a row here plus a module, not a new branch through the drawing code:
#   STAT_LABELS  the rows to draw, (key, label)
#   TINT_STAT    the row that goes green once it is non-zero, or None
#   build(prefs, stats)  a runner with .start(), .stop() and .stats
TABS = (('flea', 'FLEA SELL', sell_bot), ('gym', 'HIDEOUT GYM', gym_bot))
DEFAULT_TAB = 'flea'

DROP_ROW = (29, 63)  # centre lines of the header's two dropdown rows
TAB_ROW = 138  # the tab strip's centre line, inside the status panel
TAB_WIDTH = 132
TAB_GAP = 8
ROW_TOP = 222  # first stat row's baseline, below the tab strip
ROW_STEP = 32  # tuned to the row count: ten rows have to fit between ROW_TOP and the panel foot
PAD = 24  # panel inset used for every label and value
TIP_DELAY = 400  # ms of hover before a tooltip appears, so passing over one does not flash it


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

    def _hover(self, over):
        if self.enabled:
            self.canvas.itemconfig(self.rect, fill=theme.PLATE_HOT if over else theme.PLATE)
            self.canvas.config(cursor='hand2' if over else '')

    def config(self, enabled):
        self.enabled = enabled
        self.canvas.itemconfig(self.rect, fill=theme.PLATE,
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
        if self.prefs['tab'] not in self.modules:  # an edited settings file must not wedge it
            self.prefs['tab'] = DEFAULT_TAB
        self.tab = self.prefs['tab']
        # Owned here rather than by the runner, and handed to every one we build, so the
        # counters run for the whole session instead of restarting with each Start. One dict
        # per mode: selling counts and gym counts have nothing to say to each other.
        self.stats = {key: {k: 0 for k, _ in module.STAT_LABELS}
                      for key, _, module in TABS}
        self.drag_from = None  # where in the header a window drag started, None when not dragging

        claim_taskbar_identity()
        root.title('Tarkbot')
        if theme.ICON.is_file():
            root.iconbitmap(default=theme.ICON)  # default= so dialogs inherit it, not just this window
        root.configure(bg='#101110')
        root.resizable(False, False)
        root.protocol('WM_DELETE_WINDOW', self.close)  # the X button must kill the bot too

        family = theme.font_family(root)
        self.fonts = {'title': (family, 19), 'heading': (family, 11),
                      'label': (family, 10), 'value': (family, 15),
                      'status': (family, 12), 'plate': (family, 11), 'small': (family, 9)}

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
        self._paint_backdrop()
        self._show_tab(self.tab)  # hides the other tab's rows and dropdowns

        self._set_status('Stopped', theme.STOPPED)
        self.tick()

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

        close = bar.create_text(width - PAD, theme.TITLEBAR // 2, text='✕',
                                fill=theme.CLOSE, font=self.fonts['status'], tags='close')
        bar.tag_bind('close', '<Button-1>', lambda _: self.close())
        for event, colour in (('<Enter>', theme.CLOSE_HOT), ('<Leave>', theme.CLOSE)):
            bar.tag_bind('close', event, lambda _, c=colour: bar.itemconfig(close, fill=c))

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

        self.backdrop = ImageTk.PhotoImage(theme.backdrop(self.prefs['background']))
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

        # Both modes put their one mode-specific dropdown in the same slot, and the tab tags
        # decide which is on screen. They can share the x because they are never both visible.
        labels = [label for label, _, _ in MODES.values()]
        current = MODES.get(self.prefs['mode'], MODES['inventory'])[0]
        self.mode_var = self._dropdown('SOURCE', 916, labels, current, self._pick_mode, 150,
                                       tag='tab:flea')
        if self.prefs['routine'] not in gym_bot.ROUTINES:
            self.prefs['routine'] = gym_bot.DEFAULT_ROUTINE
        self.routine_var = self._dropdown(
            'ROUTINE', 916, [label for label, _ in gym_bot.ROUTINES.values()],
            gym_bot.ROUTINES[self.prefs['routine']][0], self._pick_routine, 150, tag='tab:gym',
            tip='How many reps to work through before resting')

        # Second row. Only the flea has anything to put here so far; the gym tab leaves it empty.
        if self.prefs['undercut'] not in UNDERCUTS:  # an edited settings file must not wedge it
            self.prefs['undercut'] = DEFAULT_UNDERCUT
        self.undercut_var = self._dropdown(
            'UNDERCUT', 916, list(UNDERCUTS), self.prefs['undercut'], self._pick_undercut, 150,
            tag='tab:flea', row=1,
            tip='How far under the suggested price to list: the higher of the flat cut and the '
                'percentage, so the flat one wins on expensive items')

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
        """Switch modes: light that tab, show its rows and dropdowns, hide the other's.

        Refuses while something is running. Swapping the panel out from under a live runner
        would leave Stop pointing at a mode the window is no longer showing, and the counters
        updating behind a hidden panel.
        """
        if self.thread and self.thread.is_alive():
            return
        self.tab = tab
        self.prefs['tab'] = tab
        settings.save(self.prefs)
        for key in self.modules:
            self.canvas.itemconfigure(f'tab:{key}', state='normal' if key == tab else 'hidden')
            self.tabs[key].select(key == tab)

    def _draw_footer(self):
        y = theme.FOOTER_RULE + 34
        self.dot = self.canvas.create_oval(PAD, y - 5, PAD + 10, y + 5,
                                           fill=theme.STOPPED, outline='')
        self.status = self.canvas.create_text(PAD + 22, y, anchor='w', text='',
                                              fill=theme.INK_DIM, font=self.fonts['status'])

    def _draw_controls(self):
        y = theme.FOOTER_RULE + 34
        self.stop_plate = Plate(self.canvas, (theme.WINDOW[0] - PAD - 130, y - 17,
                                              theme.WINDOW[0] - PAD, y + 17),
                                'STOP', self.stop, self.fonts['plate'])
        self.start_plate = Plate(self.canvas, (theme.WINDOW[0] - PAD - 276, y - 17,
                                               theme.WINDOW[0] - PAD - 146, y + 17),
                                 'START', self.start, self.fonts['plate'])
        self.stop_plate.config(False)

    def _set_status(self, text, colour):
        """The one place the state indicator is written, so lamp and words cannot disagree."""
        self.canvas.itemconfig(self.dot, fill=colour)
        self.canvas.itemconfig(self.status, text=spaced(text.upper()), fill=colour)

    # ------------------------------------------------------------------ preferences

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

    def _pick_undercut(self, label):
        self.prefs['undercut'] = label  # the dropdown's labels are the keys, so no lookup
        settings.save(self.prefs)

    def _pick_stale(self, label):
        self.prefs['stale'] = label  # the dropdown's labels are the keys, so no lookup
        settings.save(self.prefs)

    def _pick_routine(self, label):
        for key, (text, _) in gym_bot.ROUTINES.items():
            if text == label:
                self.prefs['routine'] = key
                break
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
            log(f'run ended on {type(e).__name__}: {e}')
            log(traceback.format_exc().rstrip(), 1)
            self.error = e

    def start(self):
        # ponytail: the start lock is "is it running, or about to be?"
        if self.pending or (self.thread and self.thread.is_alive()):
            return
        self.start_plate.config(False)
        # Whichever mode the tab is on. Both modules expose build(prefs, stats), so there is no
        # branch here on which one it is.
        try:
            self.bot = self.modules[self.tab].build(self.prefs, self.stats[self.tab])
        except tarkov_window.WindowError as e:
            self.bot = None
            self.start_plate.config(True)
            self._set_status(str(e), theme.ERROR)
            return
        self.error = None
        self.stop_plate.config(True)  # enabled now, so the countdown can be cancelled
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
            self.start_plate.config(True)
            self.stop_plate.config(False)
            self._set_status('Stopped', theme.STOPPED)
            return
        if self.bot:
            self.bot.stop()
        self.stop_plate.config(False)
        self._set_status('Stopping', theme.WARNING)

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
            # as the rest, so the colour means "it has actually done something" not "this row".
            tint = self.modules[tab].TINT_STAT
            if tint:
                self.canvas.itemconfig(items[tint],
                                       fill=theme.RUNNING if stats[tint] else theme.INK)
            self.canvas.itemconfig(items['runtime'],
                                   text=clock(time.monotonic() - self.started_at)
                                   if self.started_at and tab == self.tab else '-')
        if self.thread and not self.thread.is_alive():  # stopped, or died on a wrong screen
            self.thread = None
            self.started_at = None
            self.start_plate.config(True)
            self.stop_plate.config(False)
            if self.error:
                self._set_status(f'Error: {self.error}'[:60], theme.ERROR)
            else:
                self._set_status('Stopped', theme.STOPPED)
        self.root.after(1000, self.tick)


if __name__ == '__main__':
    session_log.start()  # one file per boot, same as the frozen build. See session_log.py.
    root = tk.Tk()
    App(root)
    root.mainloop()
