"""Appeal: the same move made likeable. A shape that only slides from A to B
is correct but lifeless; give it a crouch before it leaves, a stretch in the
air, a squash on landing, a settle, and a face that reacts, and it reads as a
character with some charm. `appealing_hop` is that hop as numbers, for any
shape a film draws about its base."""
import math
from collections import namedtuple

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

Hop = namedtuple('Hop', 'travel lift sx sy tilt glee')
Hop.__doc__ = """One frame of `appealing_hop`: `travel` 0..1 along the ground,
`lift` 0..1 of the hop's height, `sx`/`sy` squash and stretch about the base,
`tilt` radians of lean into the move, and `glee` 0..1, how pleased it looks
(for a face: a wider smile, eyes up)."""


def appealing_hop(p, crouch=0.2, air=0.42, squash=0.12):
    """A Hop for progress `p` in [0, 1] through one hop with appeal: it
    crouches wide for the first `crouch` share (anticipation), springs up
    tall and leaning for the next `air` share while it travels, squashes flat
    on landing, then wobbles back to round over the rest. Scale `squash` for
    a softer or rubberier character. Draw with `sx`/`sy` about its base, at
    `lift` x the hop height, `travel` of the way across."""
    p = vb.clamp01(p)
    land = crouch + air
    if p < crouch:
        u = vb.ease_in_out_quart(p / crouch)
        return Hop(0.0, 0.0, 1 + squash * u, 1 - 1.4 * squash * u, -0.06 * u, 0.3 * u)
    if p < land:
        u = (p - crouch) / air
        stretch = abs(math.cos(math.pi * u))           # tallest leaving and arriving, round at the top
        return Hop(u, math.sin(math.pi * u), 1 - squash * stretch, 1 + 1.4 * squash * stretch,
                   0.12 * math.cos(math.pi * u), 0.3 + 0.7 * math.sin(math.pi * u / 2))
    u = (p - land) / (1 - land)
    wob = math.exp(-5 * u) * math.cos(3 * math.pi * u)  # flat on contact, a quick rebound, then round
    return Hop(1.0, 0.0, 1 + 1.4 * squash * wob, 1 - 1.6 * squash * wob, 0.0, 1.0)


def _face(cv, cx, base, r, sx=1.0, sy=1.0, tilt=0.0, glee=0.0, color=demo.ACCENT, blink=False):
    """A round character standing on `base`, drawn about its feet."""
    c = cv.ctx
    c.save()
    c.translate(cx, base)
    c.rotate(tilt)
    c.scale(sx, sy)
    demo.dot(cv, 0, -r, r, color=color)
    ink = demo.BG
    ey = -r * (1.12 + 0.08 * glee)
    for side in (-1, 1):
        if blink:
            cv.line(side * r * 0.34 - r * 0.1, ey, side * r * 0.34 + r * 0.1, ey, ink, width=r * 0.07)
        else:
            demo.dot(cv, side * r * 0.34, ey, r * (0.09 + 0.03 * glee), color=ink)
    mouth = 0.15 + 0.55 * glee   # flat line -> wide grin
    if glee <= 0:
        cv.line(-r * 0.22, -r * 0.62, r * 0.22, -r * 0.62, ink, width=r * 0.07)
    else:
        cv.arc(0, -r * (0.62 + 0.25 * mouth), r * 0.38, math.pi * (0.5 - mouth / 2), math.pi * (0.5 + mouth / 2),
               ink, width=r * 0.08)
    c.restore()


def draw(n, cv):
    W, H, r = demo.W, demo.H, 40
    ground, half, span = H * 0.76, W / 2, W * 0.16
    cv.line(half, 90, half, H - 50, demo.LINE, width=2)
    f = demo.font(28, 700)
    for label, cx, ink in (('without', W / 4, demo.MUTED), ('with', 3 * W / 4, demo.INK)):
        demo.word(cv, label, cx, 60, font=f, color=ink)
        cv.line(cx - span - 60, ground, cx + span + 60, ground, demo.LINE, width=3)
    p = demo.phase(n, 0.4, 2.6)
    # Without: the same distance in the same time, slid at constant speed, blank-faced.
    x0, x1 = W / 4 - span, W / 4 + span
    _face(cv, x0 + (x1 - x0) * p, ground, r, color=demo.MUTED)
    # With: anticipation, arc, stretch, squash, settle, and a face that enjoys it.
    h = appealing_hop(p)
    x0, x1 = 3 * W / 4 - span, 3 * W / 4 + span
    x, base = x0 + (x1 - x0) * h.travel, ground - 170 * h.lift
    near = 1 - h.lift
    c = cv.ctx
    c.save()
    c.translate(x, ground + 4)
    c.scale(1, 0.2)
    demo.dot(cv, 0, 0, r * h.sx * (0.6 + 0.4 * near), color='#000000', alpha=0.15 + 0.3 * near)
    c.restore()
    _face(cv, x, base, r, h.sx, h.sy, h.tilt, h.glee, blink=2.75 < n / demo.FPS < 2.85)
    cv.mark('character', x - r * h.sx, base - 2 * r * h.sy, 2 * r * h.sx, 2 * r * h.sy)


TECHNIQUE = Technique(
    id='appeal',
    name='Appeal',
    family='principles',
    group='Disney principles',
    aliases=('charm', 'personality motion'),
    definition='Motion given enough character, through clear shapes, lively timing and a hint of emotion, '
               'that the viewer enjoys watching it and warms to whatever is moving.',
    phrasings=('make it feel friendly and full of personality',
               'give the mascot some charm when it moves',
               'make this move cute and likeable instead of mechanical'),
    related=('op-art-vibrating-pattern', 'stop-motion-animation', 'interruptible-motion', 'smooth-scroll-inertia',
             'ease-in-sine', 'motion-blur'),
    api=('videobuilder.techniques.principles.appeal.appealing_hop',),
    demo=lambda: demo.film(draw),
)
