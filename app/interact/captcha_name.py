"""Read the captcha's target item name off a frame, without an OCR engine.

The read path of _snipebot_captcha_debugging/name_reader.py, moved here so the shipped bot can
solve captchas. The debug folder keeps the labelling (KNOWN), the template harvest and the
held-out test, and imports everything below from here, so there is one reader, not two.

The target is always one of the corpus item names, so this is a closed-set lookup, not text
recognition. Two steps:

  1. **Segment.** The name sits on flat banner blue as bright text, so a column-brightness
     projection splits the strip into glyphs with no edge detection. Runs of "ink" columns are
     glyphs; a gap wider than SPACE_GAP is a word space rather than kerning.
  2. **Identify.** Each glyph is matched against every stored drawing of every character and
     takes the character whose closest drawing fits best, then the resulting pattern is snapped
     to the nearest corpus name. A run nothing fits whole is tried as two letters, because
     kerning fuses some pairs into a single run. The snap is the backstop: a glyph the templates
     do not cover becomes a wildcard. A tie, or a poor fit, answers None rather than guessing,
     which is what keeps 'WD-40 (100ml)' and 'WD-40 (400ml)' from being confused.

Data, all in captcha_data/: name_glyphs.npz (the harvested drawings, written by the debug
folder's `python name_reader.py --harvest`) and names.txt (every name the captcha can ask for,
generated from the debug folder's icon corpus).

# ponytail: binary masks and mean-absolute-difference, no classifier and no new dependency.
"""
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent / 'captcha_data'
GLYPHS = DATA / 'name_glyphs.npz'
NAMES = DATA / 'names.txt'
INK = 140       # a column holding a pixel this bright is part of a glyph, not banner background.
                # Measured: 140-180 all segment 23 of the 24 frames exactly. Lower fuses touching
                # letter pairs into one run (90 fused on 8 frames), higher eats the thin strokes
SPACE_GAP = 5   # blank columns between glyphs; wider than this is a word space, not kerning
MAX_GLYPH_COST = 0.22   # mean pixel disagreement above which a glyph is called unknown
MAX_SNAP_FRAC = 0.55    # reject the snap if the best name disagrees on more than this share of
                        # the glyphs. Every correct read disagrees on at most 0.47, every wrong
                        # one on 0.77 or more. Without it a name missing from the corpus snaps to a
                        # random same-length one instead of admitting it does not know
SHIFT = 2       # vertical slack when comparing two glyphs, in pixels
MIN_PART = 2    # a split piece narrower than this is a stray column, not a letter
SPLIT_DEPTH = 2 # how many letters a single fused run may be taken apart into; 0 disables it


def corpus_names():
    """Every item name the captcha can ask for."""
    return [ln for ln in NAMES.read_text(encoding='utf-8').splitlines() if ln]


def strip_of(frame1080, box):
    """The item-name strip at `box` (from captcha.item_name_region) as a binary ink mask."""
    left, top, width, height = box
    a = np.asarray(frame1080.crop((left, top, left + width, top + height)))
    return a.max(2) > INK


def segment(mask):
    """[(' ' or None, glyph_mask or None)] left to right; a ' ' entry marks a word space.

    Glyphs keep the strip's full height, so every template is the same height and comparing two
    is a straight overlay with no baseline maths.
    """
    ink = mask.any(0)
    runs, start = [], None
    for i, on in enumerate(ink):
        if on and start is None:
            start = i
        elif not on and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(ink)))

    out = []
    for i, (a, b) in enumerate(runs):
        if i and a - runs[i - 1][1] > SPACE_GAP:
            out.append((' ', None))
        out.append((None, mask[:, a:b]))
    return out


def _cost(a, b):
    """Mean pixel disagreement between two glyph masks, at the best vertical alignment.

    Widths are reconciled by padding. The vertical search matters: the strip's top edge comes
    from a template match, so it lands a pixel or two differently frame to frame, and without
    the slack that jitter reads as a shape difference (h for p, b for d).
    """
    if abs(a.shape[1] - b.shape[1]) > 2:        # widths this far apart are different glyphs
        return 1.0
    w = max(a.shape[1], b.shape[1])
    pa = np.pad(a, ((0, 0), (0, w - a.shape[1])))
    pb = np.pad(b, ((0, 0), (0, w - b.shape[1])))
    best = 1.0
    for dy in range(-SHIFT, SHIFT + 1):
        sa = np.roll(pa, dy, axis=0)
        if dy > 0:
            sa[:dy] = False
        elif dy < 0:
            sa[dy:] = False
        best = min(best, float((sa != pb).mean()))
    return best


