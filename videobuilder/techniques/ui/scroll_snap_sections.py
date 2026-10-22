"""Scroll Snap Sections: a page dragged part of the way between two
full-height sections never stays there; on release it glides to the
nearest section boundary, onward or back."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def snap_scroll(t, gestures, count, drag_time=0.3, settle_time=0.55, ease=vb.ease_out_quint):
    """The scroll position at `t` seconds, in sections (0 = the first at the
    top; multiply by the section height for pixels). `gestures` are
    `(start, amount)` pairs in time order: from `start` the finger drags the
    page `amount` sections (signed) over `drag_time`, then lets go and the
    page eases to the nearest whole section over `settle_time`. A drag under
    half a section snaps back. The position stays within `count` sections."""
    pos = 0.0
    for start, amount in gestures:
        if t <= start:
            break
        dragged = pos + amount * vb.clamp01((t - start) / drag_time)
        target = min(max(round(pos + amount), 0), count - 1)
        released = start + drag_time
        if t <= released:
            return dragged
        if t < released + settle_time:
            return dragged + (target - dragged) * ease((t - released) / settle_time)
        pos = float(target)
    return pos


GESTURES = ((0.3, 0.62), (1.15, 0.3), (1.95, 0.7))   # onward, a short drag that springs back, onward
SECTIONS = 3
VW, VH = 600, 380                                    # the viewport
VX, VY = (demo.W - VW) / 2 - 20, (demo.H - VH) / 2 + 14
SHADES = ('#1c1e25', '#20232b', '#1a1c22')


def _section(cv, i, top):
    cv.rect(VX, top, VW, VH, SHADES[i])
    cx, cy = VX + VW / 2, top + VH / 2 - 30
    if i == 0:
        demo.dot(cv, cx, cy, 58, color=demo.ACCENT)
    elif i == 1:
        demo.card(cv, cx, cy, w=230, h=130, color=demo.TEAL)
    else:
        for k in (-1, 0, 1):
            cv.rect(cx + k * 56 - 16, cy - 50, 32, 100, '#e3b341', radius=16)
    demo.word(cv, f'Section {i + 1}', cx, top + VH - 70, size=26, color=demo.MUTED, weight=700)
    cv.line(VX, top, VX + VW, top, '#7c86ff', width=2)          # the boundary the page snaps to


def draw(n, cv):
    t = n / demo.FPS
    pos = snap_scroll(t, GESTURES, SECTIONS)
    bar = 34
    cv.shadow(VX, VY - bar, VW, VH + bar, radius=16, dy=12, blur=34, color=(0, 0, 0, 0.5))
    cv.rect(VX, VY - bar, VW, VH + bar, '#24262e', radius=16)
    demo.dot(cv, VX + 20, VY - bar / 2, 7, color='#e3b341')
    for k in range(3):
        cv.rect(VX + VW - 90 + k * 26, VY - bar / 2 - 2, 18, 4, demo.MUTED, radius=2)
    with cv.clip(VX, VY, VW, VH):
        for i in range(SECTIONS):
            top = VY + (i - pos) * VH
            if top < VY + VH and top + VH > VY:
                _section(cv, i, top)
    cv.mark('viewport', VX, VY, VW, VH)

    # a scrollbar with one tick per section, and the finger while it drags
    sx = VX + VW + 34
    cv.line(sx, VY, sx, VY + VH, demo.LINE, width=4)
    for i in range(SECTIONS):
        demo.dot(cv, sx, VY + (i + 0.5) * VH / SECTIONS, 4, color=demo.MUTED)
    thumb = VH / SECTIONS
    cv.rect(sx - 4, VY + pos * thumb, 8, thumb, '#7c86ff', radius=4)
    for start, amount in GESTURES:
        held = demo.phase(n, start - 0.08, start) * (1 - demo.phase(n, start + 0.3, start + 0.4))
        if held > 0:
            p = vb.clamp01((t - start) / 0.3)
            fy = VY + VH * 0.72 - amount * p * VH * 0.8
            demo.dot(cv, VX + VW * 0.78, fy, 22, color=demo.INK, alpha=0.35 * held)
            demo.dot(cv, VX + VW * 0.78, fy, 12, color=demo.INK, alpha=0.8 * held)


TECHNIQUE = Technique(
    id='scroll-snap-sections',
    name='Scroll snap sections',
    family='ui',
    group='Scroll',
    aliases=('snap points', 'paged scroll', 'scroll snapping'),
    definition='A page scrolled by hand never rests between its full-screen sections: when the finger lets go '
               'it eases to the nearest section edge, forward or back.',
    phrasings=('the page snaps to each section when you stop scrolling',
               'scroll one full panel at a time, like flipping pages',
               'a swipe that locks onto the next screen instead of stopping halfway'),
    related=('roll-up', 'timeline-scroll', 'scroll-driven-text-reveal', 'momentum-fling', 'news-ticker-crawl',
             'parallax-marquee-rows'),
    api=('videobuilder.techniques.ui.scroll_snap_sections.snap_scroll',),
    demo=lambda: demo.film(draw),
)
