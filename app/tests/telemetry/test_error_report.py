"""Crash reporting, end to end: the machine id, a real upload, the size cap, and the GUI's path.

App layer: crash_report.py (crash_report.machine_id, crash_report.report, _screen_png) all the
way to the website's /api/error route and Supabase, plus gui/app.py's App._run, which must set
the lamp and fire the report on a crash and honour the send_telemetry opt-out.

WANTS THE WEBSITE running and a real screen: it posts to a live site and writes real Supabase
rows, so it is not a no-game stub but it needs no Tarkov client.
    npx next dev                 (in website/)
    python tests/telemetry/test_error_report.py
Point it at the deploy instead with TARKBOT_ERROR_URL=https://tarkbot.org/api/error.

Everything it writes is filed under TEST_MACHINE and deleted on the way out, so a run leaves the
table as it found it. Needs a screen, since half the point is grabbing one.
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import crash_report  # noqa: E402
import screen  # noqa: E402

ENDPOINT = os.environ.get('TARKBOT_ERROR_URL', 'http://localhost:3000/api/error')
FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / '2560x1440' / 'flea-filters-open.png'
TEST_MACHINE = '00000000-0000-4000-9000-000000000001'  # rows under this id are ours to delete
TABLE = 'Tarkbot_errors'
BUCKET = 'Tarkbot_screenshots'


def supabase():
    """(url, service key) out of website/.env.local, which is where this machine keeps them."""
    env = {}
    path = Path(__file__).resolve().parents[3] / 'website' / '.env.local'
    for line in path.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            key, _, value = line.partition('=')
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env['SUPABASE_URL'], env['SUPABASE_SERVICE_KEY']


URL, KEY = supabase()
KEYED = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}


def call(method, path, data=None, headers=None, base=None):
    """(status, bytes) for one request. HTTP errors come back rather than raising."""
    request = urllib.request.Request((base or URL) + path, data=data, method=method,
                                     headers={**KEYED, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def rows():
    _, body = call('GET', f'/rest/v1/{TABLE}?select=*&machine_id=eq.{TEST_MACHINE}')
    return json.loads(body)


def sweep():
    """Delete every row and object this test has made. Also clears its rate limit budget."""
    ids = [i for row in rows()
           for i in (row['before_screenshot_id'], row['after_screenshot_id']) if i]
    if ids:
        call('DELETE', f'/storage/v1/object/{BUCKET}',
             json.dumps({'prefixes': [f'{i}.png' for i in ids]}).encode(),
             {'Content-Type': 'application/json'})
    call('DELETE', f'/rest/v1/{TABLE}?machine_id=eq.{TEST_MACHINE}')


def boom(message='flea did not open'):
    """A genuinely raised exception, so it carries a real traceback and not a made up one."""
    try:
        raise RuntimeError(message)
    except RuntimeError as error:
        return error


if __name__ == '__main__':
    # --------------------------------------------------------------- the machine id
    # Derived, not stored, so the same machine has to answer the same thing every time or every
    # report looks like it came from a new person.
    assert crash_report.machine_id() == crash_report.machine_id(), 'the id is not stable'
    original = crash_report.machine_id()
    uuid.UUID(original)  # raises unless it really is a uuid, which the endpoint insists on

    # And it has to actually depend on all three inputs, or two machines collide.
    real_platform = crash_report.platform.platform
    real_user, real_size = crash_report.getpass.getuser, screen.size
    seen = {original}
    crash_report.platform.platform = lambda: 'Windows-11-10.0.99999-SP0'
    seen.add(crash_report.machine_id())
    crash_report.platform.platform = real_platform
    crash_report.getpass.getuser = lambda: 'someone-else'
    seen.add(crash_report.machine_id())
    crash_report.getpass.getuser = real_user
    crash_report.screen.size = lambda: (1920, 1080) if real_size() != (1920, 1080) else (2560, 1440)
    seen.add(crash_report.machine_id())
    crash_report.screen.size = real_size
    assert len(seen) == 4, f'os, user and resolution must each move the id, got {len(seen)} of 4'
    assert crash_report.machine_id() == original, 'the id changed after the stubs were put back'
    print(f'ok - machine id is stable and answers to all three inputs ({original})')

    # Everything below writes real rows, so from here on we are a known test machine.
    crash_report.machine_id = lambda: TEST_MACHINE
    sweep()

    # --------------------------------------------------------------- a real report
    # A real screenshot and a real traceback, and the bytes have to survive the round trip
    # exactly: a reference image cropped out of a report is only worth having if it is lossless.
    before = FIXTURE.read_bytes()
    after = crash_report._screen_png()
    assert crash_report.report(boom(), before=before, after=after, endpoint=ENDPOINT) is True
    landed = rows()
    assert len(landed) == 1, f'expected one row, found {len(landed)}'
    row = landed[0]
    assert row['error']['type'] == 'RuntimeError'
    assert 'flea did not open' in row['error']['message']
    assert 'test_error_report.py' in row['error']['traceback'], 'the real traceback was not sent'
    assert row['before_screenshot_id'] and row['after_screenshot_id']
    print(f'ok - report stored, {len(before):,}B before and {len(after):,}B after uploaded')

    for half, sent in (('before', before), ('after', after)):
        status, got = call('GET', f'/storage/v1/object/{BUCKET}/{row[half + "_screenshot_id"]}.png')
        assert status == 200, f'{half} screenshot is not in the bucket: {status}'
        assert got == sent, f'{half} screenshot came back {len(got):,}B, not the {len(sent):,}B sent'
    print('ok - both screenshots round trip byte for byte, so crops off them are lossless')

    # --------------------------------------------------------------- the size cap
    # Noise, because it will not compress: a 4000x4000 png of it lands far past the bucket's
    # 25MB limit, which is what has to turn it away. The limit is Supabase's, not ours, so it
    # applies however the upload url was come by.
    buffer = io.BytesIO()
    rng = np.random.default_rng(0)
    Image.fromarray(rng.integers(0, 256, (4000, 4000, 3), dtype=np.uint8)).save(buffer, format='PNG')
    huge = buffer.getvalue()
    assert len(huge) > 25 * 1024 * 1024, f'the oversized case is only {len(huge):,}B'

    _, body = call('POST', '', json.dumps({'machine_id': TEST_MACHINE, 'version': 'test',
                                           'error': {'type': 'SizeCheck'}}).encode(),
                   {'Content-Type': 'application/json'}, base=ENDPOINT)
    signed = json.loads(body)['before']
    try:
        # Storage hangs up mid stream rather than answering once it has seen enough bytes, so a
        # dropped connection here is a refusal, not a flaky network.
        outcome = f'HTTP {call("PUT", "", huge, {"Content-Type": "image/png"}, base=signed["upload_url"])[0]}'
    except urllib.error.URLError as dropped:
        outcome = f'connection dropped ({dropped.reason})'

    status, _ = call('GET', f'/storage/v1/object/{BUCKET}/{signed["id"]}.png')
    assert status >= 400, f'a {len(huge):,}B image reached the bucket, the cap is not holding'
    print(f'ok - {len(huge):,}B image refused, nothing stored: {outcome}')

    # --------------------------------------------------------------- the GUI's own path
    # Not a stand-in for App._run: the real method, called on a stand-in app. A crash there must
    # still set self.error and paint the lamp, with the report going out behind it.
    from gui import app as gui_app  # noqa: E402  tk is slow to import and only needed here

    class Boom:
        @staticmethod
        def start():
            raise RuntimeError('raised through _run')

    class Stub:
        """What _run touches, and nothing else: a bot to start and somewhere to put the error."""
        def __init__(self):
            self.prefs = {'send_telemetry': True}
            self.error = None
            self.bot = Boom()

    # Counted from wherever the tests above left it, not from zero: the size check posts a
    # report of its own to get an upload url, so this is not the first row in the table.
    baseline = len(rows())
    stub = Stub()
    gui_app.App._run(stub)
    assert isinstance(stub.error, RuntimeError), 'the crash never reached self.error'

    for _ in range(60):  # report_later is a daemon thread, so wait for it rather than guess
        if len(rows()) > baseline:
            break
        time.sleep(0.5)
    assert len(rows()) == baseline + 1, 'a crash through App._run never produced a report'
    print('ok - a crash through App._run sets the lamp and reports itself')

    # Opting out has to actually opt out. Safe to count now: the report above has landed, so
    # there is no thread still in flight to be mistaken for this one.
    settled = len(rows())
    stub.prefs = {'send_telemetry': False}
    gui_app.App._run(stub)
    time.sleep(3)
    assert len(rows()) == settled, 'a report was sent with send_telemetry off'
    print('ok - send_telemetry false sends nothing')

    sweep()
    assert rows() == [], 'cleanup left rows behind'
    print('\nall good')
