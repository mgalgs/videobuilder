"""Glass refraction: a clear glass ball sits over the picture, and what lies
behind it is seen bent through it -- magnified, flipped in the middle and
squeezed toward the rim, the way a real ball lens bends light."""
import math

import cairo
from PIL import Image

from .. import _demo as demo
from ..schema import Capability
from ...canvas import Canvas
from ...looks.fx import image_surface, surface_image


def _offscreen(cv, scene):
    """`scene` drawn into a fresh canvas the size, scale and transform of `cv`;
    returns its device pixels as a PIL RGB image."""
    sub = Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    sub.ctx.set_matrix(cv.ctx.get_matrix())
    scene(sub)
    return surface_image(sub.surface)


def _lens(im, cx, cy, r, strength, step, kmin=0.3):
    """The square of `im` around (cx, cy), side 2r, seen through a ball of
    radius `r`: an output point at offset d from the centre reads from
    centre + d * k, k = 1 - strength * z, z the ball's surface height there
    (1 in the middle, 0 at the rim), so the rim joins the picture outside
    seamlessly. `strength` above 1 flips the middle, like a ball lens.
    Where k nears 0 (the fold between the flipped core and the upright rim)
    the magnification would run off to infinity and smear one pixel over a
    wide band, so |k| is held at `kmin` or more there."""
    w, h = im.size
    side = max(2, math.ceil(2 * r))
    x0, y0 = cx - side / 2, cy - side / 2

    def src(u, v):
        dx, dy = x0 + u - cx, y0 + v - cy
        rho2 = (dx * dx + dy * dy) / (r * r)
        k = 1 - strength * math.sqrt(1 - rho2) if rho2 < 1 else 1.0
        if abs(k) < kmin:
            k = math.copysign(kmin, k)
        return min(max(cx + dx * k, 0), w - 1), min(max(cy + dy * k, 0), h - 1)

    cuts = list(range(0, side, step)) + [side]
    grid = {(u, v): src(u, v) for u in cuts for v in cuts}
    mesh = []
    for u0, u1 in zip(cuts, cuts[1:]):
        for v0, v1 in zip(cuts, cuts[1:]):
            mesh.append(((u0, v0, u1, v1), (*grid[u0, v0], *grid[u0, v1], *grid[u1, v1], *grid[u1, v0])))
    return im.transform((side, side), Image.Transform.MESH, mesh, resample=Image.Resampling.BILINEAR), x0, y0