def _best(g, templates):
    """(character, cost) for whichever stored drawing fits this run best."""
    return min(((k, min(_cost(g, t) for t in ts)) for k, ts in templates.items()),
               key=lambda kv: kv[1])


def _read_run(g, templates, depth=None):
    """The characters in one ink run. Usually one, but kerning fuses some pairs into a single run.

    A run only gets taken apart when nothing fits it whole. When it does, both halves have to
    match properly or the split is refused and the run stays a single '?': a bad guess at two
    letters is worse than an honest wildcard, since the wildcard still matches anything in the
    snap.
    """
    depth = SPLIT_DEPTH if depth is None else depth
    ch, cost = _best(g, templates)
    if cost <= MAX_GLYPH_COST or depth <= 0:
        return (ch if cost <= MAX_GLYPH_COST else '?'), cost
    best = None
    for cut in range(MIN_PART, g.shape[1] - MIN_PART + 1):
        left, right = g[:, :cut], g[:, cut:]
        if not left.any() or not right.any():
            continue
        lc, lcost = _best(left, templates)
        if lcost > MAX_GLYPH_COST:
            continue
        rtext, rcost = _read_run(right, templates, depth - 1)
        if '?' in rtext:
            continue
        pair = (max(lcost, rcost), lc + rtext)
        if best is None or pair < best:
            best = pair
    return ('?', cost) if best is None else (best[1], best[0])


def _join_ticks(chars):
    """Fold the tick runs back into real punctuation: two in a row is `"`, one alone is `'`.

    A double quote is drawn as two disconnected ticks and segments as two runs, so the tick is
    the template and the count decides the mark. Both are in the corpus: `"` in the Gunpowder
    names, `'` in "Tagilla's welding mask".
    """
    out, i = [], 0
    while i < len(chars):
        pair = chars[i] == '"' and i + 1 < len(chars) and chars[i + 1] == '"'
        out.append('"' if pair else ("'" if chars[i] == '"' else chars[i]))
        i += 2 if pair else 1
    return ''.join(out)


def load(path=GLYPHS):
    """{character: [glyph masks]} from the harvested templates."""
    z = np.load(path)
    out = {}
    for k in z.files:                       # '<hex>__<n>': many drawings per character
        out.setdefault(chr(int(k.split('__')[0], 16)), []).append(z[k])
    return out


def pattern(frame1080, box, templates):
    """The name in the strip at `box` as read, with '?' for any glyph no template matches."""
    out = []
    for c, g in segment(strip_of(frame1080, box)):
        if c == ' ':
            out.append(' ')
            continue
        out.extend(_read_run(g, templates)[0])
    return _join_ticks(out)


def snap(pat, names):
    """The corpus name a pattern reads as, or None if nothing is close enough.

    '?' matches any character; otherwise the best name is the one differing in fewest places. A
    tie means the read is genuinely ambiguous, so it answers None rather than guessing.
    """
    same = [n for n in names if len(n) == len(pat)]
    if not same:
        return None
    scored = sorted((sum(p != '?' and p != c for p, c in zip(pat, n)), n) for n in same)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None                                  # two names fit equally well: genuinely unsure
    if scored[0][0] > MAX_SNAP_FRAC * len(pat):
        return None                                  # nothing in the corpus is close to this read
    return scored[0][1]


if __name__ == '__main__':
    names = corpus_names()
    assert snap('WD-40 (100ml)', names) == 'WD-40 (100ml)'
    assert snap('WD-40 (?00ml)', names) is None, '100ml and 400ml tie, so no guess'
    assert snap('WD-40 (t00ml)', names) is None, 'a misread digit that fits neither is no answer'
    assert snap('Anrique roapot', names) == 'Antique teapot', 'a couple of misread letters snap'
    assert _join_ticks(list('Gunpowder ""Eagle""')) == 'Gunpowder "Eagle"'
    assert load(), 'the glyph templates load'
    print(f'ok, {len(names)} names, {len(load())} characters')
