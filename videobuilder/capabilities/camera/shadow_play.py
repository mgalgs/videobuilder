"""Shadow play: a point light throws the silhouettes of shapes held in front
of it onto a surface behind them, so every move a shape makes -- toward the
light, away from it, a turn -- is shown again, magnified, as its shadow."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...looks import kit as looks


def cast_shadow(points, light, depth):
    """The outline `points` (screen px) projected from the point `light` onto
    the surface behind it. `depth` is how far the shape stands from the light,
    as a fraction of the light's distance to the surface (0 < depth <= 1): at
    1 the shape touches the surface and the shadow is its own size; at 0.5 the
    shadow is twice the size and pushed out from the light."""
    k = 1 / max(depth, 1e-3)
    lx, ly = light
    return [(lx + (x - lx) * k, ly + (y - ly) * k) for x, y in points]


def draw_cast_shadow(cv, points, light, depth, color=(0, 0, 0, 0.8), softness=30):
    """Draw the shadow of the outline `points` cast from `light` at `depth`
    (see `cast_shadow`). The edge blurs by up to `softness` px as the shape
    nears the light, as a real penumbra does. Draw it on the surface, clipped
    to it, before the shape itself."""
    blur = softness * (1 - vb.clamp01(depth))
    cv.shape_shadow(cast_shadow(points, light, depth), blur=round(blur), color=color)


def _polygon(cx, cy, r, sides, turn=0.0):
    return [(cx + r * math.cos(turn + 2 * math.pi * i / sides), cy + r * math.sin(turn + 2 * math.pi * i / sides))
            for i in range(sides)]


LIGHT = (90, 230)
PANEL = (330, 50, 570, 430)
LIT = '#c9cde0'


def _panel(cv):
    x, y, w, h = PANEL
    cv.rect(x, y, w, h, LIT, radius=10)
    with cv.clip(x, y, w, h, radius=10):  # a soft hotspot where the lamp points
        for i in range(10):
            looks.disc(cv, x + w * 0.3, y + h * 0.45, 300 - 26 * i, '#eef0fa', alpha=0.1)


def _rod(cv, x, y):
    cv.line(x, y, x, demo.H - 40, demo.MUTED, width=4)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.2, 2.7))
    swing = math.sin(math.pi * demo.phase(n, 0.2, 2.7))
    shapes = (
        # (outline, depth): the disc travels toward the lamp, its shadow swelling;
        # the square turns; the triangle backs away to the wall and sharpens.
        (looks.circle_pts(360 - 100 * p, 200 - 20 * swing, 34), 0.62 - 0.24 * p, demo.ACCENT),
        (_polygon(420, 360, 40, 4, math.pi / 4 + 1.6 * p), 0.7, demo.TEAL),
        (_polygon(520 + 80 * p, 290, 38, 3, -math.pi / 2), 0.66 + 0.29 * p, demo.INK),
    )
    lx, ly = LIGHT
    for i in range(12):
        looks.disc(cv, lx, ly, 48 - 3.5 * i, '#fff3c4', alpha=0.06)
    cv.line(lx, ly, lx, demo.H - 40, demo.MUTED, width=4)
    looks.disc(cv, lx, ly, 10, '#fff7dc')
    _panel(cv)
    with cv.clip(*PANEL, radius=10):
        for pts, depth, _ in shapes:
            draw_cast_shadow(cv, pts, LIGHT, depth, color=(14, 16, 24, 0.92))
    for pts, _, color in shapes:
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        _rod(cv, sum(xs) / len(xs), max(ys))
        looks.fill(cv, pts, color)
    cv.mark('panel', *PANEL)


CAPABILITY = Capability(
    id='shadow-play',
    name='Shadow play',
    family='camera',
    group='Lighting & surface',
    aliases=('silhouette play', 'shadow puppetry', 'cast shadows'),
    definition='Shapes held between a lamp and a wall throw dark silhouettes onto it, and as they move, '
               'turn or near the light their shadows swell, slide and soften.',
    phrasings=('shadows of the shapes moving on the wall like a puppet show',
               'a light behind the objects casts their silhouettes onto a screen',
               'move the shapes toward the lamp so their shadows grow huge'),
    related=('drop-shadow-breathing', 'drop-shadow-lift', 'long-shadow-growth', 'noise-terrain-flyover',
             'cut-out-paper-animation', 'drag-lift-with-shadow'),
    api=('videobuilder.capabilities.camera.shadow_play.draw_cast_shadow',
         'videobuilder.capabilities.camera.shadow_play.cast_shadow'),
    demo=lambda: demo.film(draw),
)
