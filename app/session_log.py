"""One log file per session, kept beside settings.json, ten sessions deep.

A session is one app boot to one app close, not one Start to one Stop. A run that dies is
usually explained by what the Start before it did, and rotating on the button would throw
exactly that away.

ponytail: no logging module, no RotatingFileHandler. Everything already narrates through
print() (see narrate.py) so a redirected stdout catches the lot for free, and the handler
rotates on file size, which is not the thing being counted here.

Self-check (writes to a temp dir, not your real logs):  python -m session_log
"""
import sys
import time
from pathlib import Path

from gui.settings import APP_DIR
import narrate
from narrate import log

LOG_DIR = APP_DIR / 'logs'
KEEP = 10  # session files to keep, newest first. The rest are deleted as each session opens.
STAMP = '%Y%m%d-%H%M%S'  # sorts chronologically as a string, so pruning needs no stat call


class _Tee:
    """Write to every stream at once, so running from source still narrates to the console."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def path_for(directory=LOG_DIR, now=None):
    """The file this session writes to, named for the second it started."""
    stamp = time.strftime(STAMP, time.localtime(time.time() if now is None else now))
    path = Path(directory) / f'tarkbot-{stamp}.log'
    count = 2
    while path.exists():  # ponytail: two boots inside one second, rare enough to just count up
        path = Path(directory) / f'tarkbot-{stamp}-{count}.log'
        count += 1
    return path


def prune(directory=LOG_DIR, keep=KEEP, active=None):
    """Delete all but the `keep` newest session logs. Returns the paths it removed.

    `active` is never deleted whatever the clock says. Names sort by their stamp, so a machine
    whose clock went backwards (DST, an NTP correction) writes a session file that sorts as one
    of the oldest, and without this the session would prune the log it is holding open.
    """
    files = sorted(Path(directory).glob('tarkbot-*.log'))
    removed = []
    for path in files[:-keep] if keep else files:
        if path == active:
            continue
        try:
            path.unlink()
            removed.append(path)
        except OSError:
            pass  # held open by a second copy of the app; the next session will get it
    return removed


def start(directory=LOG_DIR, keep=KEEP):
    """Point stdout and stderr at a fresh session log. Returns its path.

    Pruned after the new file exists, not before, so `keep` counts this session too. Frozen
    windowed there is no console and sys.stdout is None, so the file is the only sink; from
    source it tees, because watching the run in the terminal is what the console is for.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = path_for(directory)
    stream = open(path, 'a', encoding='utf-8', buffering=1)  # line buffered, readable mid-run
    sys.stdout = stream if sys.stdout is None else _Tee(sys.stdout, stream)
    sys.stderr = stream if sys.stderr is None else _Tee(sys.stderr, stream)
    narrate.QUIET_SINK = stream  # so log(quiet=True) reaches the file but skips the terminal
    dropped = prune(directory, keep, active=path)
    log(f'session log {path}' + (f', dropped {len(dropped)} older' if dropped else ''))
    return path


if __name__ == '__main__':
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        # Named for descending seconds so the newest sorts last, same as real boots do.
        for minute in range(15):
            (directory / f'tarkbot-20260806-1200{minute:02d}.log').write_text(str(minute))
        assert len(prune(directory, 10)) == 5, 'five oldest go'
        left = sorted(p.name for p in directory.glob('*.log'))
        assert len(left) == 10, 'ten survive'
        assert left[0] == 'tarkbot-20260806-120005.log', 'and they are the newest ten'

        assert prune(directory, 10) == [], 'pruning an already trimmed folder is a no-op'
        assert prune(Path(tmp) / 'nope', 10) == [], 'a missing folder is not an error'

        # A backwards clock writes a session file that sorts as one of the oldest.
        stale = directory / 'tarkbot-20260806-115900.log'
        stale.write_text('this session')
        assert stale not in prune(directory, 5, active=stale), 'never prune the live log'
        assert stale.exists() and len(list(directory.glob('*.log'))) == 6, 'the rest still went'

        fresh = path_for(directory, now=0)
        assert not fresh.exists() and fresh.parent == directory
        fresh.write_text('taken')
        assert path_for(directory, now=0).name.endswith('-2.log'), 'same second does not clobber'

    class _Sink:
        def __init__(self):
            self.text = ''

        def write(self, text):
            self.text += text

        def flush(self):
            pass

    one, two = _Sink(), _Sink()
    _Tee(one, two).write('both')
    assert one.text == two.text == 'both', 'a tee writes to every stream'
    print(f'ok, real logs live in {LOG_DIR}')
