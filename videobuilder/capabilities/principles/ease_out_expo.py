"""Ease Out Expo: videobuilder already has it as `vb.ease_out_expo`, so this
entry only names it and demos it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

START, END = 0.4, 2.2
TICKS = 12  # where the card was at even steps of time: wide gaps early, packed tight at the end


def draw(n, cv):
    x0, x1, y = 260, demo.W - 260, demo.H / 2
    track = y + 140
    cv.line(x0, track, x1, track, demo.LINE, width=2)
    cv.outline(x1 - 130, y - 80, 260, 160, demo.MUTED, width=2, radius=18, alpha=0.5)  # where it comes to rest
    t = n / demo.FPS
    for i in range(TICKS + 1):
        at = START + (END - START) * i / TICKS
        if at <= t:
            demo.dot(cv, x0 + (x1 - x0) * vb.ease_out_expo(i / TICKS), track, r=7, color=demo.MUTED)
    demo.card(cv, x0 + (x1 - x0) * vb.ease_out_expo(demo.phase(n, START, END)), y)


CAPABILITY = Capability(
    id='ease-out-expo',
    name='Ease Out Expo',
    family='principles',
    group='Easing',
    aliases=('expo out', 'exponential ease out', 'easeOutExpo'),
    definition='A move that leaves almost at full speed and then brakes harder and harder, '
               'creeping the last stretch so it seems to glide gently into place.',
    phrasings=('shoots in fast and then slows right down as it arrives',
               'whips across and settles softly at the end',
               'a snappy start with a long, gentle landing'),
    related=('slow-in-and-slow-out', 'friction-deceleration', 'momentum-fling', 'interruptible-motion',
             'smooth-scroll-inertia', 'asymmetric-fast-in-slow-out'),
    api=('videobuilder.ease_out_expo',),
    demo=lambda: demo.film(draw),
)
