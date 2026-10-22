"""Tab panel slide: when another tab is picked, the old panel content slides
out and fades while the new content slides in from the side of the tab that
was chosen, all inside the panel's own bounds."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def tab_panel_slide(cv, a, b, p, box, direction=1, travel=0.3, ease=ease_out_cubic):
    """Draw the panel change at progress `p` (0 -> 1), clipped to `box`
    (x, y, w, h, or a Box). `a(cv)` is the outgoing content, `b(cv)` the
    incoming, each drawn where it sits at rest. `direction` is +1 when the new
    tab is to the right of the old one (new content enters from the right,
    old leaves left) and -1 when it is to the left. Each panel moves
    `travel` of the box's width and cross-fades on the way.

    In a film, call it over the frames of the switch, e.g.
    `tab_panel_slide(cv, draw_overview, draw_activity, f / switch_frames, panel, direction=+1)`;
    `direction` is `copysign(1, new_index - old_index)`."""
    x, y, w, h = box
    e = ease(vb.clamp01(p))
    shift = direction * travel * w
    with cv.clip(x, y, w, h):
        with cv.layer(opacity=1 - e, dx=-shift * e):
            a(cv)
        with cv.layer(opacity=e, dx=shift * (1 - e)):
            b(cv)


# ---- the demo: a small app window with two tabs, switched over and back ----

WIN = vb.Box(150, 70, 660, 400)
TABS = ('Overview', 'Activity')
TAB_Y, TAB_H = WIN.y + 46, 44
TAB_W = (WIN.w - 48 - 12) / 2
PANEL = vb.Box(WIN.x + 24, TAB_Y + TAB_H + 16, WIN.w - 48, WIN.h - (TAB_Y - WIN.y) - TAB_H - 40)
SWITCHES = ((0.5, 1.3, 0, 1), (1.8, 2.6, 1, 0))  # (start s, end s, from tab, to tab)


def tab_x(i):
    return WIN.x + 24 + i * (TAB_W + 12)


def overview(cv):
    x, y, w, h = PANEL
    demo.dot(cv, x + 120, y + h / 2, r=70, color=demo.ACCENT, alpha=0.9)
    demo.dot(cv, x + 120, y + h / 2, r=48, color='#1d1f26')
    cv.rect(x + 240, y + 48, 240, 18, demo.INK, radius=9)
    cv.rect(x + 240, y + 84, 300, 12, demo.MUTED, radius=6, alpha=0.6)
    cv.rect(x + 240, y + 106, 220, 12, demo.MUTED, radius=6, alpha=0.6)
    cv.rect(x + 240, y + h - 82, 120, 38, demo.ACCENT, radius=10)


def activity(cv):
    x, y, w, h = PANEL
    base = y + h * 0.58
    for i, v in enumerate((0.35, 0.6, 0.45, 0.85, 0.7, 0.95)):
        bh = v * h * 0.44
        cv.rect(x + 48 + i * 92, base - bh, 56, bh, demo.TEAL, radius=8)
    for i in range(3):
        cx = x + 24 + i * (w - 48 + 16) / 3
        cv.rect(cx, base + 22, (w - 48 - 32) / 3, h - (base - y) - 46, demo.LINE, radius=10)


def draw(n, cv):
    t = n / demo.FPS
    cv.shadow(*WIN, radius=18, dy=12, blur=36, color=(0, 0, 0, 0.5))
    cv.rect(*WIN, '#191b21', radius=18)
    for i, c in enumerate((demo.ACCENT, '#e8b44c', demo.TEAL)):
        demo.dot(cv, WIN.x + 26 + i * 20, WIN.y + 24, r=6, color=c)

    # which tab is current, and how far through a switch we are
    sel, p, frm, to = 0, 1.0, 0, 0
    for s, e, a, b in SWITCHES:
        if t >= s:
            sel, frm, to, p = b, a, b, demo.phase(n, s, e)
    pe = ease_out_cubic(p)

    f = demo.font(22, 700)
    for i, label in enumerate(TABS):
        on = (i == to) * pe + (i == frm) * (1 - pe) if frm != to else float(i == sel)
        cv.rect(tab_x(i), TAB_Y, TAB_W, TAB_H, '#20232b', radius=10)
        demo.word(cv, label, tab_x(i) + TAB_W / 2, TAB_Y + TAB_H / 2, size=22,
                  color=demo.INK, font=f, alpha=0.45 + 0.55 * on)
    ux = tab_x(frm) + (tab_x(to) - tab_x(frm)) * pe
    cv.rect(ux + 16, TAB_Y + TAB_H - 4, TAB_W - 32, 4, demo.ACCENT, radius=2)

    cv.rect(*PANEL, '#1d1f26', radius=14)
    panels = (overview, activity)
    if frm == to or p >= 1:
        panels[sel](cv)
    else:
        tab_panel_slide(cv, panels[frm], panels[to], p, PANEL, direction=1 if to > frm else -1)
    cv.mark('panel', *PANEL)


TECHNIQUE = Technique(
    id='tab-panel-slide',
    name='Tab panel slide',
    family='ui',
    group='Page transitions',
    aliases=('tab content transition', 'panel crossfade', 'tab swipe'),
    definition='Picking a different tab pushes the current panel out sideways as it fades, while the new '
               'panel glides in from the side of the tab that was chosen.',
    phrasings=('when I click the next tab, slide its content in from the right',
               'animate switching tabs so the panels swipe sideways',
               'the old tab content slides away and the new one comes in'),
    related=('tab-underline-slide', 'bottom-sheet-slide-up', 'view-transition', 'split-screen-transition',
             'image-crossfade-slideshow', 'lower-third-slide-in-bar'),
    api=('videobuilder.techniques.ui.tab_panel_slide.tab_panel_slide',),
    demo=lambda: demo.film(draw),
)
