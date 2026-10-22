"""Truck: the camera slides sideways along the scene, so every plane shifts
the other way, the near ones fast and the far ones slowly. Unlike
`videobuilder.parallax`, whose layers are endless repeated tiles, the planes
here are placed once, so a shot can move past a few set pieces."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def truck(cv, planes, camera_x, origin=0.0):
    """Draw `planes` with the camera trucked to `camera_x` px. `planes` is a
    sequence of `(depth, draw)`, listed far first; each `draw(cv)` paints its
    plane as framed with the camera at `origin`, and is shifted by
    `-(camera_x - origin) * depth`. Depth 1 is the subject's plane, under 1
    is behind it and slides less, over 1 is foreground that sweeps past
    faster; 0 stays put (a sky or a horizon).

    In a film, ease `camera_x` between two marks across the shot, e.g.
    `truck(cv, PLANES, -120 + 240 * vb.ease_in_out_quart(p))`."""
    for depth, draw in planes:
        with cv.layer(dx=-(camera_x - origin) * depth):
            draw(cv)


GROUND = demo.H - 140


def _far(cv):
    cv.rect(-400, GROUND - 240, demo.W + 800, 6, demo.LINE)            # a rail along the back wall
    for i in range(-3, 10):
        cv.rect(70 + i * 150, GROUND - 330, 34, 330, '#262830', radius=4)


def _subject(cv):
    cx = demo.W / 2
    cv.rect(cx - 150, GROUND - 270, 300, 14, '#7f86e6', radius=3)   # a frame around the subject
    cv.rect(cx - 150, GROUND - 270, 14, 270, '#6870d0')
    cv.rect(cx + 136, GROUND - 270, 14, 270, '#6870d0')
    cv.rect(cx - 85, GROUND - 80, 170, 80, '#3a3d48', radius=4)    # plinth
    demo.dot(cv, cx, GROUND - 80 - 52, 52, color='#f2b632')


def _ground(cv):
    for i in range(-6, 16):                                     # floor marks, to show the slide underfoot
        x = i * 90
        cv.line(x, GROUND + 30, x - 20, demo.H, demo.LINE, width=3)


def _near(cv):
    cv.rect(demo.W / 2 - 45, -20, 90, demo.H + 40, '#8a90f0')


PLANES = ((0.0, lambda cv: cv.rect(0, GROUND, demo.W, demo.H - GROUND, '#1b1d23')),
          (0.25, _far), (1.0, _subject), (1.6, _ground), (2.2, _near))


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.3, 2.7))
    truck(cv, PLANES, 150 - 300 * p)


CAPABILITY = Capability(
    id='truck',
    name='Truck',
    family='camera',
    group='Camera moves',
    aliases=('track left', 'track right', 'lateral dolly', 'crab'),
    definition='The camera glides sideways past the scene without turning, so close things sweep '
               'across the frame quickly while the background barely drifts.',
    phrasings=('move the camera sideways along the scene',
               'slide past it to the left with the foreground whipping by',
               'a sideways tracking shot with some depth'),
    related=('dolly-zoom', 'zoom-through', 'multiplane-camera', 'vhs-tracking-bar', 'zoom-to-location-map',
             'offset'),
    api=('videobuilder.capabilities.camera.truck.truck', 'videobuilder.parallax.draw'),
    demo=lambda: demo.film(draw),
)
