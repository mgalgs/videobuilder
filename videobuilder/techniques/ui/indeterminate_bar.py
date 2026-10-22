"""Indeterminate bar: a progress track with no known amount, so a coloured
segment keeps racing across it, stretching and shrinking as it goes, then
starts again from the left -- "working on it" with no percentage."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def indeterminate_segments(t, period=1.6, segments=2, lead=0.2):
    """The lit stretches of an indeterminate bar at `t` seconds, as
    `(start, end)` fractions of the track, clamped to 0..1 and empty ones
    dropped. Each of `segments` runs one `period`, staggered evenly: its head
    sweeps left to right on an ease-in-out, and its tail follows the same
    curve `lead` of a period later, so the segment stretches mid-track and
    shrinks as it leaves on the right. Loops seamlessly."""
    out = []
    for i in range(segments):
        u = (t / period + i / segments) % 1.0
        head = vb.ease_in_out_quart(vb.clamp01(u / (1 - lead)))
        tail = vb.ease_in_out_quart(vb.clamp01((u - lead) / (1 - lead)))
        a, b = vb.clamp01(tail), vb.clamp01(head)
        if b - a > 1e-4:
            out.append((a, b))
    return out


def draw_indeterminate_bar(cv, x, y, w, h, t, color, track=None, track_alpha=0.25, **kw):
    """Draw an indeterminate bar `w` x `h` with its top-left at (x, y), at
    `t` seconds: a rounded track (`track` colour, default `color` faint) and
    the moving segments of `indeterminate_segments` (`kw` goes there),
    clipped to the track's rounded ends. Returns the bar's Box."""
    r = h / 2
    cv.rect(x, y, w, h, track or color, radius=r, alpha=track_alpha if track is None else 1.0)
    with cv.clip(x, y, w, h, radius=r):
        for a, b in indeterminate_segments(t, **kw):
            cv.rect(x + a * w, y, (b - a) * w, h, color, radius=r)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    bw, bh = demo.W * 0.6, demo.H * 0.022
    x, y = (demo.W - bw) / 2, demo.H * 0.53
    demo.word(cv, 'Loading', demo.W / 2, demo.H * 0.42, size=round(demo.H * 0.07), color=demo.MUTED, weight=700)
    box = draw_indeterminate_bar(cv, x, y, bw, bh, n / demo.FPS, demo.ACCENT)
    cv.mark('bar', *box)


TECHNIQUE = Technique(
    id='indeterminate-bar',
    name='Indeterminate bar',
    family='ui',
    group='Loaders',
    aliases=('indeterminate progress bar', 'linear loader', 'busy bar', 'progress shuttle'),
    definition='A thin progress track where a coloured segment keeps sweeping from left to right, '
               'growing and shrinking as it travels, to show work going on without a known amount.',
    phrasings=('a loading bar that just keeps sliding across because we do not know how long it will take',
               'a progress line with a stripe racing along it over and over',
               'the endless loading strip under the header while something is busy'),
    related=('tab-underline-slide', 'balance-bar-tug', 'vhs-tracking-bar', 'refresh-bar',
             'percentage-fill-bar', 'scroll-progress-bar'),
    api=('videobuilder.techniques.ui.indeterminate_bar.draw_indeterminate_bar',
         'videobuilder.techniques.ui.indeterminate_bar.indeterminate_segments'),
    demo=lambda: demo.film(draw),
)
