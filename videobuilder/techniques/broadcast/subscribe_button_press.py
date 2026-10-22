"""Subscribe button press: a pointer clicks a bright SUBSCRIBE pill on a
channel row; the pill squashes, flips to a dark SUBSCRIBED state as it
springs back, and a little bell pops in beside the label and rings."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique
from ..ui.press_depress import CURSOR

RED = '#e8352f'
DONE = '#3a3d47'


def _mix(a, b, k):
    a, b = vb.rgba(a), vb.rgba(b)
    return tuple(255 * (x + (y - x) * k) for x, y in zip(a[:3], b[:3])) + (a[3] + (b[3] - a[3]) * k,)


def bell_points(cx, top, size, n=24):
    """A bell `size` px tall hanging from (cx, top), as a closed point list
    (flared rim at the bottom, domed crown at the top)."""
    s = size
    pts = [(cx - 0.48 * s, top + 0.80 * s), (cx - 0.38 * s, top + 0.70 * s), (cx - 0.36 * s, top + 0.48 * s)]
    for i in range(n + 1):
        a = math.pi + math.pi * i / n
        pts.append((cx + 0.36 * s * math.cos(a), top + 0.48 * s + 0.36 * s * math.sin(a)))
    pts += [(cx + 0.38 * s, top + 0.70 * s), (cx + 0.48 * s, top + 0.80 * s)]
    return pts


def draw_bell(cv, cx, top, size, color, angle=0.0, alpha=1.0):
    """Draw a bell `size` px tall hanging from (cx, top), swung `angle`
    radians about that top point, its clapper lagging behind the swing."""
    ctx = cv.ctx
    ctx.save()
    ctx.translate(cx, top)
    ctx.rotate(angle)
    ctx.translate(-cx, -top)
    vb.paths.draw(cv, bell_points(cx, top, size), color, fill=True, alpha=alpha)
    demo.dot(cv, cx, top + 0.08 * size, 0.08 * size, color=color, alpha=alpha)
    demo.dot(cv, cx + size * 0.6 * math.sin(-angle * 0.6), top + 0.90 * size, 0.12 * size, color=color, alpha=alpha)
    ctx.restore()


def subscribe_state(t, click):
    """The button's state `t` seconds into a film clicked at `click` seconds:
    `press` (0 at rest, 1 squashed; springs back with a little overshoot),
    `flip` (0 SUBSCRIBE -> 1 SUBSCRIBED), `bell` (the bell's pop-in scale,
    overshooting 1) and `ring` (the bell's swing in radians, dying away)."""
    d = t - click
    if d < 0:
        return dict(press=0.0, flip=0.0, bell=0.0, ring=0.0)
    sink = 0.08
    press = vb.ease_out_quint(d / sink) if d < sink else 1 - vb.spring(d - sink, **vb.damped(0.35, hz=3.5))
    flip = vb.ease_in_out_quart(vb.clamp01((d - 0.06) / 0.22))
    bell = vb.spring(d - 0.22, **vb.damped(0.4, hz=2.6))
    r = max(0.0, d - 0.35)
    ring = 0.55 * math.exp(-2.6 * r) * math.sin(2 * math.pi * 3.2 * r) if d > 0.35 else 0.0
    return dict(press=press, flip=flip, bell=bell, ring=ring)


def subscribe_button(cv, cx, cy, t, click, h=84, color=RED, done=DONE, ink=demo.INK, font=None,
                     label='SUBSCRIBE', done_label='SUBSCRIBED', squash=0.1):
    """Draw a subscribe button centred at (cx, cy), `h` px tall, at film time
    `t` seconds for a click at `click` seconds. Before the click it is a
    `color` pill reading `label`; the click squashes it by `squash`, throws a
    ring, and as it springs back it turns `done`, widens, and swaps to
    `done_label` with a bell that pops in and rings. Returns its Box."""
    st = subscribe_state(t, click)
    f = font or demo.font(round(h * 0.34), 800)
    pad = h * 0.5
    bell_w = h * 0.66
    w0 = vb.text.measure(label, f) + 2 * pad
    w1 = vb.text.measure(done_label, f) + 2 * pad + bell_w
    w = w0 + (w1 - w0) * st['flip']
    sc = 1 - squash * st['press']
    x, y = cx - w / 2, cy - h / 2

    d = t - click
    if 0 <= d < 0.6:  # the click's ring, in the original colour
        g = 1 - (1 - d / 0.6) ** 3
        grow = 6 + 40 * g
        cv.outline(cx - w0 / 2 - grow, y - grow, w0 + 2 * grow, h + 2 * grow, color, width=4,
                   radius=h / 2 + grow, alpha=0.8 * (1 - d / 0.6))

    with cv.layer(dx=cx * (1 - sc), dy=cy * (1 - sc), scale=sc):
        up = 1 - st['press']
        cv.shadow(x, y, w, h, radius=h / 2, dy=4 + 8 * up, blur=10 + 16 * up, color=(0, 0, 0, 0.45))
        cv.rect(x, y, w, h, _mix(color, done, st['flip']), radius=h / 2)
        th = vb.text.line_height(f)
        if st['flip'] < 1:
            lw = vb.text.measure(label, f)
            vb.text.draw(cv, [label], f, cx - lw / 2, cy - th / 2, ink, alpha=1 - st['flip'])
        if st['flip'] > 0:
            lw = vb.text.measure(done_label, f)
            lx = cx - (lw + bell_w) / 2 + bell_w
            vb.text.draw(cv, [done_label], f, lx, cy - th / 2, ink, alpha=st['flip'])
            if st['bell'] > 0:
                size = h * 0.5 * st['bell']
                draw_bell(cv, lx - h * 0.4, cy - h * 0.27 * st['bell'], size, ink, angle=st['ring'])
    return vb.Box(x, y, w, h)


def _cursor(cv, x, y, s=1.6):
    pts = [(x + px * s, y + py * s) for px, py in CURSOR]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    vb.paths.draw(cv, pts, demo.INK, fill=True)
    vb.paths.draw(cv, pts, demo.BG, width=2, closed=True)


def draw(n, cv):
    t, click = n / demo.FPS, 1.1
    cy = demo.H / 2
    # The channel row: avatar, name and subscriber count on the left, the button on the right.
    ax = demo.W / 2 - 400
    demo.dot(cv, ax, cy, 62, color=demo.TEAL)
    demo.word(cv, 'S', ax, cy, size=64, color=demo.BG)
    nf, cf = demo.font(46, 800), demo.font(28, 500)
    vb.text.draw(cv, ['Studio Notes'], nf, ax + 92, cy - 52, demo.INK)
    count = '12.4K subscribers' if t < click + 0.3 else '12.5K subscribers'
    vb.text.draw(cv, [count], cf, ax + 92, cy + 10, demo.MUTED)
    bx = demo.W / 2 + 290
    box = subscribe_button(cv, bx, cy, t, click)
    cv.mark('button', *box)
    # The pointer glides in, dips with the press, and drifts away.
    st = subscribe_state(t, click)
    arrive = vb.interpolate(t, [0.2, 1.0], [0, 1], ease=vb.ease_out_expo)
    leave = vb.interpolate(t, [2.3, 2.9], [0, 1], ease=vb.ease_in_out_quart)
    px = bx + 40 + 360 * (1 - arrive) + 160 * leave
    py = cy + 8 + 260 * (1 - arrive) + 140 * leave + 6 * st['press']
    with cv.layer(opacity=1 - leave):
        _cursor(cv, px, py, s=1.6 - 0.2 * st['press'])


TECHNIQUE = Technique(
    id='subscribe-button-press',
    name='Subscribe button press',
    family='broadcast',
    group='Social media',
    aliases=('subscribe button', 'subscribe animation', 'subscribe and bell', 'subscribe reminder'),
    definition='A pointer clicks a bright red subscribe button, which squashes and springs back as a dark '
               'subscribed button with a small bell that pops in and rings.',
    phrasings=('show someone clicking the subscribe button',
               'a cursor hits subscribe and it turns grey with the bell ringing',
               'the classic "remember to subscribe" button click for my video'),
    related=('press-depress', 'hold-to-confirm', 'click-ripple-indicator', 'glow-button', 'ui-sound-effects',
             'swipe-action-row'),
    api=('videobuilder.techniques.broadcast.subscribe_button_press.subscribe_button',
         'videobuilder.techniques.broadcast.subscribe_button_press.subscribe_state',
         'videobuilder.techniques.broadcast.subscribe_button_press.draw_bell'),
    demo=lambda: demo.film(draw),
)
