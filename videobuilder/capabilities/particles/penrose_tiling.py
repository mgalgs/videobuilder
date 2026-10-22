"""Penrose tiling: a plane covered by two rhombi, a fat one and a thin one,
that fit together with five-fold symmetry but never repeat. Here the tiles
are built by repeatedly splitting golden triangles, then grow outward from
a centre star."""
import cmath
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique

PHI = (1 + math.sqrt(5)) / 2
THIN, THICK = 0, 1


def _split(tris):
    """One deflation step: each golden (Robinson) triangle into two or three smaller ones."""
    out = []
    for kind, a, b, c in tris:
        if kind == THIN:
            p = a + (b - a) / PHI
            out += [(THIN, c, p, b), (THICK, p, c, a)]
        else:
            q = b + (a - b) / PHI
            r = b + (c - b) / PHI
            out += [(THICK, r, c, a), (THICK, q, r, b), (THIN, r, q, a)]
    return out


def penrose_triangles(generations=5, radius=600.0, cx=0.0, cy=0.0, rotation=0.0):
    """The half-rhombus triangles of a Penrose rhombus tiling filling a disc of
    `radius` about (cx, cy), split `generations` times from a ten-triangle
    wheel. Returns `(kind, a, b, c)` tuples: `kind` is `THIN` or `THICK`, the
    corners are complex numbers (x + yj), and `b`-`c` is the edge the
    triangle shares with its other half."""
    tris = []
    for k in range(10):
        b = cmath.rect(radius, (2 * k - 1) * math.pi / 10 + rotation)
        c = cmath.rect(radius, (2 * k + 1) * math.pi / 10 + rotation)
        if k % 2 == 0:
            b, c = c, b
        tris.append((THIN, 0j, b, c))
    for _ in range(generations):
        tris = _split(tris)
    o = complex(cx, cy)
    return [(kind, a + o, b + o, c + o) for kind, a, b, c in tris]


def penrose_rhombi(generations=5, radius=600.0, cx=0.0, cy=0.0, rotation=0.0):
    """The tiling as whole rhombi: `(kind, corners, centre)` per tile, corners
    as (x, y) in order and centre as complex. Halves cut by the disc's rim
    come back as triangles."""
    tiles = {}
    for kind, a, b, c in penrose_triangles(generations, radius, cx, cy, rotation):
        mid = (b + c) / 2
        key = (kind, round(mid.real, 3), round(mid.imag, 3))
        tiles.setdefault(key, []).append((a, b, c))
    out = []
    for (kind, _, _), halves in tiles.items():
        a, b, c = halves[0]
        pts = [a, b, halves[1][0], c] if len(halves) == 2 else [a, b, c]
        out.append((kind, [(z.real, z.imag) for z in pts], (b + c) / 2))
    return out


def draw_penrose(cv, p, cx=None, cy=None, radius=None, generations=5, rotation=0.0,
                 thick=demo.ACCENT, thin=demo.TEAL, edge=demo.BG, width=2.0, spread=0.75):
    """Draw a Penrose rhombus tiling about (cx, cy) (default the canvas centre),
    its tiles growing in from the centre outward as `p` runs 0 -> 1: each
    rhombus scales up about its own centre, the ring of tiles at distance d
    starting at `spread * d / radius`. `p` >= 1 draws the finished tiling.
    `thick` and `thin` colour the two tile shapes; `edge` outlines them."""
    cx = cv.width / 2 if cx is None else cx
    cy = cv.height / 2 if cy is None else cy
    radius = math.hypot(cv.width, cv.height) / 2 + 40 if radius is None else radius
    c = cv.ctx
    er, eg, eb, ea = rgba(edge)
    for kind, pts, mid in penrose_rhombi(generations, radius, cx, cy, rotation):
        start = spread * abs(mid - complex(cx, cy)) / radius
        s = vb.ease_out_back(vb.clamp01((p - start) / (1 - spread))) if p < 1 else 1.0
        if s <= 0:
            continue
        mx, my = mid.real, mid.imag
        c.new_path()
        for i, (x, y) in enumerate(pts):
            (c.move_to if i == 0 else c.line_to)(mx + (x - mx) * s, my + (y - my) * s)
        c.close_path()
        c.set_source_rgba(*rgba(thick if kind == THICK else thin))
        c.fill_preserve()
        c.set_source_rgba(er, eg, eb, ea)
        c.set_line_width(width)
        c.stroke()


def draw(n, cv):
    t = n / demo.FPS
    draw_penrose(cv, demo.phase(n, 0.15, 2.4), rotation=0.06 * t, generations=5)


TECHNIQUE = Technique(
    id='penrose-tiling',
    name='Penrose tiling',
    family='particles',
    group='Tiling & patterns',
    aliases=('penrose rhombus tiling', 'aperiodic tiling', 'quasicrystal pattern', 'P3 tiling'),
    definition='Two kinds of rhombus, one wide and one slim, lock together into a star-shaped, '
               'five-fold pattern that spreads across the frame without ever repeating.',
    phrasings=('fill the screen with that never-repeating pattern of fat and skinny diamonds',
               'a five-pointed star mosaic of rhombus tiles growing out from the middle',
               'an aperiodic diamond tile background like a quasicrystal'),
    related=('pattern-tiling', 'tessellation-triangle-flip', 'mosaic-tiling', 'radial-repeater', 'tile-flip',
             'tesseract-rotation'),
    api=('videobuilder.techniques.particles.penrose_tiling.draw_penrose',
         'videobuilder.techniques.particles.penrose_tiling.penrose_rhombi',
         'videobuilder.techniques.particles.penrose_tiling.penrose_triangles'),
    demo=lambda: demo.film(draw),
)
