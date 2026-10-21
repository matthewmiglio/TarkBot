"""Colors, fonts and the composited backdrop for the GUI.

tkinter widgets cannot be translucent, so the 'dirty glass' look is baked into a single
picture instead: the chosen background photo, blurred and dimmed, with the panel rectangles
alpha-composited onto it and the character pasted in. The app then draws its text straight
onto that image with canvas items, which do sit transparently over it.

Preview the backdrop without opening the GUI:  python -m gui.theme [background.png]
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BACKGROUNDS = Path(__file__).parent / 'backgrounds'
# One figure per mode, named for its tab key: characters/flea.png, characters/gym.png. A new
# mode drops its png in beside them and needs no change here.
CHARACTERS = Path(__file__).parent / 'characters'
# Window and taskbar icon, also the exe's. Rendered from tarkbot.svg beside it, which is the
# source: redraw the svg and re-run scripts/make_icon.py rather than editing the ico.
ICON = Path(__file__).parent / 'tarkbot.ico'

# 34 taller than it was for the header's second dropdown row, and 30 taller again for the
# boxed activity line under the buttons. Only the bottom band grows: every panel below is
# positioned from the top, so nothing above the footer moves.
WINDOW = (940, 664)

# Muted, matte, nothing pure white. Values darker than the text they carry.
INK = '#d8d7d2'        # primary text
INK_DIM = '#8f928f'    # labels and secondary text
INK_FAINT = '#5c5f5c'  # separators and disabled text
LINE = '#3b3d3b'       # panel borders and rules
PLATE = '#1d1f20'      # button faces
PLATE_HOT = '#2b2e2f'  # button under the cursor
GOLD = '#c9a227'       # the selected tab's glow: outline and label
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

# Panel rectangles as (left, top, right, bottom), in window coordinates. The header carries two
# rows of dropdowns, so everything below it sits 34px lower than it did with one.
HEADER = (0, 0, WINDOW[0], 92)
CHARACTER_PANEL = (24, 110, 436, 534)
STATUS_PANEL = (452, 110, 916, 534)
FOOTER_RULE = 550

GLASS = (12, 12, 12, 186)  # panel fill, over the dimmed photo
GLASS_EDGE = (72, 74, 72, 255)

# Windows ships Bahnschrift, which is a DIN condensed and exactly the right register. The
# rest are fallbacks for a machine that does not have it.
FONT_STACK = ('Bahnschrift SemiCondensed', 'Bahnschrift', 'Segoe UI Semilight', 'Segoe UI')

# One speech bubble per mode, the character telling the user how to get it going. Baked into the
# backdrop like the character, so it is anti-aliased and costs the canvas nothing.
# tab -> (text, (left, top) of the bubble, its width, (x, y) the tail points at), window coords,
# all inside CHARACTER_PANEL. The tail points at the figure's mouth, or near enough.
TIPS = {
    'flea': ('Put your scav cases at the top of your inventory to sell from those too!',
             (250, 140), 170, (214, 196)),
    'snipe': ('I look for cheap items on the flea to sell back to traders!',
              (262, 112), 150, (232, 176)),
    'gym': ('Start the gym bot, and Reshala will lift for you!',
            (296, 196), 134, (272, 252)),
    'crafts': ('Jaeger crafts for you! Tick which crafts to run.',
               (288, 168), 152, (264, 262)),
    'dailies': ("Start on Ragman's task screen with the Sudak task showing. I'll swap until "
                'the WD-40 task appears!', (236, 146), 190, (212, 216)),
}
# Px to slide each tab's figure sideways from centre, negative is left, to open up room on the
# right for its bubble. A tab not listed stays centred. Its TIPS tail point slides with it, so
# the tail keeps pointing at the same spot on the figure.
CHARACTER_SHIFT = {'flea': -60, 'gym': -25, 'crafts': -25, 'dailies': -25}
BUBBLE_FILL = (233, 229, 216)  # warm off-white, matte, not pure white
BUBBLE_INK = (28, 29, 28)
BUBBLE_EDGE = (10, 11, 10)
BUBBLE_TEXT = 13  # px
BUBBLE_PAD = (12, 9)  # px inside the bubble, x and y
BUBBLE_RADIUS = 13
BUBBLE_TAIL = 16  # px the tail sticks out past the bubble's edge, at most
SUPERSAMPLE = 4  # drawn this many times larger and shrunk, which is all the anti-aliasing PIL does


def lighter(color, amount=0.18):
    """A '#rrggbb' blended toward white, for the hover face of a button that carries a color.

    PLATE_HOT is only the hover for the default face; the run button has three of its own.
    """
    channels = (int(color[at:at + 2], 16) for at in (1, 3, 5))
    return '#%02x%02x%02x' % tuple(round(v + (255 - v) * amount) for v in channels)


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
    """Crop away the margin around the character so he fills his panel.

    Alpha decides that when the art has any, brightness when it does not. The three figures
    shipped today are cutouts, but they still carry colour underneath the transparency, up to
    (204, 189, 162) on snipe.png, so reading brightness through the alpha put 269k invisible
    pixels over the floor and stretched the box out to most of the sheet.
    """
    channel = image.getchannel('A') if 'A' in image.getbands() else image.convert('L')
    box = channel.point(lambda value: 255 if value > floor else 0).getbbox()
    return image.crop(box) if box else image


def _feathered(image, size, fade=90):
    """Fit image into size and fade its edges out, so its rectangle dissolves into the panel.

    Art with a painted background reads as an obvious box sat on the glass without this. Art
    that is already a cutout keeps its own transparency: the feather is multiplied into the
    alpha rather than put in its place. Replacing it made every transparent pixel opaque, and
    since these files keep real colour under the transparency, the ones that were not quite
    black came back as a scatter of dots around the figure.
    """
    image = _trim(image).convert('RGBA')
    image.thumbnail(size, Image.LANCZOS)
    mask = Image.new('L', image.size, 0)
    inset = min(fade, image.width // 2 - 1, image.height // 2 - 1)
    ImageDraw.Draw(mask).rectangle((inset, inset, image.width - inset, image.height - inset),
                                   fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(fade / 2))
    image.putalpha(ImageChops.multiply(mask, image.getchannel('A')))
    return image


def _bubble_font(px):
    """Bahnschrift SemiBold SemiCondensed at px, to match the GUI's own text, else Segoe UI."""
    try:
        font = ImageFont.truetype('bahnschrift.ttf', px)
        try:
            font.set_variation_by_name('SemiBold SemiCondensed')
        except (OSError, ValueError):
            pass  # a Pillow or FreeType without variable font support: plain Bahnschrift
        return font
    except OSError:
        return ImageFont.truetype('segoeui.ttf', px)


