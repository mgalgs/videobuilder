"""Stacked card reveal: the outgoing scene shrinks into the top card of a
deck, is flung off to one side with a tilt, and the card underneath -- the
incoming scene -- rises to the front and grows back to full frame."""
import math

from .. import _demo as demo
from ...ease import bezier, ease_in_out_quart, ease_out_quint, interpolate
from ..schema import Capability

_SWIPE = bezier(0.55, 0, 0.35, 1)  # a slow pull, then a quick fling


def _scene_card(cv, draw, cx, cy, scale, angle=0.0, radius=36, alpha=1.0):
    """`draw(cv)` as a full-frame scene shrunk to a rounded card centred at
    (cx, cy), turned by `angle` radians, with a soft shadow under it."""
    w, h = cv.width, cv.height
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(angle)
    c.scale(scale, scale)
    c.translate(-w / 2, -h / 2)
    r = radius / max(scale, 1e-3) * min(1.0, (1 - scale) * 4)  # corners round in as it leaves full frame
    with cv.layer(opacity=alpha):
        cv.shadow(0, 0, w, h, radius=r, dy=24, blur=60, color=(0, 0, 0, 0.5 * min(1.0, (1 - scale) * 4)))
        with cv.clip(0, 0, w, h, radius=r):
            draw(cv)
    c.restore()


def stacked_card_reveal(cv, a, b, p, card=0.62, depth=3, direction=1, tilt=14, gap=40,
                        background=demo.BG, blank='#2a2f3a'):
    """Draw the reveal at progress `p` (0 -> 1). For the first quarter `a`
    shrinks to a card `card` of the frame wide while the deck gathers under it
    (`b` next, then `depth - 1` `blank` cards, each `gap` px lower and a
    little smaller, on `background`); through the middle half `a` swipes off
    sideways (`direction` 1 = right, -1 = left), turning up to `tilt` degrees,
    and every card below steps up one place; for the last quarter `b` grows
    back to full frame.

    In a film, call it while two shots are live in an overlap, e.g.
    `stacked_card_reveal(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    w, h = cv.width, cv.height
    gather = ease_in_out_quart(min(1.0, p / 0.25))
    swipe = _SWIPE(interpolate(p, (0.25, 0.75), (0.0, 1.0)))
    expand = ease_in_out_quart(interpolate(p, (0.75, 1.0), (0.0, 1.0)))

    def slot(k):
        """(centre y, scale) of the card `k` places from the top (fractional k between places)."""
        return h / 2 + k * gap, card * (1 - 0.05 * k)

    cv.fill(background)
    # The deck under the top card, back to front: blanks, then b. Each sits one
    # place lower until the top card leaves, then steps up one place.
    for k in range(depth, 0, -1):
        place = k - swipe
        cy, s = slot(place)
        if k == 1:  # b, the incoming scene: once on top it grows back to full frame
            cy, s = cy + (h / 2 - cy) * expand, s + (1 - s) * expand
            _scene_card(cv, b, w / 2, cy, s, alpha=min(1.0, gather * 1.5))
        else:
            # The deck closes up behind b as it grows, then fades away.
            alpha = gather * (1 - expand)
            if alpha > 0:
                _scene_card(cv, lambda c: c.fill(blank), w / 2, cy, s, alpha=alpha)
    if swipe < 1:
        # a: full frame -> top card -> flung off the side, lifting and tilting as it goes.
        s = 1 + (card - 1) * gather
        throw = ease_out_quint(swipe) * 0.3 + swipe * 0.7
        cx = w / 2 + direction * throw * (w / 2 + w * card * 0.75)
        cy = h / 2 - math.sin(swipe * math.pi) * gap * 1.5
        _scene_card(cv, a, cx, cy, s, angle=direction * math.radians(tilt) * swipe)


def _demo():
    return demo.two_scenes(stacked_card_reveal, seconds=3.2, start=0.5, length=2.2)


CAPABILITY = Capability(
    id='stacked-card-reveal',
    name='Stacked card reveal',
    family='transitions',
    group='Slides and Pushes',
    aliases=('card swipe', 'card stack swipe', 'deck swipe', 'swipeable stack'),
    definition='The current scene becomes the top card of a small deck and is flicked off to the side, '
               'uncovering the next scene as the card beneath, which comes forward and fills the frame.',
    phrasings=('swipe the first shot away like a card to show the next one underneath',
               'make the scenes a stack of cards and flick the top one off',
               'swipe the current slide off the deck to reveal the one below'),
    related=('sticky-card-stack-on-scroll', 'card-deck-fan', 'flip', 'swipe-to-dismiss', 'title-card-reveal',
             'staggered-cascade-reveal'),
    api=('videobuilder.capabilities.transitions.stacked_card_reveal.stacked_card_reveal',),
    demo=_demo,
)
