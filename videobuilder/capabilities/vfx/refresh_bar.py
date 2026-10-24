"""Refresh bar: a wide, soft horizontal band of brighter (or darker) light
creeps down through the picture and wraps round to the top again, the way a
screen caught on camera or a set with mains hum rolls a bar through itself."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def refresh_bar(cv, p, box=None, band=0.3, strength=0.3, color='#ffffff', edge=0.3, up=False, steps=24):
    """Draw one rolling bar over what is already in `box` (default: the whole
    canvas) at position `p`: 0 -> 1 is one full roll, the band entering at the
    top and leaving at the bottom (`up` reverses it); whole numbers wrap, so
    a steadily growing `p` rolls forever. `band` is the bar's height as a
    share of the box, `strength` its peak opacity, `color` white for a bright
    bar or black for a dark one. `edge` (0 -> 1) sharpens the trailing edge,
    as a real hum bar has, so the direction of travel reads."""
    box = box or vb.Box.of(cv)
    x, y, w, h = box
    bh = band * h
    t = p % 1.0
    if up:
        t = 1 - t
    centre = y - bh / 2 + t * (h + bh)
    r, g, b, _ = vb.canvas.rgba(color)
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    for cy in (centre - (h + bh), centre, centre + (h + bh)):  # wrap across the box's edges
        top = cy - bh / 2
        if top > y + h or top + bh < y:
            continue
        grad = cairo.LinearGradient(0, top, 0, top + bh)
        for i in range(steps + 1):
            s = i / steps
            u = (1 - s) if up else s          # 0 at the trailing edge, 1 at the leading one
            # Soft raised-cosine bump, skewed so it rises fast from the trailing edge.
            k = u ** (1 - 0.6 * edge) if u > 0 else 0.0
            a = strength * 0.5 * (1 - math.cos(2 * math.pi * k))
            grad.add_color_stop_rgba(s, r, g, b, a)
        c.rectangle(x, top, w, bh)
        c.set_source(grad)
        c.fill()
    c.restore()


def _scene(cv, box):
    """The demo's 'screen': a dusk landscape of rolling hills under a sun."""
    x, y, w, h = box
    sky = cairo.LinearGradient(0, y, 0, y + h)
    sky.add_color_stop_rgb(0, 0.27, 0.30, 0.55)
    sky.add_color_stop_rgb(0.6, 0.62, 0.66, 0.88)
    cv.ctx.rectangle(x, y, w, h)
    cv.ctx.set_source(sky)
    cv.ctx.fill()
    demo.dot(cv, x + w * 0.66, y + h * 0.42, r=h * 0.13, color='#f2b705')
    for base, amp, phase, color in ((0.58, 0.07, 0.4, '#7179b5'), (0.68, 0.05, 2.1, '#3f4778'),
                                    (0.8, 0.04, 4.0, '#20263f')):
        pts = [(x + w * i / 40, y + h * (base - amp * math.sin(i / 40 * 2 * math.pi * 1.3 + phase)))
               for i in range(41)]
        c = cv.ctx
        c.move_to(x, y + h)
        for px, py in pts:
            c.line_to(px, py)
        c.line_to(x + w, y + h)
        c.close_path()
        c.set_source_rgb(*vb.canvas.rgba(color)[:3])
        c.fill()


def draw(n, cv):
    w, h = demo.W * 0.72, demo.H * 0.72
    box = vb.Box((demo.W - w) / 2, (demo.H - h) / 2, w, h)
    cv.rect(box.x - 28, box.y - 28, w + 56, h + 56, '#0c0e12', radius=36)
    with cv.clip(*box, radius=14):
        _scene(cv, box)
        # One slow roll down the screen across the clip.
        refresh_bar(cv, -0.05 + 1.1 * n / (demo.FPS * demo.SECONDS), box, band=0.32, strength=0.38)
    cv.mark('screen', *box)


CAPABILITY = Capability(
    id='refresh-bar',
    name='Refresh bar',
    family='vfx',
    group='CRT & display',
    aliases=('rolling bar', 'hum bar', 'vertical roll bar', 'monitor flicker', 'scan roll'),
    definition='A broad, blurry stripe of brighter or dimmer light drifts slowly down the image '
               'and loops back to the top, like a TV screen filmed out of sync.',
    phrasings=('make it look like we filmed an old TV, with that band rolling down the screen',
               'add a slow bright bar crawling through the picture like a CRT on camera',
               'give the footage a hum bar that rolls vertically'),
    related=('vhs-tracking-bar', 'copper-bars', 'audio-waveform-bars', 'striped-progress-bar',
             'lower-third-slide-in-bar', 'indeterminate-bar'),
    api=('videobuilder.capabilities.vfx.refresh_bar.refresh_bar',),
    demo=lambda: demo.film(draw),
)
