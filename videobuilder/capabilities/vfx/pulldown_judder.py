"""Pulldown Judder: footage shot at one frame rate played out at another by
repeating some of its frames, so a steady pan advances in an uneven,
hitching rhythm -- long hold, short hold, long hold -- instead of gliding."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def pulldown_frame(n, cadence=(3, 2)):
    """The source frame output frame `n` shows when each source frame is held
    for the next count in `cadence`, cycling: (3, 2) holds frame 0 for three
    output frames, frame 1 for two, frame 2 for three, and so on. (3, 2) is
    the classic pulldown pattern; (2, 1, 1, 1) is 24 fps carried in 30 fps
    whole frames."""
    total = sum(cadence)
    cycles, r = divmod(int(n), total)
    i = cycles * len(cadence)
    for hold in cadence:
        if r < hold:
            break
        r -= hold
        i += 1
    return i


def pulldown_time(n, fps, cadence=(3, 2)):
    """The time, in seconds, to draw output frame `n` at so the motion judders
    with `cadence`: the source runs at `fps * len(cadence) / sum(cadence)` and
    each of its frames is held per `pulldown_frame`. Draw moving things at this
    time instead of `n / fps`; at 30 fps the default (3, 2) is a 12 fps source,
    an exaggerated, easy-to-see judder."""
    source_fps = fps * len(cadence) / sum(cadence)
    return pulldown_frame(n, cadence) / source_fps


SPEED = 220            # px per second of the pan
GAP = 110              # px between posts
LANE_H = 130
LANES = ((150, 'SMOOTH', None), (330, '3:2 PULLDOWN', (3, 2)))
X0, X1 = 230, demo.W - 40


def _lane(cv, y, t, color):
    """A band panning left at a constant SPEED: posts, a ground line and a card."""
    with cv.clip(X0, y - LANE_H / 2, X1 - X0, LANE_H, radius=12):
        cv.rect(X0, y - LANE_H / 2, X1 - X0, LANE_H, '#1d2230')
        cv.line(X0, y + 42, X1, y + 42, demo.LINE, width=2)
        shift = (t * SPEED) % GAP
        x = X0 - shift
        while x < X1 + GAP:
            cv.rect(x, y - 40, 10, 82, demo.MUTED, radius=3)
            x += GAP
        cx = X1 - 70 - t * SPEED
        demo.card(cv, cx, y - 2, w=110, h=66, color=color)


def _ribbon(cv, n):
    """The cadence spelled out: the source frame each recent output frame shows."""
    f = demo.mono(20, 700)
    cell, y = 46, 470
    first = max(0, n - 12)
    for k, m in enumerate(range(first, n + 1)):
        x = X0 + k * (cell + 6)
        src = pulldown_frame(m)
        color = demo.ACCENT if src % 2 == 0 else demo.TEAL
        alpha = 1.0 if m == n else 0.45
        cv.rect(x, y - cell / 2, cell, cell, color, radius=8, alpha=alpha)
        letter = chr(ord('A') + src % 26)
        w, h = vb.text.block_size([letter], f)
        vb.text.draw(cv, [letter], f, x + (cell - w) / 2, y - h / 2, demo.BG)
    vb.text.draw(cv, ['HELD'], demo.font(18, 800), 50, y - 11, demo.MUTED)


def draw(n, cv):
    label = demo.font(20, 800)
    for y, name, cadence in LANES:
        t = n / demo.FPS if cadence is None else pulldown_time(n, demo.FPS, cadence)
        vb.text.draw(cv, [name], label, 50, y - 12, demo.INK if cadence else demo.MUTED)
        _lane(cv, y, t, demo.ACCENT if cadence else demo.TEAL)
    _ribbon(cv, n)


CAPABILITY = Capability(
    id='pulldown-judder',
    name='Pulldown judder',
    family='vfx',
    group='Time displacement',
    aliases=('3:2 pulldown', 'telecine judder', 'cadence judder', 'pulldown stutter'),
    definition='A steady move hitches along in a repeating long-short rhythm because some of its frames '
               'are shown twice to fit a different frame rate.',
    phrasings=('make the pan stutter like a movie playing on an old TV',
               'give it that uneven film-to-video judder',
               'hold every other frame a beat longer so the motion hiccups'),
    related=('video-feedback-loop', 'on-ones-on-twos-on-threes', 'push-in', 'whip-pan',
             'interruptible-motion', 'tilt-shift-miniature'),
    api=('videobuilder.capabilities.vfx.pulldown_judder.pulldown_time',
         'videobuilder.capabilities.vfx.pulldown_judder.pulldown_frame'),
    demo=lambda: demo.film(draw),
)
