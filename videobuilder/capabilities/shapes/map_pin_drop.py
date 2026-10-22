"""Map pin drop: a location marker falls onto a spot, lands with a squash,
hops once and settles, while a ring spreads out across the ground where its
tip touched down."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

LAND, HOP_END = 0.42, 0.72  # fractions of the move: first touchdown, end of the hop


def pin_drop(p, hop=0.16):
    """Progress `p` (0 -> 1) of a pin drop -> `(lift, squash, ripple)`.
    `lift` is the tip's height above its spot as a fraction of the drop (1 at
    the start, 0 on the ground); `hop` is the height of the single rebound.
    `squash` (0 -> about 0.2) flattens the pin just after each touchdown.
    `ripple` runs 0 -> 1 from the first touchdown to the end (0 before it)."""
    p = vb.clamp01(p)
    if p < LAND:
        x = p / LAND
        lift, since = 1 - x * x, None  # falls under gravity
    elif p < HOP_END:
        x = (p - LAND) / (HOP_END - LAND)
        lift, since = hop * 4 * x * (1 - x), p - LAND
    else:
        lift, since = 0.0, p - HOP_END
    squash = 0.0
    if since is not None and since < 0.12:
        strength = 0.22 if p < HOP_END else 0.1
        squash = strength * math.sin(math.pi * since / 0.12)
    ripple = 0.0 if p < LAND else (p - LAND) / (1 - LAND)
    return lift, squash, ripple


def draw_pin(cv, x, y, size=84, color=demo.ACCENT, hole=demo.BG, squash=0.0, alpha=1.0):
    """A teardrop location pin whose tip sits at (x, y), `size` tall, with a
    round hole in its head. `squash` widens and flattens it about the tip."""
    c = cv.ctx
    r = size * 0.36
    d = size - r  # tip to centre of the head
    b = math.acos(r / d)
    c.save()
    c.translate(x, y)
    c.scale(1 + squash, 1 - squash)
    c.new_path()
    c.move_to(0, 0)
    c.arc(0, -d, r, math.pi / 2 + b, math.pi / 2 - b + 2 * math.pi)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    c.fill()
    c.new_path()
    c.arc(0, -d, r * 0.42, 0, 2 * math.pi)
    c.set_source_rgba(*vb.canvas.rgba(hole, alpha))
    c.fill()
    c.restore()


def _ellipse(cv, cx, cy, rx, ry, color, alpha=1.0, width=None):
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.scale(rx, ry)
    c.new_path()
    c.arc(0, 0, 1, 0, 2 * math.pi)
    c.restore()  # restore before stroking so the line width isn't squashed too
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    if width:
        c.set_line_width(width)
        c.stroke()
    else:
        c.fill()


def draw_pin_drop(cv, x, y, p, drop=300, size=84, color=demo.ACCENT, hole=demo.BG,
                  ripple_color=None, ripple=1.0, tilt=0.38, hop=0.16):
    """A whole pin drop onto (x, y) at progress `p` (0 -> 1): the ground
    shadow, the spreading ring and the pin falling `drop` px with one hop.
    `ripple` scales the ring's reach (1 reaches about 1.6 x `size`); `tilt`
    flattens the shadow and ring into ellipses for a ground seen at an angle
    (1 for straight down). Returns the pin's Box."""
    lift, squash, spread = pin_drop(p, hop)
    rc = ripple_color or color
    if 0 < spread < 1:
        for lag in (0.0, 0.18):
            q = vb.clamp01((spread - lag) / (1 - lag))
            if q <= 0:
                continue
            e = 1 - (1 - q) ** 3
            rx = size * (0.15 + 1.45 * e) * ripple
            _ellipse(cv, x, y, rx, rx * tilt, rc, alpha=0.8 * (1 - q), width=5 * (1 - q) + 1.5)
    near = 1 - lift
    sw = size * 0.3 * (0.45 + 0.55 * near)
    _ellipse(cv, x, y, sw, sw * tilt, '#000000', alpha=0.12 + 0.3 * near)
    top = y - lift * drop
    draw_pin(cv, x, top, size, color, hole, squash)
    w = size * 0.72 * (1 + squash)
    return vb.Box(x - w / 2, top - size * (1 - squash), w, size * (1 - squash))


def _map(cv, box):
    """A plain street map tile: blocks, a few roads and a river."""
    x, y, w, h = box
    with cv.clip(x, y, w, h, radius=16):
        cv.rect(x, y, w, h, '#1d2430')
        step = 64
        for gx in range(int(x), int(x + w), step):
            cv.line(gx, y, gx, y + h, demo.LINE, width=3, alpha=0.9)
        for gy in range(int(y), int(y + h), step):
            cv.line(x, gy, x + w, gy, demo.LINE, width=3, alpha=0.9)
        cv.line(x, y + h * 0.85, x + w, y + h * 0.3, demo.TEAL, width=8, alpha=0.55)
        cv.rect(x + 2 * step + 7, y + step + 7, step - 14, step - 14, '#2b4a3a', radius=6)
        cv.line(x + w * 0.62, y, x + w * 0.62 + 40, y + h, demo.MUTED, width=6, alpha=0.5)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=16)


def draw(n, cv):
    box = vb.Box(demo.W / 2 - 380, 170, 760, 330)
    _map(cv, box)
    spot = (demo.W / 2, box.y + box.h * 0.6)
    pin = draw_pin_drop(cv, *spot, demo.phase(n, 0.35, 2.4), drop=250, size=84, tilt=0.45)
    cv.mark('pin', *pin)


CAPABILITY = Capability(
    id='map-pin-drop',
    name='Map pin drop',
    family='shapes',
    group='Explainer & infographic',
    aliases=('marker drop', 'location pin drop', 'pin drop', 'location pin bounce', 'pin land'),
    definition='A teardrop location marker falls from above onto a spot on a map, squashes and hops once '
               'as it lands, and sends a fading ring outward from its tip.',
    phrasings=('drop a location pin onto the map',
               'a marker falls in and bounces to show where it is',
               'pin the place on the map with a little bounce and a ripple'),
    related=('location-ripple-pulse', 'numbered-hotspot-pins', 'badge-stamp-impact',
             'bouncing-ball-word-marker', 'drop-target-highlight', 'highlighter-swipe'),
    api=('videobuilder.capabilities.shapes.map_pin_drop.draw_pin_drop',
         'videobuilder.capabilities.shapes.map_pin_drop.pin_drop',
         'videobuilder.capabilities.shapes.map_pin_drop.draw_pin'),
    demo=lambda: demo.film(draw),
)
