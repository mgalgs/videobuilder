"""Fireworks: a spark climbs from the ground, slows at the top of its climb and
bursts into a ring of glowing embers that fly out, droop under gravity, leave
fading trails and twinkle out."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GOLD = '#ffcf6b'


def _travel(t, drag):
    """How far a unit-velocity particle has gone after `t` s under linear `drag`."""
    return t if drag <= 0 else (1 - math.exp(-drag * t)) / drag


def _ember(vx, vy, t, drag, gravity):
    """An ember's offset from the burst point `t` s after it, launched at
    (vx, vy) px/s: drag slows it, gravity pulls it down toward terminal speed."""
    d = _travel(t, drag)
    fall = gravity * t * t / 2 if drag <= 0 else gravity / drag * (t - d)
    return vx * d, vy * d + fall


def firework(cv, x, y, t, color=GOLD, seed=0, launch=None, rise=0.7, count=70, speed=620, drag=2.0,
             gravity=240, life=1.7, trail=0.3, size=5.0, flash=True):
    """Draw one firework shell `t` seconds after it is lit, bursting at (x, y).

    With `launch` (a (x, y) point on the ground) a spark first climbs from
    there to the burst point over `rise` seconds, decelerating as it goes; the
    burst then happens at `t == rise`. Without it the shell bursts at `t == 0`.
    The burst throws `count` embers out in a rough ring at up to `speed` px/s;
    `drag` slows them, `gravity` (px/s^2) droops them, and over `life` seconds
    they shrink, fade and twinkle out, each drawing a tapering trail `trail`
    seconds long. `flash` adds a brief glow at the burst. The same `seed`
    gives the same shell, frame for frame. Drawn additively, so overlapping
    sparks brighten -- best on a dark background.

    In a film: `firework(cv, 900, 300, t - 1.2, color=..., launch=(880, 1080), seed=3)`
    for a shell lit at 1.2 s; call it every frame and it draws nothing before or after."""
    if t < 0:
        return
    rnd = random.Random(seed)
    cr, cg, cb, _ = vb.canvas.rgba(color)
    ctx = cv.ctx
    ctx.save()
    ctx.set_operator(cairo.OPERATOR_ADD)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    def spark(px, py, r, a, hot=True):
        ctx.set_source_rgba(cr, cg, cb, a * 0.35)
        ctx.arc(px, py, r * 2.6, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(*(1 - (1 - c) * (0.35 if hot else 1) for c in (cr, cg, cb)), a)
        ctx.arc(px, py, r, 0, 2 * math.pi)
        ctx.fill()

    if launch is not None:
        if t < rise:
            lx, ly = launch
            at = lambda s: 1 - (1 - s / rise) ** 2  # noqa: E731 -- ease out: it slows near the top
            for k in range(8):  # the climbing spark's trail, thinning behind it
                s0, s1 = max(0.0, t - (k + 1) * 0.03), max(0.0, t - k * 0.03)
                if s1 <= 0:
                    break
                p0, p1 = at(s0), at(s1)
                ctx.set_source_rgba(cr, cg, cb, 0.7 * (1 - k / 8))
                ctx.set_line_width(size * (1 - k / 10))
                ctx.move_to(lx + (x - lx) * p0, ly + (y - ly) * p0)
                ctx.line_to(lx + (x - lx) * p1, ly + (y - ly) * p1)
                ctx.stroke()
            p = at(t)
            spark(lx + (x - lx) * p + rnd.uniform(-1, 1), ly + (y - ly) * p, size * 0.9, 1.0)
            ctx.restore()
            return
        t -= rise

    if flash and t < 0.25:
        a = (1 - t / 0.25) ** 2
        glow = cairo.RadialGradient(x, y, 0, x, y, speed * 0.5)
        glow.add_color_stop_rgba(0, cr, cg, cb, 0.55 * a)
        glow.add_color_stop_rgba(1, cr, cg, cb, 0)
        ctx.set_source(glow)
        ctx.paint()

    for i in range(count):
        ang = 2 * math.pi * (i + rnd.uniform(-0.3, 0.3)) / count
        v = speed * rnd.uniform(0.75, 1.0)
        vx, vy = v * math.cos(ang), v * math.sin(ang)
        span = life * rnd.uniform(0.7, 1.0)
        twinkle = rnd.uniform(0, 2 * math.pi)
        if t >= span:
            continue
        age = t / span
        fade = (1 - age) ** 1.1
        if age > 0.5:  # late in life the embers flicker as they burn out
            fade *= 0.55 + 0.45 * math.sin(t * 38 + twinkle)
        steps = 6
        prev = _ember(vx, vy, max(0.0, t - trail), drag, gravity)
        for k in range(1, steps + 1):  # the trail: thin and dim at its tail, full at the head
            s = max(0.0, t - trail * (1 - k / steps))
            cur = _ember(vx, vy, s, drag, gravity)
            ctx.set_source_rgba(cr, cg, cb, fade * 0.8 * k / steps)
            ctx.set_line_width(size * (1 - 0.6 * age) * (0.3 + 0.7 * k / steps))
            ctx.move_to(x + prev[0], y + prev[1])
            ctx.line_to(x + cur[0], y + cur[1])
            ctx.stroke()
            prev = cur
        spark(x + prev[0], y + prev[1], size * 0.6 * (1 - 0.5 * age), fade, hot=age < 0.4)
    ctx.restore()


SHELLS = (  # (lit at s, burst x, burst y, launch x, colour, seed)
    (0.0, demo.W * 0.3, demo.H * 0.4, demo.W * 0.36, demo.ACCENT, 1),
    (0.4, demo.W * 0.7, demo.H * 0.36, demo.W * 0.63, demo.TEAL, 2),
    (0.85, demo.W * 0.5, demo.H * 0.44, demo.W * 0.5, GOLD, 3),
)


def draw(n, cv):
    t = n / demo.FPS
    ground = demo.H - 60
    for lit, x, y, lx, color, seed in SHELLS:
        firework(cv, x, y, t - lit, color=color, seed=seed, launch=(lx, ground))
        if t - lit >= 0.7:
            cv.mark('burst', x - 260, y - 260, 520, 520)
    cv.rect(0, ground, demo.W, demo.H - ground, '#0c0d10')


TECHNIQUE = Technique(
    id='fireworks',
    name='Fireworks',
    family='particles',
    group='Emitters',
    aliases=('firework burst', 'pyrotechnics', 'firework particles'),
    definition='Bright sparks shoot up into a dark sky and pop into rings of glowing embers '
               'that spread out, sag under gravity and flicker away.',
    phrasings=('set off some fireworks over the title',
               'rockets that go up and explode into colourful sparks',
               'a celebration with fireworks bursting in the night sky'),
    related=('shape-burst', 'doom-style-fire', 'confetti-burst', 'lens-flare', 'bloom', 'diffraction-spikes'),
    api=('videobuilder.techniques.particles.fireworks.firework',),
    demo=lambda: demo.film(draw),
)
