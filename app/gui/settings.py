"""GUI preferences, kept in %APPDATA%/tarkbot/settings.json.

Self-check (writes to a temp dir, not your real settings):  python -m gui.settings
"""
import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get('APPDATA') or Path.home()) / 'tarkbot'
SETTINGS_PATH = APP_DIR / 'settings.json'
DEFAULTS = {'background': 'camp.png', 'mode': 'inventory', 'stale': '10m',
            'tab': 'flea',  # which mode tab the GUI opens on
            # Which screen to watch and click on, as the device name Windows gives it
            # (\\.\DISPLAY1). 'auto' until the user picks, which resolves to the monitor Tarkov
            # is on, or the primary. See screen.py.
            'monitor': 'auto',
            # The one telemetry switch, over both things the app sends. A crash goes to
            # tarkbot.org with two screenshots, so it can be diagnosed and cropped into the
            # reference image that would have matched (crash_report.py). Snipe mode reports
            # each item it buys, with the price and what a trader pays for it
            # (snipe_report.py). Was send_error_reports, which stopped being true the moment
            # the second one was added; see RENAMED for what happens to a file still using it.
            'send_telemetry': True,
            'undercut': '2k rubles | 90%',  # how far under the suggested price, see sell_bot.UNDERCUTS
            # Whether to leave the offer window's autoselect similar checkbox ticked, which
            # lists every matching item as one offer. See sell_bot.AUTOSELECT.
            'autoselect': 'OFF',
            # How many roubles under trader value a flea offer has to be before snipe mode
            # buys it. See snipe_bot.MARGINS.
            'margin': '500 rubles',
            # Which trader's items snipe mode watches for, so everything bought sells to one
            # trader. 'All traders' watches the whole list. See snipe_bot.trader_choices.
            'trader': 'Therapist',
            # The key that starts and stops the bot from inside the game. A name from
            # gui.app.HOTKEYS; anything else falls back to the default at startup.
            'hotkey': 'F4'}


# Keys that changed name, as {old: new}. A settings.json written by an older build still has
# the old one, and load() only keeps keys that are in DEFAULTS, so without this a rename reads
# as "never set" and the default wins. That is fine for a background or a monitor and very much
# not fine for a telemetry switch: it would opt a user who had turned it off straight back in.
RENAMED = {'send_error_reports': 'send_telemetry'}


def load(path=SETTINGS_PATH):
    """Saved preferences, with defaults filling any gap.

    Never raises. A missing, unreadable or corrupt file is one we ignore: the GUI has to open
    either way, and a bad settings file is not worth refusing to start over.
    """
    try:
        saved = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    for was, now in RENAMED.items():
        if was in saved and now not in saved:
            saved[now] = saved[was]
    return {**DEFAULTS, **{key: saved[key] for key in DEFAULTS if key in saved}}


def save(settings, path=SETTINGS_PATH):
    """Write the known keys back. Returns True if it landed, False if the disk said no.

    Unknown keys are dropped rather than kept, so an old settings file cannot smuggle a stale
    option back into a newer build.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: settings.get(key, DEFAULTS[key]) for key in DEFAULTS}
        path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        return True
    except OSError:
        return False


if __name__ == '__main__':
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / 'nested' / 'settings.json'
        assert load(probe) == DEFAULTS, 'a missing file is all defaults'

        # Written against DEFAULTS rather than a literal dict, so adding a preference does not
        # break the check that has nothing to do with it.
        saved = {'background': 'factory.png', 'mode': 'scav', 'stale': '5m'}
        assert save({**saved, 'junk': 1}, probe)
        assert load(probe) == {**DEFAULTS, **saved}, 'junk key survived'

        probe.write_text('{not json', encoding='utf-8')
        assert load(probe) == DEFAULTS, 'a corrupt file must not stop the GUI opening'

        probe.write_text('["a list"]', encoding='utf-8')
        assert load(probe) == DEFAULTS, 'json that is not an object must not stop it either'

        probe.write_text('{"mode": "scav"}', encoding='utf-8')
        assert load(probe) == {**DEFAULTS, 'mode': 'scav'}, 'half a file fills in'

        # The rename, which is the one migration that can quietly undo a user's decision. An
        # opt-out written by an older build has to survive being read by a newer one.
        probe.write_text('{"send_error_reports": false}', encoding='utf-8')
        assert load(probe)['send_telemetry'] is False, 'an old opt-out was lost in the rename'
        probe.write_text('{"send_error_reports": true}', encoding='utf-8')
        assert load(probe)['send_telemetry'] is True, 'an old opt-in should carry over too'
        # Both present: the new name wins, since that is the one the GUI has been writing.
        probe.write_text('{"send_error_reports": true, "send_telemetry": false}', encoding='utf-8')
        assert load(probe)['send_telemetry'] is False, 'the new key must win over the old one'
        # And the old name is not written back out, or the file never stops carrying it.
        assert save(load(probe), probe)
        assert 'send_error_reports' not in probe.read_text(encoding='utf-8')
    print(f'ok, real settings live at {SETTINGS_PATH}')
