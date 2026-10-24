"""Electric Arc: a jagged bolt of light crackles between two points, its path
re-drawn every few frames so it flickers and writhes, with a soft glow around
a white-hot core and short forks splitting off it."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

ARC_COLOR = '#8fd8ff'


def arc_points(x0, y0, x1, y1, seed=0, roughness=0.22, depth=6):
    """A jagged path from (x0, y0) to (x1, y1) as a list of points, by
    midpoint displacement: each segment's middle is pushed sideways by up to
    `roughness` of its length, `depth` times over. The same `seed` gives the
    same path; change it (say, every few frames) to make the arc flicker."""
    rng = random.Random(seed)
    pts = [(x0, y0), (x1, y1)]
    for _ in range(depth):
        out = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dx, dy = bx - ax, by - ay
            k = rng.uniform(-roughness, roughness)
            out.append(((ax + bx) / 2 - dy * k, (ay + by) / 2 + dx * k))
            out.append((bx, by))
        pts = out
    return pts


def _stroke(cv, pts, color, width, alpha):
    c = cv.ctx
    c.new_path()
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.set_source_rgba(*vb.rgba(color, alpha))
    c.set_line_width(width)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    c.stroke()


def _glow(cv, x, y, r, color, alpha):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    cr, cg, cb, _ = vb.rgba(color)
    g.add_color_stop_rgba(0, cr, cg, cb, alpha)
    g.add_color_stop_rgba(1, cr, cg, cb, 0)
    cv.ctx.rectangle(x - r, y - r, 2 * r, 2 * r)
    cv.ctx.set_source(g)
    cv.ctx.fill()


def draw_arc(cv, x0, y0, x1, y1, t, color=ARC_COLOR, width=6, reach=1.0, flicker=20, roughness=0.22,
             branches=3, seed=0, alpha=1.0):
    """Draw an electric arc from (x0, y0) towards (x1, y1) at time `t`
    seconds. The path is re-rolled `flicker` times a second; `reach` (0 -> 1)
    is how far along it has struck, for an arc that leaps across. Each roll
    also sprouts up to `branches` short forks. Drawn as a wide faint glow, a
    coloured body and a white core, added onto what is beneath so it lights
    up the frame; `alpha` dims the whole thing (fade it, or flutter it)."""
    step = int(t * flicker)
    pts = arc_points(x0, y0, x1, y1, seed=f'{seed}:{step}', roughness=roughness)
    pts = pts[:max(2, round(len(pts) * vb.clamp01(reach)))]
    rng = random.Random(f'{seed}:{step}:forks')
    forks = []
    length = math.hypot(x1 - x0, y1 - y0)
    for _ in range(branches):
        i = rng.randrange(len(pts) // 5, max(len(pts) // 5 + 1, len(pts) * 4 // 5))
        if i >= len(pts):
            continue
        bx, by = pts[i]
        ang = math.atan2(y1 - y0, x1 - x0) + rng.choice((-1, 1)) * rng.uniform(0.4, 1.0)
        l = length * rng.uniform(0.08, 0.22)
        forks.append(arc_points(bx, by, bx + l * math.cos(ang), by + l * math.sin(ang),
                                seed=rng.random(), roughness=0.3, depth=4))
    c = cv.ctx
    c.save()
    c.set_operator(cairo.OPERATOR_ADD)
    for path, w in [(pts, width)] + [(f, width * 0.5) for f in forks]:
        _stroke(cv, path, color, w * 5, 0.10 * alpha)
        _stroke(cv, path, color, w * 2.2, 0.30 * alpha)
        _stroke(cv, path, color, w, 0.85 * alpha)
        _stroke(cv, path, '#ffffff', w * 0.4, 0.95 * alpha)
    hx, hy = pts[-1]
    _glow(cv, x0, y0, width * 14, color, 0.45 * alpha)
    _glow(cv, hx, hy, width * 14, color, 0.45 * alpha)
    c.restore()
    return pts


def draw(n, cv):
    t = n / demo.FPS
    y = demo.H / 2
    xa, xb = demo.W * 0.2, demo.W * 0.8
    for x in (xa, xb):  # two electrodes
        cv.rect(x - 8, y - 60, 16, 120, demo.LINE, radius=6)
        demo.dot(cv, x, y, r=14, color=demo.MUTED)
    strike = demo.phase(n, 0.4, 0.6)
    fade = 1 - demo.phase(n, 2.5, 2.8)
    if strike > 0 and fade > 0:
        flutter = 0.75 + 0.25 * random.Random(n).random()
        pts = draw_arc(cv, xa, y, xb, y, t, width=4, reach=strike, alpha=fade * flutter, seed=3)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cv.mark('arc', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys) + 1)


CAPABILITY = Capability(
    id='electric-arc',
    name='Electric arc',
    family='particles',
    group='Electricity',
    aliases=('lightning arc', 'electric bolt', 'tesla arc', 'crackling electricity',
             'branching lightning', 'electric strike'),
    definition='A jagged, glowing streak of electricity jumps between two points and keeps crackling, '
               'its zigzag path flickering into a new shape every few frames.',
    phrasings=('a crackling bolt of electricity between the two ends',
               'sparks of lightning zapping from one point to the other',
               'make it look like current is arcing across the gap'),
    related=('flight-arc', 'diffraction-spikes', 'sparks', 'fireflies', 'lightning-flash', 'embers'),
    api=('videobuilder.capabilities.particles.electric_arc.draw_arc',
         'videobuilder.capabilities.particles.electric_arc.arc_points',
         'videobuilder.capabilities.particles.lightning_bolt.bolt',
         'videobuilder.capabilities.particles.lightning_bolt.draw_bolt'),
    demo=lambda: demo.film(draw),
)
