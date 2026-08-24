"""A flea that will not open gets one retry, once the Error dialog is clicked away.

Run:  python tests/test_flea_open_error_dialog.py

No game needed, nothing is clicked: snipe.open_clean_board and sell.dismiss_error_popup are
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sell_bot  # noqa: E402
from interact import sell, snipe  # noqa: E402


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


def wrapper_with(steps, dialog):
    """_past_error_dialog over a step answering `steps` in turn. Returns (outcome, calls).

    A bare lambda rather than a sell.* call, because the point of the wrapper is that it does
    not care which step it was handed: the same two calls guard the flea, the filters, the
    price field and the place offer button.
    """
    answers, calls = list(steps), {'step': 0, 'dismiss': 0}
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

    sell.dismiss_error_popup = fake_dismiss
    try:
        return bot._past_error_dialog(step, 'could not do the thing'), calls
    except RuntimeError as e:
        return str(e), calls
    finally:
        sell.dismiss_error_popup = original


print('the wrapper on its own: any step, any message')
outcome, calls = wrapper_with([True], dialog=False)
assert (outcome, calls) == (True, {'step': 1, 'dismiss': 0}), (outcome, calls)
print(f'  ok  a step that works is never charged a match for the dialog  {calls}')

outcome, calls = wrapper_with(['a Selection'], dialog=False)
assert outcome == 'a Selection', outcome  # handed back, not flattened to True
print('  ok  what the step returned comes back out')

outcome, calls = wrapper_with([False, True], dialog=True)
assert (outcome, calls) == (True, {'step': 2, 'dismiss': 1}), (outcome, calls)
print(f'  ok  cleared the dialog and the second go worked  {calls}')

outcome, calls = wrapper_with([False], dialog=False)
assert outcome == 'could not do the thing', outcome
assert calls == {'step': 1, 'dismiss': 1}, calls
print('  ok  failed on a clean screen, so it raises the step\'s own message')

outcome, calls = wrapper_with([False, False], dialog=True)
assert outcome == 'could not do the thing after clearing the error dialog', outcome
assert calls == {'step': 2, 'dismiss': 1}, calls
print('  ok  failed twice, and the message says the dialog was not the reason')


print('a step that raises LookupError, which is how the region inferences fail')
anchors = LookupError('cannot infer inventory region, not on screen: a, b, c')

outcome, calls = wrapper_with([anchors, 'picked'], dialog=True)
assert (outcome, calls) == ('picked', {'step': 2, 'dismiss': 1}), (outcome, calls)
print(f'  ok  a raise gets the same second look as a false  {calls}')

outcome, calls = wrapper_with([anchors], dialog=False)
assert outcome == ('could not do the thing: cannot infer inventory region, '
                   'not on screen: a, b, c'), outcome
assert calls == {'step': 1, 'dismiss': 1}, calls
print('  ok  no dialog, so it raises and keeps the anchors the LookupError named')

outcome, calls = wrapper_with([anchors, anchors], dialog=True)
assert outcome == ('could not do the thing: cannot infer inventory region, '
                   'not on screen: a, b, c after clearing the error dialog'), outcome
assert calls == {'step': 2, 'dismiss': 1}, calls
print('  ok  raised twice, and the message says the dialog was not the reason')

print('ok, every step gets a second look once the Error dialog is gone, and one only')
