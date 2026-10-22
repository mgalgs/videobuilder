"""Hold to Confirm: a button that fills from left to right for as long as it
is pressed, and only switches to its confirmed state once the fill reaches
the far edge; let go early and the fill drains back out."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def hold_progress(t, press, hold=1.2, release=None, drain=0.3):
    """Fill fraction 0 -> 1 at time `t` (seconds) of a button pressed at
    `press` that confirms after `hold` seconds held down. A `release` before
    the fill completes drains it back to 0 over `drain` seconds (scaled by how
    full it was); once full it stays full. Linear while held, as a real timer."""
    if t <= press:
        return 0.0
    full = press + hold
    if release is None or release >= full:
        return vb.clamp01((t - press) / hold)
    reached = (release - press) / hold
    if t <= release:
        return vb.clamp01((t - press) / hold)
    return max(0.0, reached - (t - release) / drain)


def _check(cx, cy, s):
    return [(cx - 0.5 * s, cy), (cx - 0.15 * s, cy + 0.35 * s), (cx + 0.55 * s, cy - 0.4 * s)]


def draw_hold_button(cv, cx, cy, p, label='Hold to confirm', done='Confirmed', w=520, h=150,
                     base=demo.LINE, fill=demo.ACCENT, ink=demo.INK, done_ink=demo.BG, done_p=None,
                     font=None, radius=None):
    """A hold-to-confirm button centred at (cx, cy) with fill fraction `p`.
    The label reads `ink` over the empty part and `done_ink` over the fill,
    split exactly at the fill edge. `done_p` (0 -> 1, default 1 once `p` is 1)
    swaps the label for `done` with a check mark drawing in and a small pop.
    Returns the button's Box."""
    p = vb.clamp01(p)
    done_p = (1.0 if p >= 1 else 0.0) if done_p is None else vb.clamp01(done_p)
    radius = h * 0.22 if radius is None else radius
    f = font or demo.font(round(h * 0.26), 700)
    pop = 1 + 0.06 * math.sin(math.pi * done_p)  # a small swell as it confirms
    x, y = cx - w / 2, cy - h / 2
    c = cv.ctx
    c.save()
    try:
        c.translate(cx, cy)
        c.scale(pop, pop)
        c.translate(-cx, -cy)
        cv.shadow(x, y, w, h, radius=radius, dy=10, blur=28, color=(0, 0, 0, 0.45))
        cv.rect(x, y, w, h, base, radius=radius)
        fw = w * p
        if fw > 0:
            with cv.clip(x, y, w, h, radius=radius):
                cv.rect(x, y, fw, h, fill)
        tw, th = vb.text.block_size([label], f)
        lx, ly = cx - tw / 2, cy - th / 2
        if done_p < 1:
            a = 1 - min(1.0, done_p * 2)
            with cv.clip(x + fw, y, w - fw, h):
                vb.text.draw(cv, [label], f, lx, ly, ink, alpha=a)
            with cv.clip(x, y, fw, h):
                vb.text.draw(cv, [label], f, lx, ly, done_ink, alpha=a)
        if done_p > 0:
            a = vb.clamp01(done_p * 2 - 0.6)
            dw, dh = vb.text.block_size([done], f)
            s = h * 0.24
            gap = s * 1.1
            left = cx - (dw + s + gap) / 2
            vb.text.draw(cv, [done], f, left + s + gap, cy - dh / 2, done_ink, alpha=a)
            pts = vb.paths.reveal(_check(left + s / 2, cy, s), vb.clamp01(done_p * 1.6 - 0.3))
            vb.paths.draw(cv, pts, done_ink, width=h * 0.05)
    finally:
        c.restore()
    cv.mark('button', x, y, w, h)
    return vb.Box(x, y, w, h)


def _cursor(cv, x, y, down=0.0, s=1.6):
    """A pointer arrow with its tip at (x, y); `down` 0 -> 1 squeezes it as pressed."""
    k = s * (1 - 0.12 * down)
    tip = [(0, 0), (0, 26), (6.5, 20), (11, 30), (15, 28), (10.5, 18.5), (19, 18.5)]
    pts = [(x + px * k, y + py * k) for px, py in tip]
    vb.paths.draw(cv, pts, '#000000', fill=True, alpha=0.35)
    vb.paths.draw(cv, pts, demo.INK, fill=True)
    vb.paths.draw(cv, pts, demo.BG, width=2.5, closed=True)


PRESS, HOLD = 0.75, 1.35


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2
    p = hold_progress(t, PRESS, HOLD)
    done_p = demo.phase(n, PRESS + HOLD, PRESS + HOLD + 0.45)
    draw_hold_button(cv, cx, cy, p, done_p=done_p)
    # the pointer glides in, presses for the whole fill, then lifts away
    arrive = vb.ease_out_quint(demo.phase(n, 0.05, PRESS - 0.1))
    leave = vb.ease_in_out_quart(demo.phase(n, PRESS + HOLD + 0.3, PRESS + HOLD + 0.8))
    x0, y0 = cx + 300, cy + 230
    x1, y1 = cx + 60, cy + 20
    px = x0 + (x1 - x0) * arrive + 180 * leave
    py = y0 + (y1 - y0) * arrive + 120 * leave
    down = demo.phase(n, PRESS - 0.1, PRESS) * (1 - demo.phase(n, PRESS + HOLD, PRESS + HOLD + 0.1))
    _cursor(cv, px, py, down)


TECHNIQUE = Technique(
    id='hold-to-confirm',
    name='Hold to confirm',
    family='ui',
    group='Buttons',
    aliases=('press and hold fill', 'long press confirm', 'hold to submit'),
    definition='A button fills steadily from one side while it is pressed and kept down, and only flips '
               'to its done state once the fill reaches the other side.',
    phrasings=('the button fills up while you hold it and then confirms',
               'press and hold the button until the bar fills to make it go',
               'a long-press button that charges up before it triggers'),
    related=('subscribe-button-press', 'shape-fill-sweep', 'progress-steps-connector-fill',
             'circle-check-draw', 'area-fill-sweep', 'bookmark-fill'),
    api=('videobuilder.techniques.ui.hold_to_confirm.draw_hold_button',
         'videobuilder.techniques.ui.hold_to_confirm.hold_progress'),
    demo=lambda: demo.film(draw),
)
