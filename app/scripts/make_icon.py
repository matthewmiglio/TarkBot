"""Rasterise gui/tarkbot.svg into gui/tarkbot.ico. Run after editing the svg.

    pip install cairosvg && python scripts/make_icon.py

The .ico is committed, so this is not part of the build: cairosvg pulls native cairo libs and
there is no reason for CI to carry them to regenerate a file that never changes.

Rendered from the vector at every size rather than downscaled from one big bitmap, because
the 16x16 Windows puts in the taskbar is where a bad resize shows first.
"""
import io
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).parent.parent
SVG = ROOT / 'gui' / 'tarkbot.svg'
ICO = ROOT / 'gui' / 'tarkbot.ico'
SIZES = [16, 24, 32, 48, 64, 128, 256]  # 256 is the largest an ICO can hold


def render(size):
    png = cairosvg.svg2png(url=str(SVG), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert('RGBA')


if __name__ == '__main__':
    frames = [render(size) for size in SIZES]
    frames[-1].save(ICO, format='ICO', sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
    written = Image.open(ICO).ico.sizes()
    assert {(16, 16), (256, 256)} <= written, f'missing a frame, got {sorted(written)}'
    print(f'{ICO}  {ICO.stat().st_size} bytes  {sorted(written)}')
