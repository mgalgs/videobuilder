"""Balance bar tug: one bar split between two sides in two colours, whose
dividing line is pulled back and forth as the share swings from one side to
the other -- possession stats, a live poll, a head-to-head."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def tug_share(t, keys, start=0.5, stiffness=120.0, damping=11.0):
    """The left side's share (0..1) of a balance bar at `t` seconds. `keys`
    is a sequence of `(seconds, share)`: at each, the divider is yanked
    towards the new share on a lightly under-damped spring, so it overshoots
    a little and settles like a rope being tugged. Pulls overlap, so a new
    key can arrive before the last has settled. Starts at `start`."""
    share, prev = start, start
    for at, target in keys:
        share += (target - prev) * vb.spring(t - at, stiffness=stiffness, damping=damping)
        prev = target
    return vb.clamp01(share)


def draw_balance_bar(cv, x, y, w, h, share, left=demo.ACCENT, right=demo.TEAL, gap=4, knob=True):
    """Draw a balance bar `w` x `h` with its top-left at (x, y): the left
    `share` of it in `left`, the rest in `right`, split by a `gap`-wide notch
    and (with `knob`) a bright tab riding the divider, clipped to rounded
    ends. Returns the divider's x."""
    r = h / 2
    split = x + w * vb.clamp01(share)
    with cv.clip(x, y, w, h, radius=r):
        cv.rect(x, y, split - x, h, left)
        cv.rect(split, y, x + w - split, h, right)
        cv.rect(split - gap / 2, y, gap, h, demo.BG)
    if knob:
        kw, kh = h * 0.28, h * 1.5
        cv.rect(split - kw / 2, y + h / 2 - kh / 2, kw, kh, demo.INK, radius=kw / 2)
    return split


KEYS = ((0.35, 0.66), (1.05, 0.33), (1.75, 0.58), (2.35, 0.53))


def draw(n, cv):
    t = n / demo.FPS
    share = tug_share(t, KEYS)
    bw, bh = demo.W * 0.74, demo.H * 0.075
    x, y = (demo.W - bw) / 2, demo.H * 0.5
    size = round(demo.H * 0.06)
    tag = demo.font(round(demo.H * 0.035), 700)
    vb.text.draw(cv, ['HOME'], tag, x, y - size * 2.2, demo.ACCENT)
    w_away, _ = vb.text.block_size(['AWAY'], tag)
    vb.text.draw(cv, ['AWAY'], tag, x + bw - w_away, y - size * 2.2, demo.TEAL)
    num = demo.font(size, 800)
    pl = round(share * 100)
    vb.text.draw(cv, [f'{pl}%'], num, x, y - size * 1.5, demo.INK)
    rtxt = f'{100 - pl}%'
    rw, _ = vb.text.block_size([rtxt], num)
    vb.text.draw(cv, [rtxt], num, x + bw - rw, y - size * 1.5, demo.INK)
    cv.line(demo.W / 2, y + bh + 10, demo.W / 2, y + bh + 22, demo.MUTED, width=2)  # the 50% mark
    demo.word(cv, 'POSSESSION', demo.W / 2, y + bh + 50, size=round(demo.H * 0.032), color=demo.MUTED,
              weight=700)
    split = draw_balance_bar(cv, x, y, bw, bh, share)
    cv.mark('bar', x, y, bw, bh)
    cv.mark('divider', split - 2, y, 4, bh)


CAPABILITY = Capability(
    id='balance-bar-tug',
    name='Balance bar tug',
    family='broadcast',
    group='Comparisons',
    aliases=('tug of war bar', 'split comparison bar', 'possession bar', 'head-to-head bar',
             'versus bar'),
    definition='A single bar shared by two colours, one per side, whose dividing line gets yanked back '
               'and forth and settles as the balance between the two sides shifts.',
    phrasings=('a two-colour bar where the middle line swings between the teams as the numbers change',
               'show the possession split like a tug of war between home and away',
               'a head-to-head bar that slides towards whoever is winning'),
    related=('indeterminate-bar', 'gauge-needle-sweep', 'percentage-fill-bar', 'bar-chart-race',
             'audio-waveform-bars', 'vhs-tracking-bar'),
    api=('videobuilder.capabilities.broadcast.balance_bar_tug.draw_balance_bar',
         'videobuilder.capabilities.broadcast.balance_bar_tug.tug_share'),
    demo=lambda: demo.film(draw),
)
