"""Insert Cutaway: the main shot hard-cuts away to a short second shot -- a
close detail of the action, or something related to it -- then hard-cuts
straight back to the main shot, which has carried on in the meantime."""
from .. import _demo as demo
from ..schema import Technique


def insert_cutaway(cv, a, b, p, start=0.3, end=0.7):
    """Draw the cutaway at progress `p` (0 -> 1): `a(cv)` (the main shot),
    a hard cut to `b(cv)` (the insert) for `start <= p < end`, then a hard
    cut back to `a(cv)`. No dissolve either way: the jump is the point.

    In a film, keep the main shot's clock running through the insert so the
    action has moved on when it returns, e.g.
    `insert_cutaway(cv, lambda c: main(c, t), close_up(lambda c: main(c, t), 900, 400), t / length)`."""
    (b if start <= p < end else a)(cv)


def close_up(scene, cx, cy, zoom=3.0):
    """A scene drawing `scene` magnified `zoom` times about its point
    (cx, cy), with that point in the middle of the frame: the insert shot of
    a detail in the main shot, without drawing it twice."""
    def draw(cv):
        dx, dy = cv.width / 2 - cx * zoom, cv.height / 2 - cy * zoom
        with cv.layer(dx=dx, dy=dy, scale=zoom):
            scene(cv)
    return draw


# The demo: a wide shot of a card whose loading bar fills steadily; partway
# through it cuts in to a close-up of the bar's leading edge and back out.
CARD_X, CARD_Y, CARD_W, CARD_H = demo.W / 2, demo.H / 2, 560, 320
BAR_X, BAR_Y, BAR_W, BAR_H = CARD_X - 220, CARD_Y + 70, 440, 26


def _main(cv, t):
    cv.fill(demo.BG)
    demo.card(cv, CARD_X, CARD_Y, w=CARD_W, h=CARD_H, color=demo.TEAL)
    fill = BAR_W * min(1.0, 0.1 + 0.3 * t)
    cv.rect(BAR_X, BAR_Y, BAR_W, BAR_H, demo.BG, radius=BAR_H / 2, alpha=0.55)
    cv.rect(BAR_X, BAR_Y, fill, BAR_H, demo.ACCENT, radius=BAR_H / 2)
    demo.dot(cv, BAR_X + fill, BAR_Y + BAR_H / 2, r=20, color=demo.INK)


def _tag(cv, text, ink=demo.INK):
    demo.word(cv, text, 140, 56, size=34, color=ink)


def draw(n, cv):
    t = n / demo.FPS
    main = lambda c: (_main(c, t), _tag(c, 'Main'))  # noqa: E731
    lead = BAR_X + BAR_W * min(1.0, 0.1 + 0.3 * t)
    insert = lambda c: (close_up(lambda c2: _main(c2, t), lead, BAR_Y + BAR_H / 2, zoom=4.0)(c),  # noqa: E731
                        _tag(c, 'Insert', ink=demo.BG))
    insert_cutaway(cv, main, insert, demo.phase(n, 0.2, 2.8), start=0.3, end=0.62)


TECHNIQUE = Technique(
    id='insert-cutaway',
    name='Insert cutaway',
    family='transitions',
    group='Cuts',
    aliases=('cutaway', 'insert shot', 'cut-in'),
    definition='The main shot cuts suddenly to a brief second shot, a close look at a detail or a related '
               'subject, then cuts right back to the main shot, which has kept going.',
    phrasings=('cut in to a close-up of that detail for a second, then back to the wide',
               'jump away to a quick shot of the thing and then return',
               'show a short close-up insert in the middle of the shot'),
    related=('strike-through-draw', 'zoom-through', 'strobe-cut', 'cut-out-paper-animation',
             'dolly-in-and-out', 'zoom-out-reveal'),
    api=('videobuilder.techniques.transitions.insert_cutaway.insert_cutaway',
         'videobuilder.techniques.transitions.insert_cutaway.close_up'),
    demo=lambda: demo.film(draw),
)
