"""The end-of-run totals line survives a pass that raises, for both bots.

Run:  python tests/test_totals_line.py

No game needed, nothing is clicked. start() is driven with its one pass function replaced by
something that raises, which is what a real fatal looks like: 'could not apply the flea filters'
is a RuntimeError out of sell_one, and start() deliberately does not catch it.

The line matters most on exactly those runs. It carries the counters, and a crashed session is
the one someone reads back. Before the finally it was skipped whenever a pass raised, so the log
just stopped, and the GUI's handler printed the reason with no numbers under it.

Both bots are checked because they are copies of each other: fixing one and not the other is the
likely way this comes back.
"""
import sys
import threading
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gym_bot  # noqa: E402
import narrate  # noqa: E402
import sell_bot  # noqa: E402


def bare(cls, labels, pass_name, boom):
    """`cls` with only what start() reads, no game and no constructor.

    __init__ wants a Tarkov window, which is the thing this test exists to not need.
    """
    bot = object.__new__(cls)
    bot._stop = threading.Event()
    bot.stats = {key: 0 for key, _ in labels}
    bot._recover = lambda: None  # reads the real screen on Start; test_recover_on_start covers it
    # gym_bot.start() clears its per rep state on the way in. Unused here, since the pass
    # function is replaced, but start() must not trip over its absence before reaching it.
    bot._last, bot._due, bot._idle = deque(), None, False
    setattr(bot, pass_name, boom)
    return bot


def check(cls, labels, pass_name, expected):
    """Run start() with a pass that raises, and hand back what got logged last."""
    def boom():
        raise RuntimeError('the screen is not where I thought it was')

    bot = bare(cls, labels, pass_name, boom)
    try:
        bot.start()
    except RuntimeError as e:
        assert 'not where I thought' in str(e), 'the fatal still reaches the GUI, unswallowed'
    else:
        raise AssertionError(f'{cls.__name__}.start() swallowed the error; the run would look ok')
    assert expected in narrate.LAST, f'{cls.__name__} logged {narrate.LAST!r}, wanted {expected!r}'
    print(f'  ok  {cls.__name__:10} {narrate.LAST.strip()}')


if __name__ == '__main__':
    print('a pass raises, and the totals line still lands:')
    check(sell_bot.Tarkbot, sell_bot.STAT_LABELS, 'sell_one', 'finished after 1 passes')
    # The gym counts seconds rather than passes, so its totals line is matched on the counter
    # it carries instead of on a count of anything.
    check(gym_bot.HideoutGym, gym_bot.STAT_LABELS, 'do_one_rep', 'Reps clicked 0')

    # And the clean path still works, or the finally could be hiding a broken normal exit.
    # The pass stops the bot from inside itself: start() clears the flag on the way in, so
    # setting it beforehand does nothing and the loop runs until the disk fills up.
    bot = bare(sell_bot.Tarkbot, sell_bot.STAT_LABELS, 'sell_one', lambda: None)
    bot.sell_one = bot._stop.set  # one pass, then the while condition ends it
    bot.start()
    assert 'finished after 1 passes' in narrate.LAST, narrate.LAST
    print(f'  ok  {"clean stop":10} {narrate.LAST.strip()}')

    print('ok, the totals survive a crash and a clean stop alike')
