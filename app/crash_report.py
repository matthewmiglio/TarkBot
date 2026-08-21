"""Send a crash to the website, with a picture of the screen either side of it.

A run that dies on a wrong screen turns the GUI's lamp red and writes a traceback to the session
log, which is only any use on the machine it happened on. This posts the same traceback to
tarkbot.org along with two screenshots, so a failure on someone else's setup can be looked at
and, more usefully, cropped into the reference image that would have matched.

Nothing here holds a key. The endpoint is a route on our own site that talks to Supabase with a
server-side key, exactly like the download counter does, so the app is free to be open source.
The screenshots are not posted through it either: a lossless png of a 1440p screen is 4.5MB and
that route cannot accept one, so the endpoint answers with two single-use upload urls and the
bytes go straight to storage. Png rather than anything lossy on purpose, since the whole point
of keeping these is cutting reference crops out of them, and interact/ocr.py's digit templates
and sell.py's dead pixel colors (±5 a channel) do not survive a lossy round trip.

Nothing is written to disk here. The before picture is a frame frames.py had already saved, and
the after picture is grabbed straight into memory.
"""
import io
import json
import getpass
import os
import platform
import threading
import traceback
import urllib.request
import uuid

import frames
import screen
import version
from narrate import log

# The www host, not the bare one, which answers a 308 to it. urllib will not carry a POST across
# a redirect and raises instead, so the bare domain here means no report ever arrives.
ENDPOINT = os.environ.get('TARKBOT_ERROR_URL', 'https://www.tarkbot.org/api/error')
TIMEOUT = 20  # seconds; a slow site must not keep a dead run's thread alive for long
MESSAGE_LIMIT = 2000
TRACEBACK_LIMIT = 20000  # the endpoint refuses a body over 64KB, and a traceback is the bulk of it


def machine_id():
    """A stable anonymous id for this machine, as a uuid string.

    Derived rather than stored, so there is no file to keep, nothing to migrate, and a fresh
    install reports as the same machine it was before. Windows build, the account name and the
    working monitor's size are enough to separate one reporter from another without any of them
    being worth knowing on their own, and the hash is one way regardless.
    """
    width, height = screen.size()
    seed = f'{platform.platform()}|{getpass.getuser()}|{width}x{height}'
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _newest_frame():
    """The last png frames.py wrote, as bytes, or None if it wrote none.

    Read rather than captured: by the time a pass has raised, the screen has often already moved
    on, and the frame taken around the last click is the one showing what the bot was looking at.
    """
    try:
        frames.flush()  # frames are written by a worker thread; the newest may still be in flight
        pngs = sorted(frames.FRAME_DIR.glob('*.png'), key=lambda path: path.stat().st_mtime)
        return pngs[-1].read_bytes() if pngs else None
    except OSError:
        return None


def _screen_png():
    """The working monitor as png bytes, straight into memory."""
    buffer = io.BytesIO()
    screen.grab().save(buffer, format='PNG')
    return buffer.getvalue()


def _describe(error):
    """One exception as the json the endpoint stores."""
    trace = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    return {'type': type(error).__name__,
            'message': str(error)[:MESSAGE_LIMIT],
            'traceback': trace[-TRACEBACK_LIMIT:]}  # the end, that is where the raise is


def _send(url, data, headers, method):
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, response.read()


def report(error, before=None, after=None, endpoint=ENDPOINT):
    """Post one crash and upload its two screenshots. True if the endpoint took the report.

    before and after default to the last frame on disk and the screen as it is now. Pass b'' for
    either to send the report without that picture. Raises if the endpoint refuses; callers that
    cannot afford that want report_later().
    """
    before = _newest_frame() if before is None else before
    after = _screen_png() if after is None else after

    payload = json.dumps({'machine_id': machine_id(),
                          'version': version.__version__,
                          'error': _describe(error)}).encode('utf-8')
    _, body = _send(endpoint, payload, {'Content-Type': 'application/json'}, 'POST')
    answer = json.loads(body)

    for half, png in (('before', before), ('after', after)):
        upload = (answer.get(half) or {}).get('upload_url')
        if upload and png:
            _send(upload, png, {'Content-Type': 'image/png'}, 'PUT')
    return True


def report_later(error, **kwargs):
    """Send the report on its own thread, and never let it matter.

    A crash report is the least important thing happening at the moment it is made. The GUI still
    has to paint its red lamp and stay clickable, so a site that is slow or down cannot be
    allowed to block that, and a failure to report must never raise on top of the error it was
    reporting.
    """
    def run():
        try:
            report(error, **kwargs)
        except Exception as sending:  # noqa: BLE001  nothing here is worth a second crash
            log(f'error report not sent: {type(sending).__name__}: {sending}', 1)

    threading.Thread(target=run, daemon=True).start()
