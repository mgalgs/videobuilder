"""Op-art vibrating pattern: tight black-and-white stripes whose edges ripple
in waves that drift out of step with each other, so the bands swell and pinch
and the whole field seems to shimmer and buzz."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def stripe_edges(x, j, t, amp, wavelength=220.0, speed=2.4, twist=0.35, wobble=0.0):
    """The vertical offset of stripe edge `j` at column `x` and time `t`
    (seconds): a wave `amp` px tall, `wavelength` px long, drifting at `speed`
    radians a second. `twist` shifts each next edge's phase, so neighbouring
    edges disagree and the bands between them thicken and thin. `wobble` adds
    a second, slower cross-wave for a busier shimmer."""
    k = 2 * math.pi / wavelength
    off = amp * math.sin(k * x - speed * t + j * twist)
    if wobble:
        off += amp * wobble * math.sin(0.6 * k * x + 1.7 * speed * t - j * twist * 0.5)
    return off


def draw_op_art(cv, x, y, w, h, t, pitch=28.0, amp=18.0, ink='#0b0b0b', paper='#f4f1ea', bulge=None,
                step=12.0, **wave):
    """Fill the box (x, y, w, h) with horizontal ink/paper stripes `pitch` px
    apart whose edges ripple at time `t` (see `stripe_edges`; `wave` passes
    through). `bulge`, if given as `(cx, cy, radius, gain)`, swells the wave
    inside a soft disc, the classic op-art lens. `step` is the sampling in px
    along each edge. Returns the Box drawn."""
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    cv.rect(x, y, w, h, paper)
    xs = [x - step + i * step for i in range(int(w / step) + 3)]

    def edge(j):
        base = y - pitch + j * pitch / 2
        out = []
        for px in xs:
            a = amp
            if bulge:
                bx, by, br, gain = bulge
                a *= 1 + gain * math.exp(-((px - bx) ** 2 + (base - by) ** 2) / (br * br))
            out.append((px, base + stripe_edges(px, j, t, a, **wave)))
        return out

    c.set_source_rgba(*vb.canvas.rgba(ink))
    rows = int(h / pitch) + 3
    for i in range(rows):
        top, bottom = edge(2 * i), edge(2 * i + 1)
        c.move_to(*top[0])
        for p in top[1:]:
            c.line_to(*p)
        for p in reversed(bottom):
            c.line_to(*p)
        c.close_path()
    c.fill()
    c.restore()
    return vb.Box(x, y, w, h)


def draw(n, cv):
    t = n / demo.FPS
    grow = vb.ease_in_out_quart(demo.phase(n, 0.0, 1.0))  # starts as calm stripes, then starts to buzz
    cx, cy, r = demo.W / 2, demo.H / 2, demo.H * 0.32
    draw_op_art(cv, 0, 0, demo.W, demo.H, t, amp=4 + 16 * grow, bulge=(cx, cy, r * 1.4, 1.2 * grow),
                wobble=0.4)
    # A disc of the same stripes in counter-phase: the edge where they meet flickers hardest.
    c = cv.ctx
    c.save()
    c.new_path()
    c.arc(cx, cy, r, 0, 2 * math.pi)
    c.clip()
    draw_op_art(cv, cx - r, cy - r, 2 * r, 2 * r, -t, amp=4 + 16 * grow, ink=demo.BG, twist=-0.35,
                wobble=0.4)
    c.restore()
    cv.mark('pattern', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='op-art-vibrating-pattern',
    name='Op-art vibrating pattern',
    family='shapes',
    group='Optical & interference',
    aliases=('op art', 'optical art', 'vibrating stripes', 'moire shimmer'),
    definition='Dense high-contrast stripes ripple in slightly mismatched waves, so the bands swell and pinch '
               'and the whole surface seems to shimmer and buzz before your eyes.',
    phrasings=('black and white lines that wobble and make your eyes buzz',
               'a trippy optical-illusion stripe pattern that seems to vibrate',
               'wavy stripes like a 60s op art painting, moving'),
    related=('refraction-ripple', 'hologram-effect', 'lens-flare', 'domain-warping', 'swirl', 'line-weave'),
    api=('videobuilder.capabilities.shapes.op_art_vibrating_pattern.draw_op_art',
         'videobuilder.capabilities.shapes.op_art_vibrating_pattern.stripe_edges'),
    demo=lambda: demo.film(draw),
)
