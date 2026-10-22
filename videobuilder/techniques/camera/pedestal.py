"""Pedestal: the camera rises (or sinks) straight up its column while still
looking level, so the horizon stays put in the frame and everything in front
slides down past it -- the nearest things most -- and the tops of things come
into view."""
from .. import _demo as demo
from ..schema import Technique
from ... import paths
from ...ease import ease_in_out_quart

FOCAL = 560  # px: how large one world unit draws at a distance of one unit


def pedestal_project(x, y, z, height, focal=FOCAL, center=(demo.W / 2, demo.H / 2)):
    """Where the world point (x, y, z) lands in the frame, seen by a level
    camera standing `height` units up. x runs right, y up from the ground, z
    away from the camera (> 0). The camera never tilts, so the horizon is
    always at `center`'s y; raising `height` only slides points down, each by
    `focal * rise / z`.

    In a film, drive `height` with `pedestal_height` and project every corner
    of the set through this: `pedestal_project(x, 0, z, pedestal_height(p, 0.5, 2.5))`."""
    cx, cy = center
    return cx + focal * x / z, cy - focal * (y - height) / z


def pedestal_height(p, low, high, ease=ease_in_out_quart):
    """The camera's height at progress `p` (0 -> 1) of a pedestal from `low`
    to `high` units (swap them to pedestal down), eased in and out."""
    return low + (high - low) * ease(p)


def pedestal_shift(z, rise, focal=FOCAL):
    """How many px a flat layer `z` units from the camera slides down in the
    frame when the camera rises `rise` units (negative: it sinks). For a film
    of flat layers: `with cv.layer(dy=pedestal_shift(z, rise)): layer(cv)`,
    with a far sky (large z) barely moving and the foreground moving most."""
    return focal * rise / z


# ---- the demo: a gold ball on a plinth under a gateway, the camera rising ----
_LOW, _HIGH = 0.45, 2.9
_STONE, _STONE_TOP, _STONE_SIDE = '#3a3f4a', '#4d5361', '#2c3039'
_GATE, _GATE_TOP, _GATE_SIDE = '#6d78d8', '#8f99ec', '#525cb0'
_GOLD = '#f2b632'


def _box(cv, x0, x1, y0, y1, z0, z1, h, colors):
    """A box from x0..x1, y0..y1 (ground up), z0..z1 (near to far): its top if
    the camera is above it, the side facing the camera's column, then its front."""
    front, top, side = colors
    P = lambda x, y, z: pedestal_project(x, y, z, h)  # noqa: E731
    if h > y1:
        paths.draw(cv, [P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], top, fill=True)
    if x0 > 0:
        paths.draw(cv, [P(x0, y0, z0), P(x0, y1, z0), P(x0, y1, z1), P(x0, y0, z1)], side, fill=True)
    elif x1 < 0:
        paths.draw(cv, [P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], side, fill=True)
    paths.draw(cv, [P(x0, y0, z0), P(x1, y0, z0), P(x1, y1, z0), P(x0, y1, z0)], front, fill=True)


def _draw(n, cv):
    p = demo.phase(n, 0.4, 2.6)
    h = pedestal_height(p, _LOW, _HIGH)
    P = lambda x, y, z: pedestal_project(x, y, z, h)  # noqa: E731

    # the ground: a grid running from under the camera out towards the horizon
    for x in range(-12, 13):
        cv.line(*P(x, 0, 2.2), *P(x, 0, 60), demo.LINE, width=2, alpha=0.7)
    for z in (2.5, 3, 3.6, 4.3, 5.2, 6.3, 7.6, 9.2, 11, 13.5, 17, 22, 30, 42):
        cv.line(*P(-14, 0, z), *P(14, 0, z), demo.LINE, width=2, alpha=0.7)

    # far to near: a row of posts with a rail, the gateway, the plinth and its ball
    rail_y = 2.0
    cv.line(*P(-14, rail_y, 16), *P(14, rail_y, 16), _STONE_TOP, width=8)
    for x in (-8, -4, 0, 4, 8):
        _box(cv, x - 0.35, x + 0.35, 0, 3.2, 16, 16.7, h, (_STONE, _STONE_TOP, _STONE_SIDE))
    for x0 in (-2.4, 2.0):
        _box(cv, x0, x0 + 0.4, 0, 2.6, 9, 9.4, h, (_GATE, _GATE_TOP, _GATE_SIDE))
    _box(cv, -2.4, 2.4, 2.6, 2.9, 9, 9.4, h, (_GATE, _GATE_TOP, _GATE_SIDE))
    _box(cv, -0.8, 0.8, 0, 0.9, 5.2, 6.6, h, (_STONE, _STONE_TOP, _STONE_SIDE))
    bx, by = P(0, 1.35, 5.9)
    r = FOCAL * 0.45 / 5.9
    demo.dot(cv, bx, by, r=r, color=_GOLD)
    demo.dot(cv, bx - r * 0.3, by - r * 0.35, r=r * 0.3, color='#ffe9a8', alpha=0.6)

    # the camera's column at the left edge: the level eye rides up it
    x, top, bottom = 70, 140, demo.H - 140
    cv.line(x, top, x, bottom, demo.MUTED, width=3, alpha=0.6)
    y = bottom - (bottom - top) * (h - _LOW) / (_HIGH - _LOW)
    demo.dot(cv, x, y, r=16, color=demo.TEAL)
    cv.line(x + 22, y, x + 60, y, demo.TEAL, width=4)


TECHNIQUE = Technique(
    id='pedestal',
    name='Pedestal',
    family='camera',
    group='Camera moves',
    aliases=('pedestal up', 'pedestal down', 'vertical track', 'boom up'),
    definition='The camera rises or sinks straight up and down while still looking level, '
               'so the scene slides down or up past a fixed horizon, nearby things fastest.',
    phrasings=('raise the camera straight up without tilting it',
               'lift the view higher so we look down onto the tops of things',
               'move the camera down to ground level but keep it facing forward'),
    related=('three-d-tilt-on-hover', 'isometric-view', 'perspective-crawl', 'flip',
             'tilt-shift-miniature', 'carousel-slide'),
    api=('videobuilder.techniques.camera.pedestal.pedestal_project',
         'videobuilder.techniques.camera.pedestal.pedestal_height',
         'videobuilder.techniques.camera.pedestal.pedestal_shift'),
    demo=lambda: demo.film(_draw),
)
