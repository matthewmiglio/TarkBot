"""Tell the website what the flea sniper bought, and every captcha it ran into.

The sniper's stats already count what a run bought, and those numbers die with the run. This
sends the same fact somewhere it survives: item, price, what a trader pays for it, and the
machine that bought it. The dashboard turns the pile into what people are actually sniping.

Margin is deliberately not sent. It is trader value minus price by definition, and Postgres
computes it as a generated column, so there is no way for the number on the dashboard to
disagree with the two it comes from.

A captcha sends a screenshot of the screen as it is, into Tarkbot_captchas, so the SECURITY
CHECK modals people actually get can be collected for the captcha work. A lossless png of a
1440p screen is about 4.5MB, which Vercel refuses before route code runs, so the endpoint answers
with one single-use upload url and the bytes go straight to storage. Png, not lossy, because the
images are for cutting reference crops out of.

Nothing here holds a key: the endpoints are routes on our own site that talk to Supabase with a
server-side key, so the app stays free to be open source.

Nothing here can cost a purchase either. Every send is on a daemon thread and every failure is
swallowed into the log, because a slow website must never stall a sweep sitting on a flea board.
"""
import getpass
import io
import json
import os
import platform
import threading
import urllib.request
import uuid

import screen
import version
from narrate import log

# The www host, not the bare one, which answers a 308 to it. urllib will not carry a POST across
# a redirect and raises instead, so the bare domain here means no purchase is ever recorded.
ENDPOINT = os.environ.get('TARKBOT_SNIPE_URL', 'https://www.tarkbot.org/api/snipe')
CAPTCHA_ENDPOINT = os.environ.get('TARKBOT_CAPTCHA_URL', 'https://www.tarkbot.org/api/captcha')
TIMEOUT = 20  # seconds; a slow site must not keep a thread alive behind a running sweep
ITEM_LIMIT = 120  # the endpoint clamps to this too; clamping here keeps the body small


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


def _send(url, data, headers, method):
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def report_captcha(image, endpoint=CAPTCHA_ENDPOINT):
    """Post one captcha and upload its screenshot (a PIL image). Raises if either step fails."""
    payload = json.dumps({'machine_id': machine_id(),
                          'version': version.__version__}).encode('utf-8')
    answer = json.loads(_send(endpoint, payload, {'Content-Type': 'application/json'}, 'POST'))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    _send(answer['upload_url'], buffer.getvalue(), {'Content-Type': 'image/png'}, 'PUT')
    log(f'reported the captcha as {answer["id"]}', 1)
    return True


def report_captcha_later(**kwargs):
    """Grab the screen now, send it on a daemon thread, never raise. Returns the thread.

    The grab is here on the caller's thread, so the picture is the screen the captcha was seen
    on; only the png encoding and the upload, the slow parts, go to the thread.
    """
    try:
        image = screen.grab()
    except Exception as grabbing:  # noqa: BLE001  a failed screenshot must not mask the captcha
        log(f'captcha not reported: {type(grabbing).__name__}: {grabbing}', 1)
        return None

    def run():
        try:
            report_captcha(image, **kwargs)
        except Exception as sending:  # noqa: BLE001
            log(f'captcha not reported: {type(sending).__name__}: {sending}', 1)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def report_buy(item, price, trader_value, endpoint=ENDPOINT):
    """Post one purchase. True if the site took it, and raises if it did not.

    Raises rather than returning False on purpose: the only caller is report_buy_later, which
    catches everything and logs it, and a test wants the reason rather than a bare False.
    """
    payload = json.dumps({
        'machine_id': machine_id(),
        'version': version.__version__,
        'item': str(item)[:ITEM_LIMIT],
        'price': int(price),
        'trader_value': int(trader_value),
    }).encode('utf-8')
    request = urllib.request.Request(endpoint, data=payload, method='POST',
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        body = response.read().decode('utf-8', 'replace')
    log(f'reported buying {item} for {int(price):,}', 2)
    return json.loads(body).get('success', False)


def report_buy_later(item, price, trader_value, **kwargs):
    """Send it on a daemon thread and never raise. Returns the thread.

    This one fires in the middle of a sweep rather than after a run has already died. A telemetry post
    that raised here would end a sweep over a row nobody reads, and one that blocked would leave
    the bot sat on an offer board while the market moves.
    """
    def run():
        try:
            report_buy(item, price, trader_value, **kwargs)
        except Exception as sending:
            log(f'buy not reported: {type(sending).__name__}: {sending}', 2)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


if __name__ == '__main__':
    # No network. What can be checked without one is that the payload is the shape the endpoint
    # validates, since every field there has its own rejection.
    import uuid

    sent = {}

    def _capture(request, timeout=None):
        sent.update(json.loads(request.data.decode('utf-8')))
        raise RuntimeError('stopping before the network')

    urllib.request.urlopen = _capture
    try:
        report_buy('Salewa first aid kit', 41_000, 52_000)
    except RuntimeError:
        pass

    assert uuid.UUID(sent['machine_id']), 'machine_id must parse as a uuid, the endpoint checks it'
    assert sent['item'] == 'Salewa first aid kit', sent
    assert sent['price'] == 41_000 and sent['trader_value'] == 52_000, sent
    assert 'margin' not in sent, 'margin is generated in Postgres and must not be sent'
    assert isinstance(sent['price'], int), 'a float price is refused with a 400'

    long_name = 'x' * 500
    try:
        report_buy(long_name, 1, 2)
    except RuntimeError:
        pass
    assert len(sent['item']) == ITEM_LIMIT, f'the name should be clamped, got {len(sent["item"])}'

    # A captcha: one json post, then the png PUT at the url it answered with.
    from PIL import Image
    calls = []

    class _Answer:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return self.body

    def _fake_site(request, timeout=None):
        calls.append(request)
        if len(calls) == 1:
            return _Answer(json.dumps({'id': 'x', 'upload_url': 'https://storage/put'}).encode())
        return _Answer(b'{}')

    urllib.request.urlopen = _fake_site
    report_captcha(Image.new('RGB', (4, 4)), endpoint='https://site/api/captcha')
    assert [c.get_method() for c in calls] == ['POST', 'PUT'], calls
    assert uuid.UUID(json.loads(calls[0].data)['machine_id']), 'the captcha post needs a uuid too'
    assert calls[1].full_url == 'https://storage/put' and calls[1].data[:4] == b'\x89PNG', calls[1]

    # And the one that matters most: a failing send must not reach the caller.
    def _explode(request, timeout=None):
        raise OSError('no network here')

    urllib.request.urlopen = _explode
    report_buy_later('Salewa first aid kit', 41_000, 52_000).join(timeout=5)
    report_captcha_later().join(timeout=5)
    print('ok, both payloads are the shape the endpoints want and a failure stays swallowed')
