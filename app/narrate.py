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


def log(message, indent=0):
    """Print `message` behind an HH:MM:SS.mmm stamp.

    indent nests a detail under the step above it: 0 for a step in the pass, 1 for what a
    screen read or a click did, 2 for one attempt inside a retry loop.
    """
    now = time.time()
    stamp = time.strftime('%H:%M:%S', time.localtime(now)) + f'.{int(now % 1 * 1000):03d}'
    # flush: the frozen build writes to a line-buffered file, but a redirected stdout in a
    # test harness is block buffered, and a log that arrives after the crash is no log.
    print(f'[{stamp}] {"  " * indent}{message}', flush=True)


if __name__ == '__main__':
    log('step')
    log('detail under it', 1)
    log('attempt under that', 2)
