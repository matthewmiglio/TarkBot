"""Which monitor the bot works on, and grabbing pixels off it.

There is a monitor picker at all because of one line inside pyscreeze: every screenshot it
takes is `ImageGrab.grab(all_screens=False)`, the primary monitor and nothing else, and
locateOnScreen throws the caller's region away before grabbing. A Tarkov on the second
monitor was therefore invisible to the bot no matter what region it was handed, and the
crops it did get back were of the primary screen at coordinates that meant nothing there.

grab() takes the whole virtual desktop instead and cuts the asked-for rectangle out of it by
hand. The hand part matters: with every screen in one image, pixel (0, 0) is the top left of
the *virtual desktop*, which is negative on the very common layout of a second monitor placed
to the left of the primary one. Pillow does not adjust for that and neither does pyscreeze, so
both crop the wrong place; subtracting the virtual origin here is what puts it right.

use() picks the monitor everything else measures against, and watch() points pyautogui's own
screenshot at grab() so the test scripts and anything else calling it get the same fix without
each knowing about any of this.

Self-check, no game needed:  python -m screen
"""
import ctypes
from collections import namedtuple
from ctypes import wintypes

import pyautogui
from PIL import ImageGrab

from narrate import log

# pyautogui inserts a fixed pause after every click, press, hotkey and typewrite; its default is
# 0.1s, and a pass fires dozens of those, so the tax adds up (a four-click step pays 0.4s in pause
# alone). Halved here, once, process-wide: screen is the lowest-level module every mode and the
# tests import, so setting it here reaches all of them without each entry point remembering to.
# ponytail: 0.05 is a passive win with margin left; the game has taken clicks fine at it. Drop
# further only against a live run that proves offers still land, not on principle.
pyautogui.PAUSE = 0.05

user32 = ctypes.windll.user32
AUTO = 'auto'  # the saved preference before anyone has picked, and after a monitor is unplugged
# GetSystemMetrics indices for the rectangle enclosing every monitor.
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
MONITORINFOF_PRIMARY = 1
SRCCOPY = 0x00CC0020  # plain copy, for fast_grab. CAPTUREBLT would add layered windows, and
DIB_RGB_COLORS = 0    # measured no slower, but the game is not one and neither is the flea.

# name is the device name Windows gives it (\\.\DISPLAY1), stable enough to save and match
# against next boot. label is what the dropdown shows. rect is (left, top, width, height) in
# the same screen coordinates every region in this app uses.
Monitor = namedtuple('Monitor', 'name label rect primary')

_chosen = None  # None means "not picked yet", and every reader falls back to the primary


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT),
                ('rcWork', wintypes.RECT), ('dwFlags', wintypes.DWORD),
                ('szDevice', wintypes.WCHAR * 32)]


def monitors():
    """Every monitor Windows can see, primary first then left to right. Never empty.

    Ordered rather than left in enumeration order, so the numbers in the labels mean the same
    thing every boot: 1 is the primary, and the rest read across the desk.
    """
    found = []
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HANDLE,
                                  ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def visit(handle, _dc, _rect, _param):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            box = info.rcMonitor
            found.append((bool(info.dwFlags & MONITORINFOF_PRIMARY), box.left, box.top,
                          box.right - box.left, box.bottom - box.top, info.szDevice))
        return True

    user32.EnumDisplayMonitors(None, None, callback(visit), 0)
    found.sort(key=lambda m: (not m[0], m[1]))  # primary first, then by left edge
    # 'primary' in the label because two identical panels otherwise read as the same option,
    # and the primary is the one the user can name without going and looking.
    return [Monitor(name=device, rect=(left, top, width, height), primary=primary,
                    label=f'{index}: {width}x{height}' + (' primary' if primary else ''))
            for index, (primary, left, top, width, height, device) in enumerate(found, start=1)]


