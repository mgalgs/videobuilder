"""Lightning Bolt: a jagged, forking line of light cracks down from a source
to a target, flickers while it holds, then fades away."""
import math
import random

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique


def _displace(points, rough, rng, depth):
    """Midpoint displacement: split every segment `depth` times, pushing each
    new midpoint sideways by up to `rough` times the segment's length."""
    for _ in range(depth):
        out = [points[0]]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            dx, dy = x1 - x0, y1 - y0
            off = rng.uniform(-rough, rough)
            out.append(((x0 + x1) / 2 - dy * off, (y0 + y1) / 2 + dx * off))
            out.append((x1, y1))
        points = out
    return points


def bolt(x0, y0, x1, y1, seed=0, rough=0.25, depth=6, branches=6, branch_length=0.45):
    """A bolt from (x0, y0) to (x1, y1) as a list of `(points, start, weight)`
    strokes: the trunk first (`weight` 1), then `branches` forks that split off
    it and wander outwards (`weight` < 1). `start` is where along the trunk,
    0 -> 1, the stroke begins, so a strike can grow from the source. The same
    `seed` gives the same bolt."""
    rng = random.Random(seed)
    trunk = _displace([(x0, y0), (x1, y1)], rough, rng, depth)
    strokes = [(trunk, 0.0, 1.0)]
    length = math.hypot(x1 - x0, y1 - y0)
    heading = math.atan2(y1 - y0, x1 - x0)
    for _ in range(branches):
        at = rng.uniform(0.12, 0.8)
        bx, by = trunk[int(at * (len(trunk) - 1))]
        turn = rng.choice((-1, 1)) * rng.uniform(0.35, 0.9)
        reach = length * branch_length * rng.uniform(0.5, 1.0) * (1 - at * 0.5)
        ex, ey = bx + reach * math.cos(heading + turn), by + reach * math.sin(heading + turn)
        strokes.append((_displace([(bx, by), (ex, ey)], rough * 1.2, rng, depth - 2), at, rng.uniform(0.35, 0.6)))
    return strokes


def _path(ctx, points, upto):
    """Trace `points` up to fraction `upto` of their count."""
    n = max(2, math.ceil(upto * (len(points) - 1)) + 1) if upto < 1 else len(points)
    ctx.new_path()
    ctx.move_to(*points[0])
    for x, y in points[1:n]:
        ctx.line_to(x, y)


def brightness(p, grow=0.15, flicker=4, seed=0):
    """How bright a strike is at progress `p` (0 -> 1): full while it grows
    over the first `grow`, then `flicker` random dips while it fades out."""
    if p <= 0 or p >= 1:
        return 0.0
    rest = vb.clamp01((p - grow) / (1 - grow)) if grow < 1 else 1.0
    level = (1 - rest) ** 1.2
    if flicker and rest < 0.6:
        level *= 0.55 + 0.45 * random.Random(f'{seed}:{int(rest * flicker / 0.6)}').random()
    return level


def draw_bolt(cv, strokes, p, color='#b9c6ff', core='#ffffff', width=5.0, grow=0.15, flicker=4, seed=0):
    """Draw `strokes` (from `bolt`) striking at progress `p` (0 -> 1): it races
    out from the source over the first `grow` of the time, flickers `flicker`
    times at full strength, then fades. A soft glow in `color` sits under a
    bright `core`. Returns its `brightness` this frame (0 -> 1); call
    `brightness` first to flash the sky behind it."""
    level = brightness(p, grow, flicker, seed)
    if level <= 0:
        return 0.0
    reach = vb.clamp01(p / grow) if grow > 0 else 1.0
    ctx = cv.ctx
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    for points, start, weight in strokes:
        if reach <= start:
            continue
        upto = 1.0 if start >= 1 else vb.clamp01((reach - start) / (1 - start))
        a = level * weight
        for w, c, alpha in ((width * 7, color, 0.08), (width * 3.5, color, 0.22),
                            (width * 1.6, color, 0.75), (width * 0.7, core, 1.0)):
            _path(ctx, points, upto)
            ctx.set_source_rgba(*rgba(c, alpha * a))
            ctx.set_line_width(w * (0.45 + 0.55 * weight))
            ctx.stroke()
    ctx.restore()
    return level


def draw(n, cv):
    p = demo.phase(n, 0.4, 2.6)
    strokes = bolt(demo.W * 0.48, demo.H * 0.08, demo.W * 0.53, demo.H * 0.9, seed=11)
    cv.fill('#c8d2ff', alpha=0.08 * brightness(p, seed=11))
    draw_bolt(cv, strokes, p, seed=11)
    cv.mark('bolt', demo.W * 0.3, demo.H * 0.08, demo.W * 0.4, demo.H * 0.82)


TECHNIQUE = Technique(
    id='lightning-bolt',
    name='Lightning bolt',
    family='particles',
    group='Electricity',
    aliases=('branching lightning', 'midpoint displacement bolt', 'electric strike'),
    definition='A crooked, forking streak of glowing light shoots out from a point, '
               'stutters on and off for a moment, then dims to nothing.',
    phrasings=('a bolt of lightning cracks down the screen',
               'zap it with an electric strike that forks and flickers',
               'add a jagged glowing lightning streak that fades out'),
    related=('lightning-flash', 'particle-trail', 'diffraction-spikes', 'k-rm-n-vortex-street', 'embers', 'sparks'),
    api=('videobuilder.techniques.particles.lightning_bolt.draw_bolt',
         'videobuilder.techniques.particles.lightning_bolt.bolt',
         'videobuilder.techniques.particles.lightning_bolt.brightness'),
    demo=lambda: demo.film(draw),
)
