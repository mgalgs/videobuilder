"""Broadcast title card stinger: a coloured panel led by an accent bar wipes
across the whole frame, the show title lands big on it, then the panel and
title shrink together into a small tag parked in the corner over the picture."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _lerp(a, b, t):
    return a + (b - a) * t


def draw_title_stinger(cv, text, font, p, panel=demo.LINE, accent=demo.ACCENT, color=demo.INK,
                       tag_scale=0.36, margin=48, pad=28, bar=26, wipe=0.25, land=0.45, shrink=0.62):
    """Draw the stinger at progress `p` (0 -> 1) over whatever is already on
    `cv`. Until `wipe` the panel sweeps in from the left behind an accent bar
    of width `bar`; from `wipe * 0.8` to `land` the title (in `font`) rises
    into the middle of the frame; it holds until `shrink`, then panel and
    title ease down to `tag_scale` into a tag `margin` from the top-left
    corner, the bar slimming to a stripe on its left edge. At `p >= 1` the tag
    simply holds, so a film keeps calling it with `p = 1` for as long as the
    tag should stay up. Returns the Box of the panel as drawn."""
    W, H = cv.width, cv.height
    tw, th = vb.text.block_size([text], font)
    k = vb.ease_in_out_quart(vb.clamp01((p - shrink) / (0.92 - shrink)))
    s = _lerp(1.0, tag_scale, k)
    tag_w, tag_h = tw * tag_scale + 2 * pad, th * tag_scale + 2 * pad
    if p < wipe:
        e = vb.ease_in_out_quart(vb.clamp01(p / wipe))
        x, y, w, h = 0, 0, (W + bar) * e - bar, H
    else:
        x, y = _lerp(0, margin, k), _lerp(0, margin, k)
        w, h = _lerp(W, tag_w, k), _lerp(H, tag_h, k)
    b = _lerp(bar, bar * 0.3, k)
    if w > 0:
        if k > 0:
            cv.shadow(x, y, w, h, dy=8, blur=24 * k, color=(0, 0, 0, 0.4 * k))
        cv.rect(x, y, w, h, panel)
    if p < wipe:
        cv.rect(x + w, y, b, h, accent)  # the bar leads the panel across
    else:
        cv.rect(x, y, b, h, accent)
    rise = vb.ease_out_expo(vb.clamp01((p - wipe * 0.8) / (land - wipe * 0.8)))
    if rise > 0 and w > 0:
        cx, cy = x + w / 2 + b / 2 * k, y + h / 2
        with cv.clip(x + b, y, max(0, w - b), h):
            with cv.layer(opacity=rise, dx=cx, dy=cy + th * 0.6 * (1 - rise), scale=s):
                vb.text.draw(cv, [text], font, -tw / 2, -th / 2, color)
    return vb.Box(x, y, max(0, w), h)


def _scene(cv):
    img = demo.photo()
    cv.image(img, *vb.Box.of(cv).cover(img.w, img.h))


def draw(n, cv):
    _scene(cv)
    box = draw_title_stinger(cv, 'THE LATE SHOW', demo.font(104, 900), demo.phase(n, 0.2, 2.7))
    cv.mark('card', *box)


CAPABILITY = Capability(
    id='broadcast-title-card-stinger',
    name='Broadcast title card stinger',
    family='broadcast',
    group='Title sequences',
    aliases=('program title card', 'show title card', 'title stinger', 'segment bumper'),
    definition='A bold panel sweeps across the whole screen to present the show title, '
               'then shrinks with it into a small tag that stays in the corner.',
    phrasings=('a TV-style title that fills the screen and then tucks itself into the corner',
               'open the segment with a big full-frame name card that turns into a corner badge',
               'a colour bar wipes on the program title, then it shrinks down to a little label'),
    related=('title-card-reveal', 'end-card-with-subscribe-slot', 'quote-card-reveal',
             'stacked-card-reveal', 'logo-sting', 'cctv-surveillance-look'),
    api=('videobuilder.capabilities.broadcast.broadcast_title_card_stinger.draw_title_stinger',),
    demo=lambda: demo.film(draw),
)