def _wrap(text, font, width):
    """text broken into lines no wider than width px in font, greedily by word."""
    lines = []
    for word in text.split():
        if lines and font.getlength(f'{lines[-1]} {word}') <= width:
            lines[-1] += f' {word}'
        else:
            lines.append(word)
    return lines


def _speech_bubble(base, text, corner, width, tip):
    """Composite a rounded speech bubble with a tail onto base (RGBA), in place.

    Drawn SUPERSAMPLE times larger then shrunk, since PIL's shapes have no anti-aliasing of their
    own. The outline is the filled shape grown by a couple of pixels and painted underneath, so
    the tail and the body share one edge with no seam where they join.
    """
    s = SUPERSAMPLE
    font = _bubble_font(BUBBLE_TEXT * s)
    pad_x, pad_y = BUBBLE_PAD
    lines = _wrap(text, font, (width - 2 * pad_x) * s)
    line_h = round(BUBBLE_TEXT * 1.3 * s)
    height = 2 * pad_y + (len(lines) * line_h) / s
    left, top = corner
    right, bottom = left + width, top + height

    margin = 14  # room for the shadow and the outline around the shape
    ox, oy = min(left, tip[0]) - margin, min(top, tip[1]) - margin
    size = (round((max(right, tip[0]) + margin - ox) * s), round((max(bottom, tip[1]) + margin - oy) * s))

    def at(x, y):
        return ((x - ox) * s, (y - oy) * s)

    # The tail leaves the side of the bubble nearest the tip, its root tucked inside the body. It
    # aims at tip but stops BUBBLE_TAIL px out from the bubble's edge, so it points at the face
    # without being drawn over it.
    root_y = min(max(tip[1], top + BUBBLE_RADIUS + 8), bottom - BUBBLE_RADIUS - 8)
    root_x = left + 10
    dx, dy = tip[0] - root_x, tip[1] - root_y
    reach = min(1.0, (10 + BUBBLE_TAIL) / max((dx * dx + dy * dy) ** 0.5, 1))
    tip = (root_x + dx * reach, root_y + dy * reach)
    tail = [at(root_x, root_y - 7), at(root_x, root_y + 5), at(*tip)]
    shape = Image.new('L', size, 0)
    draw = ImageDraw.Draw(shape)
    draw.rounded_rectangle((*at(left, top), *at(right, bottom)), BUBBLE_RADIUS * s, fill=255)
    draw.polygon(tail, fill=255)

    edge = shape.filter(ImageFilter.MaxFilter(2 * s + 1))  # 1px edge once shrunk
    shadow = edge.filter(ImageFilter.GaussianBlur(4 * s)).point(lambda v: v * 0.55)
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    layer.paste((0, 0, 0, 255), (2 * s, 3 * s), shadow.crop((0, 0, size[0] - 2 * s, size[1] - 3 * s)))
    layer.paste((*BUBBLE_EDGE, 255), (0, 0), edge)
    layer.paste((*BUBBLE_FILL, 255), (0, 0), shape)

    ink = ImageDraw.Draw(layer)
    for n, line in enumerate(lines):
        ink.text(at(left + pad_x, top + pad_y + n * line_h / s), line, font=font, fill=BUBBLE_INK)

    layer = layer.resize((round(size[0] / s), round(size[1] / s)), Image.LANCZOS)
    base.alpha_composite(layer, (round(ox), round(oy)))


