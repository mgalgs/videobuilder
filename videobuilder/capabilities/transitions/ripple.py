"""Ripple: a wave front spreads out in rings from a point, bending the
picture like water as it passes, and leaves the next scene behind it."""
import math

import cairo
from PIL import Image

from .. import _demo as demo
from ..schema import Technique
from ...canvas import Canvas
from ...looks.fx import image_surface, surface_image


def _offscreen(cv, scene):
    """`scene` drawn into a fresh canvas the size, scale and transform of `cv`;
    returns its device pixels as a PIL RGB image."""
    sub = Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    sub.ctx.set_matrix(cv.ctx.get_matrix())
    scene(sub)
    return surface_image(sub.surface)


def _warp(im, shift, step):
    """`im` resampled through a grid mesh: each output vertex (x, y) reads
    from `shift(x, y)`."""
    w, h = im.size
    xs = list(range(0, w, step)) + [w]
    ys = list(range(0, h, step)) + [h]
    src = {(x, y): shift(x, y) for x in xs for y in ys}
    mesh = []
    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            mesh.append(((x0, y0, x1, y1), (*src[x0, y0], *src[x0, y1], *src[x1, y1], *src[x1, y0])))
    return im.transform((w, h), Image.Transform.MESH, mesh, resample=Image.Resampling.BILINEAR)


def ripple(cv, a, b, p, center=(0.5, 0.5), wavelength=0.07, amplitude=0.022, rings=3, glints=True):
    """Draw the ripple at progress `p` (0 -> 1): a ring-shaped wave front
    grows from `center` (fractions of the frame) until it has left every
    corner. Ahead of the front is `a(cv)`, behind it `b(cv)`; both are bent
    radially by the same travelling wave, so the picture swells and ebbs as
    the rings pass, then settles flat on `b`.

    `wavelength` and `amplitude` are fractions of the frame's diagonal;
    `rings` is how many crests trail inside the front; `glints` adds faint
    light lines on the crests, like light catching water.

    In a film, call it while two shots are live in an overlap, e.g.
    `ripple(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    if p <= 0:
        return a(cv)
    if p >= 1:
        return b(cv)
    ia, ib = _offscreen(cv, a), _offscreen(cv, b)
    sw, sh = ia.size
    diag = math.hypot(sw, sh)
    cx, cy = center[0] * sw, center[1] * sh
    lam = wavelength * diag
    reach = max(math.hypot(cx - x, cy - y) for x in (0, sw) for y in (0, sh))
    front = p * (reach + (rings + 1.5) * lam)        # all the rings are off the frame at p = 1
    amp = amplitude * diag * math.sin(math.pi * p) ** 0.6
    trail = rings * lam

    def bend(r):
        """Radial displacement at distance `r`: a wave packet riding the front."""
        u = r - front
        env = math.exp(-(u / (0.6 * lam)) ** 2) if u > 0 else math.exp(-(u / (0.55 * trail + 1e-9)) ** 2)
        return amp * env * math.sin(2 * math.pi * u / lam)

    def shift(x, y):
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        if r < 1e-6:
            return x, y
        d = bend(r)
        return min(max(x - dx / r * d, 0), sw - 1), min(max(y - dy / r * d, 0), sh - 1)  # never read off the frame

    step = max(6, round(min(sw, sh) / 36))
    sa, sb = image_surface(_warp(ia, shift, step)), image_surface(_warp(ib, shift, step))
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(sa, 0, 0)
    c.paint()
    edge = 0.35 * lam                                 # the front is a soft edge, not a hard line
    mask = cairo.RadialGradient(cx, cy, max(0.0, front - edge), cx, cy, front + edge)
    mask.add_color_stop_rgba(0, 0, 0, 0, 1)
    mask.add_color_stop_rgba(1, 0, 0, 0, 0)
    c.set_source_surface(sb, 0, 0)
    c.mask(mask)
    if glints:
        for k in range(-rings, 1):                    # one glint per crest, brightest at the front
            r = front + (k + 0.25) * lam
            if r <= 0:
                continue
            strength = abs(bend(r)) / (amplitude * diag + 1e-9)
            c.new_path()
            c.arc(cx, cy, r, 0, 2 * math.pi)
            c.set_line_width(max(1.0, 0.12 * lam))
            c.set_source_rgba(1, 1, 1, 0.35 * strength)
            c.stroke()
    c.restore()


TECHNIQUE = Technique(
    id='ripple',
    name='Ripple',
    family='transitions',
    group='Organic and Fluid',
    aliases=('ripple dissolve', 'water ripple transition', 'pond ripple'),
    definition='Rings spread outward from a point like a stone dropped in a pond, warping the picture '
               'as they pass, and the new scene is left calm behind them.',
    phrasings=('make the next shot ripple in like water',
               'drop a pebble in the middle and let the waves carry us to the next scene',
               'a watery wave transition spreading out from the centre'),
    related=('refraction-ripple', 'ripple-displacement', 'height-field-ripples', 'ripple-rings',
             'ridgeline-ripple', 'wave-deformer'),
    api=('videobuilder.techniques.transitions.ripple.ripple',),
    demo=lambda: demo.two_scenes(ripple, start=0.5, length=2.0),
)
