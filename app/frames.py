"""A screenshot either side of every input the bot sends, kept beside the session logs.

Not a recording. Frames are grabbed on change: immediately before an input goes to the game
and immediately again once it has landed, so a pass reads back as before/after pairs rather
than as thousands of near identical stills. Nothing else takes a frame.

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

ponytail: the grab and the save both happen on the bot thread, roughly 0.1s per frame, so an
input costs about 0.2s more than it did. That is invisible next to the delays sell.py already
sleeps, except in the 50 click select loop. Hand the save to a worker thread if that ever
starts mattering.

Self-check (writes to a temp dir, not your real frames):  python -m frames
"""
import time
from collections import deque
from pathlib import Path

import pyautogui
from PIL import Image

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


def start(directory=FRAME_DIR, keep=KEEP):
    """Begin capturing into `directory`, and adopt whatever is already in it. Returns the path.

    Existing frames are counted rather than cleared: the cap is KEEP frames in total, not KEEP
    per boot, and the run worth looking at is often the one before the restart.
    """
    global _dir, _keep
    _dir = Path(directory)
    _keep = keep
    _dir.mkdir(parents=True, exist_ok=True)
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


def _prune():
    """Delete oldest frames until at most `_keep` are left. Returns how many went."""
    dropped = 0
    while len(_kept) > _keep:
        path = _kept.popleft()
        try:
            path.unlink()
            dropped += 1
        except OSError:
            pass  # open in a viewer, or already gone; the next capture tries the next one
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
    (image if image is not None else pyautogui.screenshot()).save(path, compress_level=COMPRESS)
    _kept.append(path)
    _prune()
    return path


def _wrap(func, name):
    """`func`, with a frame either side of it."""
    def framed(*args, **kwargs):
        if _dir is None:
            return func(*args, **kwargs)
        before = capture('pre')
        try:
            return func(*args, **kwargs)
        finally:
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
        assert Image.open(first).size == (4, 4), 'saved at the size it was given, unscaled'

        for n in range(9):
            capture(f'post{n}', blank)
        left = sorted(p.name for p in directory.glob(f'*{SUFFIX}'))
        assert len(left) == 5, f'the cap holds, {len(left)} frames left'
        assert not first.exists(), 'and it is the oldest that goes'
        assert left[-1].endswith(f'post8{SUFFIX}'), f'newest survives, {left[-1]}'

        # start() adopts what is on disk rather than starting the count from zero.
        start(directory, keep=5)
        assert len(_kept) == 5, f'adopted {len(_kept)} of the 5 already there'
        start(directory, keep=3)
        assert len(list(directory.glob(f'*{SUFFIX}'))) == 3, 'a lower cap trims on start'

        # The wrapper takes its two frames around whatever it is given, and only once.
        pyautogui.screenshot = lambda *a, **k: blank  # no real screen needed to check the wiring
        calls = []

        class _Fake:
            def click(self, *args):
                calls.append(args)

        fake = _Fake()
        start(directory, keep=KEEP)  # room for the pair, rather than pruning it as it lands
        watch(fake, ('click',))
        watch(fake, ('click',))  # a second watch must not double wrap
        before = len(list(directory.glob(f'*{SUFFIX}')))
        fake.click(7, 9)
        pair = [p.name for p in list(_kept)[-2:]]  # capture order, which sorting by name is not
        assert calls == [(7, 9)], f'the real click still ran with its arguments, {calls}'
        assert len(list(directory.glob(f'*{SUFFIX}'))) == before + 2, 'one click, two frames'
        assert pair[0].endswith(f'-pre{SUFFIX}') and pair[1].endswith(f'-post{SUFFIX}'), pair

        stop()
        count = len(list(directory.glob(f'*{SUFFIX}')))
        assert capture('after-stop', blank) is None, 'stopped means no frame'
        fake.click(1, 1)
        assert len(list(directory.glob(f'*{SUFFIX}'))) == count, 'and the wrapper just passes through'
        assert calls[-1] == (1, 1), 'passing through still clicks'

    print(f'ok, real frames live in {FRAME_DIR}')
