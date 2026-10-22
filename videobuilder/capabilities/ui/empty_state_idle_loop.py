"""Empty State Idle Loop: the little illustration in an otherwise empty panel
(an inbox with nothing in it, a blank list) never quite sits still -- it
floats, tilts and breathes on a short cycle that repeats without a seam."""
import math
from collections import namedtuple

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

Idle = namedtuple('Idle', 'dy angle scale glow')


def idle_loop(t, period=1.5, bob=12.0, tilt=3.0, breathe=0.025, offset=0.0):
    """The idle pose at `t` seconds, repeating exactly every `period` seconds:
    `dy` (px, negative is up) floats up and down by `bob`, `angle` (degrees)
    rocks by `tilt` a quarter-cycle behind it, `scale` swells by `breathe`
    about 1, and `glow` runs 0 -> 1 -> 0 with the float (1 at the top). Every
    term is a whole number of sine cycles per period, so frame `period * fps`
    matches frame 0 and the loop never jumps. `offset` (0..1 of a cycle)
    staggers several pieces of one illustration."""
    a = 2 * math.pi * (t / period + offset)
    return Idle(dy=-bob * math.sin(a), angle=tilt * math.sin(a - math.pi / 2),
                scale=1 + breathe * math.sin(2 * a), glow=0.5 + 0.5 * math.sin(a))


def draw_empty_state(cv, cx, cy, t, caption='Nothing here yet', period=1.5, color=demo.TEAL,
                     ink=demo.MUTED, size=1.0):
    """An empty-inbox illustration centred at (cx, cy) idling at `t` seconds:
    a tray that breathes, a blank sheet floating and rocking up out of it, two sparkles twinkling off-beat, and a
    still `caption` beneath. `size` scales the whole thing. Returns the Box
    of the illustration (without the caption)."""
    s = size
    sheet = idle_loop(t, period, bob=16 * s, tilt=4)
    tray = idle_loop(t, period, bob=0, tilt=0, breathe=0.02, offset=0.25)
    tw, th = 220 * s, 92 * s
    ty = cy + 30 * s
    # The sheet, drawn behind the tray front so it seems to rise out of it.
    with cv.layer(dx=cx, dy=ty - 70 * s + sheet.dy):
        cv.ctx.rotate(math.radians(sheet.angle))
        sw, sh = 120 * s, 130 * s
        cv.rect(-sw / 2, -sh / 2, sw, sh, '#22252d', radius=10 * s)
        cv.outline(-sw / 2, -sh / 2, sw, sh, ink, width=3 * s, radius=10 * s)
        for i, frac in enumerate((0.62, 0.44, 0.52)):
            cv.rect(-sw * 0.32, -sh * 0.28 + i * 24 * s, sw * frac, 7 * s, ink, radius=3.5 * s, alpha=0.6)
    # The tray: an open-topped box with a slot handle, breathing about its centre.
    with cv.layer(dx=cx, dy=ty, scale=tray.scale):
        lip = [(-tw / 2, -th / 2), (-tw / 2 + 30 * s, -th / 2 - 34 * s), (-tw / 2 + 64 * s, -th / 2 - 34 * s),
               (-tw / 2 + 78 * s, -th / 2), (tw / 2 - 78 * s, -th / 2), (tw / 2 - 64 * s, -th / 2 - 34 * s),
               (tw / 2 - 30 * s, -th / 2 - 34 * s), (tw / 2, -th / 2)]
        vb.paths.draw(cv, lip + [(tw / 2, th / 2), (-tw / 2, th / 2)], demo.BG, fill=True)
        cv.rect(-tw / 2, -th / 2, tw, th, demo.BG, radius=12 * s)
        vb.paths.draw(cv, lip, color, width=4 * s)
        cv.outline(-tw / 2, -th / 2, tw, th, color, width=4 * s, radius=12 * s)
        cv.line(-26 * s, 4 * s, 26 * s, 4 * s, color, width=5 * s)
    # Sparkles: each twinkles on its own beat of the same loop.
    for (dx, dy, off) in ((-150, -120, 0.0), (160, -60, 0.5)):
        g = idle_loop(t, period, offset=off).glow
        x, y, r = cx + dx * s, cy + dy * s, (6 + 8 * g) * s
        cv.line(x - r, y, x + r, y, color, width=3 * s, alpha=0.3 + 0.7 * g)
        cv.line(x, y - r, x, y + r, color, width=3 * s, alpha=0.3 + 0.7 * g)
    if caption:
        demo.word(cv, caption, cx, ty + th / 2 + 56 * s, size=round(34 * s), color=ink, weight=600)
    return vb.Box(cx - tw / 2, ty - th / 2 - 160 * s, tw, th + 160 * s)


def draw(n, cv):
    pw, ph = 600, 420
    px, py = (demo.W - pw) / 2, (demo.H - ph) / 2
    cv.rect(px, py, pw, ph, '#1b1d23', radius=24)
    cv.outline(px, py, pw, ph, demo.LINE, width=2, radius=24)
    cv.rect(px + 32, py + 28, 150, 12, demo.LINE, radius=6)
    cv.line(px + 32, py + 58, px + pw - 32, py + 58, demo.LINE, width=2)
    box = draw_empty_state(cv, demo.W / 2, demo.H / 2 + 20, n / demo.FPS, size=0.85)
    cv.mark('illustration', *box)


TECHNIQUE = Technique(
    id='empty-state-idle-loop',
    name='Empty state idle loop',
    family='ui',
    group='Feedback & status',
    aliases=('idle illustration', 'empty state animation'),
    definition='The small picture shown in a view with no content yet drifts, sways and pulses softly '
               'on a short repeating cycle, so the blank screen still feels alive.',
    phrasings=('make the empty inbox picture gently float while there is nothing to show',
               'a looping idle animation for the no-results screen',
               'the placeholder graphic should breathe a little instead of sitting dead still'),
    related=('breathing-idle', 'seamless-loop', 'interruptible-motion', 'ping-pong-loop',
             'frame-by-frame-hand-drawn-animation', 'idle-float-bob'),
    api=('videobuilder.techniques.ui.empty_state_idle_loop.idle_loop',
         'videobuilder.techniques.ui.empty_state_idle_loop.draw_empty_state'),
    demo=lambda: demo.film(draw),
)
