"""Multiplane camera: flat painted planes hang at set distances in front of
the lens, and as the camera trucks and pushes in each plane slides and grows
by its own amount -- near planes a lot, far ones barely -- so a flat picture
gains real depth. Unlike `videobuilder.parallax` (side-scrolling tiles), the
camera here also moves along z, with true perspective scale per plane."""
from dataclasses import dataclass
from typing import Callable

import videobuilder as vb

from .. import _demo as demo
from ...parallax import ridge
from ...paths import draw as draw_path
from ..schema import Capability


@dataclass(frozen=True)
class Plane:
    """One flat plane of artwork. `draw(cv)` paints it centred on (0, 0), at
    the size it should appear with the camera at rest; `z` is its distance
    from the camera's rest position (any unit, larger is further away)."""
    z: float
    draw: Callable


def plane_transform(z, camera, focal=1.0, center=(0.0, 0.0)):
    """Where a plane at distance `z` lands for `camera` (x, y, z): the
    `(dx, dy, scale)` to draw its artwork with, or None if the camera has
    reached or passed it. The camera's x, y are px of pan as felt by a plane
    at distance `focal`; a plane at `z` slides `focal / (z - camera z)` times
    that, and grows `z / (z - camera z)` as the camera pushes in."""
    cx, cy, cz = camera
    d = z - cz
    if d <= 1e-3:
        return None
    return center[0] - cx * focal / d, center[1] - cy * focal / d, z / d


def multiplane(cv, planes, camera, focal=1.0, center=None, near=0.05):
    """Draw `planes` (any order; drawn far first) as seen from `camera`
    (x, y, z). `center` is the frame point the rest view is centred on
    (default the middle of the frame). Planes closer to the camera than
    `near` are skipped, so a push-in can fly through the foreground."""
    center = center or (cv.width / 2, cv.height / 2)
    for plane in sorted(planes, key=lambda p: -p.z):
        t = plane_transform(plane.z, camera, focal, center)
        if t is None or plane.z - camera[2] < near:
            continue
        dx, dy, scale = t
        with cv.layer(dx=dx, dy=dy, scale=scale):
            plane.draw(cv)


# ---- the demo: four glass panes of a night landscape, seen from off-axis, then lined up ----

PW, PH = 1440, 820       # the panes' artwork is laid out for a 1920-wide frame, then scaled by K
K = demo.W / 1920
SUN, MOUNT, HILL, TREE, ARCH, EDGE = '#f2b630', '#6c78b0', '#4b5687', '#262d4a', '#8f8ff2', '#a9b1dc'
HILLS = ridge(PW, 110, seed=4)


def _pane(art):
    """A pane of tinted glass with a thin edge, `art` clipped inside it."""
    def draw(cv):
        x, y = -PW / 2, -PH / 2
        with cv.layer(scale=K):
            cv.rect(x, y, PW, PH, '#3b4672', alpha=0.22)
            with cv.clip(x, y, PW, PH):
                art(cv)
            cv.outline(x, y, PW, PH, EDGE, width=3, alpha=0.6)
    return draw


def _sky(cv):
    cv.rect(-PW / 2, -PH / 2, PW, PH, '#2a3256', alpha=0.6)
    cv.arc(-150, -150, 62, 0, 6.2832, SUN, width=22)


def _mountains(cv):
    pts = [(-PW / 2, 60), (-330, -40), (-180, 30), (40, -150), (260, 20), (400, -60), (PW / 2, 10),
           (PW / 2, PH / 2), (-PW / 2, PH / 2)]
    draw_path(cv, pts, MOUNT, fill=True)


def _hills(cv):
    pts = [(-PW / 2 + x, 90 + y) for x, y in HILLS] + [(PW / 2, PH / 2), (-PW / 2, PH / 2)]
    draw_path(cv, pts, HILL, fill=True)
    for ax in (-260, 300):
        cv.arc(ax, 70, 48, 3.1416, 6.2832, ARCH, width=12)
        cv.line(ax - 48, 70, ax - 48, 150, ARCH, width=12)
        cv.line(ax + 48, 70, ax + 48, 150, ARCH, width=12)


def _tree(cv, x, base, h):
    cv.rect(x - 9, base - h * 0.35, 18, h * 0.35 + 60, TREE)
    draw_path(cv, [(x, base - h), (x + h * 0.32, base - h * 0.3), (x - h * 0.32, base - h * 0.3)], TREE, fill=True)


def _trees(cv):
    _tree(cv, -470, 140, 300)
    _tree(cv, 430, 150, 360)
    cv.rect(-PW / 2, 230, PW, 90, TREE)


PLANES = (Plane(4.0, _pane(_sky)), Plane(2.6, _pane(_mountains)), Plane(1.7, _pane(_hills)),
          Plane(1.15, _pane(_trees)))


def draw(n, cv):
    # The camera starts back and off to the left, so the panes stand apart in
    # a staggered stack, then trucks right and pushes in until they line up
    # as one picture, the near trees sliding and growing far more than the sun.
    p = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.7))
    cam = (K * (-1200 + 1400 * p), K * (-300 + 320 * p), -0.9 + 1.0 * p)
    multiplane(cv, PLANES, cam)
    cv.mark('planes', demo.W / 2 - K * PW / 2, demo.H / 2 - K * PH / 2, K * PW, K * PH)


CAPABILITY = Capability(
    id='multiplane-camera',
    name='Multiplane camera',
    family='camera',
    group='Depth',
    aliases=('multiplane parallax', 'multiplane shot'),
    definition='Flat layers of artwork are stacked at different distances from the lens, so when the '
               'camera moves past or into them the near layers shift and grow more than the far ones.',
    phrasings=('split the illustration into foreground, middle and background sheets and fly the camera through them',
               'an old-school animated depth shot where the trees slide past faster than the mountains',
               'push into a layered flat scene so it feels three-dimensional'),
    related=('multiples', 'zoom-to-location-map', 'fly-through', 'pan', 'orbit-shot', 'truck'),
    api=('videobuilder.capabilities.camera.multiplane_camera.multiplane',
         'videobuilder.capabilities.camera.multiplane_camera.Plane',
         'videobuilder.capabilities.camera.multiplane_camera.plane_transform'),
    demo=lambda: demo.film(draw),
)
