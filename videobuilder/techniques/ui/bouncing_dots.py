"""Bouncing dots: a row of dots that hop one after another, over and over, the
loader that says "working on it" or "someone is typing"."""
import math

from .. import _demo as demo
from ..schema import Technique


def bouncing_dots(cv, cx, cy, t, count=3, r=14, gap=None, height=None, period=0.9, stagger=0.15,
                  color=demo.ACCENT, alpha=1.0, dim=0.45):
    """Draw `count` dots in a row centred at (cx, cy) at time `t` seconds.

    Each dot hops up by `height` (default `1.6 * r`) and back on a smooth arc,
    once every `period` seconds, starting `stagger` seconds after the dot to
    its left, then rests until its next hop. A resting dot is drawn at `dim`
    times `alpha`, a dot at the top of its hop at full `alpha`. `gap` is the
    centre-to-centre spacing (default `3 * r`). Loops forever: pass any `t`."""
    gap = 3 * r if gap is None else gap
    height = 1.6 * r if height is None else height
    hop = min(period, max(stagger * count, period * 0.5))  # how long one dot is in the air
    for i in range(count):
        u = ((t - i * stagger) % period) / hop
        lift = math.sin(math.pi * u) if u < 1 else 0.0
        x = cx + (i - (count - 1) / 2) * gap
        demo.dot(cv, x, cy - height * lift, r, color=color, alpha=alpha * (dim + (1 - dim) * lift))


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    w, h = 380, 180
    cv.shadow(cx - w / 2, cy - h / 2, w, h, radius=h / 2, dy=10, blur=28, color=(0, 0, 0, 0.45))
    cv.rect(cx - w / 2, cy - h / 2, w, h, demo.LINE, radius=h / 2)  # a chat bubble, so it reads as "typing"
    bouncing_dots(cv, cx, cy + 12, n / demo.FPS, r=26, color=demo.INK)
    cv.mark('dots', cx - w / 2, cy - h / 2, w, h)


TECHNIQUE = Technique(
    id='bouncing-dots',
    name='Bouncing dots',
    family='ui',
    group='Loaders',
    aliases=('three-dot loader', 'ellipsis loader', 'typing indicator', 'three dots', 'composing bubble'),
    definition='A short row of dots that hop up and drop back one after another in a repeating wave, '
               'signalling that something is busy or a message is on its way.',
    phrasings=('the three little dots that show someone is typing',
               'a loader where the dots jump up in turn',
               'dots bouncing in a wave while it loads'),
    related=('dot-grid-displacement', 'cursor-follower-dot-and-ring', 'dot-density-map', 'circle-pop',
             'comment-pop-up-stack', 'icon-hover-bounce'),
    api=('videobuilder.techniques.ui.bouncing_dots.bouncing_dots',),
    demo=lambda: demo.film(draw),
)
