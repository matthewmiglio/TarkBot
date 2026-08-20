"""Tell the website what the flea sniper bought, one post per purchase.

The sniper's stats already count what a run bought, and those numbers die with the run. This
sends the same fact somewhere it survives: item, price, what a trader pays for it, and the
machine that bought it. The dashboard turns the pile into what people are actually sniping.

Its own module rather than more of crash_report.py, which it otherwise resembles. That one is
about a crash: a 20KB traceback, two screenshots, two signed upload urls and a whole failure
path. This is six small fields and a 200, and the only thing genuinely shared is machine_id,
which is imported rather than copied so a machine reports as the same one in both tables and the
rows can be read side by side.

Margin is deliberately not sent. It is trader value minus price by definition, and Postgres
computes it as a generated column, so there is no way for the number on the dashboard to
disagree with the two it comes from.

Nothing here holds a key, same as crash_report: the endpoint is a route on our own site that
talks to Supabase with a server-side key, so the app stays free to be open source.

Nothing here can cost a purchase either. Every send is on a daemon thread and every failure is
swallowed into the log, because a slow website must never stall a sweep sitting on a flea board.
"""
import json
import os
import threading
import urllib.request

import version
from crash_report import machine_id
from narrate import log

# The www host, not the bare one, which answers a 308 to it. urllib will not carry a POST across
# a redirect and raises instead, so the bare domain here means no purchase is ever recorded.
ENDPOINT = os.environ.get('TARKBOT_SNIPE_URL', 'https://www.tarkbot.org/api/snipe')
TIMEOUT = 20  # seconds; a slow site must not keep a thread alive behind a running sweep
ITEM_LIMIT = 120  # the endpoint clamps to this too; clamping here keeps the body small


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

    The same shape as crash_report.report_later and for the same reason, only more so: this one
    fires in the middle of a sweep rather than after a run has already died. A telemetry post
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

    # And the one that matters most: a failing send must not reach the caller.
    def _explode(request, timeout=None):
        raise OSError('no network here')

    urllib.request.urlopen = _explode
    report_buy_later('Salewa first aid kit', 41_000, 52_000).join(timeout=5)
    print('ok, the payload is the shape the endpoint wants and a failure stays swallowed')
