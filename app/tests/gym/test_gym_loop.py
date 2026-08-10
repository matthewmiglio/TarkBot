"""The gym loop's decisions, against a fake screen: when does it click, and does Stop land.

No game, no window, no real pixels. The strip the bot reads is drawn here, so a run can be
walked through a rep at a time and the click either happens on the frame it should or it does
not. What this cannot check is whether a click at the moment the lines meet actually scores the
rep in Tarkov; that is what an end to end run against the game is for.

Run:  python tests/gym/test_gym_loop.py
"""
import sys
import threading
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw  # noqa: E402

import gym_bot  # noqa: E402
from interact import find, gym  # noqa: E402

REGION = (0, 0, 1920, 1080)


def strip(bars):
    """One look's screenshot, with a white bar over each (first, last) column of the strip.

    The whole look box, not just the strip, because that is what the loop grabs now: it takes
    one shot holding the icon box and the strip both, and slices it. Bars are still given in
    strip columns, since that is what read_lines reports and what the assertions talk about.
    """
    look = gym.look_region(REGION)
    image = Image.new('RGB', (look[2], look[3]), (20, 20, 20))
    left, top, _, bottom = gym.inside(look, gym.rep_region(REGION))
    for first, last in bars:
        ImageDraw.Draw(image).rectangle((left + first, top, left + last, bottom - 1),
                                        fill=(204, 204, 204))
    return image


def make(gap=gym_bot.CLICK_GAP):
    """A HideoutGym with no Tarkov behind it.

    Built without __init__ on purpose: everything __init__ does is find the window and measure
    it, which is exactly the part there is no way to fake and nothing here is testing.
    """
    bot = object.__new__(gym_bot.HideoutGym)
    bot.region = REGION
    bot.roi = gym.rep_region(REGION)
    bot.icon_roi = gym.icon_region(REGION)
    bot.look_roi = gym.look_region(REGION)
    bot._icon_at = gym.inside(bot.look_roi, bot.icon_roi)
    bot._strip_at = gym.inside(bot.look_roi, bot.roi)
    bot.gap = gap
    bot._last = deque(maxlen=gym_bot.SPEED_SAMPLES)
    bot._due = None
    bot.stats = {key: 0 for key, _ in gym_bot.STAT_LABELS}
    bot._stop = threading.Event()
    bot._idle = False
    return bot


