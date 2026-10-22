"""Numbered hotspot pins: round badges numbered 1, 2, 3 pop onto points of an
image one after another, each sending out a slow pulsing ring, so the parts
can be talked through in order."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..shapes.ripple_rings import ripple_rings


def hotspot_pin(cv, x, y, number, t, label=None, size=22, color=demo.ACCENT, ink=demo.INK,
                pop=0.35, every=1.0, life=1.0, font=None, side='right'):
    """One numbered pin on (x, y), `t` seconds after it appears (nothing
    before 0). The badge, `size` px in radius and filled with `color`, pops
    in with an overshoot over `pop` seconds; then a ring leaves it every
    `every` seconds and fades over `life`. `label`, if given, slides out in a
    tag to the `side` ('right' or 'left') once the badge has landed. Returns
    the badge's Box."""
    if t < 0:
        return vb.Box(x - size, y - size, 2 * size, 2 * size)
    s = vb.ease_out_back(vb.clamp01(t / pop))
    ripple_rings(cv, x, y, t - pop * 0.6, radius=size * 3.2, every=every, life=life, color=color,
                 width=3, start_radius=size * 0.9)
    r = size * s
    if r > 0:
        cv.sector(x, y + 3, r, 0, math.tau, '#000000', alpha=0.3)  # a soft drop under the badge
        cv.sector(x, y, r, 0, math.tau, color)
        cv.arc(x, y, r, 0, math.tau, ink, width=max(1.0, size * 0.12))
        f = font or demo.font(round(size * 1.05), 800)
        with cv.layer(opacity=vb.clamp01(t / (pop * 0.6))):
            num = str(number)
            tw, th = vb.text.block_size([num], f)
            ctx = cv.ctx
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(s, s)
            vb.text.draw(cv, [num], f, -tw / 2, -th / 2, ink)
            ctx.restore()
    if label:
        q = vb.ease_out_quint(vb.clamp01((t - pop * 0.8) / 0.4))
        if q > 0:
            lf = demo.font(round(size * 0.8), 700)
            tw, th = vb.text.block_size([label], lf)
            tag_w, tag_h = tw + 24, th + 12
            gap = size + 10
            tx = x + gap if side == 'right' else x - gap - tag_w
            slide = (1 - q) * 14 * (-1 if side == 'right' else 1)
            with cv.layer(opacity=q, dx=slide):
                cv.rect(tx, y - tag_h / 2, tag_w, tag_h, '#101217', radius=tag_h / 2, alpha=0.85)
                vb.text.draw(cv, [label], lf, tx + 12, y - th / 2, ink)
    return vb.Box(x - size, y - size, 2 * size, 2 * size)


def hotspot_pins(cv, spots, t, stagger=0.55, **kw):
    """Pins on every spot in `spots`, numbered 1, 2, 3 in order: each is
    `(x, y)` or `(x, y, label)` (or `(x, y, label, side)`), and the k-th pops
    in `k * stagger` seconds after `t` = 0. `kw` goes to `hotspot_pin`.
    Returns the badges' Boxes."""
    boxes = []
    for k, spot in enumerate(spots):
        x, y, *rest = spot
        label = rest[0] if rest else None
        extra = {'side': rest[1]} if len(rest) > 1 else {}
        boxes.append(hotspot_pin(cv, x, y, k + 1, t - k * stagger, label=label, **kw, **extra))
    return boxes


def draw(n, cv):
    img = demo.photo()
    w = 620
    h = w * img.h / img.w
    box = vb.Box((demo.W - w) / 2, (demo.H - h) / 2, w, h)
    with cv.clip(*box, radius=18):
        cv.image(img, *box)
    cv.outline(*box, demo.LINE, width=2, radius=18)
    at = lambda fx, fy: (box.x + box.w * fx, box.y + box.h * fy)  # noqa: E731 -- a point on the photo
    spots = [(*at(0.72, 0.30), 'Sun'), (*at(0.55, 0.58), 'Ridge'), (*at(0.18, 0.64), 'Hill')]
    for k, b in enumerate(hotspot_pins(cv, spots, n / demo.FPS - 0.35, stagger=0.6)):
        cv.mark(f'pin{k + 1}', *b)


CAPABILITY = Capability(
    id='numbered-hotspot-pins',
    name='Numbered hotspot pins',
    family='broadcast',
    group='Annotation',
    aliases=('hotspot markers', 'pulse pins', 'numbered callouts', 'hotspots'),
    definition='Small round badges numbered in order pop onto chosen points of a picture one at a time, '
               'each throbbing with a soft ring so the viewer knows where to look next.',
    phrasings=('put numbered dots on the image to point out each part',
               'mark the spots one, two, three with pulsing markers',
               'pop numbered pins onto the photo in order as we explain them'),
    related=('map-pin-drop', 'milestone-marker-pop', 'highlighter-swipe', 'live-indicator-pulse',
             'scatter-plot-point-appear', 'location-ripple-pulse'),
    api=('videobuilder.capabilities.broadcast.numbered_hotspot_pins.hotspot_pins',
         'videobuilder.capabilities.broadcast.numbered_hotspot_pins.hotspot_pin',
         'videobuilder.capabilities.shapes.ripple_rings.ripple_rings'),
    demo=lambda: demo.film(draw),
)
