"""The showcase's shared look and helpers: the catalog's palette and type
(examples/capabilities/STYLE.md), this film's two formats, the stage each
shot lays itself out on, the Lumen logo and the capability tag.

Every shot is a function `shot(cv, s, st)`: `s` is the `vb.Shot` drawing
(`s.f` frames in, `s.length` frames long), `st` the `Stage` for the format.
"""
import math
from dataclasses import dataclass
from pathlib import Path

import cairo
from PIL import Image as PILImage

import videobuilder as vb
from videobuilder import Box, text

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / 'assets'
for _f in ('Inter-Variable.ttf', 'SourceCodeVF-Upright.otf'):
    text.register(ASSETS / _f)

FPS = 30
GRID = vb.Grid(fps=FPS, bpm=120)
FPB = 15  # frames a beat

# Built at 1280x720 and 720x1280: the short side is 720 in both, so type sizes
# read the same in either shape.
F16 = vb.Format('16x9', 1280, 720)
F9 = vb.Format('9x16', 720, 1280)

BG = '#14151a'
INK = '#f4f4f2'
MUTED = '#9397a1'
ACCENT = '#ef5b4c'
TEAL = '#4fc3b0'
LINE = '#2a2c33'
CARD = '#1d1f26'
CARD_HI = '#262932'

# Safe areas: 9:16 keeps clear of a phone app's caption and button strip at the bottom.
SAFE = {'16x9': (48, 40, 1184, 640), '9x16': (40, 96, 640, 1048)}


def font(size, weight=400, **kw):
    return vb.Font('Inter', size, weight=weight, **kw)


def mono(size, weight=500, **kw):
    return vb.Font('SourceCodeVF', size, weight=weight, **kw)


@dataclass(frozen=True)
class Stage:
    """Where a shot may draw: the whole frame, the safe area, and `content`,
    the safe area below the tag's strip."""
    frame: Box
    safe: Box
    content: Box
    wide: bool

    @property
    def name(self):
        return '16x9' if self.wide else '9x16'


def stage(cv):
    safe = Box(*SAFE[cv.format.name])
    room = TAG_LINES[cv.format.name] * TAG_LH + 2 * TAG_PAD[1] + 16
    return Stage(Box.of(cv), safe, Box(safe.x, safe.y + room, safe.w, safe.h - room), cv.width > cv.height)


def pick(st, wide, tall):
    """The 16:9 value or the 9:16 one."""
    return wide if st.wide else tall


# ---- motion ----
EASE_OUT = vb.ease_out_expo
SMOOTH = vb.ease_in_out_quart
SNAP = vb.critical(170)
BOUNCY = vb.damped(0.45, hz=2.4)


def prog(f, a, z, ease=EASE_OUT):
    """0 -> 1 over frames a..z, eased."""
    return ease(vb.clamp01((f - a) / max(1e-9, z - a)))


def spring(f, delay=0, spec=SNAP):
    return vb.spring_at(f - delay, FPS, **spec)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c0, c1, t):
    """A colour between two, as an (r, g, b) 0-255 tuple."""
    a, b = vb.rgba(c0), vb.rgba(c1)
    return tuple(255 * lerp(x, y, t) for x, y in zip(a[:3], b[:3]))


def scaled(cv, cx, cy, s):
    """A layer scaled by `s` about (cx, cy)."""
    s = max(s, 1e-3)  # cairo can't invert a zero scale
    return cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s)


# ---- text ----
def lines_of(copy, f, width, balance=True):
    lines = text.wrap(copy, f, width, balance=balance)
    return lines, text.block_size(lines, f)


def write(cv, name, copy, f, x, y, color, width=None, align='left', alpha=1.0, balance=True):
    """Wrap `copy` to `width`, draw it from (x, y) and mark it."""
    width = width or 10_000
    lines = text.wrap(copy, f, width, balance=balance)
    box = text.draw(cv, lines, f, x, y, color, align=align, width=width if align != 'left' else None, alpha=alpha)
    cv.mark(name, *box)
    return box


def write_centered(cv, name, copy, f, cx, cy, color, width, alpha=1.0):
    lines, (w, h) = lines_of(copy, f, width)
    box = text.draw(cv, lines, f, cx - width / 2, cy - h / 2, color, align='center', width=width, alpha=alpha)
    cv.mark(name, cx - w / 2, cy - h / 2, w, h)
    return Box(cx - w / 2, cy - h / 2, w, h)


