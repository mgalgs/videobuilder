"""Toggle Switch Slide: a pill-shaped switch flips on, its round knob sliding
from one end of the track to the other while the track fills with colour."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def _mix(a, b, t):
    """Colour `a` -> `b` at `t`, as an (r, g, b, alpha) tuple the canvas takes."""
    ca, cb = vb.rgba(a), vb.rgba(b)
    r, g, bl, al = (x + (y - x) * t for x, y in zip(ca, cb))
    return (round(r * 255), round(g * 255), round(bl * 255), al)


def draw_toggle(cv, cx, cy, p, w=220, h=None, on=demo.TEAL, off='#3a3d46', knob=demo.INK, stretch=0.35):
    """A toggle switch centred at (cx, cy) at progress `p`: 0 is off (knob
    left, track `off`), 1 is on (knob right, track `on`). Pass an eased `p`.
    Mid-slide the knob stretches by `stretch` of its width, the way a finger
    drags it, and is round again at either end. `p` running 1 -> 0 switches
    it back off. Returns the switch's Box."""
    h = h or w * 0.55
    x, y = cx - w / 2, cy - h / 2
    pad = h * 0.1
    d = h - 2 * pad                       # the knob's diameter at rest
    t = vb.clamp01(p)
    cv.rect(x, y, w, h, _mix(off, on, t), radius=h / 2)
    kw = d * (1 + stretch * math.sin(math.pi * t))
    kx = x + pad + (w - 2 * pad - kw) * t
    cv.shadow(kx, y + pad, kw, d, radius=d / 2, dy=d * 0.06, blur=d * 0.18, color=(0, 0, 0, 0.35))
    cv.rect(kx, y + pad, kw, d, knob, radius=d / 2)
    cv.mark('knob', kx, y + pad, kw, d)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    p = vb.ease_in_out_quart(demo.phase(n, 0.9, 1.4))
    box = draw_toggle(cv, demo.W / 2, demo.H / 2, p, w=360)
    cv.mark('switch', *box)
    y = demo.H / 2 + box.h / 2 + 90
    demo.word(cv, 'OFF', demo.W / 2, y, size=56, color=demo.MUTED, alpha=1 - p)
    demo.word(cv, 'ON', demo.W / 2, y, size=56, color=demo.TEAL, alpha=p)


TECHNIQUE = Technique(
    id='toggle-switch-slide',
    name='Toggle switch slide',
    family='ui',
    group='Toggles & controls',
    aliases=('toggle switch', 'switch toggle', 'on/off switch', 'iOS-style switch'),
    definition='A rounded on/off switch whose circular knob glides to the other end of its track '
               'as the track changes colour to show the new state.',
    phrasings=('flip the settings switch from off to on',
               'a little toggle that slides over and turns green',
               'show the switch being turned on'),
    related=('password-reveal-toggle', 'arrow-slide', 'hover-reveal-actions', 'carousel-slide', 'tile-flip',
             'gradient-shift-button'),
    api=('videobuilder.techniques.ui.toggle_switch_slide.draw_toggle',),
    demo=lambda: demo.film(draw),
)
