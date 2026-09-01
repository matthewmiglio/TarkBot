"""Read every collected price fixture and check it against its filename.

App layer: interact/ocr.py's price reader (ocr.read_number) against the committed corpus in
tests/fixtures/prices/. This is ocr.py's regression net.

Run:  python tests/detection/test_price_corpus.py

NO GAME needed: a pure fixture test, reading pngs off disk. Each file in fixtures/prices is
named for the number it shows, so 30999.png must read as 30999. Exits non-zero if any of them
misses, which is the whole point: a price reader that is right most of the time is a way to
lose money slowly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import Image  # noqa: E402

from interact import ocr  # noqa: E402

PRICES = Path(__file__).resolve().parents[1] / 'fixtures' / 'prices'


def truth(path):
    """The ground truth baked into the filename: 177777__2.png -> 177777."""
    return int(path.stem.split('__')[0])


if __name__ == '__main__':
    fixtures = sorted(PRICES.glob('*.png'), key=truth)
    if not fixtures:
        sys.exit(f'no fixtures in {PRICES}, collect some with tests/capture_price.py')

    failed = []
    for path in fixtures:
        want = truth(path)
        got = ocr.read_number(Image.open(path))
        ok = got == want
        print(f'{path.name:<20} truth {want:<10} read {str(got):<10} {"ok" if ok else "WRONG"}')
        if not ok:
            failed.append(path.name)

    print(f'\n{len(fixtures) - len(failed)}/{len(fixtures)} correct')
    if failed:
        sys.exit(f'FAILED: {", ".join(failed)}')
