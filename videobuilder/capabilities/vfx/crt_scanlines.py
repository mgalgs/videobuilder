"""CRT scanlines: thin dark horizontal lines laid evenly over the picture,
the gaps between a tube's rows of glowing phosphor, often with a faint
brighter band drifting down the screen and the corners falling off dark."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def crt_scanlines(cv, amount=1.0, x=0, y=0, w=None, h=None, pitch=6, darkness=0.5, t=0.0, roll=3.0,
                  band=0.18, flicker=0.04, vignette=0.45, color='#000000'):
    """Lay CRT scanlines over whatever is already drawn in (x, y, w, h)
    (default the whole frame), at strength `amount` (0 -> 1; 0 draws nothing).

    One dark line every `pitch` px, half a pitch thick, at `darkness` opacity.
    Pass the film time `t` (seconds) to animate it: a soft brighter band rolls
    down the area every `roll` seconds (`band` is its height as a share of
    `h`; `roll=0` turns it off) and the line darkness flickers by up to
    `flicker`. `vignette` darkens the corners like a curved tube's glass.
    Call it last, over the finished picture, e.g. inside a film's draw:
    `scene(cv); crt_scanlines(cv, t=n / fps)`."""
    if amount <= 0:
        return
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    ctx = cv.ctx
    ctx.save()
    ctx.rectangle(x, y, w, h)
    ctx.clip()

    # the rolling band: a slightly brighter strip, as if the refresh drifts against the camera
    if roll and band > 0:
        bh = h * band
        top = y - bh + ((t / roll) % 1.0) * (h + bh)
        g = cairo.LinearGradient(0, top, 0, top + bh)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 1, 1, 1, 0.07 * amount)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(g)
        ctx.rectangle(x, top, w, bh)
        ctx.fill()

    # the lines themselves, all in one fill
    wobble = 1 - flicker * (0.5 + 0.5 * math.sin(t * 2 * math.pi * 7.3) * math.sin(t * 2 * math.pi * 3.1))
    r, g_, b, _ = vb.canvas.rgba(color)
    ctx.set_source_rgba(r, g_, b, darkness * amount * wobble)
    thick = pitch / 2
    row = y + (pitch - thick) / 2
    while row < y + h:
        ctx.rectangle(x, row, w, thick)
        row += pitch
    ctx.fill()

    if vignette > 0:
        cx, cy = x + w / 2, y + h / 2
        vg = cairo.RadialGradient(cx, cy, min(w, h) * 0.35, cx, cy, math.hypot(w, h) / 2)
        vg.add_color_stop_rgba(0, 0, 0, 0, 0)
        vg.add_color_stop_rgba(1, 0, 0, 0, vignette * amount)
        ctx.set_source(vg)
        ctx.paint()
    ctx.restore()


SCREEN_W, SCREEN_H = 760, 440


def draw(n, cv):
    t = n / demo.FPS
    amount = vb.ease_in_out_quart(demo.phase(n, 0.5, 1.4))
    x, y = (demo.W - SCREEN_W) / 2, (demo.H - SCREEN_H) / 2
    cv.shadow(x, y, SCREEN_W, SCREEN_H, radius=24, dy=10, blur=30, color=(0, 0, 0, 0.5))
    with cv.clip(x, y, SCREEN_W, SCREEN_H, radius=24):
        img = demo.photo()
        cv.image(img, *vb.Box(x, y, SCREEN_W, SCREEN_H).cover(img.w, img.h))
        demo.word(cv, 'ON AIR', demo.W / 2, demo.H / 2, size=104, weight=900)
        crt_scanlines(cv, amount, x, y, SCREEN_W, SCREEN_H, pitch=6, darkness=0.6, t=t, roll=2.2, band=0.22)
    cv.mark('screen', x, y, SCREEN_W, SCREEN_H)


CAPABILITY = Capability(
    id='crt-scanlines',
    name='CRT scanlines',
    family='vfx',
    group='CRT & display',
    aliases=('scanline overlay', 'raster lines', 'CRT filter', 'retro TV lines'),
    definition='Fine dark stripes sit across the whole picture at an even spacing, so it looks like it is '
               'being shown on an old tube television.',
    phrasings=('make this look like it is playing on an old TV with those horizontal lines',
               'put a retro monitor line texture over the footage',
               'give the shot a vintage screen look with stripes across it'),
    related=('scanline-wipe', 'scanline-tear', 'scanline-jitter', 'crumple', 'virtual-first-down-line',
             'isolines-contour-animation'),
    api=('videobuilder.capabilities.vfx.crt_scanlines.crt_scanlines',),
    demo=lambda: demo.film(draw),
)
