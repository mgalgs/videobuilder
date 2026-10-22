"""Morphing Blob: a soft, rounded closed shape whose outline keeps swelling
and pulling in at different places, as if it were alive."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def blob_outline(cx, cy, r, t, seed=0, wobble=0.16, lobes=(2, 3, 4), period=3.0, points=120):
    """The blob's outline at time `t` seconds as a closed point list around
    (cx, cy). Its radius is `r` plus a few slow waves around the rim (one per
    entry of `lobes`, each `wobble` * r tall at most), each drifting at a
    whole number of turns per `period`, so the motion loops every `period`
    seconds. The same `seed` gives the same blob."""
    rnd = random.Random(seed)
    waves = []
    for k in lobes:
        amp = wobble * r * rnd.uniform(0.5, 1.0) / math.sqrt(k)
        turns = rnd.choice((1, -1)) * rnd.randint(1, 2)
        waves.append((k, amp, rnd.uniform(0, 2 * math.pi), 2 * math.pi * turns / period))
    out = []
    for i in range(points):
        a = 2 * math.pi * i / points
        d = r + sum(amp * math.sin(k * a + ph + w * t) for k, amp, ph, w in waves)
        out.append((cx + d * math.cos(a), cy + d * math.sin(a)))
    return out


def draw_blob(cv, cx, cy, r, t, color, alpha=1.0, shadow=None, **kw):
    """Fill the blob at time `t` (see `blob_outline`, which takes `kw`) in
    `color`. `shadow`: an optional colour for a soft drop shadow under it.
    Returns the outline."""
    pts = blob_outline(cx, cy, r, t, **kw)
    if shadow:
        cv.shape_shadow(pts, dy=r * 0.08, blur=r * 0.15, color=shadow)
    vb.paths.draw(cv, pts, color, fill=True, alpha=alpha)
    return pts


def draw(n, cv):
    r = 150
    pts = draw_blob(cv, demo.W / 2, demo.H / 2, r, n / demo.FPS, demo.ACCENT,
                    shadow=(0, 0, 0, 0.45), seed=5, wobble=0.22)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cv.mark('blob', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


TECHNIQUE = Technique(
    id='morphing-blob',
    name='Morphing blob',
    family='shapes',
    group='Liquid & organic',
    aliases=('organic blob', 'amoeba shape', 'blob animation'),
    definition='A soft rounded shape keeps reshaping its edge, bulging out in one place and '
               'drawing in at another, so it seems to breathe and wobble on its own.',
    phrasings=('a wobbly liquid blob that slowly changes shape',
               'an organic shape that pulses and ripples like it is alive',
               'a gooey amoeba-like background shape that never sits still'),
    related=('blob-to-icon-morph', 'morphing-shape-ident', 'shape-morph-loader', 'liquid-morph',
             'shape-morph', 'particle-morph'),
    api=('videobuilder.techniques.shapes.morphing_blob.draw_blob',
         'videobuilder.techniques.shapes.morphing_blob.blob_outline'),
    demo=lambda: demo.film(draw),
)
