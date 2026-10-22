"""Effector-driven instances: a grid of identical clones, each lifted, grown,
turned and recoloured by how close it sits to a moving falloff zone, so a
bulge of change travels across the set while the clones outside it rest."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..shapes.isometric_bar_rise import COS, SIN, draw_iso_floor, iso, shade
from ...looks import kit as looks


def falloff(d, radius, softness=0.6):
    """An effector's strength at distance `d` from its centre: 1 within the
    hard core (`radius * (1 - softness)`), easing smoothly to 0 at `radius`."""
    inner = radius * (1 - softness)
    if d <= inner:
        return 1.0
    if d >= radius:
        return 0.0
    t = (radius - d) / (radius - inner)
    return t * t * (3 - 2 * t)


def effector_weights(points, centre, radius, softness=0.6):
    """For each `(x, y)` in `points` (any units), the strength of a spherical
    effector at `centre` with the given `radius` (see `falloff`)."""
    cx, cy = centre
    return [falloff(math.hypot(x - cx, y - cy), radius, softness) for x, y in points]


def _iso_cube(cv, ox, oy, gx, gy, half, height, z, turn, color, tile, outline):
    """A box centred on grid point (gx, gy), `half` cells from centre to side,
    turned `turn` radians about its vertical axis, its base `z` px up."""
    c, s = math.cos(turn), math.sin(turn)
    base = [(gx + c * a - s * b, gy + s * a + c * b) for a, b in ((-half, -half), (half, -half),
                                                                  (half, half), (-half, half))]
    P = lambda pt, h: iso(ox, oy, pt[0], pt[1], h, tile)  # noqa: E731
    line = dict(outline=outline, width=1.2) if outline else {}
    for i in range(4):
        a, b = base[i], base[(i + 1) % 4]
        nx, ny = b[1] - a[1], -(b[0] - a[0])  # outward normal (corners run anticlockwise on screen)
        facing = (nx + ny) / (math.hypot(nx, ny) * math.sqrt(2) or 1)
        if facing > 0:  # the viewer looks along -(1, 1) in grid space
            k = 0.22 + 0.3 * (1 - facing) + 0.12 * (nx - ny) / (math.hypot(nx, ny) or 1)
            looks.fill(cv, [P(a, z), P(b, z), P(b, z + height), P(a, z + height)], shade(color, k), **line)
    looks.fill(cv, [P(pt, z + height) for pt in base], color, **line)


def effector_instances(cv, ox, oy, cols, rows, centre, radius, tile=60.0, size=0.62, height=None,
                       lift=70.0, grow=0.45, turn=math.pi / 4, color=demo.TEAL, hot=demo.ACCENT,
                       softness=0.6, outline=None):
    """Draw a `cols` x `rows` isometric grid of cubes (grid origin at screen
    (ox, oy), `tile` px per cell) under one spherical effector at `centre`
    (grid units, fractional) reaching `radius` cells. Each cube's strength
    `w` (see `falloff`) raises it by `lift * w` px, scales it by `1 + grow * w`,
    turns it `turn * w` about its vertical axis and mixes its colour from
    `color` to `hot`. Painted back to front. Returns the strengths, row by row."""
    height = tile * size * COS if height is None else height
    cells = [(c + 0.5, r + 0.5) for r in range(rows) for c in range(cols)]
    weights = effector_weights(cells, centre, radius, softness)
    for i in sorted(range(len(cells)), key=lambda i: (cells[i][0] + cells[i][1], cells[i][0])):
        (gx, gy), w = cells[i], weights[i]
        k = 1 + grow * w
        _iso_cube(cv, ox, oy, gx, gy, size / 2 * k, height * k, lift * w, turn * w,
                  demo.kit.mix(color, hot, w), tile, outline)
    return weights


def _ring(cv, ox, oy, centre, r, tile, alpha):
    pts = [iso(ox, oy, centre[0] + r * math.cos(a), centre[1] + r * math.sin(a), 0, tile)
           for a in (2 * math.pi * i / 72 for i in range(73))]
    looks.outline(cv, pts, demo.INK, 2, alpha=alpha)


COLS, ROWS, TILE, RADIUS = 11, 8, 44, 2.8


def draw(n, cv):
    ox, oy = demo.W / 2 + (ROWS - COLS) * TILE * COS / 2, demo.H / 2 - (COLS + ROWS) * TILE * SIN / 2 + 50
    # The effector sweeps from one end of the grid to the other on a gentle S.
    p = vb.ease_in_out_quart(demo.phase(n, 0.0, 3.0))
    gx = 0.5 + (COLS - 1) * p
    gy = ROWS / 2 + 1.8 * math.sin(2 * math.pi * p)
    draw_iso_floor(cv, ox, oy, COLS, ROWS, TILE, color=demo.LINE)
    _ring(cv, ox, oy, (gx, gy), RADIUS, TILE, 0.7)
    _ring(cv, ox, oy, (gx, gy), RADIUS * 0.4, TILE, 0.4)
    effector_instances(cv, ox, oy, COLS, ROWS, (gx, gy), RADIUS, TILE, outline=demo.BG)
    x0, _ = iso(ox, oy, 0, ROWS, 0, TILE)
    x1, _ = iso(ox, oy, COLS, 0, 0, TILE)
    cv.mark('grid', x0, oy - 120, x1 - x0, (COLS + ROWS) * TILE * SIN + 120)


TECHNIQUE = Technique(
    id='effector-driven-instances',
    name='Effector-driven instances',
    family='camera',
    group='3D motion',
    aliases=('mograph effector', 'step effector', 'falloff animation', 'plain effector', 'cloner effector'),
    definition='A field of identical 3D copies where a moving zone of influence lifts, swells, turns and '
               'recolours each copy by how near it is, leaving a travelling bump in the set.',
    phrasings=('a grid of cubes that pop up and change colour as an invisible ball rolls through them',
               'make the clones react to a moving falloff so a wave of bigger blocks passes over the grid',
               'blocks rise and twist only near a spot that slides across the field'),
    related=('droste-effect', 'mograph-grid-flip', 'spin', 'multiples', 'isolines-contour-animation', 'offset'),
    api=('videobuilder.techniques.camera.effector_driven_instances.effector_instances',
         'videobuilder.techniques.camera.effector_driven_instances.effector_weights',
         'videobuilder.techniques.camera.effector_driven_instances.falloff'),
    demo=lambda: demo.film(draw),
)
