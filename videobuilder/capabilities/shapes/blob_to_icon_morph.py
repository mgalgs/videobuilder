"""Blob-to-icon morph: a soft, wobbling blob firms up into a crisp icon
silhouette. The outline itself is `paths.morph`; what this adds is the
living blob (a seeded wobbling outline) and its wobble dying away as the
icon arrives, so the shape settles rather than just cross-fading."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

LOBES = (2, 3, 5)   # harmonics of the blob's wobble: broad bulges plus a smaller ripple


def blob(cx, cy, r, t=0.0, seed=0, wobble=0.18, n=160):
    """A closed blob outline of `n` points about (cx, cy), radius `r`. Its
    edge bulges by up to `wobble` of `r`, and the bulges drift with `t`
    (seconds), so drawing it every frame makes it breathe. Deterministic for
    a given `seed`."""
    rnd = random.Random(seed)
    waves = [(k, rnd.uniform(0.5, 1.0) / k ** 0.5, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.6, 1.4))
             for k in LOBES]
    total = sum(a for _, a, _, _ in waves)
    out = []
    for i in range(n):
        th = 2 * math.pi * i / n
        bump = sum(a * math.sin(k * th + ph + sp * t) for k, a, ph, sp in waves) / total
        rr = r * (1 + wobble * bump)
        out.append((cx + rr * math.cos(th), cy + rr * math.sin(th)))
    return out


def rounded_rect(x, y, w, h, radius, n=12):
    """A closed rounded-rectangle outline, `n` points per corner arc."""
    out = []
    for (ccx, ccy), a0 in (((x + w - radius, y + radius), -math.pi / 2), ((x + w - radius, y + h - radius), 0),
                           ((x + radius, y + h - radius), math.pi / 2), ((x + radius, y + radius), math.pi)):
        out += [(ccx + radius * math.cos(a0 + math.pi / 2 * j / (n - 1)),
                 ccy + radius * math.sin(a0 + math.pi / 2 * j / (n - 1))) for j in range(n)]
    return out


def speech_bubble(cx, cy, w, h, radius=None, tail=None):
    """A closed speech-bubble outline: a rounded box `w` x `h` centred at
    (cx, cy) with a pointed tail off its lower-left edge (`tail` px long,
    default about a third of `h`)."""
    radius = h * 0.16 if radius is None else radius
    tail = h * 0.36 if tail is None else tail
    x, y = cx - w / 2, cy - h / 2
    box = rounded_rect(x, y, w, h, radius)
    # the bottom edge runs right -> left between the 2nd and 3rd corners; cut the tail in there
    i = 24
    tx0, tx1 = x + w * 0.38, x + w * 0.14
    return box[:i] + [(tx0, y + h), (tx1 - w * 0.02, y + h + tail), (tx1, y + h)] + box[i:]


def blob_to_icon(icon, p, cx, cy, r, t=0.0, seed=0, wobble=0.18, n=160):
    """The outline at progress `p` (0 -> 1) of a blob becoming `icon` (a
    closed point list): at 0 the breathing `blob(cx, cy, r, t, seed, wobble)`,
    at 1 exactly `icon` resampled to `n` points. Pass `p` already eased. The
    blob's wobble fades out as `p` rises, so the shape firms up as it lands.
    Draw with `vb.paths.draw(cv, pts, colour, fill=True)`."""
    p = vb.clamp01(p)
    soft = blob(cx, cy, r, t, seed, wobble * (1 - p) ** 0.5, n)
    return vb.paths.morph(soft, icon, p, closed=True, n=n)


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2 - 30
    icon = speech_bubble(cx, cy, 340, 210)
    p = vb.ease_in_out_quart(demo.phase(n, 0.8, 2.1))
    pts = blob_to_icon(icon, p, cx, cy + 15, 130, t=n / demo.FPS * 1.6, seed=4, wobble=0.22)
    vb.paths.draw(cv, pts, demo.ACCENT, fill=True)
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    cv.mark('shape', min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    # three dots type into the bubble once it has landed
    for k in range(3):
        a = demo.phase(n, 2.15 + 0.12 * k, 2.4 + 0.12 * k)
        if a > 0:
            demo.dot(cv, cx + (k - 1) * 56, cy, r=16 * vb.ease_out_back(a), color=demo.INK)


CAPABILITY = Capability(
    id='blob-to-icon-morph',
    name='Blob-to-icon morph',
    family='shapes',
    group='Shape morphing',
    aliases=('organic to geometric morph', 'amorphous to icon', 'blob morph'),
    definition='A loose, wobbling organic shape pulls itself together into the clean outline of a '
               'recognisable icon.',
    phrasings=('the squishy blob turns into a chat bubble icon',
               'start with a wobbly shape that settles into the logo icon',
               'morph an organic blob into a crisp symbol'),
    related=('morphing-blob', 'morphing-shape-ident', 'shape-morph-loader', 'text-to-shape-morph',
             'liquid-morph', 'particle-morph'),
    api=('videobuilder.capabilities.shapes.blob_to_icon_morph.blob_to_icon',
         'videobuilder.capabilities.shapes.blob_to_icon_morph.blob',
         'videobuilder.capabilities.shapes.blob_to_icon_morph.speech_bubble',
         'videobuilder.paths.morph', 'videobuilder.paths.draw'),
    demo=lambda: demo.film(draw),
)
