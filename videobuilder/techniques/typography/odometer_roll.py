"""Odometer Roll: a number shown on a row of drum wheels, each digit rolling
up to the next like a mechanical counter, the higher wheels turning only when
the one to their right rolls over from 9 to 0."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def odometer_wheels(value, places):
    """Where each of `places` wheels stands for `value` (a float >= 0), most
    significant first, as a float in [0, 10): 3.4 is digit 3 a little over a
    third of the way up to 4. Like a real odometer, the ones wheel turns
    with the value and every other wheel only moves while all the wheels to
    its right are passing 9 -> 0, so a carry rolls through the row at once."""
    value = max(0.0, value)
    out = []
    for k in range(places - 1, -1, -1):
        unit = 10 ** k
        below = math.fmod(value, unit)          # what the wheels to the right are showing
        carry = max(0.0, below - (unit - 1))    # 0 -> 1 while they all roll from 9s to 0s
        out.append(math.fmod(math.floor(value / unit) + carry, 10))
    return out


def draw_odometer(cv, value, places, font, x, y, color, cell=None, face='#0d0e12', gap=None, shade=True):
    """Draw `value` on `places` drum wheels from the top-left (x, y), each a
    `cell` (w, h) window (default: sized to `font`) with `face` behind it and
    the digits rolling upwards as the value grows; `shade` darkens the top
    and bottom of each window so the wheels read as drums. Animate by
    passing a value that changes with the frame. Returns the row's Box."""
    cw, ch = cell or (vb.text.measure('0', font) * 1.5, vb.text.line_height(font) * 1.15)
    gap = cw * 0.12 if gap is None else gap
    lh = vb.text.line_height(font)
    for i, w in enumerate(odometer_wheels(value, places)):
        cx = x + i * (cw + gap)
        cv.rect(cx, y, cw, ch, face, radius=cw * 0.12)
        with cv.clip(cx, y, cw, ch, cw * 0.12):
            d, f = int(w) % 10, w - int(w)
            for j, digit in ((0, d), (1, (d + 1) % 10)):   # this digit leaves upward, the next comes up under it
                gy = y + (ch - lh) / 2 + (j - f) * ch
                dw = vb.text.measure(str(digit), font)
                vb.text.draw(cv, [str(digit)], font, cx + (cw - dw) / 2, gy, color)
            if shade:
                g = cairo.LinearGradient(0, y, 0, y + ch)
                for stop, a in ((0, 0.75), (0.28, 0), (0.72, 0), (1, 0.75)):
                    g.add_color_stop_rgba(stop, 0, 0, 0, a)
                cv.ctx.rectangle(cx, y, cw, ch)
                cv.ctx.set_source(g)
                cv.ctx.fill()
    return vb.Box(x, y, places * cw + (places - 1) * gap, ch)


def draw(n, cv):
    f = demo.mono(150, 700)
    places = 5
    cw, ch = 140, 210
    w = places * cw + (places - 1) * 16
    x, y = (demo.W - w) / 2, (demo.H - ch) / 2
    value = 9981 + 19 * vb.ease_out_quint(demo.phase(n, 0.3, 2.6))   # 09981 -> 10000: the carry rolls through slowly
    cv.rect(x - 28, y - 28, w + 56, ch + 56, demo.LINE, radius=30)
    box = draw_odometer(cv, value, places, f, x, y, demo.INK, cell=(cw, ch), gap=16)
    cv.mark('odometer', *box)


TECHNIQUE = Technique(
    id='odometer-roll',
    name='Odometer roll',
    family='typography',
    group='Mechanical display',
    aliases=('rolling digits', 'rolling counter', 'mechanical counter', 'digit roll'),
    definition='A number sits on a row of spinning drums and each digit scrolls upward into the next, '
               'the left-hand wheels ticking over only when the wheel beside them passes nine.',
    phrasings=('the number rolls up like a car mileage counter',
               'digits spin vertically on little wheels until they land on the total',
               'make the count tick over like an old mechanical meter'),
    related=('number-count-up', 'decimal-counter-with-formatting', 'number-count-down', 'turntable-rotation',
             'letter-roll', 'player-stat-card'),
    api=('videobuilder.techniques.typography.odometer_roll.draw_odometer',
         'videobuilder.techniques.typography.odometer_roll.odometer_wheels'),
    demo=lambda: demo.film(draw),
)