def virtual_origin():
    """Top-left of the rectangle enclosing every monitor. Negative when one sits left of primary."""
    return (user32.GetSystemMetrics(SM_XVIRTUALSCREEN), user32.GetSystemMetrics(SM_YVIRTUALSCREEN))


def virtual_rect():
    """That whole rectangle as (left, top, width, height)."""
    return virtual_origin() + (user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
                               user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))


def use(name):
    """Work on the monitor with this device name. Returns the Monitor actually in use.

    An unknown name is not an error: monitors get unplugged and settings files outlive them, so
    that falls back to the primary and says so rather than refusing to run.
    """
    global _chosen
    available = monitors()
    for monitor in available:
        if monitor.name == name:
            _chosen = monitor
            log(f'working on monitor {monitor.label} ({monitor.name}) at {monitor.rect}')
            return monitor
    _chosen = _default()
    if name not in (None, '', AUTO):
        log(f'no monitor named {name!r} any more, falling back to {_chosen.label}')
    else:
        log(f'monitor not picked yet, using {_chosen.label} ({_chosen.name}) at {_chosen.rect}')
    return _chosen


def current():
    """The monitor in use: the one picked, else Tarkov's own, else the primary."""
    return _chosen if _chosen is not None else _default()


def containing(point):
    """The monitor a screen (x, y) falls on, or the primary if it falls on none of them."""
    x, y = point
    for monitor in monitors():
        left, top, width, height = monitor.rect
        if left <= x < left + width and top <= y < top + height:
            return monitor
    return monitors()[0]


def _game_monitor():
    """The monitor the Tarkov window is on, or None if it is not up.

    Imported inside the function on purpose. screen.py is imported by plenty that has no
    business caring whether a game is running, and a missing window must never be able to stop
    a screenshot: everything here falls back rather than raises.
    """
    try:
        import window
        hwnd = window.handle()
        (left, top), (width, height) = window.position(hwnd), window.size(hwnd)
        return containing((left + width // 2, top + height // 2))  # centre, not a corner a
    except Exception:  # window rect can share with the neighbouring screen
        return None


def _default():
    """What to work on when nothing has been picked: Tarkov's screen, else the primary.

    The primary alone used to be the whole answer, and it is wrong on exactly the layout this
    app exists for: the game on a 1440p second monitor with a 1080p primary. find.scale()
    measures off the working monitor, so that resized every reference image by 1.0 instead of
    1.333 and every target on screen missed at once. Nothing raised and nothing looked wrong;
    the log just said the flea icon was not on screen, for hours.
    """
    return _game_monitor() or monitors()[0]


def rect():
    """The working monitor as (left, top, width, height)."""
    return current().rect


def size():
    """The working monitor as (width, height). What pyautogui.size() should have been here."""
    return current().rect[2:]


def overlap(a, b):
    """The rectangle two (left, top, width, height) rects share, or None if they share nothing.

    What the bot searches is the Tarkov window clipped to the chosen monitor: the window is the
    real bounds when the game is windowed, and the monitor is what the user picked. No overlap
    means the game is not on that screen at all, which is worth saying out loud rather than
    quietly hunting for buttons somewhere they cannot be.
    """
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    if right <= left or bottom <= top:
        return None
    return (left, top, right - left, bottom - top)


def _crop(image, region, origin):
    """`region` cut out of a whole-virtual-desktop `image` whose pixel (0, 0) is at `origin`.

    Split out from grab() because this is the part that is easy to get wrong and impossible to
    check against a live screen, which changes between one grab and the next.
    """
    left, top, width, height = region
    x, y = origin
    return image.crop((left - x, top - y, left - x + width, top - y + height))


def grab(region=None):
    """A PIL image of `region`, or of the whole working monitor. Correct on any monitor.

    region is (left, top, width, height) in screen coordinates, the same as everywhere else in
    this app. The virtual origin is subtracted before cropping, so a monitor at a negative x
    reads from the right part of the picture instead of off the left edge of it.
    """
    return _crop(ImageGrab.grab(all_screens=True), rect() if region is None else region,
                 virtual_origin())


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)]


