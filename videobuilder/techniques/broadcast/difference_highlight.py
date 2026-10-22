"""Difference highlight: two versions of a picture sit side by side, and the
regions that changed between them are boxed and tinted one after another,
on both versions at once, so the eye can check each change."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

MARKER = '#f5c84b'


def difference_highlight(cv, regions, p, panels=((0, 0),), color=MARKER, pad=6, tint=0.16, width=3,
                         radius=8, length=0.4, numbered=True, font=None):
    """Mark the changed `regions` at progress `p` (0 -> 1), drawn over what is
    already on `cv`. Each region is a box (x, y, w, h) relative to a panel's
    top-left; it is marked at every origin in `panels`, so the same spot
    lights up on the before and the after together. Regions arrive in order,
    each taking `length` of the progress: the box (grown by `pad`) settles in
    from slightly larger, flashes its `tint`, and keeps a `color` outline and,
    if `numbered`, a small count badge. Returns the marked Boxes, panel by panel."""
    n = len(regions)
    step = (1 - length) / (n - 1) if n > 1 else 0.0
    f = font or demo.font(15, 800)
    out = []
    for i, (x, y, w, h) in enumerate(regions):
        q = vb.clamp01((p - i * step) / length)
        if q <= 0:
            continue
        s = vb.ease_out_back(vb.clamp01(q / 0.6))
        a = vb.clamp01(q / 0.3)
        grow = 1 + 0.35 * (1 - s)
        flash = tint + 0.3 * math.sin(math.pi * vb.clamp01(q / 0.7))
        bw, bh = (w + 2 * pad) * grow, (h + 2 * pad) * grow
        for ox, oy in panels:
            cx, cy = ox + x + w / 2, oy + y + h / 2
            box = vb.Box(cx - bw / 2, cy - bh / 2, bw, bh)
            cv.rect(*box, color, radius=radius, alpha=flash * a)
            cv.outline(*box, color, width=width, radius=radius, alpha=a)
            if numbered:
                r = 11
                bx, by = box.x, box.y
                demo.dot(cv, bx, by, r=r, color=color, alpha=a)
                label = str(i + 1)
                tw, th = vb.text.block_size([label], f)
                vb.text.draw(cv, [label], f, bx - tw / 2, by - th / 2, demo.BG, alpha=a)
            cv.mark(f'diff{i + 1}', *box)
            out.append(box)
    return out


# ---- demo ----

K = 0.52  # the scene is laid out on a 780 x 440 grid, drawn at this scale
PW, PH = 780 * K, 440 * K
GAP = 36
TOP = (demo.H - PH) / 2 + 20
LEFT = (demo.W - 2 * PW - GAP) / 2
PANELS = ((LEFT, TOP), (LEFT + PW + GAP, TOP))
# what changed: the sun moved, a tree appeared, the house turned teal
REGIONS = tuple(tuple(v * K for v in r) for r in ((585, 50, 110, 150), (95, 245, 80, 110),
                                                  (335, 230, 160, 130)))


def _scene(cv, ox, oy, after):
    def at(x, y):
        return ox + x * K, oy + y * K

    def rect(x, y, w, h, color, radius=0):
        cv.rect(*at(x, y), w * K, h * K, color, radius=radius * K)

    with cv.clip(ox, oy, PW, PH, radius=12):
        rect(0, 0, 780, 440, '#2d3557')
        demo.dot(cv, *at(640, 100 if after else 150), r=42 * K, color='#f6d36b')
        demo.dot(cv, *at(180, 700), r=420 * K, color='#4c5d92')
        demo.dot(cv, *at(650, 770), r=440 * K, color='#435282')
        rect(0, 370, 780, 70, '#262c45')
        rect(350, 270, 130, 90, demo.TEAL if after else demo.ACCENT, radius=6)
        rect(335, 230, 160, 46, '#202640', radius=8)
        rect(400, 310, 30, 50, '#202640', radius=3)
        if after:
            rect(128, 300, 14, 50, '#202640')
            demo.dot(cv, *at(135, 285), r=36 * K, color='#2f6b5c')
    cv.outline(ox, oy, PW, PH, demo.LINE, width=2, radius=12)
    vb.text.draw(cv, ['After' if after else 'Before'], demo.font(22, 800), ox, oy - 36, demo.MUTED)


def draw(n, cv):
    for (ox, oy), after in zip(PANELS, (False, True)):
        _scene(cv, ox, oy, after)
    difference_highlight(cv, REGIONS, demo.phase(n, 0.5, 2.4), panels=PANELS)


TECHNIQUE = Technique(
    id='difference-highlight',
    name='Difference highlight',
    family='broadcast',
    group='Comparisons',
    aliases=('diff reveal', 'change overlay', 'spot the difference'),
    definition='Two versions of a picture sit together and each spot that changed between them '
               'gets a tinted box, one after another, on both versions at once.',
    phrasings=('box every place where the new version differs from the old one',
               'point out the changes between these two screenshots one at a time',
               'a spot-the-difference reveal on a before and after'),
    related=('difference-blend', 'luma-wipe', 'series-isolate-highlight', 'pixelation-reveal',
             'callout-highlight', 'border-glow-follow'),
    api=('videobuilder.techniques.broadcast.difference_highlight.difference_highlight',),
    demo=lambda: demo.film(draw),
)
