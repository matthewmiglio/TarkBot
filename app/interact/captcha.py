"""Solve Tarkov's flea SECURITY CHECK captcha: read what it asks for, click those tiles, CONFIRM.

The modal says "Confirm that you are not a bot. You must choose all: <item>" over a grid of item
icons. solve(region) does the whole thing once on the live screen and says whether the modal
went away. Built and measured in _snipebot_captcha_debugging/ (solve_captcha.py, tests/e2e.py),
moved here so the sniper can solve a captcha and carry on instead of ending the run.

Four steps, each refusing rather than guessing, because a wrong click fails the captcha and a
refusal only costs what a captcha always cost before this existed (the run ends):
    1. modal     border_region: the SECURITY CHECK title and CONFIRM button are the anchors, the
                 modal's thin grey frame is the edge, scanned out from the button
    2. target    item_name_region finds the name line under "You must choose all:", and
                 captcha_name reads it and snaps it to a corpus name, or answers None
    3. tiles     the tile detector (captcha_data/tiles.onnx, a YOLO11n exported from the debug
                 folder's tiles_fixtures run) asked about the target class alone, then any box the
                 wrong shape for that item is dropped (footprints.json)
    4. clicks    each tile's centre, top to bottom and left to right, then CONFIRM; then look again

Everything is worked in a frame scaled to 1080 tall, the size the anchor crops were cut at, and
mapped back by native/1080 for the clicks, so it holds at 1080p and 1440p alike.

Self-check, against saved frames when the debug folder is there:  python -m interact.captcha
"""
import ast
import json
import re
import time
from pathlib import Path

import numpy as np
import pyautogui
from PIL import ImageOps

import screen
from interact import captcha_name, find, sell
from narrate import log

DATA = Path(__file__).resolve().parent / 'captcha_data'
MODEL = DATA / 'tiles.onnx'
FOOTPRINTS = DATA / 'footprints.json'

NAME_LABEL = 'captcha/you_must_select_all'
BANNER_RGB = (4, 21, 41)   # the modal banner behind the text
BANNER_TOL = 16            # per-channel; the banner also renders as (0, 16, 36) on some frames
BLACK_MAX = 10             # a pixel this dark on every channel is the gap under the banner
MAX_DROP = 80              # give up scanning down after this many rows (1080-space)

FRAME_RGB = (88, 93, 96)   # the modal's thin rounded-rect frame; the edge the scan stops on
FRAME_TOL = 8              # per-channel, tight so the darker [73,81,84] interior lines are excluded
LINE_FRAC = 0.4            # an edge must be frame-colour for this fraction of the modal's span

IMGSZ = 960         # the detector's input, ~2x the modal width so each ~60px tile has pixels
TARGET_CONF = 0.02  # low on purpose: a missed target tile fails the captcha, while a spurious box
                    # is only asked about the target, so it cannot click some other item. Measured
                    # in the debug folder: 0.08 left frame 29 with zero target tiles, 0.02 found it
NMS_IOU = 0.5
PAD = 114           # the grey ultralytics letterboxes with; the model was trained against it
STRIDE = 32         # the detector's coarsest grid; its input sides must be multiples of this
CELL_PX = 63.5      # icon pixels per grid cell, the rule footprints.json was built with
SHAPE_TOL = 0.35    # allowed relative error on a box's height/width against the item's
FORBIDDEN = re.compile(r'[<>:"/\\|?*]')  # what a class name (an icon filename) cannot hold

CLICK_GAP = 0.35   # seconds between tile clicks, so each registers before the next
SETTLE = 2.0       # seconds after CONFIRM before looking whether the modal went away

_model = None       # (InferenceSession, {class name: index}), built on the first captcha


def to_1080(frame):
    if frame.height == 1080:
        return frame
    return frame.resize((round(frame.width * 1080 / frame.height), 1080))


def _find(name, frame1080):
    """find.find on a 1080-tall frame, with the references used at the size they were cut.

    find.scale() reads the live screen and resizes every reference to it, which is right for a
    screen grab and wrong for a frame already scaled to 1080.
    ponytail: swaps the module function for the call; one bot thread does all the matching.
    """
    real = find.scale
    find.scale = lambda: 1.0
    try:
        return find.find(name, haystack=frame1080)
    finally:
        find.scale = real


def _is_frame(px):
    return all(abs(int(px[i]) - FRAME_RGB[i]) <= FRAME_TOL for i in range(3))


