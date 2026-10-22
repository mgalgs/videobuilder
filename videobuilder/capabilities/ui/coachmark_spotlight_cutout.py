"""Coachmark Spotlight Cutout: the whole screen dims except a rounded hole
around one control, and a tooltip beside the hole explains it; the hole then
glides on to the next control, as in an onboarding tour."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _lerp_box(a, b, t):
    return vb.Box(*(x0 + (x1 - x0) * t for x0, x1 in zip(a, b)))


def tour_hole(targets, p, pad=12, open_from=2.4, intro=0.25):
    """Where the cutout sits at progress `p` (0 -> 1) of a tour over `targets`
    (Boxes, in order): for the first `intro` of the tour it closes in from
    `open_from` times its size onto the first target, then it glides from one
    target to the next in equal steps, holding on each. Each target is grown by
    `pad`. Returns `(box, step, settle)`: the hole, the index of the target it
    is on or heading for, and 0 -> 1 how settled it is there."""
    boxes = [vb.Box(*t).pad(-pad) for t in targets]
    p = vb.clamp01(p)
    if p < intro:
        k = vb.ease_out_quint(p / intro)
        return boxes[0].scaled(open_from + (1 - open_from) * k), 0, k
    if len(boxes) == 1:
        return boxes[0], 0, 1.0
    seg = (1 - intro) / len(boxes)
    i = min(len(boxes) - 1, int((p - intro) / seg))
    local = (p - intro - i * seg) / seg      # 0 -> 1 within this step
    if i == 0:
        return boxes[0], 0, 1.0
    move = vb.clamp01(local / 0.35)          # the first 35 % of a step travels, the rest holds
    k = vb.ease_in_out_quart(move)
    return _lerp_box(boxes[i - 1], boxes[i], k), i, k


def spotlight_cutout(cv, hole, dim=0.68, radius=16, color='#05060a', ring=None, ring_width=3):
    """Dim the whole frame with `color` at `dim` opacity except the rounded box
    `hole` (x, y, w, h), which stays clear; `ring`, a colour, outlines the hole.
    Draw it over the finished UI, before the tooltip."""
    x, y, w, h = hole
    c = cv.ctx
    c.save()
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    c.new_path()
    c.rectangle(0, 0, cv.width, cv.height)
    r = max(0.0, min(radius, w / 2, h / 2))
    c.new_sub_path()
    c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    c.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    c.close_path()
    c.set_source_rgba(*vb.rgba(color, dim))
    c.fill()
    c.restore()
    if ring is not None:
        cv.outline(x, y, w, h, ring, width=ring_width, radius=radius)


def coachmark_tip(cv, hole, lines, font, alpha=1.0, below=True, fill='#f4f4f2', ink='#14151a', gap=22,
                  pad=(18, 24), arrow=12):
    """A tooltip bubble with a small pointer at the hole `hole`: under it when
    `below`, else over it, centred on it but kept inside the frame. `lines` is
    a list of strings. It rises `gap / 2` px into place as `alpha` goes 0 -> 1.
    Returns the bubble's Box."""
    hole = vb.Box(*hole)
    tw, th = vb.text.block_size(lines, font)
    py, px = pad
    bw, bh = tw + 2 * px, th + 2 * py
    hx = hole.cx
    bx = min(max(32, hx - bw / 2), cv.width - 32 - bw)
    rise = (1 - alpha) * gap / 2
    by = hole.bottom + gap + rise if below else hole.y - gap - bh - rise
    with cv.layer(opacity=alpha):
        cv.shadow(bx, by, bw, bh, radius=14, dy=8, blur=24, color=(0, 0, 0, 0.5))
        cv.rect(bx, by, bw, bh, fill, radius=14)
        ax = min(max(bx + 24, hx), bx + bw - 24)
        ay = by if below else by + bh
        tip = ay - arrow if below else ay + arrow
        c = cv.ctx
        c.new_path()
        c.move_to(ax - arrow, ay)
        c.line_to(ax, tip)
        c.line_to(ax + arrow, ay)
        c.close_path()
        c.set_source_rgba(*vb.rgba(fill))
        c.fill()
        vb.text.draw(cv, lines, font, bx + px, by + py, ink)
    return vb.Box(bx, by, bw, bh)


# ---- the demo: a small app screen and a two-stop tour of it ----

SHARE = vb.Box(770, 58, 112, 38)
DRAFTS = vb.Box(110, 250, 260, 170)
TIPS = ((SHARE, ['Share your cut', 'with one tap'], True),
        (DRAFTS, ['Your drafts', 'live here'], False))


def _app(cv):
    W, H = demo.W, demo.H
    cv.rect(60, 40, W - 120, H - 80, '#1d1f26', radius=16)
    cv.rect(60, 40, W - 120, 72, '#23262e', radius=16)
    cv.rect(60, 96, W - 120, 16, '#23262e')
    demo.word(cv, 'Studio', 140, 77, size=24, weight=800)
    for x in (260, 360, 460):
        cv.rect(x, 70, 76, 12, demo.LINE, radius=6)
    cv.rect(*SHARE, demo.ACCENT, radius=19)
    demo.word(cv, 'Share', SHARE.cx, SHARE.cy, size=18, weight=800)
    demo.word(cv, 'Your projects', 180, 170, size=22, weight=700, color=demo.MUTED)
    demo.card(cv, DRAFTS.cx, DRAFTS.cy, w=DRAFTS.w, h=DRAFTS.h, color=demo.TEAL)
    demo.card(cv, 520, DRAFTS.cy, w=200, h=170, color='#3a3e4a')
    demo.card(cv, 760, DRAFTS.cy, w=200, h=170, color='#3a3e4a')


def draw(n, cv):
    _app(cv)
    p = demo.phase(n, 0.3, 2.9)
    if p <= 0:
        return
    hole, step, settle = tour_hole([t[0] for t in TIPS], p, pad=8)
    spotlight_cutout(cv, hole, dim=0.72 * vb.clamp01(p / 0.08), radius=12, ring=demo.INK, ring_width=2)
    cv.mark('spotlight', *hole)
    _, lines, below = TIPS[step]
    tip_in = vb.clamp01((settle - 0.75) / 0.25)
    if tip_in > 0:
        box = coachmark_tip(cv, hole, lines, demo.font(18, 700), alpha=tip_in, below=below,
                            gap=14, pad=(10, 14), arrow=8)
        cv.mark('tooltip', *box)


TECHNIQUE = Technique(
    id='coachmark-spotlight-cutout',
    name='Coachmark spotlight cutout',
    family='ui',
    group='Overlays & menus',
    aliases=('coachmark', 'onboarding spotlight', 'product tour highlight', 'feature walkthrough overlay'),
    definition='A dark veil covers the interface except for a clear rounded window around one control, '
               'with a pointer bubble explaining it, and the window then slides on to the next control.',
    phrasings=('dim the app and punch a hole around the button we are explaining',
               'an onboarding tour that highlights one feature at a time with a tip',
               'darken everything except the share button and add a little tooltip'),
    related=('spotlight-hover', 'spotlight-follow', 'spotlight-dim', 'highlighter-swipe',
             'drop-target-highlight', 'player-movement-trail'),
    api=('videobuilder.techniques.ui.coachmark_spotlight_cutout.spotlight_cutout',
         'videobuilder.techniques.ui.coachmark_spotlight_cutout.coachmark_tip',
         'videobuilder.techniques.ui.coachmark_spotlight_cutout.tour_hole'),
    demo=lambda: demo.film(draw),
)
