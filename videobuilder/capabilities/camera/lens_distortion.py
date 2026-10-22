"""Lens distortion: the picture is bent radially about the frame's centre, as
a real lens does -- barrel (the middle bulges toward you and straight lines
bow outward) or pincushion (the middle shrinks away and lines bow inward),
always strongest toward the edges."""
import math

from PIL import Image

import videobuilder as vb

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


def _hex_rgb(color):
    c = color.lstrip('#') if isinstance(color, str) else None
    if c and len(c) == 6:
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(v) for v in color[:3])


def lens_distort(cv, scene, amount, center=(0.5, 0.5), fit=True, fill=demo.BG):
    """Draw `scene(cv)` through a radial lens: `amount` > 0 is barrel
    distortion (the middle swells, straight lines bow outward), `amount` < 0
    is pincushion (lines bow inward), 0 is the plain scene. About 0.3 is a
    strong wide-angle look; 0.6 and up reads as a fisheye.

    Each output point at normalised radius r (1 = the frame's half-diagonal)
    reads the scene at radius r * (1 + amount * r^2), so the bend grows with
    the square of the distance from `center` (fractions of the frame).
    Keep `amount` above -1/3 or a pincushion folds back on itself. `fit`
    rescales so the frame's corners stay on its corners, which keeps a
    barrel's frame full; anywhere that reads from outside the scene (the
    pinched-in edges of a pincushion) is painted `fill`.

    Animate `amount` across frames to push a shot into or out of a lens
    warp, e.g. `lens_distort(cv, shot, 0.4 * vb.ease_in_out_quart(p))`."""
    if abs(amount) < 1e-4:
        return scene(cv)
    im = _offscreen(cv, scene)
    w, h = im.size
    cx, cy = center[0] * w, center[1] * h
    norm = math.hypot(w, h) / 2
    gain = 1 / (1 + amount) if fit else 1.0     # a corner (r = 1) reads a corner

    def src(x, y):
        dx, dy = (x - cx) / norm, (y - cy) / norm
        k = (1 + amount * (dx * dx + dy * dy)) * gain
        return cx + dx * k * norm, cy + dy * k * norm

    step = max(6, round(min(w, h) / 40))
    xs = list(range(0, w, step)) + [w]
    ys = list(range(0, h, step)) + [h]
    at = {(x, y): src(x, y) for x in xs for y in ys}
    mesh = [((x0, y0, x1, y1), (*at[x0, y0], *at[x0, y1], *at[x1, y1], *at[x1, y0]))
            for x0, x1 in zip(xs, xs[1:]) for y0, y1 in zip(ys, ys[1:])]
    out = im.transform((w, h), Image.Transform.MESH, mesh, resample=Image.Resampling.BILINEAR,
                       fillcolor=_hex_rgb(fill))
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(image_surface(out), 0, 0)
    c.paint()
    c.restore()


def _scene(cv):
    """A photo behind a square grid, so the bend shows in every straight line."""
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))
    cv.rect(0, 0, demo.W, demo.H, demo.BG, alpha=0.35)
    pitch = demo.H / 6
    for i in range(-6, 7):
        x = demo.W / 2 + i * pitch
        cv.line(x, 0, x, demo.H, demo.INK, width=4, alpha=0.8)
    for j in range(-3, 4):
        y = demo.H / 2 + j * pitch
        cv.line(0, y, demo.W, y, demo.INK, width=4, alpha=0.8)
    demo.card(cv, demo.W / 2, demo.H / 2, w=300, h=180)


def draw(n, cv):
    swell = vb.ease_in_out_quart(demo.phase(n, 0.3, 1.3))      # flat -> barrel
    flip = vb.ease_in_out_quart(demo.phase(n, 1.6, 2.7))       # barrel -> pincushion
    lens_distort(cv, _scene, 0.5 * swell - 0.78 * flip)
    cv.mark('frame', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='lens-distortion',
    name='Lens distortion',
    family='camera',
    group='Lens',
    aliases=('barrel distortion', 'pincushion distortion', 'fisheye warp'),
    definition='The whole picture bulges out from its centre or pinches in toward it, so straight '
               'lines curve more and more the nearer they sit to the edge of the frame.',
    phrasings=('make it look like we are filming through a fisheye lens',
               'bow the grid lines outward like a wide-angle lens',
               'pinch the shot inward so the edges curve the other way'),
    related=('refraction-ripple', 'polar-coordinate-warp', 'glass-refraction', 'rolling-shutter-wobble',
             'crt-curvature', 'taper-deformer'),
    api=('videobuilder.techniques.camera.lens_distortion.lens_distort',),
    demo=lambda: demo.film(draw),
)
