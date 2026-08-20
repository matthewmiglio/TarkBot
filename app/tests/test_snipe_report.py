"""Does a purchase reach the website, and does the opt-out really stop it.

Run:  python tests/test_snipe_report.py        (against a local site)
      TARKBOT_SNIPE_URL=https://www.tarkbot.org/api/snipe python tests/test_snipe_report.py

Needs the site running and the service key, which it reads out of website/.env.local the same
way tests/test_error_report.py does. There is only one Supabase project, so this writes a real
row and deletes it again on the way out; TEST_MACHINE exists to be recognisable and cleanable.

Two things are worth proving here and neither is provable from the endpoint's side. First that
the app sends what the endpoint validates, since every field there has its own rejection and a
mismatch would be silent: the send is fire and forget and a 400 never reaches the bot. Second
that the preference gate actually gates, because a telemetry switch that does nothing is worse
than no switch at all.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crash_report  # noqa: E402
import snipe_bot  # noqa: E402
import snipe_report  # noqa: E402

ENDPOINT = os.environ.get('TARKBOT_SNIPE_URL', 'http://localhost:3000/api/snipe')
TABLE = 'Tarkbot_snipes'
# The 9001 slot, so it cannot collide with the endpoint test's 9000 block or the crash test's
# 8000 one. Fixed, so a run that dies half way leaves a row the next run knows how to sweep.
TEST_MACHINE = '00000000-0000-4000-9000-000000000101'


def env():
    """SUPABASE_URL and SUPABASE_SERVICE_KEY out of website/.env.local."""
    path = Path(__file__).resolve().parents[2] / 'website' / '.env.local'
    if not path.exists():
        sys.exit(f'no {path}, so there is no key to read the row back with')
    values = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.strip().startswith('#'):
            key, _, value = line.partition('=')
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values['SUPABASE_URL'], values['SUPABASE_SERVICE_KEY']


SUPABASE_URL, SERVICE_KEY = env()
HEADERS = {'apikey': SERVICE_KEY, 'Authorization': f'Bearer {SERVICE_KEY}'}


def rows():
    """Every row this test has written, newest first."""
    url = (f'{SUPABASE_URL}/rest/v1/{TABLE}?select=*&machine_id=eq.{TEST_MACHINE}'
           f'&order=ts.desc')
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def sweep():
    """Delete them again."""
    url = f'{SUPABASE_URL}/rest/v1/{TABLE}?machine_id=eq.{TEST_MACHINE}'
    request = urllib.request.Request(url, headers=HEADERS, method='DELETE')
    with urllib.request.urlopen(request, timeout=20):
        pass


if __name__ == '__main__':
    crash_report.machine_id = lambda: TEST_MACHINE  # not this machine's real id, a reserved one
    sweep()

    print(f'posting one buy to {ENDPOINT}')
    snipe_report.report_buy('Salewa first aid kit', 41_000, 52_000, endpoint=ENDPOINT)

    stored = rows()
    if len(stored) != 1:
        sweep()
        sys.exit(f'expected one row, found {len(stored)}')
    row = stored[0]
    print(f'stored {row["item"]!r} at {row["price"]:,} against {row["trader_value"]:,}, '
          f'margin {row["margin"]:,}')
    for field, want in (('item', 'Salewa first aid kit'), ('price', 41_000),
                        ('trader_value', 52_000), ('margin', 11_000)):
        if row[field] != want:
            sweep()
            sys.exit(f'{field} came back as {row[field]!r}, wanted {want!r}')
    if not row['version']:
        sweep()
        sys.exit('no version on the row, so a behaviour change cannot be told apart later')

    # The gate, driven through the thing that actually sets it. build() is the only caller
    # that turns reporting on, and FleaSniper is stubbed out here so it never goes looking for a
    # game window: what is being checked is the mapping from the preference to the argument.
    built = {}

    class Stub:
        def __init__(self, **kwargs):
            built.update(kwargs)

    real_sniper = snipe_bot.FleaSniper
    snipe_bot.FleaSniper = Stub
    try:
        snipe_bot.build({'send_error_reports': False}, None)
        if built.get('report'):
            sweep()
            sys.exit('opting out of reports still built a sniper that reports')
        snipe_bot.build({'send_error_reports': True}, None)
        if not built.get('report'):
            sweep()
            sys.exit('opting in did not switch reporting on')
        snipe_bot.build({}, None)  # an older settings.json with no such key
        if built.get('report'):
            sweep()
            sys.exit('a settings file with no preference in it must not report')
    finally:
        snipe_bot.FleaSniper = real_sniper

    sweep()
    if rows():
        sys.exit('the sweep left rows behind')
    print('ok: the buy landed with the right numbers, and the opt-out sends nothing')
