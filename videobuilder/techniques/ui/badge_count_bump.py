"""Badge count bump: a small numeric badge that swells and springs back each
time its count goes up, the new number swapping in at the top of the swell."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

BUMP = vb.damped(0.3, hz=4.0)  # under-damped: one clear swell, a small dip, then rest


def bump_scale(t, amount=0.45, spec=BUMP):
    """The badge's scale `t` seconds after a bump: 1 before it, a quick swell
    of up to about `1 + amount`, then a springy settle back to 1."""
    if t <= 0:
        return 1.0
    rise = 0.07  # seconds to the top of the swell
    if t < rise:
        return 1 + amount * vb.ease_out_quint(t / rise)
    return 1 + amount * (1 - vb.spring(t - rise, **spec))


def badge_state(t, bumps, start=0, amount=0.45, spec=BUMP):
    """`(count, scale)` at `t` seconds for a badge that starts at `start` and
    goes up by one at each time in `bumps`. The count changes the moment a
    bump lands; the scale follows the latest bump (`bump_scale`)."""
    hits = [b for b in sorted(bumps) if b <= t]
    if not hits:
        return start, 1.0
    return start + len(hits), bump_scale(t - hits[-1], amount, spec)


def draw_badge(cv, count, cx, cy, r=26, scale=1.0, color=demo.ACCENT, ink=demo.INK, cap=99):
    """A round count badge centred at (cx, cy), radius `r`, scaled by `scale`
    about its centre. Wider counts stretch it into a pill; counts above `cap`
    read `cap+`. Returns its Box."""
    text = f'{cap}+' if count > cap else str(count)
    f = demo.font(round(r * 1.15), 800)
    tw, th = vb.text.block_size([text], f)
    w, h = max(2 * r, tw + r), 2 * r
    s = max(scale, 1e-3)
    with cv.layer(dx=cx * (1 - s), dy=cy * (1 - s), scale=s):
        cv.rect(cx - w / 2, cy - h / 2, w, h, color, radius=r)
        vb.text.draw(cv, [text], f, cx - tw / 2, cy - th / 2, ink)
    box = vb.Box(cx - w * s / 2, cy - h * s / 2, w * s, h * s)
    cv.mark('badge', *box)
    return box


BUMPS = (0.6, 1.25, 1.9, 2.45)


def draw(n, cv):
    cx, cy, w, h = demo.W / 2, demo.H / 2 + 20, 360, 220
    demo.card(cv, cx, cy, w=w, h=h, color=demo.LINE)
    count, s = badge_state(n / demo.FPS, BUMPS, start=1)
    draw_badge(cv, count, cx + w / 2 - 6, cy - h / 2 + 6, r=34, scale=s)


TECHNIQUE = Technique(
    id='badge-count-bump',
    name='Badge count bump',
    family='ui',
    group='Feedback & status',
    aliases=('count badge pop', 'notification bump', 'badge bounce'),
    definition='A small number badge swells and springs back to size every time its count ticks up, '
               'the new number appearing at the peak.',
    phrasings=('the notification badge pops each time the number goes up',
               'the unread count bounces when a new message arrives',
               'make the little red counter jump as it increments'),
    related=('badge-stamp-impact', 'number-count-up', 'live-indicator-pulse', 'like-heart-burst',
             'delta-arrow-badge', 'circle-pop'),
    api=('videobuilder.techniques.ui.badge_count_bump.badge_state',
         'videobuilder.techniques.ui.badge_count_bump.draw_badge',
         'videobuilder.techniques.ui.badge_count_bump.bump_scale'),
    demo=lambda: demo.film(draw),
)
