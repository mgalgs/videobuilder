"""Cut on action: one movement runs through a hard cut. The subject is
already moving when shot A ends and is still moving, at the same speed and
in the same direction, when shot B begins, so the eye follows the motion and
does not notice the change of shot."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def cut_on_action(cv, a, b, p, action, at=0.5, zoom=1.0, focus=None):
    """Draw the cut at progress `p` (0 -> 1), which is the progress of the
    action itself: `a(cv)` until `at`, then `b(cv)`, with `action(cv, p)`
    drawing the moving subject over whichever shot is up. Cut while the
    subject is moving fastest (`at` mid-movement), not before it starts.

    `zoom` > 1 makes shot B a closer framing of the same action, scaled
    about `focus` (x, y), the subject's position at the cut (default: the
    frame centre), so the subject keeps its place on screen across the cut.

    In a film, run `p` across the whole movement, e.g.
    `cut_on_action(cv, wide, close, swing, lambda c, q: arm(c, q), zoom=1.8, focus=(900, 500))`."""
    if p < at:
        a(cv)
        action(cv, p)
        return
    b(cv)
    fx, fy = focus if focus is not None else (cv.width / 2, cv.height / 2)
    with cv.layer(dx=fx * (1 - zoom), dy=fy * (1 - zoom), scale=zoom):
        action(cv, p)


# ---- demo: a card flung across the frame; the cut to a close shot lands mid-flight ----

START, END = 0.5, 2.3      # the throw, in seconds
CUT = 0.5                  # cut at the middle of the throw, where it is fastest
ZOOM = 1.3


def _path(q):
    """Where the card is at throw progress `q`: left to right on a low arc."""
    e = vb.ease_in_out_quart(q)
    x = demo.W * (0.3 + 0.4 * e)
    y = demo.H * 0.5 - math.sin(math.pi * e) * demo.H * 0.16
    return x, y


def _thrown_card(cv, q):
    for k in (3, 2, 1):  # a faint trail, so a still frame still reads as motion
        x, y = _path(max(0.0, q - 0.035 * k))
        demo.card(cv, x, y, alpha=0.12 * (4 - k))
    demo.card(cv, *_path(q))


def _shot(fill, floor, label, ink):
    def draw(cv):
        cv.fill(fill)
        demo.floor(cv, demo.H * 0.84, floor)
        vb.text.draw(cv, [label], demo.font(28, 800), 40, 32, ink)
    return draw


_wide = _shot(demo.BG, demo.LINE, 'Shot A  wide', demo.INK)
_close = _shot('#e9e6df', '#bdb8ad', 'Shot B  close', demo.BG)


def _demo():
    def draw(n, cv):
        cut_on_action(cv, _wide, _close, demo.phase(n, START, END), _thrown_card,
                      at=CUT, zoom=ZOOM, focus=_path(CUT))
    return demo.film(draw)


TECHNIQUE = Technique(
    id='cut-on-action',
    name='Cut on action',
    family='transitions',
    group='Cuts',
    aliases=('action cut', 'continuity cut', 'matching on action'),
    definition='A hard cut placed in the middle of a movement, so the subject is still moving '
               'the same way in the next shot and the motion carries the eye across the change.',
    phrasings=('cut to the close-up while it is still moving',
               'make the edit mid-motion so you barely notice the cut',
               'switch shots halfway through the throw and keep the movement going'),
    related=('push', 'strobe-cut', 'interruptible-motion', 'hold', 'cut-to-the-beat', 'overlapping-action'),
    api=('videobuilder.techniques.transitions.cut_on_action.cut_on_action',),
    demo=_demo,
)
