"""Floating Reaction Emoji: a live-stream style stream of little faces and
hearts that pop out of one spot, wobble upward on their own drifting paths
and fade away near the top -- viewers reacting in real time."""
import math
import random

import videobuilder as vb
from videobuilder import paths

from .. import _demo as demo
from ..schema import Technique

YELLOW = '#f7c531'
FACE_INK = '#5a3a06'
HEART = '#8c88f5'


def smile(cv, r):
    """A smiling face of radius `r` centred on the origin."""
    cv.sector(0, 0, r, 0, 2 * math.pi, YELLOW)
    w = max(1.5, r * 0.14)
    cv.sector(-r * 0.34, -r * 0.22, r * 0.12, 0, 2 * math.pi, FACE_INK)
    cv.sector(r * 0.34, -r * 0.22, r * 0.12, 0, 2 * math.pi, FACE_INK)
    cv.arc(0, r * 0.02, r * 0.52, math.pi * 0.2, math.pi * 0.8, FACE_INK, width=w)


def wow(cv, r):
    """A surprised face of radius `r` centred on the origin."""
    cv.sector(0, 0, r, 0, 2 * math.pi, YELLOW)
    cv.sector(-r * 0.34, -r * 0.24, r * 0.12, 0, 2 * math.pi, FACE_INK)
    cv.sector(r * 0.34, -r * 0.24, r * 0.12, 0, 2 * math.pi, FACE_INK)
    cv.sector(0, r * 0.36, r * 0.2, 0, 2 * math.pi, FACE_INK)


def heart(cv, r, n=48):
    """A filled heart about `2 r` wide centred on the origin."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x * r / 16, -y * r / 16 + r * 0.1))
    paths.draw(cv, pts, HEART, fill=True)


EMOJI = (smile, heart, wow)


def reaction_stream(t, rate=7.0, life=2.2, rise=520, sway=40, spread=18, start=0.0, stop=None, seed=0):
    """The reactions alive `t` seconds in, as `(index, dx, dy, scale, alpha)`
    tuples relative to the source point (dy negative is up). One leaves every
    `1 / rate` seconds (with a little jitter) from `start` until `stop`, rises
    `rise` px over its `life`, weaving side to side by up to `sway` px with
    its own phase and drift, pops in with a small overshoot and fades over
    the last part of its climb. `index` is a stable per-reaction integer for
    picking an emoji. The same `seed` gives the same stream."""
    out = []
    first = math.ceil(max(0.0, t - life - start) * rate) if t > start else 0
    i = max(0, first - 1)
    while True:
        rnd = random.Random(f'{seed}:{i}')
        born = start + (i + rnd.uniform(-0.35, 0.35)) / rate
        if born > t or (stop is not None and born > stop):
            break
        age = (t - born) / (life * rnd.uniform(0.85, 1.15))
        if 0 <= age < 1:
            freq = rnd.uniform(0.8, 1.6)
            phase = rnd.uniform(0, 2 * math.pi)
            drift = rnd.uniform(-1, 1) * sway * 1.2
            dx = rnd.uniform(-spread, spread) + sway * math.sin(phase + 2 * math.pi * freq * age) * age \
                + drift * age
            dy = -rise * rnd.uniform(0.85, 1.1) * age
            pop = vb.ease_out_back(vb.clamp01(age / 0.12))
            scale = rnd.uniform(0.75, 1.15) * pop
            alpha = 1.0 - vb.clamp01((age - 0.55) / 0.45)
            out.append((i, dx, dy, scale, alpha))
        i += 1
    return out


def draw_reactions(cv, x, y, t, size=26, emoji=EMOJI, seed=0, **kw):
    """Draw the reaction stream rising from (x, y) at `t` seconds: each one an
    `emoji` drawer (`draw(cv, r)` about the origin) chosen per reaction, of
    radius about `size`. `kw` goes to `reaction_stream`."""
    for i, dx, dy, scale, alpha in reaction_stream(t, seed=seed, **kw):
        if alpha <= 0 or scale <= 0:
            continue
        pick = emoji[random.Random(f'{seed}:pick:{i}').randrange(len(emoji))]
        with cv.layer(opacity=alpha, dx=x + dx, dy=y + dy, scale=scale):
            pick(cv, size)


def draw(n, cv):
    t = n / demo.FPS
    x, y = demo.W / 2 + 60, demo.H - 70
    # the button the reactions come from
    cv.sector(x, y, 26, 0, 2 * math.pi, demo.LINE)
    with cv.layer(dx=x, dy=y, scale=0.55):
        heart(cv, 26)
    draw_reactions(cv, x, y - 22, t, size=17, rate=7, life=2.0, rise=330, sway=45, start=0.1, seed=3)
    cv.mark('source', x - 26, y - 26, 52, 52)


TECHNIQUE = Technique(
    id='floating-reaction-emoji',
    name='Floating reaction emoji',
    family='broadcast',
    group='Social media',
    aliases=('reaction float', 'emoji rise', 'live reactions', 'floating hearts'),
    definition='A steady stream of small faces and hearts pops out of one spot, weaves upward along '
               'loose wandering paths and fades away as it climbs.',
    phrasings=('hearts and smileys bubbling up the side like a live stream',
               'have little emoji float up from the like button and fade out',
               'show viewers reacting with emoji drifting up the screen'),
    related=('emoji-substitution', 'icon-hover-bounce', 'circle-pop', 'character-rise',
             'rolling-shutter-wobble', 'character-scale-in'),
    api=('videobuilder.techniques.broadcast.floating_reaction_emoji.draw_reactions',
         'videobuilder.techniques.broadcast.floating_reaction_emoji.reaction_stream',
         'videobuilder.techniques.broadcast.floating_reaction_emoji.smile',
         'videobuilder.techniques.broadcast.floating_reaction_emoji.heart',
         'videobuilder.techniques.broadcast.floating_reaction_emoji.wow'),
    demo=lambda: demo.film(draw),
)
