"""Coin flip: a round badge spins edge-over-edge about its vertical axis like a
tossed coin, its face narrowing to a thin rim and widening again, front and
back taking turns, until it slows and settles on its front."""
import math

from .. import _demo as demo
from ..schema import Technique


def coin_flip(cv, cx, cy, r, angle, front, back, rim='#8a3a31', thickness=0.12, shade=0.45):
    """Draw a coin of radius `r` centred at (cx, cy), turned `angle` radians
    about its vertical axis (0: front facing the camera, pi: back).

    `front(cv, r)` and `back(cv, r)` draw a face centred at the origin, radius
    `r`; they are squashed into the turn here. `rim` colours the coin's edge,
    `thickness` is its depth as a fraction of `r`, and `shade` darkens a face
    as it turns away. Spin it by driving `angle` through whole turns, eased,
    and land on a multiple of 2*pi to finish on the front."""
    c, s = math.cos(angle), math.sin(angle)
    sx = max(abs(c), 0.004)
    depth = thickness * r
    ctx = cv.ctx
    # The edge: a run of rim discs from the back face to the front, seen side-on.
    steps = max(2, int(abs(s) * depth / 2) + 2)
    for k in range(steps):
        off = (k / (steps - 1) - 0.5) * depth * s
        ctx.save()
        ctx.translate(cx + off, cy)
        ctx.scale(sx, 1)
        demo.dot(cv, 0, 0, r, color=rim)
        ctx.restore()
    # The face toward the camera, on the near side of the edge.
    ctx.save()
    ctx.translate(cx + 0.5 * depth * s * (1 if c >= 0 else -1), cy)
    ctx.scale(sx if c >= 0 else -sx, 1)  # the back reads unmirrored once it faces us
    (front if c >= 0 else back)(cv, r)
    if shade:
        demo.dot(cv, 0, 0, r, color='#000000', alpha=shade * (1 - abs(c)))
    ctx.restore()
    cv.mark('coin', cx - r * sx - depth / 2, cy - r, 2 * r * sx + depth, 2 * r)


def _face(fill, ring, mark):
    def draw(cv, r):
        demo.dot(cv, 0, 0, r, color=fill)
        cv.arc(0, 0, r * 0.84, 0, 2 * math.pi, ring, width=r * 0.05)
        demo.word(cv, mark, 0, 0, size=r * 0.95, color=ring, weight=900)
    return draw


FRONT = _face(demo.ACCENT, demo.INK, 'V')
BACK = _face(demo.TEAL, demo.BG, '★')


def draw(n, cv):
    p = demo.phase(n, 0.3, 2.4)
    spin = 1 - (1 - p) ** 3                      # fast off the toss, slowing to land
    angle = 2 * math.pi * 4 * spin               # four whole turns: ends on the front
    hop = 4 * p * (1 - p)                        # up and back down while it spins
    r, ground = 90, demo.H - 70
    cy = ground - r - 20 - 170 * hop
    cv.ctx.save()
    cv.ctx.translate(demo.W / 2, ground)
    cv.ctx.scale(1, 0.12)
    demo.dot(cv, 0, 0, r * (1 - 0.35 * hop), color='#000000', alpha=0.45 - 0.25 * hop)
    cv.ctx.restore()
    coin_flip(cv, demo.W / 2, cy, r, angle, FRONT, BACK)


TECHNIQUE = Technique(
    id='coin-flip',
    name='Coin flip',
    family='shapes',
    group='Logo animation',
    aliases=('coin spin', 'coin toss', 'spinning coin', 'badge flip'),
    definition='A round logo or badge spins around its upright axis like a tossed coin, '
               'thinning to its edge and showing front and back in turn before it slows and lands face-up.',
    phrasings=('spin the logo like a coin being flipped',
               'toss the badge so it twirls and lands on the front',
               'make the round icon flip over and over like a coin'),
    related=('flip', 'character-3d-flip', 'turntable-rotation', 'tile-flip', 'word-flip-in',
             'rotating-polygon-loop'),
    api=('videobuilder.techniques.shapes.coin_flip.coin_flip',),
    demo=lambda: demo.film(draw),
)
