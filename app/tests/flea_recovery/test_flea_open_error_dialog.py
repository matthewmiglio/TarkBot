"""A flea that will not open gets one retry, once the Error dialog is clicked away.

App layer: sell_bot.FleaSeller.open_offer_creation and, on its own, FleaSeller._past_error_dialog
(the wrapper every screen-reading step of a pass now runs through), backed by interact/sell.py's
dismiss_error_popup clearing the "Error / 0 / OK" dialog. Verifies a failed step is retried once
and only when the dialog was really there, that the step's own return value passes back out, and
that a step needing the offer creation window gives up the pass when the dialog took that window
with it.

Run:  python tests/flea_recovery/test_flea_open_error_dialog.py

No game needed, nothing is clicked (a pure stub/logic test): snipe.open_clean_board and
sell.dismiss_error_popup are
stubbed, so this is about the order open_offer_creation tries things in, not about pixels.

Two halves. The first drives open_offer_creation, which is the step the dialog hides itself from
best: Tarkov dims the whole screen behind its "Error / 0 / OK" dialog, and sell.is_flea_open
decides open-or-shut off the mean brightness of the flea taskbar icon. Dimmed, an open flea reads
as shut (measured 89 against a threshold of 90, where the two real states are 56 and 119), and
the click that would open a genuinely shut flea lands on a modal that swallows it, so the second
read says shut too. The run of 2026-08-22 died this way 27 passes in, with the OK button sat on
screen unclicked: the dialog appeared in the half second between the previous pass's dismiss and
this pass's first look at the flea, so the dismiss already in the code found a clean screen.

The second half drives FleaSeller._past_error_dialog on its own. Every screen-reading step of a
pass now goes through it, not just this one, because the dialog is the game's to raise whenever
it likes: the run of 2026-08-23 died applying the flea filters, 154 passes in, on the same
unclicked OK button. What is worth pinning down is that the wrapper offers the retry once and
only when the dialog was really there, so a step failing on a clean screen still raises its own
message rather than one about a dialog nobody saw.
"""
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import sell_bot  # noqa: E402
from interact import find, sell, snipe  # noqa: E402

BOX = (10, 152, 116, 20)  # the offer creation window title, where it really lands


def open_flea_with(boards, dialog):
    """open_offer_creation against a flea answering `boards` in turn. Returns (outcome, calls).

    `dialog` is what dismiss_error_popup finds. Outcome is 'opened' when the flea came up, or
    the RuntimeError's message when it did not. Stop is pre-set, so the _pause immediately after
    the flea opens unwinds the pass before it can reach the offer slot wait, which in the real
    thing blocks for hours.
    """
    answers, calls = list(boards), {'open': 0, 'dismiss': 0}
    bot = object.__new__(sell_bot.FleaSeller)
    bot.region = None
    bot._stop = threading.Event()
    bot._stop.set()
    originals = (snipe.open_clean_board, sell.dismiss_error_popup)

    def fake_open(region=None, **kw):
        calls['open'] += 1
        return answers.pop(0)

    def fake_dismiss(region=None, **kw):
        calls['dismiss'] += 1
        return dialog

    snipe.open_clean_board, sell.dismiss_error_popup = fake_open, fake_dismiss
    try:
        bot.open_offer_creation()
        return 'no raise at all', calls  # unreachable: _pause raises Stopped past the flea
    except sell_bot.Stopped:
        return 'opened', calls
    except RuntimeError as e:
        return str(e), calls
    finally:
        snipe.open_clean_board, sell.dismiss_error_popup = originals


print('the flea opens first time: no dialog is looked for')
outcome, calls = open_flea_with([True], dialog=False)
assert outcome == 'opened', outcome
assert calls == {'open': 1, 'dismiss': 0}, calls
print(f'  ok  {calls}')

print('shut, and a dialog was up: click it away and the retry gets in')
outcome, calls = open_flea_with([False, True], dialog=True)
assert outcome == 'opened', f'the retry after the dialog should have opened the flea: {outcome}'
assert calls == {'open': 2, 'dismiss': 1}, calls
print(f'  ok  {calls}')

print('shut with no dialog to blame: raise, same as it always did')
outcome, calls = open_flea_with([False], dialog=False)
assert outcome == 'could not open the flea market', outcome
assert calls == {'open': 1, 'dismiss': 1}, calls
print(f'  ok  {calls}')

print('shut, dialog cleared, still shut: raise, and say the dialog was not the reason')
outcome, calls = open_flea_with([False, False], dialog=True)
assert outcome == 'could not open the flea market after clearing the error dialog', outcome
assert calls == {'open': 2, 'dismiss': 1}, calls
print(f'  ok  {calls}')


