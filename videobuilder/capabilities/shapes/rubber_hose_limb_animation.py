"""Rubber Hose Animation: a cartoon character's arms and legs are soft tubes
with no joints, bowing into smooth curves as hands and feet swing about."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def hose_curve(x0, y0, x1, y1, length, bend=1.0):
    """The cubic Bezier `(x0, y0, c1x, c1y, c2x, c2y, x1, y1)` of a jointless
    limb of rest `length` from its root (x0, y0) to its tip (x1, y1). The
    slack between `length` and the straight distance bows the tube sideways,
    so its length stays roughly constant; pulled taut it runs straight.
    `bend` picks the side (+1 bows to the left of root -> tip, -1 to the
    right) and scales the bow."""
    dx, dy = x1 - x0, y1 - y0
    chord = math.hypot(dx, dy) or 1e-6
    # A shallow arc of chord c and sag s is about c + 8 s^2 / (3 c) long.
    sag = math.sqrt(3 / 8 * chord * max(0.0, length - chord)) * bend
    nx, ny = dy / chord, -dx / chord
    k = sag * 4 / 3  # control offset that puts the curve's middle `sag` off the chord
    return (x0, y0,
            x0 + dx / 3 + nx * k, y0 + dy / 3 + ny * k,
            x0 + 2 * dx / 3 + nx * k, y0 + 2 * dy / 3 + ny * k,
            x1, y1)


def hose_limb(cv, x0, y0, x1, y1, length, width=22, color='#f4f4f2', outline='#101114', bend=1.0,
              alpha=1.0):
    """Draw a rubber-hose limb from (x0, y0) to (x1, y1): one even-width,
    round-ended tube along `hose_curve`, with a dark outline. Returns the
    curve, so a hand or shoe can be placed at its tip and aimed along it."""
    curve = hose_curve(x0, y0, x1, y1, length, bend)
    c = cv.ctx
    c.save()
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for col, w in ((outline, width + 5), (color, width)):
        c.new_path()
        c.move_to(*curve[:2])
        c.curve_to(*curve[2:])
        c.set_source_rgba(*vb.canvas.rgba(col, alpha))
        c.set_line_width(w)
        c.stroke()
    c.restore()
    return curve


def _blob(cv, cx, cy, rx, ry, color, outline='#101114', angle=0.0):
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(angle)
    c.scale(rx, ry)
    c.new_path()
    c.arc(0, 0, 1, 0, 2 * math.pi)
    c.restore()
    c.set_source_rgba(*vb.canvas.rgba(color))
    c.fill_preserve()
    c.set_source_rgba(*vb.canvas.rgba(outline))
    c.set_line_width(2.5)
    c.stroke()


def draw(n, cv):
    t = n / demo.FPS
    step = 2 * math.pi * t / 1.0  # one full stride a second: three in the demo
    ground = demo.H - 80
    cx = demo.W / 2
    cy = ground - 205 - 7 * abs(math.sin(step))  # the body bobs twice a stride
    r = 66
    demo.floor(cv, ground + 10, demo.LINE)
    limb, shoe = '#e9e7e2', '#ffffff'

    # Legs: hips under the body, feet stepping in place, each lifting on its forward swing.
    for side, ph in ((-1, 0.0), (1, math.pi)):
        hx, hy = cx + side * 21, cy + r * 0.8
        fx = cx + side * 25 + 60 * math.cos(step + ph)
        fy = ground - 35 * max(0.0, math.sin(step + ph))
        hose_limb(cv, hx, hy, fx, fy, 168, width=12, color=limb, bend=0.9)  # knees bow forward
        _blob(cv, fx + 11, fy, 24, 11, shoe)

    # Body: a ball, lower half a pair of shorts with two buttons, and a face looking ahead.
    _blob(cv, cx, cy, r, r, '#f2b632')
    c = cv.ctx
    c.save()
    c.new_path()
    c.arc(cx, cy, r - 2, 0.1, math.pi - 0.1)
    c.close_path()
    c.set_source_rgba(*vb.canvas.rgba(demo.TEAL))
    c.fill()
    c.restore()
    for bx in (-14, 14):
        demo.dot(cv, cx + bx, cy + 20, 5, '#f2b632')
    for ex in (6, 29):
        _blob(cv, cx + ex, cy - 25, 10, 14, '#ffffff')
        demo.dot(cv, cx + ex + 3, cy - 23, 5, '#101114')
    cv.arc(cx + 20, cy - 5, 23, 0.35, 1.7, '#101114', width=3)

    # Arms: shoulders on the body's sides, each hand looping forward as the opposite foot does,
    # so each arm keeps bowing and straightening with no elbow.
    for side, ph in ((-1, math.pi), (1, 0.0)):
        sx, sy = cx + side * (r - 9), cy + 4
        a = step + ph
        hx = sx + side * 30 + 55 * math.cos(a)
        hy = sy + 60 + 30 * math.sin(a)
        hose_limb(cv, sx, sy, hx, hy, 118, width=11, color=limb, bend=-0.8)
        _blob(cv, hx, hy, 15, 14, shoe)
        _blob(cv, hx + side * 11, hy - 7, 6, 5, shoe)  # thumb
    cv.mark('character', cx - 140, cy - r, 280, ground - cy + r + 20)


TECHNIQUE = Technique(
    id='rubber-hose-limb-animation',
    name='Rubber hose animation',
    family='shapes',
    group='Characters & rigs',
    aliases=('rubber hose', 'rubber hose style', 'noodle limbs', 'noodle arms', 'hose arms', 'bendy arms',
             'boneless limbs'),
    definition='An old-cartoon character style whose arms and legs are smooth, jointless tubes that '
               'bend into soft curves instead of folding at elbows and knees.',
    phrasings=('make the character walk with floppy noodle arms like a 1930s cartoon',
               'arms and legs that curve like bendy hoses instead of having joints',
               'old-timey cartoon character with wiggly boneless limbs'),
    related=('rotoscope-look', 'stop-motion-animation', 'handheld-shake', 'elastic-stretch',
             'animated-sprite-particles', 'swirl'),
    api=('videobuilder.techniques.shapes.rubber_hose_limb_animation.hose_limb',
         'videobuilder.techniques.shapes.rubber_hose_limb_animation.hose_curve'),
    demo=lambda: demo.film(draw),
)