def border_region(native):
    """The modal as (left, top, width, height) in `native`'s own pixels, or None.

    None when no captcha is up or an edge could not be found, never a guessed edge. The scan runs
    on the native frame, where the 1-2px frame line is crisp; it blurs under downscaling.
    """
    f1080 = to_1080(native)
    title = _find(sell.CAPTCHA_TITLE_TARGET, f1080)
    confirm = _find(sell.CAPTCHA_CONFIRM_TARGET, f1080)
    if confirm and not title:
        # Caught mid fade-in, the dimmed title bar drops under its bar while the chunkier CONFIRM
        # still clears its own. Stretching the levels puts it back (the debug folder's frame 49);
        # only tried once the button has said a modal is there, so it cannot invent one.
        title = _find(sell.CAPTCHA_TITLE_TARGET, ImageOps.autocontrast(f1080, cutoff=2))
    if not title or not confirm:
        return None
    s = native.height / 1080.0
    a = np.asarray(native)
    h, w = a.shape[:2]
    cx = int((confirm.left + confirm.width / 2) * s)  # scan origin: the button's centre column
    top = int(title.top * s)
    start = int((confirm.top + confirm.height) * s)   # scan the bottom frame from below the button

    span = start - top
    col_line = lambda x: sum(_is_frame(a[y][x]) for y in range(top, start)) >= LINE_FRAC * span  # noqa: E731

    def scan_x(step):
        x = cx
        while 0 < x < w - 1 and not col_line(x):
            x += step
        return x if col_line(x) else None

    left, right = scan_x(-1), scan_x(+1)
    if left is None or right is None or right - left < 1:
        return None
    width = right - left
    row_line = lambda y: sum(_is_frame(a[y][x]) for x in range(left, right)) >= LINE_FRAC * width  # noqa: E731
    y = start
    while y < h - 1 and not row_line(y):
        y += 1
    if not row_line(y):
        return None
    return (left, top, width + 1, y - top + 1)


def region_1080(native):
    """The modal in 1080-normalised coords, or None if no captcha is up."""
    nat = border_region(native)
    if nat is None:
        return None
    s = native.height / 1080.0
    return tuple(round(v / s) for v in nat)


def item_name_region(frame1080):
    """(left, top, width, height) around the target item's name, or None.

    The "You must choose all:" label above it is fixed, so it is matched; the name changes every
    time, so it is found by geometry: down the label's centre column to the black gap above the
    grid, and out sideways while a column still holds banner blue.
    """
    label = _find(NAME_LABEL, frame1080)
    if not label:
        return None
    a = np.asarray(frame1080)
    h, w = a.shape[:2]
    top = label.top + label.height
    cx = label.left + label.width // 2
    if not 0 <= top < h:
        return None
    y = top
    while y < min(h, top + MAX_DROP) and a[y][cx].max() > BLACK_MAX:
        y += 1
    if y >= min(h, top + MAX_DROP):
        return None
    bottom = y
    band = (np.abs(a[top:bottom].astype(int) - np.array(BANNER_RGB)) <= BANNER_TOL).all(-1)
    if not band.any():
        return None
    x = cx
    while x > 0 and band[:, x - 1].any():
        x -= 1
    left = x
    x = cx
    while x < w - 1 and band[:, x + 1].any():
        x += 1
    return (left, top, x - left + 1, bottom - top)


def _session():
    """The detector and its class index, loaded once. onnxruntime is imported here, not at the
    top, so a run that never meets a captcha never pays for it."""
    global _model
    if _model is None:
        import onnxruntime
        sess = onnxruntime.InferenceSession(str(MODEL), providers=['CPUExecutionProvider'])
        names = ast.literal_eval(sess.get_modelmeta().custom_metadata_map['names'])
        _model = sess, {FORBIDDEN.sub('_', v): int(k) for k, v in names.items()}
    return _model


_shapes = None


def plausible(name, box_w, box_h):
    """Could a box this shape hold `name`? True for an unknown class, so this only ever removes
    a detection it can positively refute. It is what tells WD-40 (100ml), one cell, from the
    identical-looking (400ml), two cells tall."""
    global _shapes
    if _shapes is None:
        _shapes = json.loads(FOOTPRINTS.read_text(encoding='utf-8'))
    allowed = _shapes.get(FORBIDDEN.sub('_', name).strip())
    if not allowed or box_w <= 0 or box_h <= 0:
        return True
    got = box_h / box_w
    return any(abs(got - rows / cols) <= SHAPE_TOL * (rows / cols) for cols, rows in allowed)


