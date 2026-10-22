"""Staging: clear the frame for the one thing that matters. Everything else
steps back -- fades, greys out, gets out of the way -- and a pool of light
falls on the subject, so the eye lands on it before it acts."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique


def staging(cv, props, hero, p, cx, cy, radius=320, recede=0.6, darken=0.55):
    """Draw a staged shot at progress `p` (0 = unstaged, 1 = fully staged):
    `props(cv)` (everything but the subject) composited at `1 - recede * p`
    opacity, then the frame darkened by up to `darken` away from a pool of
    light `radius` wide around (cx, cy), then `hero(cv)` on top, untouched.

    In a film, ramp `p` up just before the subject's key action, e.g.
    `staging(cv, draw_rest, draw_subject, vb.ease_in_out_quart(t), *subject_centre)`."""
    p = vb.clamp01(p)
    with cv.layer(opacity=1 - recede * p):
        props(cv)
    if p > 0 and darken > 0:
        ctx = cv.ctx
        far = math.hypot(cv.width, cv.height) / 2
        g = cairo.RadialGradient(cx, cy, radius * 0.55, cx, cy, max(radius, far))
        g.add_color_stop_rgba(0, 0, 0, 0, 0)
        g.add_color_stop_rgba(0.35, 0, 0, 0, darken * p * 0.8)
        g.add_color_stop_rgba(1, 0, 0, 0, darken * p)
        ctx.save()
        ctx.set_source(g)
        ctx.paint()
        ctx.restore()
    hero(cv)


# The demo: a busy frame of same-coloured shapes all shouting at once; then it
# is staged -- the rest shrink, grey out and drift aside, light pools on one dot
# -- and that dot, now unmistakable, hops.
HX, HY = demo.W / 2, demo.H / 2 + 40
CLUTTER = (  # (kind, x, y, size) scattered around and over the hero
    ('dot', -250, -150, 70), ('card', 150, -170, 1.0), ('dot', 300, 40, 56), ('card', -330, 110, 0.85),
    ('dot', -90, 150, 46), ('dot', 120, 120, 62), ('card', -40, -60, 0.7), ('dot', 420, -190, 40),
    ('dot', -470, -40, 52), ('card', 380, 200, 0.75), ('dot', 40, -230, 38), ('dot', -200, -10, 34),
)


def draw(n, cv):
    s = vb.ease_in_out_quart(demo.phase(n, 0.7, 1.6))

    def props(cv):
        for kind, x, y, size in CLUTTER:
            push = 1 + 0.45 * s  # step out of the subject's way
            px, py = HX + x * push, HY + y * push
            color = kit.mix(demo.ACCENT, demo.MUTED, s)
            k = 1 - 0.3 * s
            if kind == 'dot':
                demo.dot(cv, px, py, size * k, color=color)
            else:
                demo.card(cv, px, py, color=color, scale=size * k)

    def hero(cv):
        hop = math.sin(math.pi * demo.phase(n, 1.9, 2.6)) * 120
        r = 50 * (1 + 0.15 * s)
        demo.dot(cv, HX, HY - hop, r, color=demo.ACCENT)
        cv.mark('hero', HX - r, HY - hop - r, 2 * r, 2 * r)

    staging(cv, props, hero, s, HX, HY, radius=300)


TECHNIQUE = Technique(
    id='staging',
    name='Staging',
    family='principles',
    group='Disney principles',
    aliases=('composition for motion', 'readability of action'),
    definition='The frame is arranged so one subject clearly owns it, with everything else pushed back '
               'in brightness, size and placement, so the eye goes straight to the action that matters.',
    phrasings=('make it obvious where to look',
               'clear the clutter so the main thing stands out',
               'put a spotlight on the one element doing the action'),
    related=('staged-onboarding-walkthrough', 'page-load-sequence', 'kinetic-poster-layout',
             'slide-over-cover', 'shadow-play', 'cut-on-action'),
    api=('videobuilder.techniques.principles.staging.staging',),
    demo=lambda: demo.film(draw),
)
