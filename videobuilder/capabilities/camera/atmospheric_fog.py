"""Atmospheric Fog: everything is tinted toward one haze colour by how far it
is from the camera, so near shapes stay dark and crisp while distant ones
lose contrast and melt into the air behind them."""
import math

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def fog_amount(depth, density, start=0.0):
    """How much fog covers something `depth` away from the camera, 0 (clear)
    -> 1 (lost in the fog): exponential fog, `1 - exp(-density * d)` for the
    distance `d` past `start`. Double `density` and the same fog sits at half
    the distance."""
    if density <= 0:
        return 0.0
    return 1 - math.exp(-density * max(0.0, depth - start))


def fogged(color, fog_color, amount):
    """`color` blended toward `fog_color` by `amount` (0 -> 1), as an
    (r, g, b, a) tuple of 0-255 channels and 0-1 alpha that any canvas call
    takes as a colour. Alpha is kept from `color`."""
    r0, g0, b0, a = rgba(color)
    r1, g1, b1, _ = rgba(fog_color)
    k = vb.clamp01(amount)
    return tuple(255 * (x + (y - x) * k) for x, y in ((r0, r1), (g0, g1), (b0, b1))) + (a,)


def fog_gradient(x0, y0, x1, y1, color, fog_color, near, far, density, start=0.0, stops=6):
    """A cairo linear gradient from (x0, y0) to (x1, y1) for a flat face whose
    depth runs from `near` at (x0, y0) to `far` at (x1, y1), fogged at each of
    `stops` points. Set it as the source to fill a receding face (a wall, the
    ground) so its far end fades properly instead of in one flat tint.

    The gradient is perspective-correct: on screen, a receding face's depth
    goes as 1/z, not z, so it is 1/depth that runs evenly from end to end and
    most of the length sits close to the camera. `far` may be `math.inf` for
    a face that runs out to the horizon. Fog climbs steeply near the far end,
    so give a long face (the ground) a dozen or more stops."""
    g = cairo.LinearGradient(x0, y0, x1, y1)
    inv_near, inv_far = 1 / max(near, 1e-6), 1 / max(far, 1e-6)
    for i in range(stops):
        t = i / (stops - 1)
        inv = inv_near + (inv_far - inv_near) * t
        depth = 1 / inv if inv > 0 else math.inf
        r, gr, b, a = fogged(color, fog_color, fog_amount(depth, density, start))
        g.add_color_stop_rgba(t, r / 255, gr / 255, b / 255, a)
    return g


FOG = '#7d89a6'
FRONT, SIDE, GROUND = '#252b3a', '#171c28', '#1b1f2a'
FOCAL = 300           # px per unit of world distance at depth 1
EYE_Y = 0.46          # the horizon, as a fraction of the frame height
FLOOR, TOP = 1.5, -1.9  # world y of the ground and the pillar tops (y down; the eye is at 0)
FOG_START = 2.0       # the fog only starts this far from the camera, so the nearest pillars stay crisp


def _project(x, y, z):
    return demo.W / 2 + x * FOCAL / z, demo.H * EYE_Y + y * FOCAL / z


def _poly(cv, pts, source):
    c = cv.ctx
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source(source) if isinstance(source, cairo.Pattern) else c.set_source_rgba(*rgba(source))
    c.fill()


def _pillar(cv, x, z, density, w=1.1, d=0.9):
    """One box pillar at lateral `x`, nearest face at depth `z`: the face
    toward the corridor (graded from near to far) then the front."""
    inner = x - w / 2 if x > 0 else x + w / 2
    outer = x + w / 2 if x > 0 else x - w / 2
    side = [_project(inner, TOP, z), _project(inner, TOP, z + d), _project(inner, FLOOR, z + d),
            _project(inner, FLOOR, z)]
    (sx0, _), (sx1, _) = side[0], side[1]
    _poly(cv, side, fog_gradient(sx0, 0, sx1, 0, SIDE, FOG, z, z + d, density, FOG_START))
    (fx0, fy0), (fx1, fy1) = _project(min(inner, outer), TOP, z), _project(max(inner, outer), FLOOR, z)
    cv.rect(fx0, fy0, fx1 - fx0, fy1 - fy0, fogged(FRONT, FOG, fog_amount(z, density, FOG_START)))


def draw(n, cv):
    density = 0.01 + 0.19 * vb.ease_in_out_quart(demo.phase(n, 0.3, 2.5))
    horizon = demo.H * EYE_Y
    cv.fill(FOG)
    c = cv.ctx
    sky = cairo.LinearGradient(0, 0, 0, horizon)
    sky.add_color_stop_rgba(0, *rgba('#5d6886'))
    sky.add_color_stop_rgba(1, *rgba(FOG))
    c.rectangle(0, 0, demo.W, horizon)
    c.set_source(sky)
    c.fill()
    # the ground recedes from the bottom edge (near) up to the horizon (infinitely far): a row
    # `y` below the horizon lies at depth FLOOR * FOCAL / (y - horizon)
    near = FLOOR * FOCAL / (demo.H - horizon)
    ground = fog_gradient(0, demo.H, 0, horizon, GROUND, FOG, near, math.inf, density, FOG_START, stops=32)
    c.rectangle(0, horizon, demo.W, demo.H - horizon)
    c.set_source(ground)
    c.fill()
    for z in reversed([3.2 + 2.2 * i for i in range(14)]):  # far to near
        for x in (-2.0, 2.0):
            _pillar(cv, x, z, density)


CAPABILITY = Capability(
    id='atmospheric-fog',
    name='Atmospheric fog',
    family='camera',
    group='Depth',
    aliases=('distance fog', 'depth fog', 'aerial perspective', 'atmospheric haze', 'mist'),
    definition='Things farther from the camera are washed toward a single haze colour, so the '
               'distance goes pale and flat while the foreground keeps its contrast.',
    phrasings=('add some mist so the far-off stuff fades into the background',
               'make the scene feel deep by hazing out whatever is far away',
               'roll in fog so the end of the corridor disappears'),
    related=('heat-haze', 'smoke-dissolve', 'rain-on-glass', 'god-rays', 'aurora-gradient-background',
             'drop-shadow-breathing'),
    api=('videobuilder.capabilities.camera.atmospheric_fog.fog_amount',
         'videobuilder.capabilities.camera.atmospheric_fog.fogged',
         'videobuilder.capabilities.camera.atmospheric_fog.fog_gradient'),
    demo=lambda: demo.film(draw),
)
