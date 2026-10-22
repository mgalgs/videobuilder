"""Click ripple indicator: in a screen walkthrough, every click the pointer
makes leaves a ring that swells out from the click point and fades, so the
viewer sees exactly where and when the input happened."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ..ui.cursor_state_change import draw_cursor


def click_ripple(cv, x, y, p, color=demo.ACCENT, reach=84, width=6, rings=2, lag=0.22, alpha=1.0,
                 core=0.35):
    """Draw a click indicator at progress `p` (0 -> 1) centred on the click
    point (x, y): `rings` outlines, each starting `lag` of the run after the
    last, grow to `reach` pixels with an ease-out and thin and fade as they
    go. A soft filled disc of opacity `core` flashes at the point over the
    first part of the run. Nothing draws outside 0 < p < 1. Draw it over the
    UI and under the pointer."""
    if not 0 < p < 1:
        return
    flash = 1 - vb.clamp01(p / 0.4)
    if flash > 0 and core > 0:
        cv.sector(x, y, reach * (0.18 + 0.2 * (1 - flash)), 0, 2 * math.pi, color,
                  alpha=alpha * core * flash)
    span = 1 - lag * (rings - 1)
    for i in range(rings):
        q = vb.clamp01((p - i * lag) / span)
        if not 0 < q < 1:
            continue
        r = reach * (0.12 + 0.88 * vb.ease_out_quint(q))
        cv.arc(x, y, r, 0, 2 * math.pi, color, width=max(width * (1 - 0.7 * q), 0.5),
               alpha=alpha * (1 - q) ** 1.5)


# The demo: a settings card; the pointer glides to its button, clicks it,
# moves to a toggle row, clicks again, then drifts away.
CW, CH = 620, 360
CX, CY = (demo.W - CW) / 2, (demo.H - CH) / 2
BUTTON = vb.Box(CX + 48, CY + CH - 104, 200, 64)
TOGGLE = vb.Box(CX + CW - 160, CY + 56, 96, 48)
CLICKS = ((0.9, BUTTON.x + BUTTON.w * 0.55, BUTTON.y + BUTTON.h * 0.5),
          (1.9, TOGGLE.x + TOGGLE.w * 0.5, TOGGLE.y + TOGGLE.h * 0.5))
RUN = 0.75
PATH = ((0.2, demo.W * 0.72, demo.H * 0.86), (0.75,) + CLICKS[0][1:], (1.0,) + CLICKS[0][1:],
        (1.75,) + CLICKS[1][1:], (2.2,) + CLICKS[1][1:], (2.8, demo.W * 0.74, demo.H * 0.8))


def pointer(t):
    """Where the pointer is at `t` seconds: eased glides between the PATH stops."""
    ts = [k[0] for k in PATH]
    return (vb.interpolate(t, ts, [k[1] for k in PATH], ease=vb.ease_in_out_quart),
            vb.interpolate(t, ts, [k[2] for k in PATH], ease=vb.ease_in_out_quart))


def draw(n, cv):
    t = n / demo.FPS
    cv.shadow(CX, CY, CW, CH, radius=20, dy=10, blur=30, color=(0, 0, 0, 0.45))
    cv.rect(CX, CY, CW, CH, demo.LINE, radius=20)
    cv.rect(CX + 48, CY + 62, 220, 14, demo.MUTED, radius=7, alpha=0.9)
    cv.rect(CX + 48, CY + 92, 300, 10, demo.MUTED, radius=5, alpha=0.5)
    cv.rect(CX + 48, CY + 140, 380, 10, demo.MUTED, radius=5, alpha=0.5)
    cv.rect(CX + 48, CY + 164, 320, 10, demo.MUTED, radius=5, alpha=0.5)

    pressed = [max(0.0, 1 - abs(t - (s + 0.05)) / 0.12) for s, _, _ in CLICKS]
    on = vb.ease_in_out_quart(demo.phase(n, CLICKS[1][0], CLICKS[1][0] + 0.25))
    cv.rect(*TOGGLE, demo.kit.mix(demo.MUTED, demo.TEAL, on), radius=TOGGLE.h / 2, alpha=0.9)
    demo.dot(cv, TOGGLE.x + 24 + (TOGGLE.w - 48) * on, TOGGLE.y + TOGGLE.h / 2, r=18, color=demo.INK)
    s = 1 - 0.05 * pressed[0]
    bw, bh = BUTTON.w * s, BUTTON.h * s
    cv.rect(BUTTON.x + (BUTTON.w - bw) / 2, BUTTON.y + (BUTTON.h - bh) / 2, bw, bh, demo.TEAL, radius=14)
    demo.word(cv, 'SAVE', BUTTON.x + BUTTON.w / 2, BUTTON.y + BUTTON.h / 2, size=30, color=demo.BG)
    cv.mark('button', *BUTTON)

    for start, x, y in CLICKS:
        click_ripple(cv, x, y, demo.phase(n, start, start + RUN), color='#f5c84c')

    x, y = pointer(t)
    cv.mark('cursor', *draw_cursor(cv, x, y, 0, size=1.8 - 0.2 * max(pressed)))


CAPABILITY = Capability(
    id='click-ripple-indicator',
    name='Click ripple indicator',
    family='broadcast',
    group='UI walkthroughs',
    aliases=('tap indicator', 'click highlight', 'click ring', 'click visualiser'),
    definition='Each time the pointer clicks in a screen recording, a ring bursts out from the click point '
               'and fades, marking where the input landed.',
    phrasings=('show a circle pulse wherever the mouse clicks in the demo',
               'highlight the clicks in my screen recording so people can follow along',
               'a little ring animation at the cursor every time it taps something'),
    related=('touch-ripple', 'location-ripple-pulse', 'focus-ring-draw', 'callout-highlight',
             'drop-target-highlight', 'border-glow-follow'),
    api=('videobuilder.capabilities.broadcast.click_ripple_indicator.click_ripple',
         'videobuilder.capabilities.ui.cursor_state_change.draw_cursor'),
    demo=lambda: demo.film(draw),
)
