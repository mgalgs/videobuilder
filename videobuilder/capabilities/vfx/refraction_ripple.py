"""Refraction ripple: a ring of waves runs out from a point across a still
picture, and wherever it passes the picture bends as if seen through rippled
glass, with a faint sheen on the crests; behind the wave it settles flat."""
import math

import cairo
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...looks.fx import image_surface, surface_image


def _pixels(cv, scene):
    """`scene(c)` drawn on a fresh canvas the size, scale and transform of
    `cv`, as a PIL RGB image of its device pixels."""
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    sub.ctx.set_matrix(cv.ctx.get_matrix())
    scene(sub)
    return surface_image(sub.surface)


def _mesh_warp(im, src, cells=56):
    """`im` resampled so each output point (x, y) shows the input at
    `src(x, y)`: a bilinear mesh of `cells` quads across."""
    w, h = im.size
    ny = max(1, round(cells * h / w))
    xs = [w * i / cells for i in range(cells + 1)]
    ys = [h * j / ny for j in range(ny + 1)]
    grid = [[src(x, y) for x in xs] for y in ys]
    mesh = []
    for j in range(ny):
        for i in range(cells):
            box = (round(xs[i]), round(ys[j]), round(xs[i + 1]), round(ys[j + 1]))
            mesh.append((box, (*grid[j][i], *grid[j + 1][i], *grid[j + 1][i + 1], *grid[j][i + 1])))
    return im.transform((w, h), Image.Transform.MESH, mesh, resample=Image.Resampling.BILINEAR)


def refraction_ripple(cv, scene, p, center=None, wavelength=90, amplitude=26, rings=3, sheen=0.25):
    """Draw `scene(cv)` with a refraction ripple at progress `p` (0 -> 1).

    A packet of `rings` concentric waves leaves `center` (film px, default
    the frame centre) at p = 0 and has run past every corner by p = 1. Each
    point the packet covers is pushed toward or away from the centre by up
    to `amplitude` film px, so edges in the picture bow and wobble like light
    through a lens of water; the waves weaken as they spread. `wavelength`
    is the crest spacing in film px. `sheen` (0 = none) lays a faint light
    on the slopes facing the centre and a shade on the far ones, which sells
    the glassy refraction. Outside 0 < p < 1 the scene is drawn untouched.

    It bends whatever `scene` draws: a photo, a title card, a whole shot,
    e.g. `refraction_ripple(cv, lambda c: shot(c, n), (n - hit) / (1.5 * fps), center=impact_xy)`
    to send a shockwave out from an impact."""
    if p <= 0 or p >= 1:
        return scene(cv)
    s = cv.scale
    cx, cy = center or (cv.width / 2, cv.height / 2)
    cx, cy = cx * s, cy * s
    lam = wavelength * s
    im = _pixels(cv, scene)
    w, h = im.size
    reach = max(math.hypot(cx - x, cy - y) for x in (0, w) for y in (0, h))
    trail = rings * lam
    front = p * (reach + trail + lam)                 # the whole packet is off the frame at p = 1
    amp = amplitude * s * min(1.0, p / 0.08) * (1 - p) ** 1.2

    def bend(r):
        """Outward push at distance `r`: a wave train riding just inside the front."""
        u = r - front
        if u > 0:
            env = math.exp(-(u / (0.45 * lam)) ** 2)      # a steep leading edge
        else:
            env = math.exp(-(u / (0.6 * trail + 1e-9)) ** 2)
        return amp * env * math.sin(2 * math.pi * u / lam) * min(1.0, r / lam)  # still at the very centre

    def src(x, y):
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        if r < 1e-6:
            return x, y
        d = bend(r)
        return min(max(x - dx / r * d, 0), w - 1), min(max(y - dy / r * d, 0), h - 1)

    out = image_surface(_mesh_warp(im, src))
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(out, 0, 0)
    c.paint()
    if sheen > 0 and amp > 0:
        # Light where the push is growing (the image is stretched toward us),
        # shade where it is shrinking: the derivative of `bend`, as a radial gradient.
        r0, r1 = max(0.0, front - 2.2 * trail), front + 1.2 * lam
        g = cairo.RadialGradient(cx, cy, r0, cx, cy, r1)
        steps = 64
        slopes = []
        for k in range(steps + 1):
            r = r0 + (r1 - r0) * k / steps
            slopes.append((bend(r + 1) - bend(r - 1)) / 2)
        peak = 2 * math.pi * amplitude * s / lam      # the steepest slope the wave can reach
        for k, sl in enumerate(slopes):
            v = max(-1.0, min(1.0, sl / peak))
            tone = 1.0 if v > 0 else 0.0
            g.add_color_stop_rgba(k / steps, tone, tone, tone, sheen * abs(v))
        c.set_source(g)
        c.paint()
    c.restore()


# ---- demo ----

def _scene(cv):
    """A photo with a clean grid of thin lines over it, so the bend reads."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    for x in range(0, demo.W + 1, 120):
        cv.line(x, 0, x, demo.H, demo.INK, width=2, alpha=0.24)
    for y in range(0, demo.H + 1, 120):
        cv.line(0, y, demo.W, y, demo.INK, width=2, alpha=0.24)


def draw(n, cv):
    p = demo.phase(n, 0.35, 2.75)
    refraction_ripple(cv, _scene, p, center=(demo.W * 0.5, demo.H * 0.5))


CAPABILITY = Capability(
    id='refraction-ripple',
    name='Refraction ripple',
    family='vfx',
    group='Distortion & displacement',
    aliases=('ripple distortion', 'shockwave distortion', 'ripple warp', 'shockwave'),
    definition='A ring of waves spreads out from one point over a still picture, bending everything under '
               'it as if seen through rippling glass, and the picture lies flat again once it has passed.',
    phrasings=('send a shockwave out from the middle that warps the image',
               'make the picture wobble like water where the ripple rings go by',
               'a glassy distortion ring expanding across the frame'),
    related=('ripple-rings', 'ripple', 'ripple-displacement', 'height-field-ripples', 'wave-deformer',
             'glass-refraction'),
    api=('videobuilder.capabilities.vfx.refraction_ripple.refraction_ripple',),
    demo=lambda: demo.film(draw),
)
