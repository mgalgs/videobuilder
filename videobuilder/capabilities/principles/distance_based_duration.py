"""Distance-Based Duration: how long a move takes comes from how far it goes,
so a short hop is quick, a long trip takes longer, and every move feels like
it travels at a similar pace instead of all sharing one fixed length."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def distance_duration(distance, ref_distance=400.0, ref_seconds=0.6, exponent=0.5, shortest=0.12, longest=None):
    """Seconds a move of `distance` pixels should take: `ref_seconds` at
    `ref_distance`, scaled by `(distance / ref_distance) ** exponent` and
    clamped to [`shortest`, `longest`].

    `exponent=1` is a constant speed; the default 0.5 grows more slowly, so a
    long trip takes longer than a short one without dragging. Measure
    `distance` in the frame's own pixels (it may be negative: only its size
    counts). In a film, turn it into frames with `round(fps * seconds)`."""
    if ref_distance <= 0 or ref_seconds <= 0:
        raise ValueError('ref_distance and ref_seconds must be positive')
    seconds = ref_seconds * (abs(distance) / ref_distance) ** exponent
    seconds = max(shortest, seconds)
    return seconds if longest is None else min(longest, seconds)


START = 0.4                   # every dot sets off together, at this second
X0 = 90                       # and from this x
TRIPS = (120, 360, 700)       # how far each lane's dot travels, in pixels
LANES = (210, 315, 420)       # each lane's y


def draw(n, cv):
    t = n / demo.FPS
    demo.word(cv, 'longer trip, longer move', demo.W / 2, 95, size=30, color=demo.MUTED, weight=600)
    cv.line(X0, LANES[0] - 50, X0, LANES[-1] + 50, demo.LINE, width=2)
    for i, (dist, y) in enumerate(zip(TRIPS, LANES)):
        secs = distance_duration(dist, ref_distance=700, ref_seconds=1.8)
        p = demo.phase(n, START, START + secs)
        x1 = X0 + dist
        cv.line(X0, y, x1, y, demo.LINE, width=2, alpha=0.6)
        arrived = p >= 1
        cv.outline(x1 - 40, y - 40, 80, 80, demo.TEAL if arrived else demo.MUTED, width=3, radius=40,
                   alpha=1.0 if arrived else 0.5)
        x = X0 + dist * vb.ease_in_out_quart(p)
        demo.dot(cv, x, y, 30, color=demo.TEAL if arrived else demo.ACCENT)
        cv.mark(f'dot{i}', x - 30, y - 30, 60, 60)
        label = f'{min(t - START, secs):.1f} s' if t > START else '0.0 s'
        f = demo.mono(24)
        vb.text.draw(cv, [label], f, x1 + 56, y - 14, demo.INK if arrived else demo.MUTED)


TECHNIQUE = Technique(
    id='distance-based-duration',
    name='Distance-Based Duration',
    family='principles',
    group='Timing & spacing',
    aliases=('distance-scaled timing', 'travel-time scaling', 'velocity-based duration'),
    definition='Each move is given a length of time that grows with how far it travels, '
               'so short moves finish quickly and long ones take longer at a similar pace.',
    phrasings=('make things that move further take longer to get there',
               'time each move by how far it has to go',
               'keep the speed consistent instead of giving every move the same duration'),
    related=('timing', 'time-remapping', 'delay', 'offset', 'speed-ramp', 'proximity-stagger'),
    api=('videobuilder.techniques.principles.distance_based_duration.distance_duration',),
    demo=lambda: demo.film(draw),
)
