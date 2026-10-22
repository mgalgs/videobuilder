"""Spotlight follow: the frame sits in darkness except for one soft pool of
light, and that pool tracks a moving subject, trailing it a touch like an
operator swinging a follow spot, lighting whatever it passes over."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def spotlight(cv, cx, cy, radius, darkness=0.88, softness=0.35, glow=0.08, color=(0, 0, 0)):
    """Darken everything already on `cv` except a round pool of light
    `radius` wide centred at (cx, cy). The pool's edge fades over the outer
    `softness` fraction of the radius; outside it the frame is covered by
    `color` at `darkness`. `glow` adds a faint white wash inside the pool so
    it reads as light, not just a hole in the dark."""
    ctx = cv.ctx
    inner = radius * (1 - vb.clamp01(softness))
    r, g, b = color
    shade = cairo.RadialGradient(cx, cy, inner, cx, cy, radius)
    shade.add_color_stop_rgba(0, r, g, b, 0)
    shade.add_color_stop_rgba(1, r, g, b, darkness)
    shade.set_extend(cairo.EXTEND_PAD)  # full darkness from the rim out to the frame's edges
    ctx.save()
    ctx.set_source(shade)
    ctx.paint()
    if glow > 0:
        wash = cairo.RadialGradient(cx, cy, 0, cx, cy, radius)
        wash.add_color_stop_rgba(0, 1, 1, 1, glow)
        wash.add_color_stop_rgba(1, 1, 1, 1, 0)
        ctx.set_source(wash)
        ctx.arc(cx, cy, radius, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()


def follow_point(subject, t, lag=0.18, samples=8):
    """Where a follow spot aims at time `t` when it chases `subject(t) -> (x, y)`:
    the mean of the subject's positions over the last `lag` seconds, so the
    light trails behind a fast move, eases through turns and settles onto
    the subject when it stops. `lag=0` aims straight at it."""
    if lag <= 0:
        return subject(t)
    pts = [subject(max(0.0, t - lag * i / (samples - 1))) for i in range(samples)]
    return sum(x for x, _ in pts) / samples, sum(y for _, y in pts) / samples


def spotlight_follow(cv, subject, t, radius=200, lag=0.18, **kw):
    """Light the subject at time `t` (seconds): darken `cv` everywhere but a
    pool `radius` wide aimed by `follow_point(subject, t, lag)`. Draw the
    scene and the subject first, then call this over them. `kw` goes to
    `spotlight`. Returns the pool's centre.

    In a film: `spotlight_follow(cv, lambda s: hero_at(s), f / fps, radius=240)`."""
    cx, cy = follow_point(subject, t, lag)
    spotlight(cv, cx, cy, radius, **kw)
    return cx, cy


# The demo: a dark stage lined with cards; a dot runs a wavy line across it,
# pausing mid-stage, and the pool of light trails it, picking out each card
# as it passes.
CARDS = [(demo.W / 2 + dx, demo.H / 2 + dy) for dx, dy in
         ((-330, -110), (-110, -120), (110, -110), (330, -120),
          (-330, 120), (-110, 110), (110, 120), (330, 110))]


def hero(s):
    """The dot's position at `s` seconds: a sweep across, a beat's pause in the middle, a sweep on."""
    sweep = lambda a, b: (1 - math.cos(math.pi * demo.phase(s * demo.FPS, a, b))) / 4  # noqa: E731
    p = sweep(0.2, 1.3) + sweep(1.6, 2.8)
    x = demo.W / 2 - 390 + 780 * p
    y = demo.H / 2 + 115 * math.sin(p * 2 * math.pi * 1.5)
    return x, y


def draw(n, cv):
    for i, (x, y) in enumerate(CARDS):
        demo.card(cv, x, y, w=170, h=105, color=demo.TEAL if i % 2 else demo.ACCENT)
    x, y = hero(n / demo.FPS)
    demo.dot(cv, x, y, 18, color=demo.INK)
    cv.mark('subject', x - 18, y - 18, 36, 36)
    cx, cy = spotlight_follow(cv, hero, n / demo.FPS, radius=150, lag=0.22)
    cv.mark('spotlight', cx - 150, cy - 150, 300, 300)


TECHNIQUE = Technique(
    id='spotlight-follow',
    name='Spotlight follow',
    family='camera',
    group='Lighting & surface',
    aliases=('follow spot', 'tracking spotlight', 'moving spotlight'),
    definition='The scene is kept dark except for a soft circle of light that chases a moving subject, '
               'trailing slightly behind it and revealing whatever it sweeps across.',
    phrasings=('keep everything dark and have a light circle follow the thing as it moves',
               'a stage spotlight that tracks the character across the screen',
               'let a moving pool of light chase the cursor and show what is underneath'),
    related=('spotlight-dim', 'spotlight-hover', 'coachmark-spotlight-cutout', 'tracking-shot',
             'player-movement-trail', 'path-follow-motion'),
    api=('videobuilder.techniques.camera.spotlight_follow.spotlight_follow',
         'videobuilder.techniques.camera.spotlight_follow.spotlight',
         'videobuilder.techniques.camera.spotlight_follow.follow_point'),
    demo=lambda: demo.film(draw),
)