def target_tiles(crop, said):
    """Boxes (x0, y0, x1, y1) in `crop`'s pixels where the detector puts item `said`.

    Reproduces the debug folder's ultralytics target pass (predict with classes=[target],
    conf=TARGET_CONF), which tests/onnx_parity.py checks over every saved frame: the same
    letterbox (scaled to fit IMGSZ, padded to a STRIDE multiple with PAD grey), the same
    best-class filter, the same NMS.
    """
    import cv2
    sess, index = _session()
    cls = index.get(FORBIDDEN.sub('_', said))
    if cls is None:
        return []
    w, h = crop.size
    r = min(IMGSZ / w, IMGSZ / h)
    nw, nh = round(w * r), round(h * r)
    # Padded only up to the next multiple of STRIDE, not out to a square: ultralytics' own
    # inference pads this way, and at TARGET_CONF the difference matters. Padding to 960x960
    # instead found up to 7 'target' tiles where the model, fed as trained, found 3.
    px, py = (IMGSZ - nw) % STRIDE / 2, (IMGSZ - nh) % STRIDE / 2
    top, left = round(py - 0.1), round(px - 0.1)
    canvas = np.full((nh + top + round(py + 0.1), nw + left + round(px + 0.1), 3), PAD, np.uint8)
    canvas[top:top + nh, left:left + nw] = cv2.resize(np.asarray(crop), (nw, nh),
                                                      interpolation=cv2.INTER_LINEAR)
    x = canvas.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]   # (4 + classes, anchors)
    # A box is the target's when the target is its best class, at the low TARGET_CONF bar. That
    # is what ultralytics' class-filtered predict does (filter by class after the argmax), and
    # it is what every measurement in the debug folder was taken with. Taking any box whose
    # target score clears the bar instead, whatever it scored best as, added up to 4 wrong tiles
    # a frame on 5 of 172 frames (frame 96: 7 'morphine injectors' against 3).
    scores = out[4 + cls]
    keep = np.flatnonzero((out[4:].argmax(0) == cls) & (scores > TARGET_CONF))
    if not len(keep):
        return []
    cx, cy, bw, bh = out[:4, keep]
    rects = np.stack([cx - bw / 2, cy - bh / 2, bw, bh], 1)
    picked = cv2.dnn.NMSBoxes(rects.tolist(), scores[keep].tolist(), TARGET_CONF, NMS_IOU)
    boxes = []
    for i in np.array(picked).flatten():
        x0, y0, bw_, bh_ = rects[i]
        b = ((x0 - left) / r, (y0 - top) / r, (x0 + bw_ - left) / r, (y0 + bh_ - top) / r)
        if plausible(said, b[2] - b[0], b[3] - b[1]):
            boxes.append(b)
    return boxes


def plan(native, templates=None, names=None):
    """(said, [tile points], confirm point, note) for a frame, points in its own pixels.

    said is None, or the tile list empty, when there is nothing safe to click; note says why.
    """
    region = region_1080(native)
    if region is None:
        return None, [], None, 'no captcha on screen'
    frame = to_1080(native)
    s = native.height / 1080.0
    box = item_name_region(frame)
    if box is None:
        return None, [], None, 'the item name line was not found'
    read = captcha_name.pattern(frame, box, templates or captcha_name.load())
    said = captcha_name.snap(read, names or captcha_name.corpus_names()) if read else None
    if said is None:
        return None, [], None, f'could not read the target (read {read!r})'
    l, t, w, h = region
    boxes = target_tiles(frame.crop((l, t, l + w, t + h)), said)
    # Top to bottom, left to right: the order a person would click.
    boxes.sort(key=lambda b: (round(b[1] / 32), b[0]))
    tiles = [(round((l + (b[0] + b[2]) / 2) * s), round((t + (b[1] + b[3]) / 2) * s))
             for b in boxes]
    confirm = _find(sell.CAPTCHA_CONFIRM_TARGET, frame)
    if confirm is None:
        return said, [], None, 'the CONFIRM button was not found'
    ok = (round((confirm.left + confirm.width / 2) * s),
          round((confirm.top + confirm.height / 2) * s))
    if not tiles:
        return said, [], ok, f'no {said!r} tile found'
    return said, tiles, ok, f'asks for {said!r}, {len(tiles)} tiles'


def solve(region):
    """One attempt at the captcha on screen in `region`. True if the modal went away after it.

    Nothing is clicked unless the target was read and at least one of its tiles found. One try
    only, by design: a failed captcha on a watched account is worse than ending the run.
    """
    left, top = region[0], region[1]
    native = screen.grab(region).convert('RGB')
    said, tiles, confirm, note = plan(native)
    log(f'captcha: {note}')
    if not tiles or confirm is None:
        return False
    for x, y in tiles:
        pyautogui.click(left + x, top + y)
        time.sleep(CLICK_GAP)
    log(f'captcha: clicked {len(tiles)} {said!r} tiles, confirming', 1)
    pyautogui.click(left + confirm[0], top + confirm[1])
    time.sleep(SETTLE)
    if region_1080(screen.grab(region).convert('RGB')) is None:
        log('captcha: solved, the modal is gone')
        return True
    log('captcha: still up after CONFIRM, so that answer was refused')
    return False


if __name__ == '__main__':
    from PIL import Image
    frames = Path(__file__).resolve().parents[2] / '_snipebot_captcha_debugging' / 'frames'
    expect = {'168': ('WD-40 (100ml)', 2), '169': ('Antique teapot', 2),
              '170': ('Aseptic bandage', 3), '45': ('Pack of sugar', 2), '29': ('Zibbo lighter', 2)}
    if not frames.exists():
        print(f'no saved frames at {frames}, nothing to check against')
    for stem, (name, n) in expect.items():
        p = frames / f'{stem}.png'
        if not p.exists():
            continue
        said, tiles, confirm, note = plan(Image.open(p).convert('RGB'))
        print(f'{stem}: {note}, confirm at {confirm}')
        assert said == name and len(tiles) == n and confirm, f'frame {stem}: {note}'
    print('ok')
