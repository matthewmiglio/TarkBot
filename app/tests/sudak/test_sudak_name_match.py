"""Tune the sudak item-name detection: score every sudak reference against every quest fixture,
inside the item-name search region, and report the gap between true matches (a reference against
its own item's fixture) and false ones (against any other item). No game needed.

The references are matched through the shipping find.best_score, grown by needle() to each
fixture's resolution exactly as a live screen would, so the numbers are the ones find() would judge.

    python tests/sudak/test_sudak_name_match.py       # from the app/ directory
"""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from interact import find  # noqa: E402

REGION_1080 = (552, 577, 1919, 703)  # item-name search region in 1080p screen pixels (L,T,R,B)
# The threshold sudak detection should hold a craftable-item name match to. The full objective-line
# crop shares its prefix with every other offer, so a wrong item still matches up to 0.900; the
# right item matches 0.990 (both resolutions, honest 1080p captures included). 0.95 sits in that
# gap with ~0.05 margin each side. The wd_40_400ml decoy reads 0.871 against the wd_40_100ml ref,
# so the 100ml/400ml confusion the old tight-crop fought is clear of 0.95 outright.
SUDAK_CONFIDENCE = 0.95
FIX = Path(__file__).resolve().parents[1] / 'fixtures' / 'sudak_quests'
SUDAK = find.REFS / 'sudak'
REFS = sorted(d.name for d in SUDAK.iterdir() if d.is_dir())  # 23 craftable slugs
CRAFTABLE = set(REFS)


def scaled_region(h):
    f = h / 1080
    l, t, r, b = REGION_1080
    return (round(l * f), round(t * f), round(r * f), round(b * f))


def score_fixture(path):
    from PIL import Image
    img = Image.open(path).convert('RGB')
    h = img.height
    find.scale = lambda: h / 1080            # make needle() grow refs to this fixture's resolution
    find._resized.cache_clear()
    hay = img.crop(scaled_region(h))
    return {slug: find.best_score(f'sudak/{slug}', haystack=hay)[0] for slug in REFS}


def main():
    rows = []  # (resolution, fixture_slug, is_craftable, scores dict)
    for folder in ('1080p', '1440p'):
        for fp in sorted((FIX / folder).glob('*.png')):
            rows.append((folder, fp.stem, score_fixture(fp)))

    tp, fp_scores = [], []     # true-positive and false-positive peak scores
    tp_1080 = []               # honest TPs only (refs are not cut from the 1080p captures)
    print(f'{"fixture":34s} {"res":5s} {"own":>6s}  top false match')
    print('-' * 78)
    for res, slug, scores in rows:
        own = scores.get(slug) if slug in CRAFTABLE else None
        others = {s: v for s, v in scores.items() if s != slug}
        fsl, fsc = max(others.items(), key=lambda kv: kv[1])
        for s, v in others.items():
            fp_scores.append(v)
        if own is not None:
            tp.append(own)
            if res == '1080p':
                tp_1080.append(own)
        owns = f'{own:.3f}' if own is not None else '  -  '
        flag = '  <-- FALSE >= own' if (own is not None and fsc >= own) else ''
        print(f'{slug:34s} {res:5s} {owns:>6s}  {fsl:30s} {fsc:.3f}{flag}')

    print('-' * 78)
    print(f'true-positive  (own ref vs own item): min {min(tp):.3f}  n={len(tp)}')
    print(f'  of those, 1080p only (honest):      min {min(tp_1080):.3f}  n={len(tp_1080)}')
    print(f'false-positive (ref vs other item):   max {max(fp_scores):.3f}  n={len(fp_scores)}')
    print(f'\nGAP (honest TP floor - FP ceiling):   {min(tp_1080) - max(fp_scores):+.3f}')

    # Regression: SUDAK_CONFIDENCE must sit in the gap - every real match above it, every
    # look-alike below it. If a game update or a new reference closes the gap, this fails here.
    tp_fail = min(tp) < SUDAK_CONFIDENCE
    fp_fail = max(fp_scores) >= SUDAK_CONFIDENCE
    if tp_fail or fp_fail:
        if tp_fail:
            print(f'FAIL: a true match ({min(tp):.3f}) fell below SUDAK_CONFIDENCE {SUDAK_CONFIDENCE}')
        if fp_fail:
            print(f'FAIL: a false match ({max(fp_scores):.3f}) reached SUDAK_CONFIDENCE {SUDAK_CONFIDENCE}')
        sys.exit(1)
    print(f'ok: SUDAK_CONFIDENCE {SUDAK_CONFIDENCE} separates all {len(tp)} true from all '
          f'{len(fp_scores)} false matches (margin {min(tp) - SUDAK_CONFIDENCE:+.3f} / '
          f'{SUDAK_CONFIDENCE - max(fp_scores):+.3f}).')


if __name__ == '__main__':
    main()
