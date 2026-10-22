"""Heat haze: the picture behind hot air wavers -- rows of it slide a little
side to side in thin, shifting bands that drift upward, strongest just above
the hot ground and calming higher up."""
import math

import cairo
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


def haze_offset(x, y, t, amplitude, wavelength, speed=1.0, seed=0):
    """The displacement `(dx, dy)` heat haze applies at (x, y) at time `t`
    seconds, before any falloff: mostly sideways, a third as much up/down.

    Three sines of `y` at unrelated wavelengths (around `wavelength`) beat
    against each other so the bands never settle into a pattern; their phase
    advances with `t` so the bands climb (`speed` scales how fast), and each
    is nudged slowly by `x` so a band is never a perfectly straight row."""
    k = 2 * math.pi / wavelength
    s = seed * 1.7
    w = 2 * math.pi * speed * t
    a = math.sin(k * y + 1.9 * w + 0.9 * math.sin(k * 0.21 * x + 0.7 * w + s))
    b = math.sin(k * 1.73 * y + 2.6 * w + 0.6 * math.sin(k * 0.13 * x - 0.5 * w + 2 * s) + 1.3)
    c = math.sin(k * 0.61 * y + 1.2 * w + 0.4 * k * 0.08 * x + 4.1 + s)
    dx = amplitude * (0.5 * a + 0.3 * b + 0.2 * c)
    dy = amplitude * 0.35 * (0.6 * math.sin(k * 0.83 * y + 2.2 * w + 0.7 + s) + 0.4 * b)
    return dx, dy


def heat_haze(cv, scene, t, amount=1.0, amplitude=0.008, wavelength=0.035, speed=0.6, source=1.0,
              reach=0.55, seed=0, rows=None):
    """Draw `scene(cv)` seen through rising heat at time `t` seconds.

    The scene is drawn offscreen and resampled through a fine mesh whose rows
    are pushed by `haze_offset`. `amount` (0 -> 1) fades the effect in or out;
    0 draws the scene untouched. `amplitude` and `wavelength` are fractions
    of the frame height (the largest sideways push, the band spacing);
    `speed` is how fast the bands climb. The heat comes from the height
    `source` (a fraction of the frame, 1 = the bottom edge): at and below it
    the haze is full strength, above it it fades out over `reach` of the
    frame. `rows` overrides the mesh row height in device pixels (finer is
    smoother, slower). Pass the film's time (`n / fps`) every frame so the
    shimmer keeps moving; a held `t` freezes it."""
    if amount <= 0:
        return scene(cv)
    im = _offscreen(cv, scene)
    sw, sh = im.size
    amp, lam = amplitude * sh * amount, wavelength * sh
    base, fade = source * sh, max(reach * sh, 1.0)
    step_y = rows or max(3, round(sh / 140))
    step_x = max(8, round(sw / 24))
    xs = list(range(0, sw, step_x)) + [sw]
    ys = list(range(0, sh, step_y)) + [sh]

    def src(x, y):
        u = vb.clamp01((base - y) / fade)
        strength = (1 - u) ** 1.5                       # full at the source, easing to nothing above it
        if strength <= 0:
            return x, y
        dx, dy = haze_offset(x, y, t, amp * strength, lam, speed, seed)
        return min(max(x + dx, 0), sw - 1), min(max(y + dy, 0), sh - 1)

    grid = {(x, y): src(x, y) for x in xs for y in ys}
    mesh = [((x0, y0, x1, y1), (*grid[x0, y0], *grid[x0, y1], *grid[x1, y1], *grid[x1, y0]))
            for x0, x1 in zip(xs, xs[1:]) for y0, y1 in zip(ys, ys[1:])]
    out = image_surface(im.transform((sw, sh), Image.Transform.MESH, mesh, resample=Image.Resampling.BILINEAR))
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(out, 0, 0)
    c.paint()
    c.restore()


HORIZON = demo.H * 0.62


def _desert(cv):
    """A hot flat plain at dusk: a gradient sky, a low sun, a far skyline and
    a row of poles marching to the horizon -- straight verticals the haze
    visibly bends."""
    c = cv.ctx
    sky = cairo.LinearGradient(0, 0, 0, HORIZON)
    for s, col in ((0, '#1d2340'), (0.6, '#6b4a6e'), (1, '#e48a5a')):
        sky.add_color_stop_rgba(s, *vb.rgba(col))
    c.rectangle(0, 0, demo.W, HORIZON)
    c.set_source(sky)
    c.fill()
    demo.dot(cv, demo.W * 0.68, HORIZON - 70, r=54, color='#ffd27a')
    x = demo.W * 0.16
    for w, h in ((60, 70), (34, 120), (48, 90), (26, 150), (70, 60), (40, 105), (56, 80)):
        cv.rect(x, HORIZON - h, w, h, '#3a2c44')
        x += w + 6
    ground = cairo.LinearGradient(0, HORIZON, 0, demo.H)
    ground.add_color_stop_rgba(0, *vb.rgba('#c9774e'))
    ground.add_color_stop_rgba(1, *vb.rgba('#5a2f2a'))
    c.rectangle(0, HORIZON, demo.W, demo.H - HORIZON)
    c.set_source(ground)
    c.fill()
    road = [(demo.W * 0.47, HORIZON), (demo.W * 0.53, HORIZON), (demo.W * 0.78, demo.H), (demo.W * 0.22, demo.H)]
    vb.paths.draw(cv, road, '#2c2228', fill=True)
    for i in range(5):                                 # dashes shrinking toward the horizon
        d0, d1 = 0.12 + 0.18 * i, 0.2 + 0.18 * i
        y0, y1 = HORIZON + (demo.H - HORIZON) * d0 ** 1.6, HORIZON + (demo.H - HORIZON) * d1 ** 1.6
        cv.line(demo.W / 2, y0, demo.W / 2, y1, '#f1e3b0', width=2 + 4 * d1)
    for i in range(6):                                 # poles along the left verge
        d = 0.25 + 0.15 * i
        x = demo.W * 0.47 - (demo.W * 0.3) * d ** 1.3
        y = HORIZON + (demo.H - HORIZON) * d ** 1.6
        h = 40 + 230 * d ** 1.6
        cv.line(x, y, x, y - h, demo.INK, width=2 + 4 * d)
        cv.line(x - 14 * d - 4, y - h + 8, x + 14 * d + 4, y - h + 8, demo.INK, width=2 + 3 * d)


def draw(n, cv):
    t = n / demo.FPS
    heat_haze(cv, _desert, t, amount=vb.ease_in_out_quart(demo.phase(n, 0.2, 1.0)), source=0.95, reach=0.7)
    cv.mark('haze', 0, demo.H * 0.4, demo.W, demo.H * 0.6)


TECHNIQUE = Technique(
    id='heat-haze',
    name='Heat haze',
    family='vfx',
    group='Distortion & displacement',
    aliases=('heat shimmer', 'mirage', 'thermal shimmer', 'heat distortion'),
    definition='The scene behind hot air wobbles in thin wavy bands that keep drifting upward, '
               'as if seen through the rising heat over a sunbaked road.',
    phrasings=('make the road look like it is shimmering in the heat',
               'add that wavy hot-air wobble above the ground',
               'make the background ripple like a desert mirage'),
    related=('gooch-shading', 'lens-dirt-overlay', 'lens-flare', 'atmospheric-fog', 'smoke-overlay',
             'fresnel-edge-glow'),
    api=('videobuilder.techniques.vfx.heat_haze.heat_haze',
         'videobuilder.techniques.vfx.heat_haze.haze_offset'),
    demo=lambda: demo.film(draw),
)
