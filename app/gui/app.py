"""Tarkbot GUI. Run: python -m gui.app

The whole interface is drawn onto one canvas over a pre-composited backdrop (see theme.py),
because tk widgets cannot be translucent and would punch opaque rectangles through the glass.
Canvas text and rectangles can sit over it, so the only real widgets are the two dropdowns.
"""
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import MODES, STAT_LABELS, Tarkbot  # noqa: E402
import tarkov_window  # noqa: E402
from gui import settings, theme  # noqa: E402

JOIN_TIMEOUT = 10  # seconds to give the bot to unwind before the window goes anyway
COUNTDOWN = 3  # seconds to alt-tab into Tarkov before the clicking starts

ROW_TOP = 152  # first stat row's baseline, inside the status panel
ROW_STEP = 42
PAD = 24  # panel inset used for every label and value


def spaced(text):
    """Letter-spacing, which tk fonts do not do, faked for the few headings that want it."""
    return ' '.join(text)


def clock(seconds):
    """Seconds as hh:mm:ss."""
    seconds = int(seconds)
    return f'{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}'


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


class App:
    def __init__(self, root):
        self.root = root
        self.bot = None
        self.thread = None
        self.error = None
        self.started_at = None
        self.pending = None  # the after() id of a running countdown, so Stop can cancel it
        self.prefs = settings.load()

        root.title('Tarkbot')
        root.configure(bg='#101110')
        root.resizable(False, False)
        root.protocol('WM_DELETE_WINDOW', self.close)  # the X button must kill the bot too

        family = theme.font_family(root)
        self.fonts = {'title': (family, 19), 'heading': (family, 11),
                      'label': (family, 10), 'value': (family, 15),
                      'status': (family, 12), 'plate': (family, 11), 'small': (family, 9)}

        self.canvas = tk.Canvas(root, width=theme.WINDOW[0], height=theme.WINDOW[1],
                                highlightthickness=0, bd=0)
        self.canvas.pack()
        self.backdrop_id = self.canvas.create_image(0, 0, anchor='nw')
        self._draw_chrome()
        self._draw_stats()
        self._draw_footer()
        self._draw_controls()
        self._paint_backdrop()

        self._set_status('Stopped', theme.STOPPED)
        self.tick()

    # ------------------------------------------------------------------ drawing

    def _paint_backdrop(self):
        """Recomposite and swap in the backdrop. Held on self, or tk garbage collects it."""
        from PIL import ImageTk

        self.backdrop = ImageTk.PhotoImage(theme.backdrop(self.prefs['background']))
        self.canvas.itemconfig(self.backdrop_id, image=self.backdrop)

    def _draw_chrome(self):
        self.canvas.create_text(PAD, 29, anchor='w', text=spaced('TARKBOT'),
                                fill=theme.INK, font=self.fonts['title'])
        self.canvas.create_text(PAD + 148, 31, anchor='w', text=spaced('FLEA MARKET OPERATOR'),
                                fill=theme.INK_FAINT, font=self.fonts['small'])

        names = theme.backgrounds()
        if self.prefs['background'] not in names and names:  # a deleted png must not wedge it
            self.prefs['background'] = names[0]
        self.background_var = self._dropdown('BACKGROUND', 646, names or ['none'],
                                             self.prefs['background'], self._pick_background, 128)
        labels = [label for label, _, _ in MODES.values()]
        current = MODES.get(self.prefs['mode'], MODES['inventory'])[0]
        self.mode_var = self._dropdown('SOURCE', 916, labels, current, self._pick_mode, 160)

    def _dropdown(self, caption, right, values, current, command, width):
        """A caption and a tk OptionMenu, right-aligned to x. The one real widget style here."""
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
        self.canvas.create_window(right, 29, anchor='e', window=menu, width=width, height=24)
        self.canvas.create_text(right - width - 10, 30, anchor='e', text=spaced(caption),
                                fill=theme.INK_FAINT, font=self.fonts['small'])
        return var

    def _draw_stats(self):
        left, top, right, _ = theme.STATUS_PANEL
        self.canvas.create_text(left + PAD, top + 28, anchor='w', text=spaced('STATUS'),
                                fill=theme.INK_DIM, font=self.fonts['heading'])
        self.canvas.create_line(left + PAD, top + 48, right - PAD, top + 48, fill=theme.LINE)

        self.values = {}
        rows = [*STAT_LABELS, ('runtime', 'Run time')]
        for index, (key, label) in enumerate(rows):
            y = top + ROW_TOP - 76 + index * ROW_STEP
            indent = 12 if label.startswith(' ') else 0  # the two "from ..." rows sit inset
            self.canvas.create_text(left + PAD + indent, y, anchor='w',
                                    text=spaced(label.strip().upper()),
                                    fill=theme.INK_FAINT if indent else theme.INK_DIM,
                                    font=self.fonts['label'])
            self.values[key] = self.canvas.create_text(right - PAD, y, anchor='e', text='-',
                                                       fill=theme.INK, font=self.fonts['value'])
            if index < len(rows) - 1:
                self.canvas.create_line(left + PAD, y + 20, right - PAD, y + 20,
                                        fill='#2a2c2a')

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

    # ------------------------------------------------------------------ running

    def _run(self):
        """The bot's whole life, off the tk thread so the window keeps painting and responding."""
        try:
            self.bot.start()
        except Exception as e:  # a wrong screen raises RuntimeError or LookupError mid pass
            self.error = e

    def start(self):
        # ponytail: the start lock is "is it running, or about to be?"
        if self.pending or (self.thread and self.thread.is_alive()):
            return
        self.start_plate.config(False)
        _, scav, chance = MODES.get(self.prefs['mode'], MODES['inventory'])
        try:
            self.bot = Tarkbot(target_scav_cases=scav, scav_chance=chance)
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
        if self.bot:
            for key, item in self.values.items():
                if key in self.bot.stats:
                    self.canvas.itemconfig(item, text=f'{self.bot.stats[key]:,}')
        self.canvas.itemconfig(self.values['runtime'],
                               text=clock(time.monotonic() - self.started_at)
                               if self.started_at else '-')
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
    root = tk.Tk()
    App(root)
    root.mainloop()
