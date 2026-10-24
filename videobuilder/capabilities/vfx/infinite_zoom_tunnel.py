"""Infinite zoom: a picture holds a smaller framed copy of itself, which holds
a smaller copy again, and the camera keeps pushing in, so each inner copy
grows to fill the frame just as the next one arrives behind it."""
import math

from ...looks import kit as looks
from .. import _demo as demo
from ..schema import Capability


def infinite_zoom(cv, scene, travel, ratio=2.2, cx=None, cy=None, depth=None, border='#ffffff',
                  border_width=4.0, shade=0.12, smallest=4.0):
    """Draw `scene(cv)` with copies of itself nested inside, `travel` copies deep.

    Each copy is the whole frame shrunk by `ratio` about (cx, cy) (default the
    centre) and laid inside the one before it, framed by a `border` line of
    `border_width` px. Every unit of `travel` zooms in by one `ratio`, so the
    next copy has grown to exactly fill the frame: whole-number `travel`
    values look the same and any speed loops seamlessly. Animate `travel`
    (e.g. `2 * eased_progress`) to fall that many copies in.

    `shade` darkens each copy a little more than the one around it
    (0 for none), which reads as depth. Copies stop below `smallest` px wide
    or after `depth` levels. `scene` draws in the frame's own coordinates."""
    w, h = cv.width, cv.height
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    frac = travel - math.floor(travel)
    zoom = ratio ** frac
    levels = depth if depth is not None else math.ceil(math.log(w * zoom / smallest) / math.log(ratio))
    for k in range(levels + 1):  # outermost first; each copy covers the middle of the one before
        s = zoom / ratio ** k
        if w * s < smallest:
            break
        x, y = cx - cx * s, cy - cy * s  # the copy's top-left: (cx, cy) stays put under scaling
        with cv.clip(x, y, w * s, h * s):
            with cv.layer(dx=x, dy=y, scale=s):
                scene(cv)
            if shade and k:
                cv.fill('#000000', alpha=min(0.6, shade * (k - frac)))
        if k and border_width:
            # thinner as copies recede; fades out as a copy reaches the frame edge, where it takes over
            cv.outline(x, y, w * s, h * s, border, width=max(1.0, border_width * min(1.0, 2 * s)),
                       alpha=min(1.0, 6 * (1 - s)))


SKY, HILL_FAR, HILL_NEAR, SUN = '#4b5aa8', '#6e7cc4', '#252a4a', '#f2b830'


def landscape(cv):
    """The demo's scene: a dusk sky, an off-centre sun and two rows of hills,
    so the nested copies trail a line of shrinking suns into the distance."""
    W, H = demo.W, demo.H
    cv.fill(SKY)
    cv.rect(0, H * 0.45, W, H * 0.55, '#8b97dc', alpha=0.35)
    looks.disc(cv, W * 0.70, H * 0.36, H * 0.14, SUN)
    far = [(x, H * 0.60 + H * 0.06 * math.sin(x / W * 7.0 + 1.0)) for x in range(0, W + 41, 40)]
    near = [(x, H * 0.76 + H * 0.07 * math.sin(x / W * 5.0 + 3.2)) for x in range(0, W + 41, 40)]
    looks.fill(cv, far + [(W + 40, H), (0, H)], HILL_FAR)
    looks.fill(cv, near + [(W + 40, H), (0, H)], HILL_NEAR)


def draw(n, cv):
    p = demo.phase(n, 0.0, demo.SECONDS)
    infinite_zoom(cv, landscape, 2.0 * p)  # two whole copies deep, so the last frame matches the first
    cv.mark('tunnel', demo.W / 2 - 60, demo.H / 2 - 34, 120, 68)


CAPABILITY = Capability(
    id='infinite-zoom-tunnel',
    name='Infinite zoom',
    family='vfx',
    group='Symmetry & geometry',
    aliases=('infinite zoom tunnel', 'zoom tunnel', 'recursive zoom', 'Matryoshka zoom', 'Droste zoom',
             'Droste effect', 'mise en abyme', 'recursive picture'),
    definition='The picture contains a smaller framed copy of itself, which contains another, and the camera '
               'pushes in without end as each inner copy swells to fill the screen.',
    phrasings=('a zoom that never stops going in',
               'the image keeps showing up inside itself as we push in',
               'pictures nested inside pictures, zooming in forever'),
    related=('zoom-through-shape', 'canvas-pan-and-zoom', 'zoom-through', 'scale-zoom-through',
             'ui-walkthrough-camera-zoom', 'zoom-to-location-map'),
    api=('videobuilder.capabilities.vfx.infinite_zoom_tunnel.infinite_zoom',),
    demo=lambda: demo.film(draw),
)
