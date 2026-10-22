"""Morphing shape ident: one solid shape runs through a chain of forms and
lands as the logo mark, then the name joins it. Each step is `paths.morph`;
what this adds is the chain itself -- splitting one progress value across the
steps with a short rest on every form, and a little twist mid-step so the
shape tumbles between forms rather than sliding flat."""
import math

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Capability


def _rotate(points, cx, cy, angle):
    c, s = math.cos(angle), math.sin(angle)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in points]


def ident_step(count, p, rest=0.3):
    """Which step of a chain of `count` shapes progress `p` (0 -> 1) is in,
    and how far through it: `(i, t)`, morphing shape `i` into `i + 1` with
    `t` 0 -> 1 (not eased). Each step spends its first `rest` share holding
    shape `i`, so every form is seen before it moves on."""
    steps = count - 1
    u = vb.clamp01(p) * steps
    i = min(int(u), steps - 1)
    return i, vb.clamp01((u - i - rest) / (1 - rest))


def morph_ident(shapes, p, rest=0.3, spin=0.35, ease=vb.ease_in_out_quart, n=240):
    """The outline at progress `p` (0 -> 1) of one shape morphing through
    `shapes` (closed point lists, the last being the logo mark) in turn. At 0
    it is `shapes[0]`, at 1 exactly the mark. Each step rests on its form for
    `rest` of its share, then morphs with `ease`, twisting up to `spin`
    radians about the shape's centre mid-move and back to square on landing.
    Returns `(points, i, t)`: `i, t` as `ident_step` gives them, eased, for
    colouring or cueing. Draw with `vb.paths.draw(cv, pts, colour, fill=True)`."""
    i, t = ident_step(len(shapes), p, rest)
    t = ease(t)
    pts = paths.morph(shapes[i], shapes[i + 1], t, closed=True, n=n)
    if spin and 0 < t < 1:
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        pts = _rotate(pts, cx, cy, spin * math.sin(math.pi * t))
    return pts, i, t


def regular(cx, cy, r, sides, turn=-math.pi / 2):
    """A closed regular polygon outline about (cx, cy), radius `r`, first
    vertex at angle `turn` (default: pointing up)."""
    return [(cx + r * math.cos(turn + 2 * math.pi * k / sides),
             cy + r * math.sin(turn + 2 * math.pi * k / sides)) for k in range(sides)]


def _mix(c0, c1, t):
    a, b = vb.canvas.rgba(c0), vb.canvas.rgba(c1)
    return tuple(round(255 * (x + (y - x) * t)) for x, y in zip(a[:3], b[:3]))


CX, CY, R = demo.W / 2, demo.H / 2, 150


def _mark(cx, cy, s):
    """The demo's logo mark: a bold block 'V' monogram, 2s wide."""
    return [(cx - s, cy - s), (cx - s * 0.42, cy - s), (cx, cy + s * 0.18), (cx + s * 0.42, cy - s),
            (cx + s, cy - s), (cx + s * 0.28, cy + s), (cx - s * 0.28, cy + s)]


SHAPES = (regular(CX, CY, R, 64), regular(CX, CY + 20, R * 1.15, 3), regular(CX, CY, R * 1.05, 6, 0),
          _mark(CX, CY, R * 0.95))
COLORS = (demo.ACCENT, demo.TEAL, '#e8b04a', demo.ACCENT)
MORPH = (0.2, 2.0)        # seconds the chain of morphs runs over
SLIDE = (2.05, 2.6)       # the mark slides aside...
NAME = (2.25, 2.75)       # ...and the name fades in once it has cleared


def draw(n, cv):
    pts, i, t = morph_ident(SHAPES, demo.phase(n, *MORPH))
    color = _mix(COLORS[i], COLORS[i + 1], t)
    q = vb.ease_out_quint(demo.phase(n, *SLIDE))
    a = vb.ease_out_quint(demo.phase(n, *NAME))
    f = demo.font(130, 800)
    name = 'VERTA'
    tw, _ = vb.text.block_size([name], f)
    gap, mark_w = 50, 2 * R * 0.95
    dx = -(tw + gap) / 2 * q
    pts = [(x + dx, y) for x, y in pts]
    paths.draw(cv, pts, color, fill=True)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    if a > 0:
        x0 = CX - (tw + gap) / 2 + mark_w / 2 + gap   # where the name rests once the mark has moved aside
        box = demo.word(cv, name, x0 + tw / 2 + 40 * (1 - a), CY, size=130, alpha=a)
        cv.mark('text', *box)


CAPABILITY = Capability(
    id='morphing-shape-ident',
    name='Morphing shape ident',
    family='broadcast',
    group='Bumpers & idents',
    aliases=('shape morph logo', 'blob morph ident', 'morphing logo ident', 'shape-shifting logo sting'),
    definition='A single solid shape keeps changing into one form after another, pausing briefly on each, '
               'until it settles as the brand mark and the name appears beside it.',
    phrasings=('a shape that keeps transforming and ends up as our logo',
               'circle turns into a triangle, then a hexagon, then the logo for the channel ident',
               'a morphing geometric sting that resolves into the brand mark'),
    related=('blob-to-icon-morph', 'morphing-blob', 'shape-morph-loader', 'shape-morph',
             'text-to-shape-morph', 'letter-morph'),
    api=('videobuilder.capabilities.broadcast.morphing_shape_ident.morph_ident',
         'videobuilder.capabilities.broadcast.morphing_shape_ident.ident_step',
         'videobuilder.capabilities.broadcast.morphing_shape_ident.regular',
         'videobuilder.paths.morph', 'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)
