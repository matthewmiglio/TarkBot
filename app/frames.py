"""A screenshot either side of every input the bot sends, kept beside the session logs.

Not a recording. Frames are grabbed on change: immediately before an input goes to the game
and immediately again once it has landed, so a pass reads back as before/after pairs rather
than as thousands of near identical stills. The one other source is find.py, which saves the
screen it just judged on every detection while find.VERBOSE is on (craft mode's runs), so a
target the bot could not see leaves a picture of the screen it could not see it on, not just a
log line. Nothing takes a frame outside those two paths.

Each file is named for the millisecond it was taken (`1754702835123-pre.png`), which is what
lets a frame be lined up against the session log: the log line printed right beside it says
what the bot thought it was doing, the pair of frames says what the screen actually did.

The whole screen at its own resolution, never scaled or cropped, so a frame is what the user
was looking at even on a monitor nothing was measured on. PNG is lossless, so the pixels come
back exactly; only the bytes on disk are packed, at the cheapest level PIL has.

ponytail: pyautogui's input functions are wrapped in place by watch(), rather than 33 call
sites in interact/sell.py each learning to take a frame. It buys frames around clicks that do
not exist yet, and it costs the surprise of a patched module. Unpick it into explicit calls
the day something needs frames somewhere that is not an input.

The grab has to happen on the bot thread, at the moment the frame is of. The save does not, so
it does not: a worker thread does the PNG encoding and the writing, and the pruning behind it.
An input now costs the bot two grabs rather than two grabs and two encodes.

Self-check (writes to a temp dir, not your real frames):  python -m frames
"""
import queue
import threading
import time
from collections import deque
from pathlib import Path

import pyautogui
from PIL import Image

import screen
from gui.settings import APP_DIR
from narrate import log

FRAME_DIR = APP_DIR / 'frames'  # sister of logs/, same reason: it belongs to the app, not the repo
KEEP = 250  # frames on disk, oldest deleted as new ones arrive
SUFFIX = '.png'  # lossless. ponytail: '.bmp' for literally uncompressed, at ~6MB a frame
COMPRESS = 1  # PNG level: 0-9, all lossless. 1 is the fastest that still packs anything
# The pyautogui calls that change what is on screen. moveTo is deliberately absent: the cursor
# moving is not a change worth two frames, and the failsafe corner dance would flood the folder.
WATCHED = ('click', 'doubleClick', 'rightClick', 'middleClick', 'dragTo', 'drag',
           'press', 'hotkey', 'typewrite', 'write', 'scroll')

_dir = None  # None until start(), and capture() is a no-op until then
_keep = KEEP  # the live cap, so every capture prunes to the number start() was given
_kept = deque()  # frame paths, oldest first, so pruning is a popleft rather than a glob
# True while a wrapped call is in flight. Several of the watched functions are written in terms
# of the others: pyautogui.typewrite presses each character through the module's own press(),
# which is patched too, so typing 18900 left a pair of frames per digit inside the pair around
# the typewrite. Only the outermost call takes frames now.
# ponytail: one flag, not threading.local, because only ever one bot thread clicks at a time.
_busy = False
# Work for the saver thread, in the order it was asked for: (path, image) writes that image,
# (path, None) deletes that file. Both go through the one queue so a frame is always written
# before the prune that drops it, whatever the timing.
# The cap is small and put() blocks: a screenshot is megabytes, and a saver that has fallen
# eight frames behind should slow the bot down rather than fill memory up. Falling behind at
# all takes a burst of inputs with no sleeps between them.
_saves = queue.Queue(maxsize=8)
_saver = None  # the thread, started by the first start() and left running


def _save_loop():
    """Write and delete whatever capture() and _prune() ask for, off the bot thread."""
    while True:
        path, image = _saves.get()
        try:
            if image is None:
                path.unlink()
            else:
                image.save(path, compress_level=COMPRESS)
        except OSError:
            pass  # a full disk, or a frame open in a viewer; the next one is not this one's problem
        finally:
            _saves.task_done()


def flush():
    """Block until every queued frame is on disk. For anything that reads the folder."""
    _saves.join()


