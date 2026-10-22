"""Split-screen comparison: two panels slide in from opposite edges of the
frame and settle side by side, a divider drawing down between them, so two
options, products or states can be read against each other."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def split_screen_comparison(cv, left, right, p, split=0.5, lag=0.15, gap=8, color='#000000',
                            ease=vb.ease_out_quint):
    """Draw the comparison at progress `p` (0 -> 1): `left(cv)` slides in
    from the left edge and `right(cv)` from the right, `right` starting
    `lag` of the way later, until the frame is divided at `split` of its
    width. Each panel shows its scene centred in it. A `gap`-wide bar of
    `color` then grows down the seam over the last stretch. At `p >= 1` the
    split simply holds, so a film keeps calling it with 1 for as long as
    the comparison stays up.

    In a film, e.g. `split_screen_comparison(cv, lambda c: plan(c, 'Basic'),
    lambda c: plan(c, 'Pro'), shot.f / intro_frames)`."""
    w, h = cv.width, cv.height
    x = w * split
    span = 1 - lag
    pl = ease(vb.clamp01(p / span))
    pr = ease(vb.clamp01((p - lag) / span))
    if pl > 0:
        off = -x * (1 - pl)
        with cv.clip(0, 0, x + off, h), cv.layer(dx=x / 2 - w / 2 + off):
            left(cv)
    if pr > 0:
        off = (w - x) * (1 - pr)
        with cv.clip(x + off, 0, w - x - off, h), cv.layer(dx=x / 2 + off):
            right(cv)
    g = ease(vb.clamp01((p - 0.7) / 0.3))
    if g > 0 and gap > 0:
        cv.rect(x - gap / 2, h / 2 * (1 - g), gap, h * g, color)


def _panel(title, fill, card, ink, ratio):
    def draw(cv):
        cv.fill(fill)
        demo.word(cv, title, demo.W / 2, demo.H * 0.24, size=64, color=ink)
        demo.card(cv, demo.W / 2, demo.H * 0.52, w=300 * ratio, h=190 * ratio, color=card)
        demo.word(cv, f'{round(ratio * 100)}%', demo.W / 2, demo.H * 0.8, size=56, color=ink, weight=700)
    return draw


_A = _panel('Option A', '#2b3a55', demo.ACCENT, demo.INK, 0.8)
_B = _panel('Option B', '#e9e6df', demo.TEAL, demo.BG, 1.2)


def _draw(n, cv):
    p = demo.phase(n, 0.3, 1.9)
    split_screen_comparison(cv, _A, _B, p, gap=14, color=demo.BG)


TECHNIQUE = Technique(
    id='split-screen-comparison',
    name='Split-screen comparison',
    family='broadcast',
    group='Comparisons',
    aliases=('side-by-side reveal', 'two-panel compare', 'versus split'),
    definition='Two halves of the picture slide in from either side and meet in the middle, '
               'putting two things next to each other so they can be compared.',
    phrasings=('show the two options next to each other on a split screen',
               'slide in a left and a right panel so we can compare them',
               'put the old one and the new one side by side'),
    related=('split-screen-transition', 'curtain-reveal', 'shutter-wipe', 'split-flap-display',
             'barn-door-wipe', 'sidebar-collapse-width'),
    api=('videobuilder.techniques.broadcast.split_screen_comparison.split_screen_comparison',),
    demo=lambda: demo.film(_draw),
)