# ---- the Lumen logo: an orange sun in a teal ring, like the 3D render ----
def logo(cv, cx, cy, r, spin=0.0, name='logo', alpha=1.0):
    """The ring's outer radius is `r`; `spin` (radians) turns the small moon on the ring."""
    with cv.layer(opacity=alpha):
        cv.arc(cx, cy, r * 0.84, 0, 2 * math.pi, TEAL, width=r * 0.32)
        cv.rect(cx - r * 0.42, cy - r * 0.42, r * 0.84, r * 0.84, ACCENT, radius=r * 0.42)
        mx, my = cx + r * 0.84 * math.cos(spin), cy + r * 0.84 * math.sin(spin)
        cv.rect(mx - r * 0.1, my - r * 0.1, r * 0.2, r * 0.2, INK, radius=r * 0.1)
    if name:
        cv.mark(name, cx - r, cy - r, 2 * r, 2 * r)


def glow(cv, cx, cy, r, color=ACCENT, alpha=0.35):
    """A soft radial glow behind something."""
    ctx = cv.ctx
    g = cairo.RadialGradient(cx, cy, 0, cx, cy, r)
    cr, cg, cb, _ = vb.rgba(color)
    g.add_color_stop_rgba(0, cr, cg, cb, alpha)
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    ctx.save()
    ctx.set_source(g)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


# ---- the tag: which catalog cards this shot shows ----
TAG_F = font(36, 700)
TAG_LH = 44          # one line of the tag
TAG_PAD = (22, 12)   # pill padding, x and y
TAG_SEP = '  ·  '
# Room kept clear for the tag above each shot: two lines in 16:9, three in 9:16
# (a tag listing several cards wraps there).
TAG_LINES = {'16x9': 2, '9x16': 3}
TAG_H = TAG_LH + 2 * TAG_PAD[1]


def tag_lines(items, width):
    """Pack tag items into lines no wider than `width`, breaking only between items."""
    lines = []
    for item in items:
        if lines and text.measure(lines[-1] + TAG_SEP + item, TAG_F) <= width:
            lines[-1] += TAG_SEP + item
        else:
            lines.append(item)
    return lines


def tag(cv, st, items, alpha=1.0):
    """An accent pill, top left of the safe area, naming the capabilities in
    the shot: the reel's headline, so it reads at a glance on a phone."""
    if alpha <= 0:
        return
    lines = tag_lines(items, st.safe.w - 2 * TAG_PAD[0])
    tw = max(text.measure(line, TAG_F) for line in lines)
    w = TAG_PAD[0] + tw + TAG_PAD[0]
    h = len(lines) * TAG_LH + 2 * TAG_PAD[1]
    x, y = st.safe.x, st.safe.y
    r = min(h / 2, TAG_H / 2)
    with cv.layer(opacity=alpha):
        cv.shadow(x, y, w, h, radius=r, dy=6, blur=18, color=(0, 0, 0, 0.35))
        cv.rect(x, y, w, h, ACCENT, radius=r)
        lh = text.line_height(TAG_F)
        for i, line in enumerate(lines):
            text.draw(cv, line, TAG_F, x + TAG_PAD[0], y + TAG_PAD[1] + i * TAG_LH + (TAG_LH - lh) / 2, '#ffffff')
    cv.mark('tag', x, y, w, h)


# ---- pictures made here ----
def to_image(cv):
    """A drawn Canvas as a `vb.Image` (for scenes drawn once and reused)."""
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    pil = PILImage.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
    return vb.Image.from_pil(pil.convert('RGBA'))


def to_pil(cv):
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    return PILImage.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA',
                               cv.surface.get_stride(), 1).convert('RGBA')


def paint_surface(cv, surf, operator=cairo.OPERATOR_OVER, alpha=1.0):
    """Paint a device-sized surface cached for `cv.scale` over the frame."""
    ctx = cv.ctx
    ctx.save()
    ctx.scale(1 / cv.scale, 1 / cv.scale)
    ctx.set_source_surface(surf, 0, 0)
    ctx.set_operator(operator)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def poly(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def rounded_points(x, y, w, h, r, per_corner=8):
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for k in range(per_corner + 1):
            a = math.radians(a0 + 90 * k / per_corner)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rect_points(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