def glass_refraction(cv, scene, cx, cy, radius, strength=2.0, tint=(0.82, 0.9, 1.0), gloss=True):
    """Draw `scene(cv)` with a glass ball of `radius` centred at (cx, cy)
    in front of it, refracting it.

    Inside the ball the scene is re-read through a spherical lens (see
    `_lens`): magnified, and with `strength` above 1 turned upside down in
    the middle and pinched near the rim; at 0 the glass is flat and
    invisible. `tint` is a faint RGB colour cast for the glass; `gloss`
    adds a rim light, a darker edge and a specular highlight so the ball
    reads as an object, not just a warp.

    In a film, call it in place of drawing the background, moving (cx, cy)
    frame to frame, e.g. `glass_refraction(cv, lambda c: backdrop(c, f), x, y, 120)`."""
    im = _offscreen(cv, scene)
    c = cv.ctx
    dcx, dcy = c.user_to_device(cx, cy)
    r = math.hypot(*c.user_to_device_distance(radius, 0))
    step = max(3, round(r / 40))
    lens, x0, y0 = _lens(im, dcx, dcy, r, strength, step)
    c.save()
    c.identity_matrix()
    c.set_source_surface(image_surface(im), 0, 0)
    c.paint()
    c.new_path()
    c.arc(dcx, dcy, r, 0, 2 * math.pi)
    c.clip()
    c.set_source_surface(image_surface(lens), x0, y0)
    c.paint()
    c.set_source_rgba(*tint, 0.08)
    c.paint()
    if strength > 1:
        # the fold, where the flipped core meets the upright rim, jumps between
        # mesh cells; a soft dark band hides that seam, as a real ball shows one
        fold = r * math.sqrt(1 - 1 / (strength * strength))
        w = max(2.5 * step, 0.05 * r) / r
        f = fold / r
        band = cairo.RadialGradient(dcx, dcy, 0, dcx, dcy, r)
        band.add_color_stop_rgba(max(f - w, 0), 0, 0, 0, 0)
        band.add_color_stop_rgba(f, 0, 0, 0, 0.6)
        band.add_color_stop_rgba(min(f + w, 1), 0, 0, 0, 0)
        c.set_source(band)
        c.paint()
    if gloss:
        edge = cairo.RadialGradient(dcx, dcy, 0.55 * r, dcx, dcy, r)     # glass darkens toward its edge
        edge.add_color_stop_rgba(0, 0, 0, 0, 0)
        edge.add_color_stop_rgba(0.8, 0, 0, 0, 0.12)
        edge.add_color_stop_rgba(1, 0, 0, 0, 0.4)
        c.set_source(edge)
        c.paint()
        hx, hy = dcx - 0.42 * r, dcy - 0.45 * r                          # a window light, upper left
        spec = cairo.RadialGradient(hx, hy, 0, hx, hy, 0.32 * r)
        spec.add_color_stop_rgba(0, 1, 1, 1, 0.85)
        spec.add_color_stop_rgba(0.25, 1, 1, 1, 0.45)
        spec.add_color_stop_rgba(1, 1, 1, 1, 0)
        c.set_source(spec)
        c.paint()
        bounce = cairo.RadialGradient(dcx + 0.35 * r, dcy + 0.6 * r, 0, dcx + 0.35 * r, dcy + 0.6 * r, 0.5 * r)
        bounce.add_color_stop_rgba(0, *tint, 0.18)                       # light caught low in the glass
        bounce.add_color_stop_rgba(1, *tint, 0)
        c.set_source(bounce)
        c.paint()
    c.reset_clip()
    if gloss:
        c.new_path()
        c.arc(dcx, dcy, r - 0.75, 0, 2 * math.pi)
        c.set_line_width(max(1.0, r / 90))
        c.set_source_rgba(1, 1, 1, 0.35)
        c.stroke()
    c.restore()


BLUE, GOLD = '#7f86ff', '#f2b21b'


def _backdrop(cv):
    """A dark grid with straight, bold things to bend: a vertical bar, a
    floor line and a ring standing on the line."""
    cv.fill(demo.BG)
    for x in range(0, demo.W + 1, 60):
        cv.line(x, 0, x, demo.H, demo.LINE, width=1.5)
    for y in range(0, demo.H + 1, 60):
        cv.line(0, y, demo.W, y, demo.LINE, width=1.5)
    cv.rect(300, 0, 34, demo.H, BLUE)
    cv.rect(0, 372, demo.W, 14, demo.INK)
    cv.arc(560, 290, 92, 0, 2 * math.pi, GOLD, width=34)


def _draw(n, cv):
    p = demo.phase(n, 0.2, 2.8)
    p = p * p * (3 - 2 * p)
    x = 317 + 463 * p                       # from the bar, through the ring's foot,
    y = 379 - 24 * math.sin(math.pi * p)    # riding the floor line all the way
    glass_refraction(cv, _backdrop, x, y, 130)


CAPABILITY = Capability(
    id='glass-refraction',
    name='Glass refraction',
    family='camera',
    group='Lighting & surface',
    aliases=('refractive glass', 'refraction distortion', 'lens refraction', 'glass ball lens'),
    definition='A clear glass shape passes over the picture and everything behind it looks bent, '
               'magnified and flipped through the glass, as if seen through a real lens.',
    phrasings=('roll a glass marble across the background so it warps what is behind it',
               'make it look like we are seeing the scene through a curved glass lens',
               'a see-through crystal ball that bends the shapes behind it'),
    related=('refraction-ripple', 'lens-distortion', 'crt-curvature', 'heat-haze', 'rain-on-glass', 'ripple'),
    api=('videobuilder.capabilities.camera.glass_refraction.glass_refraction',),
    demo=lambda: demo.film(_draw),
)