def backdrop(background_name, tab='flea', size=WINDOW):
    """The whole static chrome as one RGB image: photo, wash, panels, rules and character.

    tab picks which figure goes in the character panel, so switching modes repaints it.
    """
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

    character = CHARACTERS / f'{tab}.png'
    shift = CHARACTER_SHIFT.get(tab, 0)
    if character.is_file():
        left, top, right, bottom = CHARACTER_PANEL
        art = _feathered(Image.open(character), (right - left + 40, bottom - top - 20))
        # Into a panel-sized layer first, so a figure slid sideways is clipped at the panel's
        # edge rather than spilling over its border onto the wash outside it.
        panel = Image.new('RGBA', (right - left, bottom - top), (0, 0, 0, 0))
        # paste, not alpha_composite: the art is wider than the panel, so its x is negative, which
        # alpha_composite refuses. Onto an empty layer the two give the same pixels.
        panel.paste(art, ((right - left - art.width) // 2 + shift, (bottom - top - art.height) // 2))
        base.alpha_composite(panel, (left, top))
    if tab in TIPS:
        text, corner, width, (tip_x, tip_y) = TIPS[tab]
        _speech_bubble(base, text, corner, width, (tip_x + shift, tip_y))
    return base.convert('RGB')


if __name__ == '__main__':
    import sys

    names = backgrounds()
    if not names:
        sys.exit(f'no backgrounds in {BACKGROUNDS}')
    chosen = sys.argv[1] if len(sys.argv) > 1 else names[0]
    tab = sys.argv[2] if len(sys.argv) > 2 else 'flea'
    out = Path(__file__).resolve().parent.parent / 'tests' / 'output' / f'gui_backdrop_{tab}.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    backdrop(chosen, tab).save(out)
    print(f'backgrounds: {", ".join(names)}')
    print(f'characters: {", ".join(sorted(p.stem for p in CHARACTERS.glob("*.png")))}')
    print(f'wrote {out} using {chosen}')

    # A cutout has to come out of the feather still cut out. Putting the feather in place of
    # the alpha instead of into it made every transparent pixel opaque, and the colour these
    # files keep under the transparency then showed as dots around the figure.
    for character in sorted(CHARACTERS.glob('*.png')):
        source = Image.open(character)
        if 'A' not in source.getbands() or source.getchannel('A').getextrema()[0] != 0:
            continue  # painted background rather than a cutout, nothing to preserve
        faded = _feathered(source, (500, 500))
        assert faded.getchannel('A').getextrema()[0] == 0,             f'{character.name} went fully opaque through _feathered, so its cutout was lost'
    print('cutouts survive the feather')
