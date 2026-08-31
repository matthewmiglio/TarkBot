"""One timestamped line of narration, so a run can be read back off the log.

Every print in the selling path goes through log() instead of print(), because without a
clock on each line there is no way to tell a slow step from a stuck one, and "it opened the
case then failed" loses the four seconds that were the whole problem.

ponytail: print, not logging. Every entry point already captures stdout (main.py points it
at tarkbot.log, the GUI and the test scripts inherit a console), whereas logging silently
drops INFO until someone calls basicConfig in each of them. Swap to logging the day two
sinks need the same lines.

Named narrate rather than the obvious trace: `trace` is a stdlib module, and a file of that
name at the repo root shadows it for the whole process.
"""
import time

# The line log() printed most recently, for the GUI to show under its buttons. Written on the
# bot thread and read on the GUI thread, which needs no lock: rebinding a name is atomic, so a
# reader gets either the old line or the new one and never half of either.
# ponytail: one string, not a ring buffer or a queue. The session log already keeps the whole
# history, and the footer has room for exactly one line.
LAST = ''

# The log file on its own, for quiet=True lines that belong in the session log but would drown
# the terminal. session_log.start() sets it to the file stream; None means no file sink is up
# (tests, a bare shell), and a quiet line then falls back to the normal print so it is not lost.
QUIET_SINK = None


def log(message, indent=0, quiet=False):
    """Print `message` behind an HH:MM:SS.mmm stamp, and keep it as LAST.

    indent nests a detail under the step above it: 0 for a step in the pass, 1 for what a
    screen read or a click did, 2 for one attempt inside a retry loop.

    quiet=True writes to the session log only, never the terminal: the verbose detection
    narration is too noisy to watch live but is exactly what the log exists to keep.
    """
    global LAST
    now = time.time()
    stamp = time.strftime('%H:%M:%S', time.localtime(now)) + f'.{int(now % 1 * 1000):03d}'
    LAST = f'[{stamp}] {"  " * indent}{message}'
    # flush: the frozen build writes to a line-buffered file, but a redirected stdout in a
    # test harness is block buffered, and a log that arrives after the crash is no log.
    print(LAST, file=QUIET_SINK if quiet and QUIET_SINK is not None else None, flush=True)


if __name__ == '__main__':
    log('step')
    log('detail under it', 1)
    log('attempt under that', 2)
    assert LAST.endswith('    attempt under that'), LAST  # indent 2, and the stamp in front
    assert LAST.startswith('['), LAST

    import io
    QUIET_SINK = sink = io.StringIO()
    log('to the file only', quiet=True)
    assert 'to the file only' in sink.getvalue(), 'quiet lines reach the sink'
