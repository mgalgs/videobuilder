"""Interruptible Motion: a move that can be sent somewhere else mid-flight --
stopped, reversed, re-aimed -- and carries on from where it is and how fast it
is going, with no jump and no restart."""
import math

from .. import _demo as demo
from ..schema import Technique


def interruptible(t, moves, start=0.0, hz=0.7):
    """Value at `t` seconds of something that heads for each new target as it
    is given, without ever jumping. `moves` is `[(at, target), ...]` in time
    order: at `at` seconds the value is re-aimed at `target`, starting from
    its current position *and* velocity, on a critically damped spring of
    natural frequency `hz` (no overshoot; higher is snappier). `start` is
    where it rests before the first move.

    Closed form per segment, so any frame evaluates alone. Animate x and y
    (or any number) with one call each, sharing the same move times."""
    w = 2 * math.pi * hz
    x, v, t0 = float(start), 0.0, None
    goal = x
    for at, target in moves:
        if at > t:
            break
        if t0 is not None:
            x, v = _settle(at - t0, x - goal, v, w, goal)
        goal, t0 = float(target), at
    if t0 is None:
        return x
    return _settle(t - t0, x - goal, v, w, goal)[0]


def _settle(dt, d0, v0, w, goal):
    """Critically damped spring: offset `d0` from `goal` and velocity `v0`,
    `dt` seconds later -> (position, velocity)."""
    b = v0 + w * d0
    e = math.exp(-w * dt)
    return goal + (d0 + b * dt) * e, (b - w * (d0 + b * dt)) * e


CLICKS = ((0.35, 1), (0.85, 0), (1.45, 1))  # (seconds, toggle state): the 2nd and 3rd land mid-flight
LEFT, RIGHT, ROW = demo.W / 2 - 250, demo.W / 2 + 250, demo.H / 2 - 50


def draw(n, cv):
    t = n / demo.FPS
    for x in (LEFT, RIGHT):  # the two places it can be sent
        cv.outline(x - 130, ROW - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.45)
    moves = [(at, RIGHT if on else LEFT) for at, on in CLICKS]
    for k in range(6, 0, -1):  # a short fading trail shows the turn-around is smooth
        x = interruptible(t - k * 0.035, moves, start=LEFT)
        demo.card(cv, x, ROW, color=demo.ACCENT, alpha=0.08 * (7 - k) / 6)
    demo.card(cv, interruptible(t, moves, start=LEFT), ROW)
    _toggle(cv, t)


def _toggle(cv, t):
    """A switch under the card, clicked by a cursor at each of `CLICKS`."""
    on, last = 0, None
    for at, state in CLICKS:
        if t >= at:
            on, last = state, at
    knob = interruptible(t, [(at, s) for at, s in CLICKS], hz=2.2)
    cx, cy, w, h = demo.W / 2, demo.H - 110, 96, 50
    cv.rect(cx - w / 2, cy - h / 2, w, h, demo.LINE, radius=h / 2)
    cv.rect(cx - w / 2, cy - h / 2, w, h, demo.TEAL, radius=h / 2, alpha=knob)
    kx = cx - w / 2 + h / 2 + (w - h) * knob
    demo.dot(cv, kx, cy, h / 2 - 6, color=demo.INK)
    if last is not None and t - last < 0.35:  # a ring pulses out on each click
        p = (t - last) / 0.35
        cv.arc(kx, cy, h / 2 + 30 * p, 0, 2 * math.pi, demo.INK, width=3, alpha=0.6 * (1 - p))
    _cursor(cv, kx + 6, cy + 4, pressed=last is not None and t - last < 0.12)
    label = 'interrupt!' if last is not None and last > CLICKS[0][0] and t - last < 0.5 else ''
    if label:
        demo.word(cv, label, cx, cy + 58, size=24, color=demo.MUTED, weight=700)


def _cursor(cv, x, y, pressed=False):
    """A plain arrow pointer with its tip at (x, y)."""
    s = 0.9 if pressed else 1.0
    pts = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)]
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.new_path()
    for i, (px, py) in enumerate(pts):
        (ctx.move_to if i == 0 else ctx.line_to)(px, py)
    ctx.close_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.08, 0.08, 0.1)
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()


TECHNIQUE = Technique(
    id='interruptible-motion',
    name='Interruptible Motion',
    family='principles',
    group='Timing & spacing',
    aliases=('cancellable animation', 'interrupt and reverse', 'retargetable animation'),
    definition='A move that can be cut off or turned around partway through and simply heads for its new '
               'destination from wherever it is, keeping its momentum instead of snapping or starting over.',
    phrasings=('if I click again halfway, it should turn around smoothly instead of jumping',
               'let the animation change direction mid-move without restarting',
               'the panel can be reversed while it is still sliding'),
    related=('reverse-playback', 'delay', 'stop-motion-animation', 'reverse-motion-cut', 'seamless-loop',
             'frame-by-frame-hand-drawn-animation'),
    api=('videobuilder.techniques.principles.interruptible_motion.interruptible',),
    demo=lambda: demo.film(draw),
)
