"""Callout line with label: a short caption appears off to one side, then a
thin leader line runs from under it -- along a short shelf, then a bend --
to a point of interest, where a small dot lands with a ring pulse."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def callout_line(cv, target, anchor, label, p, color=demo.INK, dot_color=demo.ACCENT, font=None,
                 width=3, dot=9, shelf=None, gap=10):
    """Annotate the point `target` (x, y) with `label`, its text sitting
    above the line's start at `anchor` (x, y), at progress `p` (0 -> 1),
    drawn over what is already on `cv`. Over the first 30% the label fades
    and rises into place; from 25% to 80% the line draws from the anchor
    along a horizontal shelf (`shelf` px, default the label's width), then
    bends straight to the target; over the last 25% a dot of radius `dot`
    pops onto the target with one ring pulse. The shelf runs towards the
    target, so the label can sit on either side. Returns the label's Box."""
    f = font or demo.font(30, 800)
    tw, th = vb.text.block_size([label], f)
    ax, ay = anchor
    tx, ty = target
    side = 1 if tx >= ax else -1
    elbow = (ax + side * (tw if shelf is None else shelf), ay)
    lx = ax if side > 0 else ax - tw
    box = vb.Box(lx, ay - gap - th, tw, th)

    t = vb.ease_out_quint(vb.clamp01(p / 0.3))
    if t > 0:
        vb.text.draw(cv, [label], f, box.x, box.y + 14 * (1 - t), color, alpha=t)
        cv.mark('label', *box)

    # stop the line at the dot's rim so it doesn't cross the marker
    d = math.hypot(tx - elbow[0], ty - elbow[1]) or 1.0
    end = (tx - (tx - elbow[0]) / d * dot, ty - (ty - elbow[1]) / d * dot)
    pts = [anchor, elbow, end]
    run = vb.ease_in_out_quart(vb.clamp01((p - 0.25) / 0.55))
    if run > 0:
        vb.paths.draw(cv, vb.paths.reveal(pts, run), color, width=width, alpha=0.9)
        cv.mark('line', min(ax, tx, elbow[0]), min(ay, ty), abs(max(ax, tx, elbow[0]) - min(ax, tx, elbow[0])),
                abs(ty - ay) or 1)

    k = vb.clamp01((p - 0.75) / 0.25)
    if k > 0:
        r = dot * vb.ease_out_back(k)
        cv.arc(tx, ty, dot + 26 * k, 0, 2 * math.pi, dot_color, width=3, alpha=0.8 * (1 - k))
        cv.sector(tx, ty, max(0.0, r), 0, 2 * math.pi, dot_color)
        cv.arc(tx, ty, max(0.0, r), 0, 2 * math.pi, color, width=2)
        cv.mark('dot', tx - dot, ty - dot, 2 * dot, 2 * dot)
    return box


def draw(n, cv):
    # a plain night scene: a moon over two ridges, so the callout has something to point at
    cx, cy = demo.W * 0.66, demo.H * 0.36
    for r, a in ((170, 0.04), (140, 0.06), (120, 0.08)):
        cv.sector(cx, cy, r, 0, 2 * math.pi, '#f2d27a', alpha=a)
    cv.sector(cx, cy, 104, 0, 2 * math.pi, '#f2d27a')
    for base, amp, col in ((demo.H * 0.66, 50, '#2b3346'), (demo.H * 0.78, 36, '#1c2230')):
        ridge = [(x, base + amp * math.sin(x / 210 + base)) for x in range(0, demo.W + 40, 40)]
        vb.paths.draw(cv, ridge + [(demo.W, demo.H), (0, demo.H)], col, fill=True)
    callout_line(cv, (cx - 30, cy + 20), (demo.W * 0.18, demo.H * 0.2), 'FULL MOON',
                 demo.phase(n, 0.3, 2.3), font=demo.font(40, 800), dot=12)


CAPABILITY = Capability(
    id='callout-line-with-label',
    name='Callout line with label',
    family='broadcast',
    group='Annotation',
    aliases=('leader line callout', 'annotation callout', 'leader line'),
    definition='A caption appears beside the picture and a thin line then draws out from it to one '
               'exact spot, ending in a small dot that marks what the caption names.',
    phrasings=('point at that spot with a line and put a label on it',
               'draw a pointer line from a caption to the thing it describes',
               'annotate this part of the image with a little label and a line to it'),
    related=('callout-highlight', 'virtual-first-down-line', 'line-chart-draw-on', 'streamlines',
             'icon-line-to-fill', 'sparkline-draw'),
    api=('videobuilder.capabilities.broadcast.callout_line_with_label.callout_line',),
    demo=lambda: demo.film(draw),
)