def wrapper_with(steps, dialog, needs_offer_window=False, offer_window=True):
    """_past_error_dialog over a step answering `steps` in turn. Returns (outcome, calls).

    A bare lambda rather than a sell.* call, because the point of the wrapper is that it does
    not care which step it was handed: the same two calls guard the flea, the filters, the
    price field and the place offer button.

    needs_offer_window is passed straight through, and offer_window is what the screen answers
    when the wrapper goes looking for that window after clearing the dialog.
    """
    answers, calls = list(steps), {'step': 0, 'dismiss': 0, 'looked': 0}
    bot = object.__new__(sell_bot.FleaSeller)
    bot.region = None
    original = sell.dismiss_error_popup

    def step():
        calls['step'] += 1
        answer = answers.pop(0)
        if isinstance(answer, Exception):  # how the region inferences fail
            raise answer
        return answer

    def fake_dismiss(region=None, **kw):
        calls['dismiss'] += 1
        return dialog

    def fake_find(target, region=None, **kw):
        calls['looked'] += 1
        assert target == sell.OFFER_TARGET, target
        return BOX if offer_window else None

    sell.dismiss_error_popup = fake_dismiss
    was_find = find.find
    find.find = fake_find
    try:
        return bot._past_error_dialog(step, 'could not do the thing',
                                      needs_offer_window=needs_offer_window), calls
    except sell_bot.Retry as e:
        return f'Retry: {e}', calls
    except RuntimeError as e:
        return str(e), calls
    finally:
        sell.dismiss_error_popup = original
        find.find = was_find


print('the wrapper on its own: any step, any message')
outcome, calls = wrapper_with([True], dialog=False)
assert (outcome, calls) == (True, {'step': 1, 'dismiss': 0, 'looked': 0}), (outcome, calls)
print(f'  ok  a step that works is never charged a match for the dialog  {calls}')

outcome, calls = wrapper_with(['a Selection'], dialog=False)
assert outcome == 'a Selection', outcome  # handed back, not flattened to True
print('  ok  what the step returned comes back out')

outcome, calls = wrapper_with([False, True], dialog=True)
assert (outcome, calls) == (True, {'step': 2, 'dismiss': 1, 'looked': 0}), (outcome, calls)
print(f'  ok  cleared the dialog and the second go worked  {calls}')

outcome, calls = wrapper_with([False], dialog=False)
assert outcome == 'could not do the thing', outcome
assert calls == {'step': 1, 'dismiss': 1, 'looked': 0}, calls
print('  ok  failed on a clean screen, so it raises the step\'s own message')

outcome, calls = wrapper_with([False, False], dialog=True)
assert outcome == 'could not do the thing after clearing the error dialog', outcome
assert calls == {'step': 2, 'dismiss': 1, 'looked': 0}, calls
print('  ok  failed twice, and the message says the dialog was not the reason')


print('a step that raises LookupError, which is how the region inferences fail')
anchors = LookupError('cannot infer inventory region, not on screen: a, b, c')

outcome, calls = wrapper_with([anchors, 'picked'], dialog=True)
assert (outcome, calls) == ('picked', {'step': 2, 'dismiss': 1, 'looked': 0}), (outcome, calls)
print(f'  ok  a raise gets the same second look as a false  {calls}')

outcome, calls = wrapper_with([anchors], dialog=False)
assert outcome == ('could not do the thing: cannot infer inventory region, '
                   'not on screen: a, b, c'), outcome
assert calls == {'step': 1, 'dismiss': 1, 'looked': 0}, calls
print('  ok  no dialog, so it raises and keeps the anchors the LookupError named')

outcome, calls = wrapper_with([anchors, anchors], dialog=True)
assert outcome == ('could not do the thing: cannot infer inventory region, '
                   'not on screen: a, b, c after clearing the error dialog'), outcome
assert calls == {'step': 2, 'dismiss': 1, 'looked': 0}, calls
print('  ok  raised twice, and the message says the dialog was not the reason')

print('a dialog that took the offer creation window with it')
# The run of 2026-08-31, 18 items in. The bot picked a Morphine injector, the flea had no
# offers for it at all, and Tarkov raised its dialog over a board reading "No offers have been
# found in the Morphine injector category". The dialog also closed the offer creation window,
# so infer_inventory_region came back with all three of its anchors missing. Clearing the
# dialog worked; retrying against a screen the window had left could not, and the run ended on
# a RuntimeError over a market condition a fresh pass walks straight past.
outcome, calls = wrapper_with([anchors], dialog=True, needs_offer_window=True,
                              offer_window=False)
assert outcome.startswith('Retry: '), f'ended the run instead of starting a fresh pass: {outcome}'
assert 'no offer creation window' in outcome, outcome
assert calls == {'step': 1, 'dismiss': 1, 'looked': 1},     f'retried the step against a screen with no window on it: {calls}'
print(f'  ok  window gone       Retry, and the step is not run a second time  {calls}')

# The window still up is the ordinary case, and it must behave exactly as it always did.
outcome, calls = wrapper_with([anchors, 'picked'], dialog=True, needs_offer_window=True)
assert (outcome, calls) == ('picked', {'step': 2, 'dismiss': 1, 'looked': 1}), (outcome, calls)
print(f'  ok  window still up   the retry runs as before  {calls}')

# And a step that does not live in that window never pays for the look. open_clean_board runs
# before the window exists, so asking would fail every time and end runs that are fine.
outcome, calls = wrapper_with([False, True], dialog=True)
assert (outcome, calls) == (True, {'step': 2, 'dismiss': 1, 'looked': 0}), (outcome, calls)
print(f'  ok  window not wanted no look, no Retry, opening the flea still retries  {calls}')

print('ok, every step gets a second look once the Error dialog is gone, and one only, and a '
      'step that needs the offer creation window gives up the pass when it has gone')
