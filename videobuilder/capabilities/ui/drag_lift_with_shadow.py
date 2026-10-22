"""Drag lift with shadow: an item picked up by the pointer grows a little and
its shadow drops further and spreads wider, so it reads as held above the
surface while it is dragged, then settles back down where it is let go."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def lift_look(lift, scale=0.08, rest=(4, 10, 0.4), held=(26, 44, 0.85)):
    """The look of an item `lift` (0 resting -> 1 held) off its surface, as
    `(scale, dy, blur, alpha)`: it grows by up to `scale`, and its shadow goes
    from `rest` to `held`, each a `(dy, blur, alpha)`, falling further below it,
    softer and darker."""
    k = vb.clamp01(lift)
    dy, blur, alpha = (a + (b - a) * k for a, b in zip(rest, held))
    return 1 + scale * k, dy, blur, alpha


def draw_lifted(cv, cx, cy, w, h, lift, body, radius=18, **look):
    """Draw an item of size w x h centred at (cx, cy), `lift` (0 -> 1) off the
    surface: its shadow from `lift_look` (`look` passes through), then
    `body(cv, x, y, w, h)` for the item itself at its lifted size. Returns the
    drawn Box."""
    s, dy, blur, alpha = lift_look(lift, **look)
    w, h, radius = w * s, h * s, radius * s
    x, y = cx - w / 2, cy - h / 2
    cv.shadow(x, y, w, h, radius=radius, dy=dy, blur=blur, color=(0, 0, 0, alpha))
    body(cv, x, y, w, h)
    return vb.Box(x, y, w, h)


def pointer(cv, x, y, size=28, pressed=False, color='#ffffff'):
    """An arrow cursor with its tip at (x, y); `pressed` shrinks it a touch,
    the way a click reads."""
    s = size * (0.9 if pressed else 1.0) / 34
    pts = [(0, 0), (0, 30), (8, 23), (13.5, 34), (18, 32), (12.5, 21.5), (22, 21.5)]
    c = cv.ctx
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(0, 0, 0, 0.85)
    c.set_line_width(2)
    c.stroke()
    c.restore()


CW, CH = 280, 170
HOME = (demo.W * 0.28, demo.H * 0.56)
DROP = (demo.W * 0.72, demo.H * 0.44)
GRAB = (CW * 0.3, CH * 0.22)  # where the pointer holds the card, from its centre


def _card_body(cv, x, y, w, h):
    cv.rect(x, y, w, h, '#3a4558', radius=18 * w / CW)
    bar = h * 0.07
    for i, (frac, a) in enumerate(((0.45, 0.9), (0.7, 0.55), (0.55, 0.55))):
        cv.rect(x + w * 0.09, y + h * 0.16 + i * bar * 2.1, w * frac, bar, demo.INK, radius=bar / 2, alpha=a)
    cv.rect(x + w * 0.09, y + h * 0.66, w * 0.28, h * 0.17, demo.ACCENT, radius=8 * w / CW)


def _slot(cv, cx, cy):
    x, y = cx - CW / 2, cy - CH / 2
    cv.rect(x - 3, y - 3, CW + 6, CH + 6, '#3a3e4a', radius=21)
    cv.rect(x, y, CW, CH, '#20222a', radius=18)


def draw(n, cv):
    cv.rect(50, 60, demo.W - 100, demo.H - 120, '#2c2f39', radius=28)  # a lighter surface, so the shadow shows
    for c in (HOME, DROP):
        _slot(cv, *c)
    up = vb.ease.bezier(0.3, 0, 0.2, 1)
    move = up(demo.phase(n, 0.9, 1.9))
    lift = up(demo.phase(n, 0.55, 0.85)) * (1 - up(demo.phase(n, 1.95, 2.25)))
    cx = HOME[0] + (DROP[0] - HOME[0]) * move
    cy = HOME[1] + (DROP[1] - HOME[1]) * move - 40 * math.sin(math.pi * move)
    box = draw_lifted(cv, cx, cy, CW, CH, lift, _card_body)
    cv.mark('card', *box)
    # The pointer glides in, grabs, carries the card, lets go and drifts off.
    come = up(demo.phase(n, 0.0, 0.5))
    leave = up(demo.phase(n, 2.3, 2.9))
    px = cx + GRAB[0] + 120 * (1 - come) + 70 * leave
    py = cy + GRAB[1] + 110 * (1 - come) + 50 * leave
    pointer(cv, px, py, pressed=0.5 <= n / demo.FPS < 2.1)


TECHNIQUE = Technique(
    id='drag-lift-with-shadow',
    name='Drag lift with shadow',
    family='ui',
    group='Gestures & drag',
    aliases=('picked-up item', 'drag elevation', 'lift on drag'),
    definition='When the pointer grabs an item it grows a little and its shadow falls further and softer '
               'beneath it, so it seems to hover above the page as it is dragged, then sinks back when dropped.',
    phrasings=('pick the card up with the cursor so it floats with a bigger shadow while I drag it',
               'the item lifts off the page when grabbed and settles back down when dropped',
               'show the card being dragged with a raised, elevated look'),
    related=('drop-shadow-lift', 'hover-lift', 'drop-shadow-breathing', 'shadow-play',
             'hover-letter-displacement', 'magnetic-snap'),
    api=('videobuilder.techniques.ui.drag_lift_with_shadow.draw_lifted',
         'videobuilder.techniques.ui.drag_lift_with_shadow.lift_look',
         'videobuilder.techniques.ui.drag_lift_with_shadow.pointer'),
    demo=lambda: demo.film(draw),
)
