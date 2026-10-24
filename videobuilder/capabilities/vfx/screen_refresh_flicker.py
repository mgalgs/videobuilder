"""Screen refresh flicker: the same soft band rolling down the picture like
a screen filmed out of sync as Refresh bar (`refresh_bar.py`, which keeps
the capability); they share the aliases rolling bar and hum bar. This
module adds a brightness wobble and faint scanlines on top of the rolling
band. This module's own code stays (a film may still import it), but it is
no longer a capability of its own."""
import random

import videobuilder as vb

from .. import _demo as demo

MERGED_INTO = 'refresh-bar'


def refresh_bar(t, h, roll=1.2, bar=0.38):
    """Where the rolling band is at time `t` seconds on a screen `h` px tall:
    `(top, height)` in px from the screen's top. The band takes `roll`
    seconds to sweep from just above the screen to just below it, then
    starts again; `bar` is its height as a share of `h`."""
    bh = bar * h
    return ((t / roll) % 1.0) * (h + bh) - bh, bh


def screen_refresh_flicker(cv, draw, t, amount=1.0, x=0, y=0, w=None, h=None, roll=1.2, bar=0.38,
                           dark=0.45, edge=0.35, pulse=0.12, lines=4, line_alpha=0.18, seed=0, steps=24,
                           flicker=12):
    """Draw `draw(cv)`, then the refresh flicker over (x, y, w, h) (default the
    whole frame) at time `t` seconds and strength `amount` (0 -> 1; at 0 it
    is `draw(cv)` untouched). The band from `refresh_bar(t, h, roll, bar)`
    darkens by up to `dark`, fading in from its top and ending in a bright
    line of strength `edge`; `pulse` is how far the whole picture dips in
    brightness, picking a new random dip `flicker` times a second and holding
    it in between, so it wobbles rather than strobes (the same `seed` and `t`
    give the same dip); a dark scan line every `lines` px at `line_alpha`.
    `steps` is how many strips draw the band's soft gradient."""
    w = cv.width if w is None else w
    h = cv.height if h is None else h
    draw(cv)
    if amount <= 0:
        return
    with cv.clip(x, y, w, h):
        dip = pulse * random.Random(f'{seed}:{int(t * flicker + 1e-6)}').random()
        if dip > 0:
            cv.rect(x, y, w, h, '#000000', alpha=amount * dip)
        top, bh = refresh_bar(t, h, roll, bar)
        strip = bh / steps
        for i in range(steps):
            k = (i + 1) / steps                       # darker toward the leading (lower) edge
            cv.rect(x, y + top + i * strip, w, strip + 1, '#000000', alpha=amount * dark * k * k)
        edge_h = max(2.0, h * 0.012)
        lead = y + top + bh
        cv.rect(x, lead - edge_h, w, edge_h, '#ffffff', alpha=amount * edge)
        cv.rect(x, lead, w, edge_h * 3, '#ffffff', alpha=amount * edge * 0.3)
        if lines and line_alpha > 0:
            row = y
            while row < y + h:
                cv.rect(x, row, w, max(1.0, lines * 0.35), '#000000', alpha=amount * line_alpha)
                row += lines


def draw(n, cv):
    t = n / demo.FPS
    bx, by, bw, bh = 150, 50, demo.W - 300, demo.H - 100
    cv.shadow(bx - 16, by - 16, bw + 32, bh + 32, radius=26, dy=8, blur=24, color=(0, 0, 0, 0.5))
    cv.rect(bx - 16, by - 16, bw + 32, bh + 32, '#2a2b30', radius=26)

    def screen(c):
        img = demo.photo()
        with c.clip(bx, by, bw, bh, radius=14):
            c.image(img, *vb.Box(bx, by, bw, bh).cover(img.w, img.h))
        demo.word(c, 'LIVE', bx + bw / 2, by + bh / 2, size=120, color=demo.INK, weight=900)

    with cv.clip(bx, by, bw, bh, radius=14):
        screen_refresh_flicker(cv, screen, t, amount=demo.phase(n, 0.0, 0.4), x=bx, y=by, w=bw, h=bh,
                               roll=1.4, dark=0.6, edge=0.45, pulse=0.1, lines=3, seed=4, flicker=10)
    cv.mark('screen', bx, by, bw, bh)
