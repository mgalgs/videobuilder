"""Lightning flash: a jagged bolt cracks across the frame, the whole picture
blows out pale blue-white for an instant, flickers once, and the light dies
away over the next half second while the bolt lingers as an afterglow.

`lightning_flash(cv, t, bolt)` draws the flash and the bolt over whatever a
film has already drawn, `t` seconds after the strike; `flash_level(t)` is the
brightness envelope on its own, for lighting the scene itself (mix a hill's
colour toward its lit colour by it). `lightning_bolt(...)` builds the bolt.

Mind photosensitive viewers: one strike is two flashes (the hit and its
re-flicker), so leave a second or more between strikes."""
import math
import random

import cairo

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Capability

FLASH = '#dfe6ff'


def lightning_bolt(x0, y0, x1, y1, seed=1, jag=0.3, depth=4, branches=3):
    """A bolt from (x0, y0) to (x1, y1) as a list of polylines, the main
    channel first, then up to `branches` shorter forks splitting off it.
    Built by midpoint displacement: each segment's midpoint is pushed
    sideways by up to `jag` of its length, `depth` times over. The same
    `seed` gives the same bolt, so a film can redraw it every frame."""
    rnd = random.Random(seed)

    def crack(ax, ay, bx, by, levels, amount):
        pts = [(ax, ay), (bx, by)]
        for _ in range(levels):
            out = [pts[0]]
            for (px, py), (qx, qy) in zip(pts, pts[1:]):
                dx, dy = qx - px, qy - py
                off = rnd.uniform(-amount, amount)
                out.append(((px + qx) / 2 - dy * off, (py + qy) / 2 + dx * off))
                out.append((qx, qy))
            pts = out
        return pts

    main = crack(x0, y0, x1, y1, depth, jag)
    paths = [main]
    length = math.hypot(x1 - x0, y1 - y0)
    for _ in range(branches):
        i = rnd.randrange(len(main) // 6, len(main) * 2 // 3)
        bx, by = main[i]
        ang = math.atan2(y1 - y0, x1 - x0) + rnd.choice((-1, 1)) * rnd.uniform(0.4, 0.9)
        reach = length * rnd.uniform(0.15, 0.3)
        paths.append(crack(bx, by, bx + math.cos(ang) * reach, by + math.sin(ang) * reach, depth - 2, jag))
    return paths


def flash_level(t, decay=0.35, flicker=True):
    """Brightness 0 -> 1 of a strike `t` seconds after it hits: full at once,
    a quick dip and re-flash about a tenth of a second in (when `flicker`),
    then an exponential fall-off with time constant `decay` seconds. 0 before
    the strike."""
    if t < 0:
        return 0.0
    if flicker and t < 0.14:
        if t < 0.05:
            return 1.0
        if t < 0.09:
            return 0.25
        return 0.9
    t0 = 0.14 if flicker else 0.0
    return (0.9 if flicker else 1.0) * math.exp(-(t - t0) / decay)


def lightning_flash(cv, t, bolt, color=FLASH, strength=0.85, width=6, afterglow=0.7, decay=0.35):
    """Draw a strike `t` seconds after it hits, over what is already on `cv`:
    a full-frame wash of `color` at `strength` times `flash_level(t)`, and the
    `bolt` (polylines from `lightning_bolt`) as a glowing white stroke `width`
    px thick at its trunk, which fades more slowly (time constant `afterglow`)
    than the wash. Draws nothing before the strike. Returns the flash level."""
    level = flash_level(t, decay)
    if level <= 0:
        return 0.0
    cv.fill(color, alpha=strength * level)
    glow = flash_level(t, afterglow)
    c = cv.ctx
    c.save()
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    for i, pts in enumerate(bolt):
        w = width * (1.0 if i == 0 else 0.5)
        for grow, a, col in ((6, 0.12, color), (3, 0.25, color), (1, 1.0, '#ffffff')):
            c.new_path()
            c.move_to(*pts[0])
            for p in pts[1:]:
                c.line_to(*p)
            c.set_source_rgba(*vb.rgba(col, a * glow))
            c.set_line_width(w * grow)
            c.stroke()
    c.restore()
    return level


# ---- demo ----

STRIKE = 0.9
SKY_TOP, SKY_LOW = '#0c1020', '#1f2740'
HILLS = (('#151a26', '#5a6478', 0.70, 60, 0.004), ('#0d1018', '#3c4454', 0.80, 45, 0.006))
BOLT = lightning_bolt(demo.W * 0.52, -20, demo.W * 0.44, demo.H * 0.74, seed=1)


def _sky(cv, lit):
    g = cairo.LinearGradient(0, 0, 0, demo.H)
    g.add_color_stop_rgba(0, *vb.rgba(kit.mix(SKY_TOP, '#6b7590', lit)))
    g.add_color_stop_rgba(1, *vb.rgba(kit.mix(SKY_LOW, '#9aa4bd', lit)))
    cv.ctx.rectangle(0, 0, demo.W, demo.H)
    cv.ctx.set_source(g)
    cv.ctx.fill()


def _hills(cv, lit):
    c = cv.ctx
    for dark, bright, base, amp, freq in HILLS:
        c.new_path()
        c.move_to(0, demo.H)
        for x in range(0, demo.W + 41, 40):
            c.line_to(x, demo.H * base - amp * (math.sin(x * freq) + 0.5 * math.sin(x * freq * 2.7 + 1)))
        c.line_to(demo.W, demo.H)
        c.close_path()
        c.set_source_rgba(*vb.rgba(kit.mix(dark, bright, lit)))
        c.fill()


def _draw(n, cv):
    t = n / demo.FPS - STRIKE
    lit = flash_level(t) * 0.8
    _sky(cv, lit)
    _hills(cv, lit)
    lightning_flash(cv, t, BOLT)


CAPABILITY = Capability(
    id='lightning-flash',
    name='Lightning flash',
    family='camera',
    group='Lighting & surface',
    aliases=('lightning strobe', 'storm flash', 'lightning strike'),
    definition='A forked bolt cracks across a dark scene while the whole picture blinks bright '
               'white, flickers, and then sinks back into darkness with the bolt glowing a moment longer.',
    phrasings=('make lightning strike and light up the whole sky',
               'a stormy flash where everything goes bright for a split second',
               'add a thunderstorm flash with a zigzag bolt'),
    related=('lightning-bolt', 'strobe-cut', 'electric-arc', 'sparks', 'fireflies', 'meteor-shower'),
    api=('videobuilder.capabilities.camera.lightning_flash.lightning_flash',
         'videobuilder.capabilities.camera.lightning_flash.lightning_bolt',
         'videobuilder.capabilities.camera.lightning_flash.flash_level'),
    demo=lambda: demo.film(_draw),
)
