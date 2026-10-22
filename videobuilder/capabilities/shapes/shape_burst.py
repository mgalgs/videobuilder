"""Shape Burst: a spray of small mixed shapes -- dots, rings, triangles,
squares, dashes -- flies out from one point, spinning as it goes, then
shrinks away to nothing."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

KINDS = ('dot', 'ring', 'triangle', 'square', 'dash')


def burst_pieces(count=18, seed=0, kinds=KINDS, colors=(demo.ACCENT, demo.TEAL, demo.INK)):
    """The pieces of one burst, as dicts: `angle` (radians, spread evenly
    round the circle with a little jitter), `reach` (0.55 -> 1, a fraction of
    the burst's radius), `size` (0.7 -> 1.3), `spin` (turns over the burst),
    `tilt`, `kind` and `color`. The same `seed` gives the same burst."""
    rnd = random.Random(seed)
    turn = rnd.uniform(0, 2 * math.pi)
    out = []
    for i in range(count):
        out.append(dict(angle=turn + 2 * math.pi * (i + rnd.uniform(-0.3, 0.3)) / count,
                        reach=rnd.uniform(0.55, 1.0), size=rnd.uniform(0.7, 1.3),
                        spin=rnd.uniform(-0.6, 0.6), tilt=rnd.uniform(0, 2 * math.pi),
                        kind=kinds[i % len(kinds)], color=colors[rnd.randrange(len(colors))]))
    return out


def _piece(cv, kind, x, y, s, rot, color, alpha):
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.new_path()
    if kind == 'dot':
        c.arc(0, 0, s * 0.5, 0, 2 * math.pi)
    elif kind == 'ring':
        c.arc(0, 0, s * 0.45, 0, 2 * math.pi)
        c.set_line_width(s * 0.18)
    elif kind == 'triangle':
        for k in range(3):
            a = -math.pi / 2 + k * 2 * math.pi / 3
            c.line_to(s * 0.6 * math.cos(a), s * 0.6 * math.sin(a))
        c.close_path()
    elif kind == 'square':
        c.rectangle(-s * 0.4, -s * 0.4, s * 0.8, s * 0.8)
    else:  # dash: a short rounded bar along the direction of travel
        c.move_to(-s * 0.55, 0)
        c.line_to(s * 0.55, 0)
        c.set_line_width(s * 0.22)
        c.set_line_cap(1)  # cairo.LINE_CAP_ROUND
    c.set_source_rgba(*vb.rgba(color, alpha))
    if kind in ('ring', 'dash'):
        c.stroke()
    else:
        c.fill()
    c.restore()


def shape_burst(cv, cx, cy, p, radius=380, size=34, count=18, seed=0, pieces=None, alpha=1.0, **kw):
    """Draw one shape burst centred on (cx, cy) at progress `p` (0 -> 1).
    Pieces shoot out fast and slow to a stop (`ease_out_expo`) at up to
    `radius` px, spinning, and pop up to `size` px then shrink to nothing
    over the last 60 %. Nothing is drawn at `p` <= 0 or >= 1. `pieces`
    (from `burst_pieces`) overrides `count`, `seed` and `kw`, which go to
    `burst_pieces`."""
    if p <= 0 or p >= 1:
        return
    pieces = pieces if pieces is not None else burst_pieces(count, seed, **kw)
    travel = vb.ease_out_expo(p)
    grow = vb.clamp01(p / 0.12)
    shrink = 1 - vb.clamp01((p - 0.4) / 0.6) ** 1.5
    for pc in pieces:
        d = radius * pc['reach'] * travel
        x, y = cx + d * math.cos(pc['angle']), cy + d * math.sin(pc['angle'])
        rot = pc['tilt'] + 2 * math.pi * pc['spin'] * travel
        if pc['kind'] == 'dash':
            rot = pc['angle']  # dashes stay pointed outward, like a spark
        s = size * pc['size'] * grow * shrink
        if s > 0.5:
            _piece(cv, pc['kind'], x, y, s, rot, pc['color'], alpha)


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    hit = 0.9
    # a dot swells, then pops into the burst
    swell = demo.phase(n, 0.2, hit)
    if swell < 1:
        demo.dot(cv, cx, cy, r=20 + 30 * vb.ease_in_expo(swell))
    shock = demo.phase(n, hit, hit + 0.45)
    if 0 < shock < 1:
        cv.arc(cx, cy, 60 + 260 * vb.ease_out_expo(shock), 0, 2 * math.pi, demo.INK,
               width=6 * (1 - shock), alpha=0.6 * (1 - shock))
    shape_burst(cv, cx, cy, demo.phase(n, hit, hit + 1.7), radius=420, size=40, count=22, seed=4)
    cv.mark('burst', cx - 420, cy - 420, 840, 840)


TECHNIQUE = Technique(
    id='shape-burst',
    name='Shape burst',
    family='shapes',
    group='Bursts & particles',
    aliases=('shape explosion', 'confetti burst', 'particle pop', 'burst shapes'),
    definition='A handful of small mixed shapes shoots out from a single point in every direction, '
               'spinning as it slows, then shrinks away to nothing.',
    phrasings=('little shapes pop out from the middle like a tiny explosion',
               'a burst of dots, triangles and squares flying outward',
               'make it explode into confetti-like shapes when it lands'),
    related=('fireworks', 'type-explosion', 'like-heart-burst', 'circle-pop', 'diffraction-spikes',
             'spiral-bloom'),
    api=('videobuilder.techniques.shapes.shape_burst.shape_burst',
         'videobuilder.techniques.shapes.shape_burst.burst_pieces'),
    demo=lambda: demo.film(draw),
)
