"""Shape Morph Loader: a busy indicator made of one solid shape that keeps
melting from circle to square to triangle and back, turning a little on each
change, in a seamless loop. The outline blend is `vb.paths.morph`; this
module adds the shape cycle, the timing and the drawing."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability

N = 96  # outline points: enough for a smooth circle at any loader size


def polygon(cx, cy, r, sides, turn=0.0):
    """A regular polygon's corners (a closed point list) on a circle of
    radius `r` about (cx, cy), the first corner straight up, turned by `turn`
    radians. Many `sides` give a circle."""
    return [(cx + r * math.sin(turn + 2 * math.pi * i / sides),
             cy - r * math.cos(turn + 2 * math.pi * i / sides)) for i in range(sides)]


def circle(cx, cy, r):
    return polygon(cx, cy, r, N)


def square(cx, cy, r):
    s = r * 0.86  # a little inside the circle, so the shapes read the same size
    return polygon(cx, cy, s * math.sqrt(2), 4, math.pi / 4)


def triangle(cx, cy, r):
    return polygon(cx, cy + r * 0.18, r * 1.18, 3)  # dropped a touch so it sits optically centred


SHAPES = (circle, square, triangle)


def _turned(points, turn):
    c, s = math.cos(turn), math.sin(turn)
    return [(x * c - y * s, x * s + y * c) for x, y in points]


def loader_outline(cx, cy, r, t, period=1.0, hold=0.35, shapes=SHAPES, spin=math.pi / 2):
    """The loader's outline at time `t` seconds, as a closed point list about
    (cx, cy), radius about `r`. Every `period` seconds it moves on to the next
    of `shapes` (functions `(cx, cy, r) -> points`), wrapping round: it holds
    for the first `hold` of the period, then morphs with an ease-in-out while
    turning by `spin`, landing upright on each shape. Returns
    `(points, index, k)`: `index` is the shape it is leaving and `k` (0 -> 1)
    how far it has morphed, for tinting."""
    step, frac = divmod(t / period, 1.0)
    i = int(step) % len(shapes)
    k = vb.ease_in_out_quart(vb.clamp01((frac - hold) / (1 - hold)))
    a = shapes[i](0, 0, r)
    b = _turned(shapes[(i + 1) % len(shapes)](0, 0, r), -spin)  # so the turn brings it upright
    pts = vb.paths.morph(a, b, k, closed=True, n=N)
    turn = spin * k
    c, s = math.cos(turn), math.sin(turn)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts], i, k


def draw_loader(cv, cx, cy, t, r=60, colors=(demo.ACCENT, demo.TEAL, demo.INK), alpha=1.0, **kw):
    """Draw the shape-morph loader at time `t` seconds, centred at (cx, cy),
    filled with `colors[i]` for shape `i` and blending to the next as it morphs. A
    soft squash on the change keeps it lively. `kw` goes to `loader_outline`.
    Returns the Box it occupies."""
    pts, i, k = loader_outline(cx, cy, r, t, **kw)
    pop = 1 + 0.12 * math.sin(math.pi * k)  # swells mid-morph, settles on each shape
    pts = [(cx + (x - cx) * pop, cy + (y - cy) * pop) for x, y in pts]
    color = kit.mix(colors[i % len(colors)], colors[(i + 1) % len(colors)], k)
    vb.paths.draw(cv, pts, color, fill=True, alpha=alpha)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return vb.Box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def draw(n, cv):
    t = n / demo.FPS
    box = draw_loader(cv, demo.W / 2, demo.H / 2 - 40, t, r=120)
    cv.mark('loader', *box)
    dots = '.' * (1 + int(t * 3) % 3)
    f = demo.font(40, 600)
    w, h = vb.text.block_size(['Loading...'], f)
    vb.text.draw(cv, ['Loading' + dots], f, (demo.W - w) / 2, demo.H / 2 + 150, demo.MUTED)


CAPABILITY = Capability(
    id='shape-morph-loader',
    name='Shape morph loader',
    family='ui',
    group='Loaders',
    aliases=('morphing loader', 'shape-shifting spinner', 'geometric morph loader'),
    definition='A waiting indicator in which a single filled shape keeps reshaping itself, circle to square '
               'to triangle and round again, turning slightly with each change.',
    phrasings=('a loading icon that changes from a circle into a square into a triangle',
               'a spinner where the shape keeps morphing while it waits',
               'a loader made of one shape that melts between geometric forms on a loop'),
    related=('morphing-blob', 'morphing-shape-ident', 'shape-morph', 'blob-to-icon-morph',
             'text-to-shape-morph', 'particle-morph'),
    api=('videobuilder.capabilities.ui.shape_morph_loader.draw_loader',
         'videobuilder.capabilities.ui.shape_morph_loader.loader_outline',
         'videobuilder.paths.morph'),
    demo=lambda: demo.film(draw),
)
