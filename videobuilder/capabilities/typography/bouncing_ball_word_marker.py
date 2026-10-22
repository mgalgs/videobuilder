"""Bouncing Ball Word Marker: a small ball hops along a line of lyrics,
touching down above each word on its beat, and the words it has reached
light up -- the sing-along ball."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def ball_position(xs, times, t, hop=0.9, lift=120):
    """Where the ball is at time `t` (seconds) as `(x, rise, i)`: `x` its
    centre, `rise` its height above the resting line in pixels (0 on a
    landing), and `i` the index of the last word it has landed on (-1 before
    the first). It lands on `xs[k]` at `times[k]` and between landings flies
    a parabola that starts after `1 - hop` of the gap, so it sits a moment on
    each word; the arc is `lift` tall, less for short hops. Before the first
    landing it drops in from above the first word."""
    if t < times[0]:
        p = vb.clamp01(1 - (times[0] - t) / max(1e-6, (times[1] - times[0]) if len(times) > 1 else 0.5))
        return xs[0], lift * (1 - p * p), -1
    for k in range(len(times) - 1):
        a, b = times[k], times[k + 1]
        if t < b:
            p = vb.clamp01((t - (b - (b - a) * hop)) / ((b - a) * hop))
            height = min(lift, 0.55 * abs(xs[k + 1] - xs[k]) + 30)
            return xs[k] + (xs[k + 1] - xs[k]) * p, 4 * height * p * (1 - p), k
    return xs[-1], 0.0, len(times) - 1


def draw_bouncing_ball_line(cv, words, font, x, y, times, t, color, sung, ball=None, r=14, gap=16,
                            lift=120, hop=0.9):
    """Draw the lyric line `words` from its top-left (x, y) with a ball
    marking the word sung at time `t`: word `k` is due at `times[k]`, words
    already reached draw in `sung`, the rest in `color`, and the ball (in
    `ball`, default `sung`) of radius `r` rests `gap` above the line, squashing
    a little as it lands. Returns the Box of the line."""
    space = vb.text.measure(' ', font)
    lh = vb.text.line_height(font)
    lefts, xs, left = [], [], x
    for w in words:
        adv = vb.text.measure(w, font)
        lefts.append(left)
        xs.append(left + adv / 2)
        left += adv + space
    bx, rise, i = ball_position(xs, times, t, hop=hop, lift=lift)
    for k, w in enumerate(words):
        vb.text.draw(cv, [w], font, lefts[k], y, sung if k <= i else color)
    since = t - times[i] if i >= 0 else 1.0
    squash = 0.3 * math.exp(-since * 14) if rise < 1 else 0.0  # a quick squash on each touch-down
    rest = y + lh * 0.12 - gap - r
    cv.ctx.save()
    cv.ctx.translate(bx, rest - rise + r * squash)
    cv.ctx.scale(1 + squash, 1 - squash)
    demo.dot(cv, 0, 0, r, color=ball or sung)
    cv.ctx.restore()
    cv.mark('ball', bx - r, rest - rise - r, 2 * r, 2 * r)
    w = left - space - x
    return vb.Box(x, y, w, lh)


def draw(n, cv):
    f = demo.font(60, 800)
    words = ['SING', 'IT', 'ALL', 'TOGETHER']
    w, h = vb.text.block_size([' '.join(words)], f)
    x, y = (demo.W - w) / 2, demo.H / 2 - h / 2 + 30
    times = [0.6, 1.1, 1.6, 2.2]
    box = draw_bouncing_ball_line(cv, words, f, x, y, times, n / demo.FPS, demo.MUTED, demo.INK,
                                  ball=demo.ACCENT, r=12, gap=12, lift=90)
    cv.mark('text', *box)


CAPABILITY = Capability(
    id='bouncing-ball-word-marker',
    name='Bouncing ball word marker',
    family='typography',
    group='Lyrics and captions',
    aliases=('karaoke bouncing ball', 'word hop marker', 'follow the bouncing ball'),
    definition='A little ball jumps in arcs along a line of lyrics, landing on top of each word '
               'right when it should be sung.',
    phrasings=('a ball that bounces over the words like a sing-along',
               'karaoke lyrics with a dot hopping from word to word',
               'show which word is being sung with a bouncing ball'),
    related=('map-pin-drop', 'ball-bounce', 'highlighter-swipe', 'bouncing-dots', 'icon-hover-bounce',
             'impact-shake'),
    api=('videobuilder.capabilities.typography.bouncing_ball_word_marker.draw_bouncing_ball_line',
         'videobuilder.capabilities.typography.bouncing_ball_word_marker.ball_position'),
    demo=lambda: demo.film(draw),
)
