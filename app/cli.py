"""Headless entry point: run any mode from the command line instead of the GUI.

    python -m cli --mode craft
    python -m cli --mode craft --no-wires-enabled --crackers-max 20000

The same seam the GUI uses (each mode module's build(prefs, stats) -> runner with
start/stop), driven by settings.json plus per-run overrides. See docs/cli.md.

Self-check, no game needed:  python -m cli --mode craft --dry-run
"""
import argparse
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # top-level module; imports need app/ on the path

import craft_bot
import frames
import gym_bot
import screen  # noqa: F401  (imported for parity; build() calls screen.use itself)
import sell_bot
import session_log
import snipe_bot
import window
from gui import settings

# Friendly CLI mode name -> (settings tab key, mode module). The tab key is what the GUI stores
# in last_run_mode, so the frame-wipe rule below lines up with a GUI run of the same mode.
MODES = {'flea-sell': ('flea', sell_bot), 'flea-snipe': ('snipe', snipe_bot),
         'gym': ('gym', gym_bot), 'craft': ('crafts', craft_bot)}

# Bookkeeping keys the CLI sets itself; not offered as user overrides.
INTERNAL_KEYS = {'tab', 'last_run_mode'}

# Settings keys whose flag needs a different name. 'mode' is the flea-sell SOURCE dropdown, and
# --mode is already the run selector; expose it as --source (its GUI label), dest stays 'mode'.
FLAG_ALIASES = {'mode': 'source'}


def _parser():
    p = argparse.ArgumentParser(
        prog='tarkbot', description=__doc__.split('\n')[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    # dest is run_mode, not mode: 'mode' is a settings key (flea-sell source) with its own flag.
    p.add_argument('--mode', dest='run_mode', required=True, choices=sorted(MODES),
                   help='which bot to run')
    p.add_argument('--dry-run', action='store_true',
                   help='print the resolved settings and exit without touching the game')

    # One flag per settings key, generated from DEFAULTS so a new preference needs no change here.
    g = p.add_argument_group('config overrides', 'any settings.json key, applied for this run only')
    for key, default in settings.DEFAULTS.items():
        if key in INTERNAL_KEYS:
            continue
        dashed = FLAG_ALIASES.get(key, key).replace('_', '-')
        if isinstance(default, bool):
            g.add_argument(f'--{dashed}', dest=key, action='store_true', default=None,
                           help=f'enable (default {default})')
            g.add_argument(f'--no-{dashed}', dest=key, action='store_false',
                           help=argparse.SUPPRESS)
        else:
            # A literal % in a default (e.g. '2k rubles | 90%') would be read as a format spec
            # by argparse's help rendering, so double it.
            hint = repr(default).replace('%', '%%')
            g.add_argument(f'--{dashed}', dest=key, default=None, metavar='VALUE',
                           help=f'(default {hint})')
    return p


def resolve_prefs(args):
    """settings.json (created with defaults if absent) overlaid with any flags passed."""
    if not settings.SETTINGS_PATH.exists():
        settings.save(settings.DEFAULTS)  # "initialize with defaults if not changed yet"
    prefs = settings.load()  # never raises
    for key in settings.DEFAULTS:
        val = getattr(args, key, None)
        if val is not None:  # None means the flag was not passed
            prefs[key] = val
    return prefs


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    tab, module = MODES[args.run_mode]
    prefs = resolve_prefs(args)

    if args.dry_run:
        print(f'mode {args.run_mode} -> tab {tab}, module {module.__name__}')
        for key in settings.DEFAULTS:
            print(f'  {key} = {prefs[key]!r}')
        return 0

    # ponytail: no update.boot_gate() here. The GUI gates on a pending MSI and relaunches itself;
    # a CLI run started from a shell should run the bot now, not swap itself for an installer.
    session_log.start()  # redirect stdout to the session log before any bot narration
    frames.start()
    if prefs.get('last_run_mode') != tab:  # same wipe rule as gui/app.App.start
        frames.clear()
        settings.save({**settings.load(), 'last_run_mode': tab})  # persist only the mode marker

    try:
        bot = module.build(prefs, None)  # None -> the runner keeps its own stats dict
    except window.WindowError:
        parser.error('Tarkov window not found - start the game first')
    except ValueError as e:  # craft build() raises when no craft is enabled
        parser.error(str(e))

    signal.signal(signal.SIGINT, lambda *_: bot.stop())  # Ctrl+C -> clean unwind
    bot.start()  # blocks until stop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
