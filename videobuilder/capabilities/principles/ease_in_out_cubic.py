"""Ease In-Out Cubic: the gentle S-curve -- a move that gathers speed from
rest, is quickest halfway, and comes to rest just as gently as it began."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_in_out_cubic(x):
    """Progress `x` in [0, 1] -> eased progress: 4x^3 for the first half,
    mirrored for the second, so it leaves and arrives with zero speed."""
    x = vb.clamp01(x)
    if x < 0.5:
        return 4 * x * x * x
    y = 2 - 2 * x
    return 1 - y * y * y / 2


START, END = 0.5, 2.3   # seconds the move runs between


def draw(n, cv):
    t = demo.phase(n, START, END)
    p = ease_in_out_cubic(t)

    # The move: a dot travelling between two rings, with ghosts left at even time steps
    # so the spacing shows it -- bunched at both ends, spread wide through the middle.
    x0, x1, y, r = demo.W / 2 - 340, demo.W / 2 + 340, 130, 30
    cv.line(x0, y + r + 18, x1, y + r + 18, demo.LINE, width=3)
    for cx in (x0, x1):
        cv.arc(cx, y, r + 4, 0, 6.2832, demo.MUTED, width=2, alpha=0.6)
    steps = 12
    for i in range(steps + 1):
        if i / steps <= t:
            demo.dot(cv, x0 + (x1 - x0) * ease_in_out_cubic(i / steps), y, 5, color=demo.MUTED, alpha=0.7)
    demo.dot(cv, x0 + (x1 - x0) * p, y, r)
    cv.mark('ball', x0 + (x1 - x0) * p - r, y - r, 2 * r, 2 * r)

    # The curve itself, traced in step with the dot.
    gx, gy, gw, gh = demo.W / 2 - 240, 240, 480, 220
    for i in range(1, 4):
        cv.line(gx + gw * i / 4, gy, gx + gw * i / 4, gy + gh, demo.LINE, width=1, alpha=0.5)
        cv.line(gx, gy + gh * i / 4, gx + gw, gy + gh * i / 4, demo.LINE, width=1, alpha=0.5)
    cv.outline(gx, gy, gw, gh, demo.LINE, width=1, alpha=0.7)
    seg = 60
    pts = [(gx + gw * i / seg, gy + gh * (1 - ease_in_out_cubic(i / seg))) for i in range(seg + 1)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        done = (bx - gx) / gw <= t + 1e-9
        cv.line(ax, ay, bx, by, demo.ACCENT if done else demo.MUTED, width=3 if done else 1.5,
                alpha=1.0 if done else 0.5)
    px, py = gx + gw * t, gy + gh * (1 - p)
    cv.line(px, py, px, gy + gh, demo.ACCENT, width=1, alpha=0.6)
    demo.dot(cv, px, py, 6, color=demo.INK)


TECHNIQUE = Technique(
    id='ease-in-out-cubic',
    name='Ease In-Out Cubic',
    family='principles',
    group='Easing',
    aliases=('easeInOutCubic', 'power 3 in-out', 'cubic in-out'),
    definition='A move that pulls away from rest gently, is quickest at its halfway point, '
               'then slows just as gently into its stop.',
    phrasings=('glides across, slow at both ends and fastest in the middle',
               'a smooth start and a smooth stop',
               'eases in and eases out, with nothing abrupt'),
    related=('slow-in-and-slow-out', 'asymmetric-fast-in-slow-out', 'inertia', 'dolly-in-and-out', 'push-in',
             'smooth-scroll-inertia'),
    api=('videobuilder.techniques.principles.ease_in_out_cubic.ease_in_out_cubic',),
    demo=lambda: demo.film(draw),
)