def start(directory=FRAME_DIR, keep=KEEP):
    """Begin capturing into `directory`, and adopt whatever is already in it. Returns the path.

    Existing frames are counted rather than cleared: the cap is KEEP frames in total, not KEEP
    per boot, and the run worth looking at is often the one before the restart.
    """
    global _dir, _keep, _saver
    _dir = Path(directory)
    _keep = keep
    _dir.mkdir(parents=True, exist_ok=True)
    if _saver is None:
        _saver = threading.Thread(target=_save_loop, name='frames', daemon=True)
        _saver.start()
    _kept.clear()
    _kept.extend(sorted(_dir.glob(f'*{SUFFIX}')))  # millisecond stamps sort chronologically
    dropped = _prune()
    watch()
    log(f'frame capture into {_dir}, {len(_kept)} already there'
        + (f', dropped {dropped} over the {keep} cap' if dropped else ''))
    return _dir


def stop():
    """Stop capturing. The wrappers stay on pyautogui; with no directory they just pass through."""
    global _dir
    _dir = None
    flush()  # whatever the last pass took is worth having on disk before anyone looks


def clear():
    """Delete every frame on disk now, for a clean start (a new mode's run wants only its own).

    Queued through the saver like every other delete, so it cannot race a write already in flight,
    and _kept is reset so the cap counts from zero. A no-op before start(), when there is no
    directory yet. Returns how many were dropped.
    """
    if _dir is None:
        return 0
    dropped = 0
    for path in sorted(_dir.glob(f'*{SUFFIX}')):
        _saves.put((path, None))
        dropped += 1
    _kept.clear()
    return dropped


def _prune():
    """Queue the oldest frames for deletion until at most `_keep` are left. Returns how many."""
    dropped = 0
    while len(_kept) > _keep:
        _saves.put((_kept.popleft(), None))
        dropped += 1
    return dropped


def capture(label='', image=None):
    """Save one frame named for now, as `<unix milliseconds>-<label>.png`. Its path, or None.

    None when capture has not been started, which is what makes every call site safe to leave
    in: the tests and the geometry self-checks import sell.py without ever calling start().

    image: a PIL image to save instead of grabbing the screen. Only the self-check passes one.
    """
    if _dir is None:
        return None
    stamp = int(time.time() * 1000)
    # No collision guard: a grab takes tens of milliseconds, so two frames cannot share a
    # stamp *and* a label unless the clock jumps, and a lost frame is not worth a stat call.
    path = _dir / (f'{stamp}-{label}{SUFFIX}' if label else f'{stamp}{SUFFIX}')
    # The working monitor, not the primary and not the whole desk: the point of a frame is what
    # the game was showing, and screen.py is the only thing that knows which screen that is.
    # The grab is the bot thread's; the encode and the write belong to the saver.
    _saves.put((path, image if image is not None else screen.grab()))
    _kept.append(path)
    _prune()
    return path


def _wrap(func, name):
    """`func`, with a frame either side of it. Nested watched calls pass straight through."""
    def framed(*args, **kwargs):
        global _busy
        if _dir is None or _busy:
            return func(*args, **kwargs)
        _busy = True
        before = capture('pre')
        try:
            return func(*args, **kwargs)
        finally:
            _busy = False
            after = capture('post')
            # The names go in the log so a line of narration points straight at the two
            # pictures taken around it, which is the whole point of stamping them.
            log(f'frames {before.name} / {after.name} around '
                f'{name}{args if args else ""}', 2)
    framed._framed = True
    return framed


def watch(module=pyautogui, names=WATCHED):
    """Wrap `module`'s input functions so each one leaves a before and an after frame.

    Idempotent: a second call finds the wrappers already in place and leaves them, or the
    frames would come in pairs of pairs.
    """
    for name in names:
        func = getattr(module, name, None)
        if func is not None and not getattr(func, '_framed', False):
            setattr(module, name, _wrap(func, name))


