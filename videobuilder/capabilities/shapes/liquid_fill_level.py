"""Liquid Fill Level: a container fills up with liquid whose surface keeps
rippling and sloshing as the level climbs, then calms once it stops."""
import math

import cairo
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def liquid_surface(u, t, amplitude, waves=1.6, speed=1.0):
    """The surface's height offset (px, + is down) at `u` (0 -> 1 across the
    container) and time `t` seconds: two travelling sines that drift against
    each other, plus a slow side-to-side tilt, all scaled by `amplitude`."""
    k = 2 * math.pi * waves
    w = 2 * math.pi * speed
    ripple = 0.6 * math.sin(k * u - 1.7 * w * t) + 0.4 * math.sin(1.9 * k * u + 1.1 * w * t + 1.0)
    tilt = math.sin(0.8 * w * t) * (u - 0.5) * 1.6
    return amplitude * (ripple + tilt)


def fill_wobble(t, start, end, settle=0.9):
    """How lively the surface is at `t` for a fill running `start` -> `end`
    seconds: a calm 0.25 before, 1 while it rises, then dying away over
    `settle` seconds back to 0.25. Pass it as `liquid_fill(..., wobble=)`."""
    if t < start:
        return 0.25
    if t <= end:
        return 1.0
    return 0.25 + 0.75 * math.exp(-3.0 * (t - end) / settle)


def liquid_fill(cv, x, y, w, h, level, t, color=demo.TEAL, radius=0, wobble=1.0, amplitude=None, back=True):
    """Fill the box (x, y, w, h) with liquid up to `level` (0 empty -> 1 full)
    at time `t` seconds. The surface ripples by `liquid_surface`, its height
    `amplitude` px (default 3% of `h`) times `wobble`; drive `wobble` with
    `fill_wobble` so it sloshes while rising and settles after. A fainter,
    out-of-step back wave gives depth (`back=False` drops it). Everything is
    clipped to the box's rounded corners (`radius`); draw the container's
    outline over it yourself."""
    level = vb.clamp01(level)
    if level <= 0:
        return
    amp = (h * 0.03 if amplitude is None else amplitude) * wobble
    amp *= min(1.0, level * 8) * min(1.0, (1 - level) * 8 + 0.15)  # flatter at the very bottom and brim
    base = y + h * (1 - level)
    steps = max(24, int(w / 8))
    c = cv.ctx
    r, g, b, _ = vb.canvas.rgba(color)

    def body(phase, alpha, light):
        c.new_path()
        c.move_to(x, y + h + 1)
        for i in range(steps + 1):
            u = i / steps
            c.line_to(x + u * w, base + liquid_surface(u, t + phase, amp))
        c.line_to(x + w, y + h + 1)
        c.close_path()
        grad = cairo.LinearGradient(0, base - amp, 0, y + h)
        grad.add_color_stop_rgba(0, min(1, r + light), min(1, g + light), min(1, b + light), alpha)
        grad.add_color_stop_rgba(1, r * 0.6, g * 0.6, b * 0.6, alpha)
        c.set_source(grad)
        c.fill()

    with cv.clip(x, y, w, h, radius):
        if back:
            body(0.37, 0.45, 0.12)
        body(0.0, 1.0, 0.08)
        c.new_path()  # a bright meniscus line along the front surface
        for i in range(steps + 1):
            u = i / steps
            c.line_to(x + u * w, base + liquid_surface(u, t, amp))
        c.set_source_rgba(1, 1, 1, 0.55)
        c.set_line_width(3)
        c.stroke()


START, END = 0.3, 2.3


def draw(n, cv):
    t = n / demo.FPS
    gw, gh, rad = 190, 300, 26
    x, y = (demo.W - gw) / 2, (demo.H - gh) / 2 - 24
    level = 0.06 + 0.78 * vb.ease_in_out_quart(demo.phase(n, START, END))
    cv.rect(x, y, gw, gh, demo.LINE, radius=rad, alpha=0.5)  # the empty glass
    liquid_fill(cv, x, y, gw, gh, level, t, radius=rad, wobble=fill_wobble(t, START, END))
    cv.rect(x + 14, y + 26, 7, gh - 52, demo.INK, radius=5, alpha=0.12)  # a glint on the glass
    cv.outline(x, y, gw, gh, demo.INK, width=3, radius=rad, alpha=0.85)
    demo.word(cv, f'{round(level * 100)}%', demo.W / 2, y + gh + 34, size=30, color=demo.MUTED, weight=700)
    cv.mark('glass', x, y, gw, gh)


CAPABILITY = Capability(
    id='liquid-fill-level',
    name='Liquid fill level',
    family='shapes',
    group='Liquid & organic',
    aliases=('liquid level rise', 'fill wave', 'tank fill animation', 'water fill'),
    definition='A shape fills up from the bottom with liquid whose top edge waves and sloshes as it rises, '
               'then calms down when it stops.',
    phrasings=('fill the glass up with water, wobbling as it goes',
               'show the tank filling up with a wavy liquid surface',
               'a progress meter that fills like liquid sloshing in a jar'),
    related=('color-fill-rise', 'liquid-morph', 'bubbles', 'sph-fluid', 'height-field-ripples', 'liquid-melt'),
    api=('videobuilder.capabilities.shapes.liquid_fill_level.liquid_fill',
         'videobuilder.capabilities.shapes.liquid_fill_level.fill_wobble',
         'videobuilder.capabilities.shapes.liquid_fill_level.liquid_surface'),
    demo=lambda: demo.film(draw),
)
