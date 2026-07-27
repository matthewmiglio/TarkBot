"""Colours, fonts and the composited backdrop for the GUI.

tkinter widgets cannot be translucent, so the 'dirty glass' look is baked into a single
picture instead: the chosen background photo, blurred and dimmed, with the panel rectangles
alpha-composited onto it and the character pasted in. The app then draws its text straight
onto that image with canvas items, which do sit transparently over it.

Preview the backdrop without opening the GUI:  python -m gui.theme [background.png]
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

BACKGROUNDS = Path(__file__).parent / 'backgrounds'
CHARACTER = Path(__file__).parent / 'poster_character.png'
# Window and taskbar icon, also the exe's. Rendered from tarkbot.svg beside it, which is the
# source: redraw the svg and re-run scripts/make_icon.py rather than editing the ico.
ICON = Path(__file__).parent / 'tarkbot.ico'

WINDOW = (940, 600)

# Muted, matte, nothing pure white. Values darker than the text they carry.
INK = '#d8d7d2'        # primary text
INK_DIM = '#8f928f'    # labels and secondary text
INK_FAINT = '#5c5f5c'  # separators and disabled text
LINE = '#3b3d3b'       # panel borders and rules
PLATE = '#1d1f20'      # button faces
PLATE_HOT = '#2b2e2f'  # button under the cursor
RUNNING = '#6f8e58'
WARNING = '#b56d43'
ERROR = '#944848'
STOPPED = '#6d706d'
CLOSE = '#8a4a4a'      # the close X, dim until hovered
CLOSE_HOT = '#d05a5a'

# Our own title bar, since the system one is gone. Darker than anything below it, so it reads
# as chrome rather than as part of the app.
TITLEBAR = 30
TITLEBAR_BG = '#0d0e0d'

BLUR = 4  # how far out of focus the background photo goes
DIM = 0.5  # what fraction of the photo's brightness survives the wash

# Panel rectangles as (left, top, right, bottom), in window coordinates
HEADER = (0, 0, WINDOW[0], 58)
CHARACTER_PANEL = (24, 76, 436, 500)
STATUS_PANEL = (452, 76, 916, 500)
FOOTER_RULE = 516

GLASS = (12, 12, 12, 186)  # panel fill, over the dimmed photo
GLASS_EDGE = (72, 74, 72, 255)

# Windows ships Bahnschrift, which is a DIN condensed and exactly the right register. The
# rest are fallbacks for a machine that does not have it.
FONT_STACK = ('Bahnschrift SemiCondensed', 'Bahnschrift', 'Segoe UI Semilight', 'Segoe UI')


def font_family(root):
    """The first font in the stack this machine actually has."""
    from tkinter import font as tkfont

    available = {name.lower() for name in tkfont.families(root)}
    for name in FONT_STACK:
        if name.lower() in available:
            return name
    return 'TkDefaultFont'


def backgrounds():
    """Every background png on disk, by filename, sorted. Empty list if the folder is gone."""
    return sorted(path.name for path in BACKGROUNDS.glob('*.png')) if BACKGROUNDS.is_dir() else []


def _cover(image, size):
    """Scale and centre-crop image to exactly fill size, the way a CSS cover background does."""
    scale = max(size[0] / image.width, size[1] / image.height)
    scaled = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                          Image.LANCZOS)
    left, top = (scaled.width - size[0]) // 2, (scaled.height - size[1]) // 2
    return scaled.crop((left, top, left + size[0], top + size[1]))


def _trim(image, floor=64):
    """Crop away the dark painted margin around the character so he fills his panel.

    The art is a figure on a dark gradient, not a cutout, so there is no alpha to trim
    against. Anything brighter than floor counts as subject.
    """
    lit = image.convert('L').point(lambda value: 255 if value > floor else 0)
    box = lit.getbbox()
    return image.crop(box) if box else image


def _feathered(image, size, fade=90):
    """Fit image into size and fade its edges out, so its rectangle dissolves into the panel.

    The character art has a dark painted background rather than transparency, which would
    otherwise read as an obvious box sat on the glass.
    """
    image = _trim(image).convert('RGBA')
    image.thumbnail(size, Image.LANCZOS)
    mask = Image.new('L', image.size, 0)
    inset = min(fade, image.width // 2 - 1, image.height // 2 - 1)
    ImageDraw.Draw(mask).rectangle((inset, inset, image.width - inset, image.height - inset),
                                   fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(fade / 2))
    image.putalpha(mask)
    return image


def backdrop(background_name, size=WINDOW):
    """The whole static chrome as one RGB image: photo, wash, panels, rules and character."""
    base = Image.new('RGB', size, '#101110')
    path = BACKGROUNDS / background_name
    if path.is_file():
        photo = _cover(Image.open(path).convert('RGB'), size)
        photo = photo.filter(ImageFilter.GaussianBlur(BLUR))
        base = Image.blend(base, photo, DIM)  # dim by mixing toward near black, not by alpha

    glass = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glass)
    draw.rectangle(HEADER, fill=(10, 10, 10, 214))
    for panel in (CHARACTER_PANEL, STATUS_PANEL):
        draw.rectangle(panel, fill=GLASS, outline=GLASS_EDGE, width=1)
    draw.line((HEADER[0], HEADER[3], HEADER[2], HEADER[3]), fill=GLASS_EDGE, width=1)
    draw.line((24, FOOTER_RULE, size[0] - 24, FOOTER_RULE), fill=(72, 74, 72, 140), width=1)
    base = Image.alpha_composite(base.convert('RGBA'), glass)

    if CHARACTER.is_file():
        left, top, right, bottom = CHARACTER_PANEL
        art = _feathered(Image.open(CHARACTER), (right - left + 40, bottom - top - 20))
        base.alpha_composite(art, (left + (right - left - art.width) // 2,
                                   top + (bottom - top - art.height) // 2))
    return base.convert('RGB')


if __name__ == '__main__':
    import sys

    names = backgrounds()
    if not names:
        sys.exit(f'no backgrounds in {BACKGROUNDS}')
    chosen = sys.argv[1] if len(sys.argv) > 1 else names[0]
    out = Path(__file__).resolve().parent.parent / 'tests' / 'output' / 'gui_backdrop.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    backdrop(chosen).save(out)
    print(f'backgrounds: {", ".join(names)}')
    print(f'wrote {out} using {chosen}')