if __name__ == '__main__':
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        start(directory, keep=5)

        blank = Image.new('RGB', (4, 4), (10, 20, 30))
        first = capture('pre', blank)
        assert first.parent == directory and first.suffix == SUFFIX
        assert first.stem.endswith('-pre') and first.stem[:-4].isdigit(), first.name
        assert abs(int(first.stem[:-4]) / 1000 - time.time()) < 5, 'stamped in unix milliseconds'
        # Every look at the folder from here down flushes first: capture() returns as soon as
        # the frame is queued, so without this the checks race the saver thread.
        flush()
        assert Image.open(first).size == (4, 4), 'saved at the size it was given, unscaled'

        for n in range(9):
            capture(f'post{n}', blank)
        flush()
        left = sorted(p.name for p in directory.glob(f'*{SUFFIX}'))
        assert len(left) == 5, f'the cap holds, {len(left)} frames left'
        assert not first.exists(), 'and it is the oldest that goes'
        assert left[-1].endswith(f'post8{SUFFIX}'), f'newest survives, {left[-1]}'

        # start() adopts what is on disk rather than starting the count from zero.
        start(directory, keep=5)
        assert len(_kept) == 5, f'adopted {len(_kept)} of the 5 already there'
        start(directory, keep=3)
        flush()
        assert len(list(directory.glob(f'*{SUFFIX}'))) == 3, 'a lower cap trims on start'

        # The wrapper takes its two frames around whatever it is given, and only once.
        screen.grab = lambda *a, **k: blank  # no real screen needed to check the wiring
        calls = []

        class _Fake:
            def click(self, *args):
                calls.append(args)

        fake = _Fake()
        start(directory, keep=KEEP)  # room for the pair, rather than pruning it as it lands
        watch(fake, ('click',))
        watch(fake, ('click',))  # a second watch must not double wrap
        flush()
        before = len(list(directory.glob(f'*{SUFFIX}')))
        fake.click(7, 9)
        flush()
        pair = [p.name for p in list(_kept)[-2:]]  # capture order, which sorting by name is not
        assert calls == [(7, 9)], f'the real click still ran with its arguments, {calls}'
        assert len(list(directory.glob(f'*{SUFFIX}'))) == before + 2, 'one click, two frames'
        assert pair[0].endswith(f'-pre{SUFFIX}') and pair[1].endswith(f'-post{SUFFIX}'), pair

        # A watched function written in terms of another watched one, which is what
        # pyautogui.typewrite is: one pair of frames for the whole call, not one per keystroke.
        class _Nested:
            def press(self, key):
                calls.append(key)

            def typewrite(self, text):
                for character in text:
                    nested.press(character)  # the module's own press, wrapper and all

        nested = _Nested()
        watch(nested, ('press', 'typewrite'))
        calls.clear()
        # Counted off _kept rather than off the directory: a real grab takes tens of
        # milliseconds, but the fake one above is instant, so back to back frames land on the
        # same millisecond stamp and overwrite each other. _kept gets an entry per capture.
        before = len(_kept)
        nested.typewrite('18900')
        assert calls == list('18900'), f'every keystroke still went through, {calls}'
        assert len(_kept) - before == 2, \
            f'one typewrite is two frames, not two per character, got {len(_kept) - before}'
        # And the guard is released afterwards, so the next call up top still takes its pair.
        before = len(_kept)
        nested.press('f5')
        assert len(_kept) - before == 2, 'the guard lifted again'

        # clear() empties the folder for a fresh mode, and leaves the cap counting from zero.
        capture('keep-me', blank)
        flush()
        assert list(directory.glob(f'*{SUFFIX}')), 'a frame to clear'
        clear()
        flush()
        assert not list(directory.glob(f'*{SUFFIX}')), 'clear() emptied the folder'
        assert len(_kept) == 0, 'and reset the cap bookkeeping'

        stop()
        count = len(list(directory.glob(f'*{SUFFIX}')))
        assert capture('after-stop', blank) is None, 'stopped means no frame'
        fake.click(1, 1)
        assert len(list(directory.glob(f'*{SUFFIX}'))) == count, 'and the wrapper just passes through'
        assert calls[-1] == (1, 1), 'passing through still clicks'

    print(f'ok, real frames live in {FRAME_DIR}')
