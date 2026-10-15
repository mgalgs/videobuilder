"""Shared helpers for the transition components: beat timing inside a
transition's own overlap, fitting a title to a box, a second procedural
sample picture, and a few polygon helpers. Not a component itself (the
leading underscore keeps it out of the catalog).

Every transition here follows `overlap_slide`'s contract: `draw(cv, shots)`
gets `Timeline.live(n)` -- the outgoing shot alone while it holds, then
(outgoing, this transition's own shot) during the overlap -- and draws its
own from/to pair from its slots.
"""
import math
import random
from functools import lru_cache

from PIL import Image as PILImage, ImageDraw, ImageFilter

import videobuilder as vb
from videobuilder import text

from .. import kit


# ---- timing ----

def frames_per_beat(shot):
    beats = shot.segment.until - shot.segment.at
    return shot.length / beats if beats else kit.GRID.frames_per_beat


def start_frame(shots, motion_beats):
    """Frames into the transition's own shot at which its move starts, on a
    beat. In its own preview the outgoing shot has already held on its own
    (it is this transition's `from` phase, carrying the same data), so the
    move starts at once; between two real neighbours the `from` card is new
    on screen, so it holds for a beat first when the step has room for one
    and still leaves a beat for the incoming card to settle in."""
    shot = shots[-1]
    fpb = frames_per_beat(shot)
    if len(shots) > 1 and shots[0].data is shot.data:
        return 0
    beats = shot.length / fpb
    lead = 1.0 if beats - motion_beats >= 2 else 0.0
    return round(lead * fpb)


def phase(shots, motion_beats):
    """(in_transition, p, after, fpb): whether the incoming card is on screen
    yet, the move's linear progress 0..1, and frames since the move ended
    (negative while it runs), for this frame's `shots`."""
    if len(shots) == 1:
        return False, 0.0, -1, frames_per_beat(shots[0])
    shot = shots[-1]
    fpb = frames_per_beat(shot)
    t0 = start_frame(shots, motion_beats)
    dur = max(1, round(motion_beats * fpb))
    f = shot.f - t0
    if f < 0:
        return False, 0.0, -1, fpb
    return True, vb.clamp01(f / dur), f - dur, fpb


def hold_f(shots):
    """Frames the outgoing card has been on screen, for its own idle motion
    and entrance: its own `f` in the preview's `from` phase; in a recipe the
    outgoing card is new at the transition's first frame but shown already at
    rest (a large number), so nothing re-enters mid-film."""
    if len(shots) == 1:
        return shots[0].f
    if shots[0].data is shots[-1].data:
        return shots[0].f
    return 10_000 + shots[-1].f


def smoothstep(t):
    t = vb.clamp01(t)
    return t * t * t * (t * (6 * t - 15) + 10)


def lerp(a, b, t):
    return a + (b - a) * t


# ---- type ----

def fit(copy, width, sizes, weight=800, max_lines=3, tracking=-0.02, line_height=1.02, balance=True):
    """(font, lines): `copy` wrapped at the largest of `sizes` that fits
    `width` in at most `max_lines` lines (no single word wider than the box),
    falling back to the smallest size."""
    font = lines = None
    for size in sizes:
        font = kit.font(size, weight, tracking=tracking, line_height=line_height)
        lines = text.wrap(copy, font, width, balance=balance) if copy else ()
        if len(lines) <= max_lines and all(text.measure(ln, font) <= width + 0.5 for ln in lines):
            return font, lines
    return font, lines