def fast_grab(region):
    """`region` copied straight off the screen, for callers that care more about when than what.

    grab() goes through Pillow, which photographs the entire virtual desktop and crops: about
    45ms whatever is asked for, and passing Pillow a bbox does not help because it crops
    internally too. This copies only the asked-for rectangle, measured at 17ms for a 311x155
    box, and the difference is not saved work but freshness. It exists for gym_bot, whose whole
    job is pressing a button at a particular instant, and where 28ms is several columns of a
    moving target.

    NOT a drop-in for grab(), which is why it is a separate function with a duller name rather
    than an option on that one. Its pixels come back one to two levels a channel off Pillow's
    on roughly half of them, and nobody has explained why. That is nothing against a threshold
    of 100 sitting between a floor of 18 and a peak of 204, and nothing against template
    matching at 0.9 confidence, and it is a real problem for ocr.py's digit bitmaps and for
    sell.py's dead pixel colors, which match to within ±5 a channel. Those go through grab().

    region is (left, top, width, height) in the same screen coordinates as everything else: the
    screen DC covers the whole virtual desktop, so a monitor at a negative x needs no
    adjustment here, unlike the Pillow path.
    """
    from PIL import Image

    gdi32 = ctypes.windll.gdi32
    left, top, width, height = region
    screen_dc = user32.GetDC(None)
    memory_dc = gdi32.CreateCompatibleDC(screen_dc)
    bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
    try:
        gdi32.SelectObject(memory_dc, bitmap)
        gdi32.BitBlt(memory_dc, 0, 0, width, height, screen_dc, left, top, SRCCOPY)
        header = _BITMAPINFOHEADER()
        header.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        header.biWidth, header.biHeight = width, -height  # negative height means top down rows
        header.biPlanes, header.biBitCount = 1, 32
        buffer = ctypes.create_string_buffer(width * height * 4)
        gdi32.GetDIBits(memory_dc, bitmap, 0, height, buffer, ctypes.byref(header),
                        DIB_RGB_COLORS)
        return Image.frombuffer('RGB', (width, height), buffer, 'raw', 'BGRX', 0, 1)
    finally:
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)


def watch(module=pyautogui):
    """Point pyautogui.screenshot at grab(), so call sites that never heard of this still work.

    Idempotent, and it keeps pyautogui's signature: the test scripts pass region= and expect a
    PIL image back, which is exactly what grab() is.
    """
    if getattr(module.screenshot, '_multimonitor', False):
        return

    def screenshot(imageFilename=None, region=None, **_kwargs):
        image = grab(region)
        if imageFilename is not None:
            image.save(imageFilename)
        return image

    screenshot._multimonitor = True
    module.screenshot = screenshot


# On import, not on request. Every screenshot in this app and its test scripts goes through
# pyautogui, and any one of them left unpatched quietly saves a picture of the primary monitor
# while claiming to be a picture of the game. One line here beats forty call sites remembering.
watch()


