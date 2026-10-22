"""Liquid Melt: a word softens and sags, the feet of its letters stretching
down off the baseline into tapering drips, and drops break from the longest
tips and fall."""
import math
import random
from functools import lru_cache

import cairo
from gi.repository import PangoCairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ... import paths, text


@lru_cache(maxsize=64)
def _contours(line, font, step=2.0):
    """`line`'s glyph outlines as closed point lists, drawn as `text.draw`
    would at (0, 0), resampled every ~`step` px so even a straight edge has
    points to bend."""
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))
    content, _ = text._content(font)
    ctx.move_to(0, (text.line_height(font) - content) / 2)
    PangoCairo.layout_path(ctx, text._layout(ctx, line, font))
    out, cur = [], []
    for kind, pts in ctx.copy_path_flat():
        if kind == cairo.PATH_MOVE_TO:
            if len(cur) > 2:
                out.append(cur)
            cur = [pts]
        elif kind == cairo.PATH_LINE_TO:
            cur.append(pts)
        elif kind == cairo.PATH_CLOSE_PATH:
            if len(cur) > 2:
                out.append(cur)
            cur = []
    if len(cur) > 2:
        out.append(cur)
    return tuple(tuple(paths.resample(c, max(8, round(paths.length(c, closed=True) / step)), closed=True))
                 for c in out)


def _feet(contours, base, tol):
    """The x-spans where ink rests on the baseline `base`: runs of outline
    points within `tol` px of it, merged when they touch."""
    xs = sorted(x for c in contours for x, y in c if y >= base - tol)
    spans = []
    for x in xs:
        if spans and x - spans[-1][1] <= tol * 2:
            spans[-1][1] = x
        else:
            spans.append([x, x])
    return [(a, b) for a, b in spans if b - a >= tol]


@lru_cache(maxsize=64)
def drips(line, font, seed=0, share=0.7):
    """The drips for `line`: `(x, width, length, start)` tuples in px from the
    line's top-left, one per foot of ink on the baseline (wide feet may get
    two), a seeded `share` of them kept. `start` (0 -> 0.4) staggers when each
    begins to run; `length` is how far below the baseline it ends."""
    cs = _contours(line, font)
    size = font.size
    base = max(y for c in cs for _, y in c)
    rnd = random.Random(seed)
    out = []
    for a, b in _feet(cs, base, size * 0.02):
        n = 2 if b - a > size * 0.5 else 1
        for k in range(n):
            if rnd.random() > share:
                continue
            x = a + (b - a) * (k + 0.5 + rnd.uniform(-0.2, 0.2)) / n
            width = min((b - a) / n, size * 0.14) * rnd.uniform(0.35, 0.5)
            out.append((x, width, size * rnd.uniform(0.25, 1.0), rnd.uniform(0, 0.4)))
    return tuple(out)


def melt(contours, p, drip_list, base, size, sag=0.12):
    """`contours` bent at melt progress `p` (0 -> 1): every point near the
    baseline `base` slides down by up to `sag` x `size`, more the lower it
    sits, and each drip `(x, width, length, start)` pulls the bottom edge
    under it down into a rounded, tapering finger that runs slowly then
    faster. Returns new point lists; points above the lower part of the
    letters do not move."""
    reach = size * 0.45
    soft = vb.ease_in_out_quart(vb.clamp01(p))
    runs = [(x, w, length * vb.clamp01((p - s) / (1 - s)) ** 1.7) for x, w, length, s in drip_list]
    out = []
    for c in contours:
        bent = []
        for x, y in c:
            low = vb.clamp01((y - (base - reach)) / reach)
            if low <= 0:
                bent.append((x, y))
                continue
            dy = sag * size * soft * low * low
            for dx, w, run in runs:
                g = math.exp(-((x - dx) / w) ** 2)
                if g > 0.01:
                    dy += run * g * low ** 6
            bent.append((x, y + dy))
        out.append(bent)
    return out


def draw_melt(cv, line, font, x, y, p, color, seed=0, share=0.7, sag=0.12, drops=True):
    """Draw `line` melting at progress `p` (0 -> 1) from its top-left (x, y):
    the letters sag and drip off the baseline (see `melt`), and when `drops`,
    a drop pinches off the tip of each long drip and falls once it has run
    most of its length. `seed` and `share` pick the drips (see `drips`).
    Returns the Box of the upright line."""
    cs = _contours(line, font)
    base = max(py for c in cs for _, py in c)
    ds = drips(line, font, seed, share)
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x, y)
    ctx.new_path()
    for c in melt(cs, p, ds, base, font.size, sag):
        ctx.move_to(*c[0])
        for pt in c[1:]:
            ctx.line_to(*pt)
        ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill()
    if drops:
        for dx, w, length, s in ds:
            q = vb.clamp01((p - s) / (1 - s))
            if length < font.size * 0.55 or q < 0.6:
                continue
            fall = (q - 0.6) / 0.4
            tip = base + vb.ease_in_out_quart(vb.clamp01(p)) * sag * font.size + length * q ** 1.7
            r = w * 0.6
            ctx.new_path()
            ctx.arc(dx, tip + r + font.size * 1.6 * fall * fall, r, 0, 2 * math.pi)
            ctx.fill()
    ctx.restore()
    w, h = text.block_size([line], font)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    f = demo.font(190, 900)
    line = 'MELTING'
    w, h = text.block_size([line], f)
    box = draw_melt(cv, line, f, (demo.W - w) / 2, (demo.H - h) / 2 - 90, demo.phase(n, 0.4, 2.7),
                    demo.INK, seed=3)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='liquid-melt',
    name='Liquid melt',
    family='typography',
    group='Liquid and organic',
    aliases=('melting type', 'drip type', 'melting text', 'dripping text'),
    definition='A word goes soft like warm wax: the bottoms of its letters sag and run down past the '
               'baseline in tapering drips, and drops fall from the longest ones.',
    phrasings=('make the title melt and drip like it is left out in the sun',
               'the letters should drip down like paint running off them',
               'have the text turn to liquid and ooze downwards'),
    related=('color-fill-rise', 'type-explosion', 'drip-wipe', 'liquid-button', 'jitter-and-boil-text',
             'line-boil'),
    api=('videobuilder.capabilities.typography.liquid_melt.draw_melt',
         'videobuilder.capabilities.typography.liquid_melt.melt',
         'videobuilder.capabilities.typography.liquid_melt.drips'),
    demo=lambda: demo.film(draw),
)
