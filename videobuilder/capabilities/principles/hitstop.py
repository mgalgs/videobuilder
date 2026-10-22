"""Hitstop: at the instant something lands, the action stops dead for a few
frames, then carries on from exactly where it was -- the pause sells the
force of the hit."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def hitstop(n, at, hold=6):
    """Remap film frame `n` to the frame the action should show for a hit on
    frame `at` that freezes for `hold` frames: unchanged before the hit,
    stuck on `at` for `hold` frames, then running again `hold` frames behind.

    In a film, draw the scene at the remapped frame, e.g.
    `scene(cv, hitstop(n, at=HIT, hold=5))`; for several hits, nest the calls,
    latest hit outermost (each `at` in the remapped timeline of the hits
    before it)."""
    if n < at:
        return n
    return at if n < at + hold else n - hold


def frozen(n, at, hold=6):
    """Whether frame `n` is one of the `hold` frames frozen on a hit at `at`."""
    return at <= n < at + hold


HIT, HOLD = 34, 10       # the ball meets the post on frame 34 and the world stops for 10 frames (1/3 s)
GROUND = demo.H - 110
R = 30
POST_W, POST_H = 36, 180
POST_X = demo.W / 2 + 170   # the post's left edge at rest


def _scene(cv, s):
    """The action at scene frame `s`: the ball rushes at the post, hits it,
    the post rocks back and the ball bounces away."""
    contact = POST_X - R
    if s < HIT:
        x = 140 + (contact - 140) * (s / HIT) ** 2      # gathering speed into the hit
        kick = 0.0
    else:
        k = (s - HIT) / demo.FPS
        x = contact - 150 * vb.ease_out_expo(vb.clamp01(k / 0.9))
        kick = 40 * vb.ease_out_expo(vb.clamp01(k / 0.6))
    demo.floor(cv, GROUND)
    cv.rect(POST_X + kick, GROUND - POST_H, POST_W, POST_H, demo.TEAL, radius=8)
    demo.dot(cv, x, GROUND - R, R)
    cv.mark('ball', x - R, GROUND - 2 * R, 2 * R, 2 * R)


def draw(n, cv):
    _scene(cv, hitstop(n, HIT, HOLD))
    # real time keeps running across the top while the action is frozen
    y, x0, x1 = 60, 80, demo.W - 80
    cv.line(x0, y, x1, y, demo.LINE, width=2)
    demo.dot(cv, x0 + (x1 - x0) * n / (demo.FPS * demo.SECONDS - 1), y, 6, color=demo.INK)
    if frozen(n, HIT, HOLD):
        cx, cy = POST_X, GROUND - R
        for i in range(3):
            cv.arc(cx, cy, R + 14 + 14 * i, 0, 6.2832, demo.INK, width=3 - i, alpha=0.7 - 0.2 * i)
        demo.word(cv, 'HOLD', demo.W / 2, 110, size=22, color=demo.MUTED, font=demo.mono(22, 700))


TECHNIQUE = Technique(
    id='hitstop',
    name='Hitstop',
    family='principles',
    group='Time remapping',
    aliases=('hit stop', 'impact freeze', 'freeze on impact', 'hit pause'),
    definition='At the moment of a hit the motion stops dead for a handful of frames, '
               'then picks up again, so the blow feels heavier.',
    phrasings=('pause for a beat right when it hits',
               'freeze the action for a split second on impact',
               'make the hit feel heavy with a tiny stop on contact'),
    related=('impact-hit', 'impact', 'impact-shake', 'punch-in', 'recoil', 'smash-cut'),
    api=('videobuilder.techniques.principles.hitstop.hitstop',
         'videobuilder.techniques.principles.hitstop.frozen'),
    demo=lambda: demo.film(draw),
)
