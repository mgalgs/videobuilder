"""Drop Shadow Breathing: a shape's drop shadow drifts farther, spreads softer
and fades as the shape lifts toward the viewer, then pulls in tight and dark
as it settles back down, so height reads from the shadow alone."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def elevation_shadow(height, near=(4, 8, 0.55), far=(42, 64, 0.22)):
    """Shadow settings `(dy, blur, alpha)` for a shape lifted by `height`
    (0 resting on the surface -> 1 at its highest). `near` and `far` are the
    `(dy, blur, alpha)` at those two ends; between them the offset and blur
    grow and the shadow fades. Blur is rounded to half pixels so the canvas's
    cached shadow masks are reused across frames."""
    h = vb.clamp01(height)
    dy, blur, alpha = (a + (b - a) * h for a, b in zip(near, far))
    return dy, round(blur * 2) / 2, alpha


def draw_elevated(cv, x, y, w, h, height, color, radius=0, lift=24, **kw):
    """Draw the box (x, y, w, h) raised by `height` (0 -> 1): its shadow from
    `elevation_shadow` stays where the box rests while the box itself rises
    `lift` px and grows a few percent toward the viewer. `kw` goes to
    `elevation_shadow`. Returns the Box the shape was drawn in."""
    dy, blur, alpha = elevation_shadow(height, **kw)
    k = vb.clamp01(height)
    cv.shadow(x, y, w, h, radius=radius, dy=dy, blur=blur, color=(0, 0, 0, alpha))
    s = 1 + 0.05 * k
    bw, bh = w * s, h * s
    bx, by = x + (w - bw) / 2, y + (h - bh) / 2 - lift * k
    cv.rect(bx, by, bw, bh, color, radius=radius * s)
    return vb.Box(bx, by, bw, bh)


def breath(t, period):
    """A smooth 0 -> 1 -> 0 rise and settle every `period` seconds, resting at
    0 when `t` is a whole number of periods."""
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / period)


def draw(n, cv):
    cv.fill('#e9e6df')  # a light surface, so the shadow reads
    w, h = 300, 190
    x, y = (demo.W - w) / 2, (demo.H - h) / 2 + 20
    box = draw_elevated(cv, x, y, w, h, breath(n / demo.FPS, 1.5), demo.TEAL, radius=22, lift=36)
    bar = box.h * 0.12
    cv.rect(box.x + box.w * 0.12, box.y + box.h * 0.3, box.w * 0.62, bar, demo.INK, radius=bar / 2, alpha=0.95)
    cv.rect(box.x + box.w * 0.12, box.y + box.h * 0.3 + 2 * bar, box.w * 0.4, bar, demo.INK, radius=bar / 2,
            alpha=0.6)
    cv.mark('card', *box)


TECHNIQUE = Technique(
    id='drop-shadow-breathing',
    name='Drop shadow breathing',
    family='shapes',
    group='Depth & shadows',
    aliases=('shadow pulse', 'elevation change', 'lift and shadow'),
    definition='A shape rises and settles while its shadow loosens, slides away and fades on the way up, '
               'then snaps back tight and dark beneath it as it comes down.',
    phrasings=('the card floats up off the page and its shadow gets softer',
               'make it look like it lifts and lands just by changing the shadow',
               'a gentle hover where the shadow spreads out and pulls back in'),
    related=('drop-shadow-lift', 'drag-lift-with-shadow', 'shadow-play', 'long-shadow-growth', 'gravity-drop',
             'twist-deformer'),
    api=('videobuilder.techniques.shapes.drop_shadow_breathing.draw_elevated',
         'videobuilder.techniques.shapes.drop_shadow_breathing.elevation_shadow',
         'videobuilder.techniques.shapes.drop_shadow_breathing.breath'),
    demo=lambda: demo.film(draw),
)
