"""Gauge Needle Sweep: a needle swings round a dial of ticks and coloured
ranges to a reading, carried a little past it by its own momentum before it
settles, while the number under the hub counts with it."""
import math

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability

START = math.radians(135)    # bottom left; canvas angles run clockwise
SWEEP = math.radians(270)
BANDS = ((0.0, 0.3, '#3a3f4a'), (0.3, 0.75, demo.TEAL), (0.75, 1.0, demo.ACCENT))


def needle_value(t, frm, to, ratio=0.45, hz=0.9):
    """The needle's reading `t` seconds after it starts moving from `frm`
    towards `to`: a damped spring, so a `ratio` below 1 swings past `to` and
    settles back (lower overshoots more); 1 or above arrives without
    overshooting. `hz` sets how quick the swing is."""
    return frm + (to - frm) * vb.spring(t, **vb.damped(ratio, hz=hz))


def draw_gauge(cv, cx, cy, r, value, lo=0, hi=100, bands=BANDS, ticks=10, minor=5,
               needle=demo.INK, ink=demo.INK, muted=demo.MUTED, font=None, number=True):
    """A dial centred at (cx, cy), outer radius `r`, reading `value` on a
    scale `lo`..`hi` over a 270-degree arc. `bands` are `(from, to, color)`
    ranges as fractions of the scale, drawn as the outer rim; `ticks` major
    divisions are labelled, `minor` minor ticks sit between each. The needle
    stops at the ends of the scale; the number under the hub is `value`
    rounded. Returns the needle's angle in radians."""
    ctx = cv.ctx
    rim = r * 0.07
    for a, b, color in bands:
        cv.arc(cx, cy, r - rim / 2, START + SWEEP * a, START + SWEEP * b, color, width=rim)
    label_f = font or demo.font(round(r * 0.085), 700)
    for i in range(ticks * minor + 1):
        a = START + SWEEP * i / (ticks * minor)
        major = i % minor == 0
        r0, r1 = r - rim * (2.6 if major else 1.9), r - rim * 1.3
        cv.line(cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r1 * math.cos(a), cy + r1 * math.sin(a),
                ink if major else muted, width=r * (0.012 if major else 0.006))
        if major:
            rl = r - rim * 4.2
            demo.word(cv, f'{lo + (hi - lo) * i / (ticks * minor):g}', cx + rl * math.cos(a),
                      cy + rl * math.sin(a), font=label_f, color=muted)
    if number:
        demo.word(cv, f'{round(value)}', cx, cy + r * 0.42, font=demo.font(round(r * 0.26), 800), color=ink)
    f = min(max((value - lo) / (hi - lo), -0.02), 1.02)  # a needle stops just past its pins
    ang = START + SWEEP * f
    tip, tail, half = r * 0.78, r * 0.16, r * 0.028
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(ang)
    ctx.move_to(-tail, -half)
    ctx.line_to(tip, -half * 0.25)
    ctx.line_to(tip, half * 0.25)
    ctx.line_to(-tail, half)
    ctx.close_path()
    ctx.set_source_rgba(*rgba(needle))
    ctx.fill()
    ctx.restore()
    demo.dot(cv, cx, cy, r * 0.075, color=ink)
    demo.dot(cv, cx, cy, r * 0.035, color=demo.BG)
    return ang


def draw(n, cv):
    t = n / demo.FPS
    value = needle_value(t - 0.35, 0, 72)
    r = demo.H * 0.42
    cx, cy = demo.W / 2, demo.H / 2 + r * 0.1
    ang = draw_gauge(cv, cx, cy, r, value, needle=demo.ACCENT)
    tip = r * 0.78
    tx, ty = cx + tip * math.cos(ang), cy + tip * math.sin(ang)
    cv.mark('needle', min(cx, tx) - 6, min(cy, ty) - 6, abs(tx - cx) + 12, abs(ty - cy) + 12)


CAPABILITY = Capability(
    id='gauge-needle-sweep',
    name='Gauge needle sweep',
    family='broadcast',
    group='Charts',
    aliases=('speedometer dial', 'dial gauge', 'needle gauge'),
    definition='A pointer swings round a marked dial to land on a value, carrying a little past it '
               'before it settles back.',
    phrasings=('a speedometer needle that swings up to the number',
               'show the score on a dial with a needle that sweeps across',
               'a meter needle that overshoots and settles on the reading'),
    related=('balance-bar-tug', 'dimension-line-annotation', 'stopwatch-count-up', 'interlace-combing',
             'jiggle', 'scanline-jitter'),
    api=('videobuilder.capabilities.broadcast.gauge_needle_sweep.draw_gauge',
         'videobuilder.capabilities.broadcast.gauge_needle_sweep.needle_value'),
    demo=lambda: demo.film(draw),
)
