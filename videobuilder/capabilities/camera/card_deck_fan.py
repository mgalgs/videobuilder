"""Card Deck Fan: a neat stack of cards spreads into a fan, each card swinging
about a shared pivot below the deck like a hand of playing cards."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def fan_pose(i, count, p, spread=0.9, radius=520, stack=4.0):
    """Where card `i` of `count` sits at fan progress `p` (0 = stacked, 1 =
    fanned), as `(dx, dy, angle)` relative to the deck's centre: the cards
    turn about a pivot `radius` px below the centre, splitting `spread`
    radians evenly from left to right. Stacked, each card sits `stack` px
    up-left of the one in front of it, so the deck reads as a pile."""
    t = i / (count - 1) - 0.5 if count > 1 else 0.0
    angle = spread * t * p
    back = (count - 1 - i) * stack * (1 - p)
    return (radius * math.sin(angle) - back, radius * (1 - math.cos(angle)) - back, angle)


def draw_fan(cv, cx, cy, count, p, draw_card, stagger=0.25, ease=vb.ease_out_back, **kw):
    """Draw `count` cards fanning out from a stack centred at (cx, cy) at
    progress `p` (0 -> 1). `draw_card(cv, i)` draws card `i` centred on the
    origin; it is called back to front (card 0, the leftmost, first) with the
    canvas turned into place. The outer cards start up to `stagger` of the
    move later than the middle, so the fan opens from the centre; `ease`
    shapes each card's own move. `kw` goes to `fan_pose`."""
    c = cv.ctx
    for i in range(count):
        off = abs(i / (count - 1) - 0.5) * 2 if count > 1 else 0.0
        q = ease(vb.clamp01((p - stagger * off) / (1 - stagger)))
        dx, dy, angle = fan_pose(i, count, q, **kw)
        c.save()
        c.translate(cx + dx, cy + dy)
        c.rotate(angle)
        draw_card(cv, i)
        c.restore()


SHADES = ('#2b3340', '#313a49', '#374152', '#3d485b', '#434f64')


def _card(cv, i):
    w, h = 300, 190
    x, y = -w / 2, -h / 2
    cv.shadow(x, y, w, h, radius=18, dy=8, blur=24, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, SHADES[i % len(SHADES)], radius=18)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=18, alpha=0.6)
    for k, frac in enumerate((0.62, 0.78, 0.46)):
        cv.rect(x + 28, y + 30 + k * 22, w * frac - 28, 8, demo.INK, radius=4, alpha=0.45)
    cv.rect(x + 28, y + h - 58, 72, 30, demo.ACCENT if i == 4 else demo.TEAL, radius=8)


def draw(n, cv):
    p = demo.phase(n, 0.5, 2.1)
    draw_fan(cv, demo.W / 2, demo.H / 2 - 30, 5, p, _card, spread=1.0, radius=560)
    cv.mark('deck', demo.W / 2 - 420, demo.H / 2 - 200, 840, 360)


CAPABILITY = Capability(
    id='card-deck-fan',
    name='Card deck fan',
    family='camera',
    group='3D motion',
    aliases=('card stack spread', 'fanned stack', 'hand of cards fan'),
    definition='A tidy pile of cards opens into an arc, every card tilting about a common point below '
               'so they splay out like a hand of playing cards.',
    phrasings=('the stack of cards spreads out into a fan',
               'fan the cards out like someone holding a hand in a card game',
               'cards pile up then swing apart into an arc'),
    related=('sticky-card-stack-on-scroll', 'stacked-card-reveal', 'flip', 'shape-stacking-drop',
             'rotating-polygon-loop', 'character-3d-flip'),
    api=('videobuilder.capabilities.camera.card_deck_fan.draw_fan',
         'videobuilder.capabilities.camera.card_deck_fan.fan_pose'),
    demo=lambda: demo.film(draw),
)
