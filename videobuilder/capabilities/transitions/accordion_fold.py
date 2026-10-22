"""Accordion Fold: the outgoing scene creases into alternating pleats, like a
paper fan, and concertinas shut towards the middle, uncovering the incoming
scene behind it."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def accordion_fold(cv, a, b, p, pleats=8, axis='x', shade=0.7, depth=0.14, ease=vb.bezier(0.6, 0, 0.4, 1)):
    """Draw the fold at progress `p` (0 -> 1): `b(cv)` underneath, and `a(cv)`
    cut into `pleats` strips that fold alternately towards and away from the
    viewer, so the whole scene closes up like a fan about the frame's centre
    and is gone at `p` = 1.

    `axis='x'` gives vertical pleats closing sideways; `'y'` horizontal ones
    closing upwards and downwards. `shade` is how dark a pleat facing away
    from the light gets when folded nearly flat; `depth` how much the pleats
    sinking away from the viewer shrink along their length, so the folded
    edges zigzag. In a film, call it inside a
    two-shot overlap, e.g.
    `accordion_fold(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    b(cv)
    q = ease(vb.clamp01(p))
    if q >= 1:
        return
    fw, fh = cv.width, cv.height
    across = fw if axis == 'x' else fh            # the length that folds up
    angle = q * math.pi / 2                       # every pleat's tilt away from the screen plane
    k = math.cos(angle)                           # how much of its width a tilted pleat still covers
    lean = math.sin(angle)
    size = across / pleats
    start = across * (1 - k) / 2                  # the folded stack stays centred
    total = across * k
    ctx = cv.ctx

    def span(lo, length):                         # a band across the folding axis, as (x, y, w, h)
        return (lo, 0, length, fh) if axis == 'x' else (0, lo, fw, length)

    if q > 0:  # the stack lifts off the scene below and throws a soft shadow onto it
        cv.shadow(*span(start, total), blur=40 * lean, dy=14 * lean, color=(0, 0, 0, 0.5 * lean))
    for i in range(pleats):
        lo = start + i * size * k
        seam = 0.6 if i < pleats - 1 else 0  # a hair of overlap, so no background shows between pleats
        with cv.clip(*span(lo, size * k + seam)):
            ctx.save()   # the pleat's own depth, which its shading shares
            if i % 2:  # this pleat runs back into the screen: a little smaller, about the frame's middle
                sink = 1 - depth * lean
                ctx.translate(fw / 2, fh / 2)
                ctx.scale(*((1, sink) if axis == 'x' else (sink, 1)))
                ctx.translate(-fw / 2, -fh / 2)
                ctx.rectangle(*span(lo, size * k + seam))  # so a scene that paints the whole frame shrinks too
                ctx.clip()
            ctx.save()
            if axis == 'x':
                ctx.translate(lo, 0)
                ctx.scale(k, 1)
                ctx.translate(-i * size, 0)
            else:
                ctx.translate(0, lo)
                ctx.scale(1, k)
                ctx.translate(0, -i * size)
            a(cv)
            ctx.restore()
            # Light from one side: pleats facing it stay bright, the others darken, and each
            # darkens further into its valley crease (the odd edges), so the zigzag reads.
            face = 0.12 if i % 2 == 0 else 0.55
            x0, y0, w, h = span(lo, size * k + seam)
            ridge, valley = (lo, lo + size * k) if i % 2 == 0 else (lo + size * k, lo)
            g = cairo.LinearGradient(*((ridge, 0, valley, 0) if axis == 'x' else (0, ridge, 0, valley)))
            g.add_color_stop_rgba(0, 0, 0, 0, shade * lean * face * 0.4)
            g.add_color_stop_rgba(1, 0, 0, 0, shade * lean * (face + 0.45))
            ctx.rectangle(x0, y0, w, h)
            ctx.set_source(g)
            ctx.fill()
            if i % 2 == 0:  # a thin highlight along each ridge crease
                cv.rect(*span(lo, max(1.0, 3 * lean)), '#ffffff', alpha=0.25 * lean)
            ctx.restore()


CAPABILITY = Capability(
    id='accordion-fold',
    name='Accordion fold',
    family='transitions',
    group='Page and Fold',
    aliases=('zigzag fold', 'pleat fold', 'fan fold', 'concertina fold', 'fold panel'),
    definition='The first scene is creased into a row of zigzag pleats that squeeze shut like a closing fan, '
               'and the next scene shows through as it folds away.',
    phrasings=('fold the shot up like an accordion to get to the next one',
               'concertina the picture closed into the middle',
               'squash the scene into zigzag folds and reveal what is behind'),
    related=('accordion-fold-text', 'paper-fold-reveal', 'accordion-height-expand', 'zigzag-wipe', 'corner-wipe',
             'word-flip-in'),
    api=('videobuilder.capabilities.transitions.accordion_fold.accordion_fold',),
    demo=lambda: demo.two_scenes(accordion_fold, start=0.7, length=1.6),
)
