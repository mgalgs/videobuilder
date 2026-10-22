"""Underline swash draw: a hand-drawn underline sweeps in beneath a word from
left to right -- a gently wavering stroke, thick in the middle and tapering
to fine points at both ends, as if dashed off with a brush pen."""
import math
import random

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

_HAND = vb.bezier(0.45, 0.0, 0.25, 1.0)  # a quick flick: slow start, fast middle, soft finish


def swash_path(x0, x1, y, wave=6.0, lift=10.0, seed=0, steps=80):
    """The centre line of a swash from (x0, y) to (x1, y), as a point list:
    a slight seeded wobble of about `wave` px, with the end flicking up by
    `lift` px the way a quick pen stroke does. The same `seed` gives the
    same line."""
    rng = random.Random(f'swash:{seed}')
    phase, freq = rng.uniform(0, 2 * math.pi), rng.uniform(1.2, 1.8)
    out = []
    for i in range(steps + 1):
        t = i / steps
        dy = wave * math.sin(phase + 2 * math.pi * freq * t) * math.sin(math.pi * t) - lift * t ** 3
        out.append((x0 + (x1 - x0) * t, y + dy))
    return out


def draw_swash(cv, points, p, color=demo.ACCENT, width=12.0, taper=0.8, alpha=1.0):
    """Draw the leading `p` (0 -> 1) of the stroke along `points` as a filled
    ribbon at most `width` px thick. The thickness follows the whole stroke,
    swelling in the middle and thinning to points at both ends (`taper` 0
    keeps it even, 1 runs the ends to nothing), so a half-drawn swash already
    has its fine tail and grows its full body as it goes."""
    part = vb.paths.reveal(points, p)
    if len(part) < 2:
        return
    total = vb.paths.length(points) or 1.0
    left, right, s = [], [], 0.0
    for i, (x, y) in enumerate(part):
        if i:
            s += math.hypot(x - part[i - 1][0], y - part[i - 1][1])
        a, b = part[max(i - 1, 0)], part[min(i + 1, len(part) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        d = math.hypot(tx, ty) or 1.0
        u = min(s / total, 1.0)
        half = width / 2 * ((1 - taper) + taper * math.sin(math.pi * u) ** 0.6)
        nx, ny = -ty / d * half, tx / d * half
        left.append((x + nx, y + ny))
        right.append((x - nx, y - ny))
    vb.paths.draw(cv, left + right[::-1], color, fill=True, alpha=alpha)
    # a round nib at the moving tip, so the drawing end never looks sheared off
    if p < 1:
        x, y = part[-1]
        dx, dy = left[-1][0] - right[-1][0], left[-1][1] - right[-1][1]
        cv.sector(x, y, math.hypot(dx, dy) / 2, 0, 2 * math.pi, color, alpha=alpha)


def underline_swash(cv, box, p, color=demo.ACCENT, width=12.0, gap=18, overhang=0.06, seed=0, **kw):
    """Underline `box` (x, y, w, h), typically a word's Box, at progress `p`
    (0 -> 1): the swash starts a little before the box's left edge and runs
    `overhang` of its width past the right, `gap` px under its bottom, with
    a hand-like ease applied to `p`. `kw` goes to `swash_path`. Returns the
    path, so a film can reuse it (to erase it again, say)."""
    x, y, w, h = box
    pts = swash_path(x - w * overhang, x + w * (1 + overhang), y + h + gap, seed=seed, **kw)
    draw_swash(cv, pts, _HAND(vb.clamp01(p)), color, width)
    return pts


def draw(n, cv):
    box = demo.word(cv, 'MOTION', demo.W / 2, demo.H / 2 - 20, size=150, weight=900)
    underline_swash(cv, box, demo.phase(n, 0.5, 1.5), width=16, gap=4, seed=3)
    cv.mark('word', *box)


CAPABILITY = Capability(
    id='underline-swash-draw',
    name='Underline swash draw',
    family='broadcast',
    group='Annotation',
    aliases=('underline scribble', 'underline stroke', 'swash underline', 'hand-drawn underline'),
    definition='A wavy, brush-like line with thin pointed ends sweeps in under a word from left to right, '
               'as if someone underlined it by hand.',
    phrasings=('underline the key word with a quick hand-drawn stroke',
               'a marker-style squiggle draws itself under the title',
               'swoosh a brushy line underneath that word to stress it'),
    related=('highlighter-swipe', 'underline-wipe', 'stroke-draw-on', 'whiteboard-marker-drawing',
             'per-character-fade-in', 'character-rise'),
    api=('videobuilder.capabilities.broadcast.underline_swash_draw.underline_swash',
         'videobuilder.capabilities.broadcast.underline_swash_draw.draw_swash',
         'videobuilder.capabilities.broadcast.underline_swash_draw.swash_path'),
    demo=lambda: demo.film(draw),
)
