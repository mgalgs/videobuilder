"""Multiples: on a move too fast to follow, the subject is drawn several times
at once along the stretch of path it just covered, so a single frame shows a
row of copies instead of one blurred shape."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def multiples(cv, draw, at, t, span, count=4, fade=0.0):
    """Draw `count` copies of a subject at times `t - span` .. `t`, oldest
    first so the current one sits on top.

    `at(time)` gives the subject's state at a time (a position, a tuple,
    anything) and `draw(cv, state, alpha)` draws it. Copies sampled while the
    subject holds still land on one another, so the effect appears only
    where it moves fast -- no speed threshold needed. `fade` (0 -> 1) makes the
    oldest copy that much fainter; 0 keeps every copy solid, the classic
    hand-drawn look."""
    count = max(1, int(count))
    for i in range(count):
        k = i / (count - 1) if count > 1 else 1.0  # 0 = oldest, 1 = now
        draw(cv, at(t - span * (1 - k)), 1 - fade * (1 - k))


R = 46
LEFT, RIGHT, Y = demo.W * 0.16, demo.W * 0.84, demo.H / 2


def _x(s):
    """The ball's x at `s` seconds: a hold, a zip right, a hold, a zip back."""
    go = vb.ease_in_out_quart(demo.phase(s * demo.FPS, 0.6, 0.9))
    back = vb.ease_in_out_quart(demo.phase(s * demo.FPS, 1.8, 2.1))
    return LEFT + (RIGHT - LEFT) * (go - back)


def _ball(cv, x, alpha):
    demo.dot(cv, x, Y, R, alpha=alpha)


def draw(n, cv):
    demo.floor(cv, Y + R + 24)
    multiples(cv, _ball, _x, n / demo.FPS, span=2.5 / demo.FPS, count=5)
    x = _x(n / demo.FPS)
    cv.mark('ball', x - R, Y - R, 2 * R, 2 * R)


TECHNIQUE = Technique(
    id='multiples',
    name='Multiples',
    family='principles',
    group='Principle sub-techniques',
    aliases=('multiple images', 'multi-image smear', 'drybrush multiples'),
    definition='During a very fast move, several copies of the subject appear in one frame, '
               'strung out along its path, so the eye reads speed instead of a jump.',
    phrasings=('show a few copies of it as it whips across',
               'cartoon-style speed where the thing appears several times along its path',
               'leave a row of duplicates behind it when it moves fast'),
    related=('double-exposure', 'accumulation-motion-blur', 'multiplane-camera', 'hyperlapse', 'oner',
             'frame-delay-echo'),
    api=('videobuilder.techniques.principles.multiples.multiples',),
    demo=lambda: demo.film(draw),
)
