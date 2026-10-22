"""Wobble: something gets knocked, rocks and jiggles about where it stands,
and the jiggle dies away until it is still again. `wobble` is the decaying
swing; `wobbling` bends a canvas around a base point by it, so anything drawn
inside rocks and goes jelly-like."""
import math
from contextlib import contextmanager

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def wobble(t, hz=3.0, decay=3.0):
    """The swing `t` seconds after a knock: a sine of `hz` cycles a second
    under an exponential fade of rate `decay`, in [-1, 1]. 0 before the knock
    and at it, so the swing starts from rest."""
    if t <= 0:
        return 0.0
    return math.sin(2 * math.pi * hz * t) * math.exp(-decay * t)


@contextmanager
def wobbling(cv, ax, ay, k, tilt=0.05, shear=0.45, squash=0.08):
    """Draw inside this to wobble by `k` (from `wobble`) about the base point
    (ax, ay), the spot that stays planted: the body rocks by up to `tilt`
    radians, its top lags behind by `shear`, and it bulges sideways by
    `squash` as it sways. At `k` = 0 nothing changes."""
    c = cv.ctx
    c.save()
    c.translate(ax, ay)
    c.rotate(k * tilt)
    c.transform(cairo.Matrix(1, 0, -k * shear, 1, 0, 0))  # the top trails the rocking base
    c.scale(1 + squash * abs(k), 1 - squash * abs(k))
    c.translate(-ax, -ay)
    try:
        yield cv
    finally:
        c.restore()


KNOCK = 0.75  # when the dot reaches the card, in seconds


def draw(n, cv):
    ground, cx = demo.H / 2 + 110, demo.W / 2 + 60
    w, h = 210, 160
    demo.floor(cv, ground)
    cv.outline(cx - w / 2, ground - h, w, h, demo.MUTED, width=2, radius=18, alpha=0.35)  # the rest pose
    # A dot rolls in, taps the card's side and rebounds a little.
    r = 22
    hit = cx - w / 2 - r
    go, back = demo.phase(n, 0.15, KNOCK), demo.phase(n, KNOCK, KNOCK + 0.6)
    x = hit - 300 * (1 - go * go) - 60 * vb.ease_out_expo(back)
    demo.dot(cv, x, ground - r, r, color=demo.TEAL)
    k = wobble(n / demo.FPS - KNOCK, hz=2.6, decay=2.2)
    with wobbling(cv, cx, ground, k):
        demo.card(cv, cx, ground - h / 2, w=w, h=h)


TECHNIQUE = Technique(
    id='wobble',
    name='Wobble',
    family='principles',
    group='Physics',
    aliases=('jelly wobble', 'wiggle', 'jiggle', 'sine wave warp', 'wave warp'),
    definition='After a knock, a shape sways and jiggles back and forth about its base, each swing '
               'smaller than the last, until it settles where it started.',
    phrasings=('give it a jelly jiggle when it gets hit',
               'make it rock back and forth and settle down',
               'have the box wobble after the bump'),
    related=('tape-wobble', 'wiggle-path', 'noise-vertex-wobble', 'wave-deformer', 'sine-wave-distortion',
             'wave-stagger'),
    api=('videobuilder.techniques.principles.wobble.wobble',
         'videobuilder.techniques.principles.wobble.wobbling'),
    demo=lambda: demo.film(draw),
)
