"""Spring Motion: videobuilder already has it as `vb.spring` (seconds) and
`vb.spring_at` (frames), tuned with `vb.damped(ratio, hz)`, so this entry only
names it and demos it: a card on a coil, sent to one target and then another,
overshooting and ringing down each time."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

SPRING = vb.damped(0.22, hz=1.6)    # light damping: a clear overshoot and a few visible wobbles
WALL = demo.W * 0.12                # x of the fixed anchor the coil hangs from
STOPS = ((0.3, demo.W * 0.48), (1.6, demo.W * 0.7))  # (start s, target card centre x): out, then further


def card_x(n, x0=demo.W * 0.3):
    """The card's centre at frame `n`: each move springs from where the last
    one was aiming, so a second move starts while the first is still settling."""
    x, prev = x0, x0
    for start, target in STOPS:
        x += (target - prev) * vb.spring_at(n - start * demo.FPS, demo.FPS, **SPRING)
        prev = target
    return x


def coil(cv, x0, x1, y, turns=9, amp=20):
    """A zig-zag spring from (x0, y) to (x1, y); it stretches and squeezes with the gap."""
    pts = [(x0, y), (x0 + 16, y)]
    span = (x1 - 16) - (x0 + 16)
    for i in range(1, 2 * turns):
        pts.append((x0 + 16 + span * i / (2 * turns), y + (amp if i % 2 else -amp)))
    pts += [(x1 - 16, y), (x1, y)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, demo.INK, width=3, alpha=0.85)


def draw(n, cv):
    y, w, h = demo.H / 2, 180, 110
    x = card_x(n)
    cv.rect(WALL - 12, y - 100, 12, 200, demo.MUTED, radius=3)
    for _, target in STOPS:  # where each move comes to rest
        cv.line(target, y + 80, target, y + 100, demo.MUTED, width=2, alpha=0.7)
    coil(cv, WALL, x - w / 2, y)
    demo.card(cv, x, y, w=w, h=h)


CAPABILITY = Capability(
    id='spring-motion',
    name='Spring Motion',
    family='principles',
    group='Physics',
    aliases=('spring animation', 'spring physics', 'physics-based easing', 'damped spring',
             'spring ease', 'wobbly spring', 'damped oscillation', 'wobble to rest'),
    definition='Movement driven by a simulated spring, so a thing shoots toward its target, '
               'runs past it and wobbles back and forth in shrinking swings until it settles.',
    phrasings=('make it move like it is on a spring',
               'give it a springy, physical feel instead of a plain ease',
               'let it overshoot and wobble a bit before it comes to rest'),
    related=('spring-return', 'interruptible-motion', 'springs-network', 'mass-spring-cloth',
             'spring-drag-letters', 'icon-hover-bounce'),
    api=('videobuilder.spring', 'videobuilder.spring_at', 'videobuilder.ease.damped'),
    demo=lambda: demo.film(draw),
)