if __name__ == '__main__':
    import pyautogui

    import screen

    clicks, icon_looks = [], []
    # The fake grab costs real time, because the predictor's arithmetic is about real elapsed
    # time: with an instant screen every reading lands in the same instant, the measured speed
    # is nonsense, and the test would prove the opposite of what it claims to.
    GRAB = 0.02
    # fast_grab, not grab: the loop takes the low latency path and faking the other one would
    # leave it reading the real desktop while this file believed it was driving the screen.
    screen.fast_grab = lambda region=None: (time.sleep(GRAB), screen.fast_grab.answer)[1]
    find.find = lambda *a, **kw: icon_looks.append(a[0]) or find.find.answer
    pyautogui.mouseDown = lambda *a, **k: clicks.append(a)
    pyautogui.mouseUp = lambda *a, **k: None
    find.find.answer = True
    gym_bot.REP_COOLDOWN = 0  # the real 0.5s is not worth waiting through 4 times
    # Both trims pinned off, so the timings below are the predictor's own arithmetic and not
    # whatever the shipping constants happen to be tuned to this week. Each is exercised on
    # purpose further down.
    gym_bot.AIM_COLUMNS, gym_bot.CLICK_LEAD = 0.0, 0.0

    # A ring closing at 25 columns per 20ms look, which is 1250 a second, in the range a real
    # set reaches by its last few reps. Target centre is 25, so a gap of g puts the ring at
    # 25 + g.
    def closing(gap):
        return strip([(20, 30), (24 + gap, 26 + gap)])

    # One reading proves nothing: with no speed yet, a wide gap is not a rep and not a wait.
    bot = make()
    screen.fast_grab.answer = closing(95)
    started = time.perf_counter()
    assert bot.do_one_rep() is False, 'one reading cannot measure a speed'
    assert clicks == [], f'clicked with the lines apart, {clicks}'
    assert time.perf_counter() - started < gym_bot.IDLE_POLL, 'the closing phase must not sleep'

    # A second reading gives a speed, but this overlap is still two looks out, so it is not
    # committed to: the next look sees it closer and aims better off a shorter extrapolation.
    screen.fast_grab.answer = closing(70)
    assert bot.do_one_rep() is False, 'still far out, so no commitment yet'
    assert clicks == [], f'clicked too early, {clicks}'

    # Now the overlap will happen before the next look could report it. That is the last chance
    # to aim, so it sleeps out the remaining travel and presses into it.
    clicks.clear()
    screen.fast_grab.answer = closing(45)
    started = time.perf_counter()
    assert bot.do_one_rep() is True, 'the last look before the overlap must commit'
    waited = time.perf_counter() - started - GRAB
    left, top, width, height = bot.roi
    assert clicks == [(left + width // 2, top + height // 2)], f'clicked at {clicks}'
    assert bot.stats['reps'] == 1, bot.stats
    # It pressed into the future, not on sight: 45 columns at 1250 a second is 36ms away and 20
    # of those went on the grab, so about 16ms should have been slept. Sleeping accurately is
    # the point, so the window is tight; a threading.Event wait would round this up past it.
    assert 0.010 < waited < 0.024, f'waited {waited * 1000:.0f}ms, wanted about 16'

    # The same rep with a column of offset asked for presses earlier by exactly that much
    # travel, which is the knob for a miss that looks the same at every speed.
    gym_bot.AIM_COLUMNS = 12.5  # 12.5 columns at 1250 a second is 10ms sooner
    bot = make()
    clicks.clear()
    for gap in (95, 70, 45):
        screen.fast_grab.answer = closing(gap)
        started = time.perf_counter()
        landed = bot.do_one_rep()
    offset_waited = time.perf_counter() - started - GRAB
    assert landed is True and len(clicks) == 1, (landed, clicks)
    assert offset_waited < waited - 0.005, (f'offset pressed at {offset_waited * 1000:.0f}ms, '
                                            f'no earlier than the {waited * 1000:.0f}ms without')
    gym_bot.AIM_COLUMNS = 0.0

    # And a lead in seconds presses earlier by that time whatever the ring is doing, which is
    # the knob for reps that only start missing once a set has sped up.
    gym_bot.CLICK_LEAD = 0.010
    bot = make()
    clicks.clear()
    for gap in (95, 70, 45):
        screen.fast_grab.answer = closing(gap)
        started = time.perf_counter()
        landed = bot.do_one_rep()
    lead_waited = time.perf_counter() - started - GRAB
    assert landed is True and len(clicks) == 1, (landed, clicks)
    assert lead_waited < waited - 0.005, (f'a 10ms lead pressed at {lead_waited * 1000:.0f}ms, '
                                          f'no earlier than the {waited * 1000:.0f}ms without')
    # A negative lead aims *after* the two lines merge, which is legal: the ring keeps
    # travelling once its edge is inside the band. The rep must still be held for the aimed
    # moment rather than pressed the instant the merge is seen, or a late aim is silently
    # capped at "as late as the merge" and the knob stops working past that point.
    gym_bot.CLICK_LEAD = -0.030
    bot = make()
    clicks.clear()
    for gap in (95, 70, 45):
        screen.fast_grab.answer = closing(gap)
        bot.do_one_rep()
    assert clicks == [], f'a lead this late should not have pressed yet, {clicks}'
    screen.fast_grab.answer = strip([(20, 30)])  # merged, and the aimed moment is still ahead
    started = time.perf_counter()
    assert bot.do_one_rep() is True, 'the merged look must still press'
    held = time.perf_counter() - started - GRAB
    assert held > 0.005, f'pressed on sight and threw the {30}ms lead away, held {held:.3f}s'
    gym_bot.CLICK_LEAD = 0.0

    # Lines already together on the first look of a rep, with no speed measured: press now and
    # be late rather than never press. This is the path that catches a rep whose whole overlap
    # happened inside one look.
    bot = make()
    clicks.clear()
    screen.fast_grab.answer = strip([(20, 30)])
    assert bot.do_one_rep() is True, 'a single line means they have met'
    assert len(clicks) == 1 and bot.stats['reps'] == 1, (clicks, bot.stats)

    # Lines drifting apart are not a ring closing in, and must never be extrapolated into one.
    bot = make()
    clicks.clear()
    screen.fast_grab.answer = strip([(20, 30), (40, 43)])
    bot.do_one_rep()
    screen.fast_grab.answer = strip([(20, 30), (100, 104)])
    assert bot.do_one_rep() is False, 'a widening gap is not a rep'
    assert clicks == [], f'clicked on a receding line, {clicks}'

    # No icon: nothing is read and nothing is clicked, however inviting the strip looks. This
    # is the case that cost fifteen clicks at a character standing still, where a bright scene
    # filled the whole strip and read as one run, which is what "they have met" looks like.
    bot = make()
    clicks.clear()
    _, _, wide, _ = gym.rep_region(REGION)
    screen.fast_grab.answer = strip([(0, wide - 1)])  # the entire strip lit, as a bright scene does
    find.find.answer = None
    started = time.perf_counter()
    assert bot.do_one_rep() is False, 'no icon means no rep, whatever the pixels say'
    assert clicks == [], f'clicked with no skill check on screen, {clicks}'
    # 0.9, not 1.0: Windows' clock ticks about every 15ms, so a 100ms wait can measure as 94ms.
    assert time.perf_counter() - started >= gym_bot.IDLE_POLL * 0.9, 'no icon should wait'

    find.find.answer = True

    # An empty strip with the icon up is the prompt fading in: no rep, no wait either, because
    # the ring is about to start moving.
    bot = make()
    clicks.clear()
    screen.fast_grab.answer = strip([])
    started = time.perf_counter()
    assert bot.do_one_rep() is False, 'an empty strip is no rep'
    assert clicks == [], f'clicked at nothing, {clicks}'
    assert time.perf_counter() - started < gym_bot.IDLE_POLL, 'the icon is up, so do not sleep'

    # The icon is read on every look, not once per idle stretch: it is the thing that says a
    # rep is being asked for, so a stale answer is a click at whatever is on screen instead.
    icon_looks.clear()
    for _ in range(3):
        bot.do_one_rep()
    assert len(icon_looks) == 3, f'icon read {len(icon_looks)}x over 3 looks'

    # Stop lands while the loop is running, rather than at the end of some longer unit.
    bot = make()
    screen.fast_grab.answer = strip([(20, 30), (100, 104)])  # never a rep, so it only ever loops
    thread = threading.Thread(target=bot.start, daemon=True)
    thread.start()
    time.sleep(0.2)
    assert thread.is_alive(), 'the loop should still be going'
    bot.stop()
    thread.join(timeout=2)
    assert not thread.is_alive(), 'Stop did not get the loop to come back'

    # Stop out of the idle wait too, which is where the loop sits most of the time.
    bot = make()
    screen.fast_grab.answer = strip([])
    thread = threading.Thread(target=bot.start, daemon=True)
    thread.start()
    time.sleep(0.2)
    bot.stop()
    thread.join(timeout=2)
    assert not thread.is_alive(), 'Stop did not get the loop out of its idle wait'

    print('ok')