if __name__ == '__main__':
    from PIL import Image

    found = monitors()
    assert found, 'a machine with no monitors is not one this runs on'
    assert found[0].primary, f'the primary sorts first, got {found[0]}'
    assert len({m.name for m in found}) == len(found), 'device names are unique'
    for monitor in found:
        print(f'{monitor.label:16} {monitor.name:14} at {monitor.rect}'
              + ('  primary' if monitor.primary else ''))
    print(f'virtual desktop {virtual_rect()}, origin {virtual_origin()}')

    # Both fallbacks go through _default(), which is Tarkov's screen when the game is up and the
    # primary when it is not. Asserted against _default() rather than against .primary, which
    # was the old rule and is only still true with the game closed or on the primary.
    assert current() == _default(), 'nothing picked yet means the game screen, else the primary'
    assert use('\\\\.\\NOPE') == _default(), 'an unplugged monitor falls back the same way'
    assert _game_monitor() is None or _game_monitor() in found, 'the game is on a real monitor'
    last = found[-1]
    assert use(last.name) == last, 'picking one by device name selects it'
    assert size() == last.rect[2:] and rect() == last.rect

    # containing() reads a point back to the monitor it is on, including the far corner of the
    # last one, which is the pixel a corner drag lands on.
    left, top, width, height = last.rect
    assert containing((left, top)) == last, 'top left corner belongs to that monitor'
    assert containing((left + width - 1, top + height - 1)) == last, 'and so does bottom right'
    assert containing((10 ** 6, 10 ** 6)).primary, 'a point on no monitor falls back'

    # The crop math against a made-up desktop, so the check does not depend on this machine
    # having two monitors, or on the screen holding still between one grab and the next. Two
    # 4x4 monitors side by side, the left one at a negative x the way a real one is: every
    # pixel of the left monitor is red, every pixel of the right one blue.
    desktop = Image.new('RGB', (8, 4), (255, 0, 0))
    desktop.paste(Image.new('RGB', (4, 4), (0, 0, 255)), (4, 0))
    assert _crop(desktop, (-4, 0, 4, 4), (-4, 0)).getpixel((0, 0)) == (255, 0, 0), \
        'the monitor at a negative x reads as the left half'
    assert _crop(desktop, (0, 0, 4, 4), (-4, 0)).getpixel((0, 0)) == (0, 0, 255), \
        'and the one at x=0 reads as the right half, not off the left edge'
    assert _crop(desktop, (2, 1, 3, 2), (-4, 0)).size == (3, 2), 'and the size is what was asked'

    # overlap(), which is how the Tarkov window gets clipped to the chosen monitor.
    assert overlap((0, 0, 100, 100), (50, 50, 100, 100)) == (50, 50, 50, 50), 'the shared corner'
    assert overlap((0, 0, 100, 100), (0, 0, 100, 100)) == (0, 0, 100, 100), 'identical rects'
    assert overlap((0, 0, 1920, 1080), (-1920, 0, 1920, 1080)) is None, 'side by side, touching'
    assert overlap((0, 0, 10, 10), (100, 100, 10, 10)) is None, 'nowhere near each other'
    assert overlap((-1920, 0, 1920, 1080), (-1920, -1, 1920, 1080)) == (-1920, 0, 1920, 1079), \
        'a window one pixel off its monitor still overlaps almost all of it'

    use(AUTO)
    grabbed = grab()
    assert grabbed.size == size(), f'a bare grab is the whole monitor, {grabbed.size} != {size()}'
    part = grab((rect()[0] + 4, rect()[1] + 6, 20, 10))
    assert part.size == (20, 10), f'a region grab is exactly that region, {part.size}'

    # fast_grab against grab(), which is the only thing that says the BitBlt geometry is right.
    # Pixels are not compared: the screen moves between the two, and they are known to disagree
    # slightly anyway (see fast_grab). Size and placement are what would break silently.
    box = (rect()[0] + 40, rect()[1] + 30, 64, 48)
    quick = fast_grab(box)
    assert quick.size == (64, 48), f'fast_grab returned {quick.size}'
    assert quick.mode == 'RGB', quick.mode
    assert fast_grab(rect()).size == size(), 'a whole monitor comes back whole'
    # Off the left of the primary is where a BGRX or an origin mistake would show up, since
    # BitBlt takes screen coordinates and Pillow does not.
    left_edge = (virtual_origin()[0], rect()[1], 16, 16)
    assert fast_grab(left_edge).size == (16, 16), 'the far left of the desktop is reachable'

    watch()
    watch()  # a second call must not wrap the wrapper
    shot = pyautogui.screenshot(region=(rect()[0], rect()[1], 8, 8))
    assert isinstance(shot, Image.Image) and shot.size == (8, 8), 'pyautogui.screenshot still works'
    print(f'ok, working monitor {current().label} at {rect()}')
