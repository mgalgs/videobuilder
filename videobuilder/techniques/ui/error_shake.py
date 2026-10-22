"""Error Shake: a rejected field wobbles quickly left and right, each swing
smaller than the last, the way a login box says "no"."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

ERROR = '#f2b134'


def error_shake(p, amount=18, swings=4):
    """Horizontal offset in px at progress `p` (0 -> 1) of an error shake:
    `swings` full left-right cycles, the first reaching about `amount` px,
    shrinking smoothly so the offset is 0 at both ends. Add it to the x of
    the field (or pass it as `cv.layer(dx=...)`)."""
    p = vb.clamp01(p)
    return amount * (1 - p) ** 2 * math.sin(2 * math.pi * swings * p)


def draw(n, cv):
    t = n / demo.FPS
    press = 0.75                          # the button is clicked; the field rejects the entry
    dx = error_shake(demo.phase(n, press, press + 0.55), amount=28)
    wrong = t >= press
    pw, ph = 420, 250
    px, py = (demo.W - pw) / 2, (demo.H - ph) / 2

    cv.shadow(px, py, pw, ph, radius=18, dy=10, blur=28, color=(0, 0, 0, 0.45))
    cv.rect(px, py, pw, ph, '#1d1f26', radius=18)
    cv.outline(px, py, pw, ph, demo.LINE, width=2, radius=18)
    vb.text.draw(cv, ['Access code'], demo.font(15, 500), px + 28, py + 24, demo.MUTED)

    fx, fy, fw, fh = px + 28, py + 56, pw - 56, 56
    with cv.layer(dx=dx):
        cv.rect(fx, fy, fw, fh, '#121318', radius=10)
        cv.outline(fx, fy, fw, fh, ERROR if wrong else demo.LINE, width=2.5 if wrong else 2, radius=10)
        vb.text.draw(cv, ['MOTION'], demo.font(24, 800), fx + 18, fy + 14, demo.INK)
        if wrong:
            demo.dot(cv, fx + fw - 26, fy + fh / 2, 11, color=ERROR)
            demo.word(cv, '!', fx + fw - 26, fy + fh / 2, size=16, color='#121318', weight=900)
            vb.text.draw(cv, ['Code not recognized'], demo.font(14, 600), fx, fy + fh + 10, ERROR)
        cv.mark('field', fx, fy, fw, fh)

    bx, by, bw, bh = fx, py + ph - 72, fw, 46
    down = 0 < t - press + 0.12 < 0.18     # a brief press-in just before the shake
    s = 0.97 if down else 1.0
    cv.rect(bx + bw * (1 - s) / 2, by + bh * (1 - s) / 2, bw * s, bh * s, '#7c83ff', radius=10)
    demo.word(cv, 'Continue', bx + bw / 2, by + bh / 2, size=17, color='#121318', weight=700)


TECHNIQUE = Technique(
    id='error-shake',
    name='Error shake',
    family='ui',
    group='Feedback & status',
    aliases=('validation shake', 'input nudge', 'shake to reject', 'wrong password shake'),
    definition='An input that was just rejected jerks quickly from side to side, each swing smaller '
               'than the one before, then settles back in place.',
    phrasings=('shake the text box like a wrong password',
               'make the field wiggle no when the entry is invalid',
               'the login form shakes its head at a bad code'),
    related=('impact-shake', 'shake', 'handheld-shake', 'bouncing-dots', 'jiggle', 'noise-dissolve'),
    api=('videobuilder.techniques.ui.error_shake.error_shake',),
    demo=lambda: demo.film(draw),
)
