"""Squash on tap: a button flattens and widens under the press, then springs
back past its shape, a little tall and narrow, wobbling until it settles."""
from contextlib import contextmanager

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def tap_squash(t, depth=0.2, press=0.09, spec=vb.damped(0.28, hz=4.0)):
    """Scale `(sx, sy)` of something tapped `t` seconds ago. For `press`
    seconds it squashes in to `depth` (wider by `depth`, shorter to match, so
    its area holds); on release a spring (`spec`, `vb.damped` params) carries
    it back past rest into a tall, narrow stretch and wobbles out to (1, 1).
    Before the tap (t < 0) it is (1, 1)."""
    if t <= 0:
        s = 0.0
    elif t < press:
        s = depth * vb.ease_out_expo(t / press)
    else:
        s = depth * (1 - vb.spring(t - press, **spec))
    sx = 1 + s
    return sx, 1 / sx


@contextmanager
def squashed(cv, cx, cy, sx, sy):
    """Draw inside the block scaled by (sx, sy) about the point (cx, cy): the
    centre of a button, or the middle of its base to keep it on its shelf."""
    c = cv.ctx
    c.save()
    c.translate(cx, cy)
    c.scale(sx, sy)
    c.translate(-cx, -cy)
    try:
        yield
    finally:
        c.restore()


TAPS = (0.9, 1.95)


def _button(cv, cx, cy, w=240, h=170):
    x, y = cx - w / 2, cy - h / 2
    cv.shadow(x, y, w, h, radius=30, dy=10, blur=26, color=(0, 0, 0, 0.45))
    cv.rect(x, y, w, h, demo.ACCENT, radius=30)
    c = cv.ctx
    c.set_line_cap(1)  # round
    c.set_line_join(1)
    c.move_to(cx - 40, cy + 2)
    c.line_to(cx - 10, cy + 30)
    c.line_to(cx + 44, cy - 28)
    c.set_source_rgba(*vb.rgba(demo.BG))
    c.set_line_width(14)
    c.stroke()


def _cursor(cv, x, y, s=1.0):
    pts = [(0, 0), (0, 46), (11, 35), (19, 54), (27, 50), (19, 32), (34, 32)]
    c = cv.ctx
    c.new_path()
    for i, (px, py) in enumerate(pts):
        (c.move_to if i == 0 else c.line_to)(x + px * s, y + py * s)
    c.close_path()
    c.set_source_rgba(*vb.rgba(demo.INK))
    c.fill_preserve()
    c.set_source_rgba(*vb.rgba(demo.BG))
    c.set_line_width(3)
    c.stroke()


def draw(n, cv):
    cx, cy = demo.W / 2, demo.H / 2
    t = n / demo.FPS
    since = max((t - at for at in TAPS if t >= at), default=-1)
    sx, sy = tap_squash(since)
    with squashed(cv, cx, cy, sx, sy):
        _button(cv, cx, cy)
    cv.mark('button', cx - 120 * sx, cy - 85 * sy, 240 * sx, 170 * sy)
    # the pointer glides onto the button, clicks twice, then drifts off
    arrive = vb.ease_in_out_quart(demo.phase(n, 0.2, 0.8))
    leave = vb.ease_in_out_quart(demo.phase(n, 2.55, 3.0))
    px = cx + 300 + (40 - 300) * arrive + 260 * leave
    py = cy + 230 + (20 - 230) * arrive + 200 * leave
    down = since >= 0 and since < 0.09
    _cursor(cv, px, py, 0.88 if down else 1.0)


CAPABILITY = Capability(
    id='squash-on-tap',
    name='Squash on tap',
    family='ui',
    group='Buttons',
    aliases=('jelly press', 'elastic tap', 'squishy button'),
    definition='When pressed, a button flattens and spreads sideways, then springs back past its '
               'shape into a brief tall stretch and wobbles to rest.',
    phrasings=('the button squishes when you click it and bounces back',
               'make the icon feel like jelly when it gets tapped',
               'a springy press on the button, flattening then wobbling back'),
    related=('squash-and-stretch', 'elastic-stretch', 'rubber-band-snap', 'elastic-horizontal-squash',
             'icon-hover-bounce', 'rubber-band-overscroll'),
    api=('videobuilder.capabilities.ui.squash_on_tap.tap_squash',
         'videobuilder.capabilities.ui.squash_on_tap.squashed'),
    demo=lambda: demo.film(draw),
)