def is_light(color):
    r, g, b, _ = vb.rgba(color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.5


def ink_on(color):
    """Readable ink for type set directly on `color`."""
    return kit.BG if is_light(color) else kit.INK


# ---- shapes ----

def poly(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def rounded_points(x, y, w, h, r, per_corner=10):
    r = max(0.0, min(r, w / 2, h / 2))
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for k in range(per_corner + 1):
            a = math.radians(a0 + 90 * k / per_corner)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def bounds(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


# ---- a second sample picture ----

def _night_photo(w=720, h=720, seed=23):
    """A seeded procedural 'photo' to pair with `kit.sample_photo()`: a dusk
    harbour -- deep sky into warm haze, a low moon, a skyline of blocks with
    lit windows, and their reflection broken up in the water."""
    rnd = random.Random(seed)
    top, mid = (17, 24, 44), (196, 104, 92)
    horizon = int(h * 0.62)
    grad = PILImage.new('RGB', (1, h))
    for y in range(h):
        if y < horizon:
            t = (y / horizon) ** 1.6
            c = tuple(int(top[i] + (mid[i] - top[i]) * t) for i in range(3))
        else:
            t = (y - horizon) / (h - horizon)
            c = tuple(int(mid[i] * (0.55 - 0.35 * t) + top[i] * (0.45 + 0.35 * t)) for i in range(3))
        grad.putpixel((0, y), c)
    img = grad.resize((w, h)).convert('RGBA')

    glow = PILImage.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    mx, my, mr = w * 0.3, h * 0.36, w * 0.075
    d.ellipse((mx - mr * 2.6, my - mr * 2.6, mx + mr * 2.6, my + mr * 2.6), fill=(255, 196, 160, 60))
    glow = glow.filter(ImageFilter.GaussianBlur(w * 0.04))
    img = PILImage.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    d.ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=(255, 232, 206, 255))
    for _ in range(70):
        sx, sy = rnd.uniform(0, w), rnd.uniform(0, horizon * 0.55)
        a = rnd.randint(90, 220)
        d.point((sx, sy), fill=(255, 255, 255, a))

    city = PILImage.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(city)
    x = -10
    while x < w:
        bw = rnd.uniform(w * 0.05, w * 0.12)
        bh = rnd.uniform(h * 0.06, h * 0.26) * (1.35 if 0.45 < x / w < 0.75 else 1.0)
        tone = rnd.choice(((14, 20, 34), (20, 27, 44), (26, 33, 52)))
        d.rectangle((x, horizon - bh, x + bw, horizon), fill=tone + (255,))
        for wy in range(int(horizon - bh + 8), horizon - 6, 9):
            for wx in range(int(x + 5), int(x + bw - 5), 8):
                if rnd.random() < 0.32:
                    d.rectangle((wx, wy, wx + 3, wy + 4), fill=(255, rnd.randint(170, 215), 120, 230))
        x += bw + rnd.uniform(0, w * 0.02)
    img = PILImage.alpha_composite(img, city)

    # The water: the skyline flipped, squashed, and cut into ripples.
    refl = city.crop((0, 0, w, horizon)).transpose(PILImage.FLIP_TOP_BOTTOM)
    refl = refl.resize((w, h - horizon)).filter(ImageFilter.GaussianBlur(2))
    rows = PILImage.new('RGBA', refl.size, (0, 0, 0, 0))
    for y in range(0, refl.size[1], 3):
        shift = int(6 * math.sin(y * 0.35 + rnd.random()))
        strip = refl.crop((0, y, w, min(y + 3, refl.size[1])))
        rows.paste(strip, (shift, y))
    a = rows.split()[3].point(lambda v: v * 0.45)
    rows.putalpha(a)
    img.alpha_composite(rows, (0, horizon))
    return img.convert('RGB')


@lru_cache(maxsize=1)
def night_photo():
    """A shared `vb.Image` of `_night_photo`, built once."""
    return vb.Image.from_pil(_night_photo())


def cover(cv, img, box, zoom=1.0, focus=(0.5, 0.5)):
    """`img` cover-fitted into `box` (clipped by the caller), scaled by `zoom`
    about the `focus` point of the box."""
    s = max(box.w / img.w, box.h / img.h) * zoom
    w, h = img.w * s, img.h * s
    fx, fy = focus
    x = box.x + (box.w - w) * fx
    y = box.y + (box.h - h) * fy
    cv.image(img, x, y, w, h)


def text_path(cv, line, font, x, y):
    """One line of `font` as a cairo path at (x, y) -- the same placement
    `text.draw` gives it -- for stroking as outline type. Returns the Box of
    its ink (the glyphs themselves, not the line box)."""
    from gi.repository import PangoCairo
    ctx = cv.ctx
    lh = text.line_height(font)
    content, _ = text._content(font)
    ctx.new_path()
    ctx.move_to(x, y + (lh - content) / 2)
    PangoCairo.layout_path(ctx, text._layout(ctx, line, font))
    x0, y0, x1, y1 = ctx.path_extents()
    return vb.Box(x0, y0, x1 - x0, y1 - y0)


def outline_text(cv, line, font, x, y, color, width=2.0, alpha=1.0, align='left'):
    """`line` as stroked outline type, its ink's top-left (or, with `align`
    'right', top-right) corner at (x, y). Returns the ink's Box."""
    ctx = cv.ctx
    ctx.save()
    ink = text_path(cv, line, font, 0, 0)
    ctx.new_path()
    ox = x - ink.x - (ink.w if align == 'right' else 0)
    ctx.translate(ox, y - ink.y)
    text_path(cv, line, font, 0, 0)
    ctx.set_source_rgba(*vb.rgba(color, alpha))
    ctx.set_line_width(width)
    ctx.set_line_join(1)  # round
    ctx.stroke()
    ctx.restore()
    return vb.Box(ink.x + ox, y, ink.w, ink.h)
