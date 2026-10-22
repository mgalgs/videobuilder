"""Sidebar collapse width: a navigation sidebar narrows from full labels to a
slim rail of icons, the labels fading out as the edge passes them, while the
content beside it widens to take the freed space."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def sidebar_width(p, expanded=220, collapsed=64, ease=vb.ease_in_out_quart):
    """The sidebar's width at collapse progress `p` (0 = `expanded`, 1 = `collapsed`).
    Run `p` backwards (1 -> 0) to expand it again."""
    return expanded + (collapsed - expanded) * ease(vb.clamp01(p))


def draw_sidebar(cv, x, y, h, width, items, expanded=220, collapsed=64, active=0,
                 color='#1e2027', ink=demo.INK, muted=demo.MUTED, accent=demo.ACCENT, font=None):
    """Draw a sidebar `width` wide at (x, y), `h` tall, sized between `collapsed`
    and `expanded`. `items` are labels; each row keeps its icon fixed in the
    rail while its label is clipped by the moving edge and fades as the
    sidebar closes. Row `active` gets the `accent` highlight. Returns the
    sidebar's Box, so the content beside it can start at its right edge."""
    open_ = vb.clamp01((width - collapsed) / max(1, expanded - collapsed))
    f = font or demo.font(19, 600)
    rail = collapsed / 2
    with cv.clip(x, y, width, h):
        cv.rect(x, y, width, h, color)
        # the brand row: a mark that stays, a wordmark that goes
        demo.dot(cv, x + rail, y + 40, r=13, color=accent)
        vb.text.draw(cv, ['Workspace'], demo.font(21, 800), x + collapsed - 2, y + 27, ink, alpha=open_)
        for i, label in enumerate(items):
            ry = y + 100 + i * 52
            if i == active:
                pad = 9
                cv.rect(x + pad, ry - 19, width - 2 * pad, 38, accent, radius=9, alpha=0.22)
            c = accent if i == active else muted
            cv.rect(x + rail - 10, ry - 10, 20, 20, c, radius=5, alpha=0.9)
            vb.text.draw(cv, [label], f, x + collapsed - 2, ry - 13, ink if i == active else muted,
                         alpha=open_ ** 1.5)
        # the toggle: a chevron at the foot that flips as the sidebar closes
        cx, cy, s = x + width - rail, y + h - 36, 8
        k = math.cos(math.pi * (1 - open_)) * s * 0.6   # points left when open, right when closed
        cv.line(cx - k, cy, cx + k, cy - s, muted, width=3)
        cv.line(cx - k, cy, cx + k, cy + s, muted, width=3)
    cv.line(x + width, y, x + width, y + h, demo.LINE, width=2)
    cv.mark('sidebar', x, y, width, h)
    return vb.Box(x, y, width, h)


def draw(n, cv):
    t = demo.phase(n, 0.5, 1.3) - demo.phase(n, 2.0, 2.8)   # collapse, hold, expand back
    x, y, w, h = 60, 45, demo.W - 120, demo.H - 90
    with cv.clip(x, y, w, h, radius=16):
        cv.rect(x, y, w, h, '#181a20')
        side = draw_sidebar(cv, x, y, h, sidebar_width(t), ['Home', 'Projects', 'Messages', 'Reports', 'Settings'],
                            active=1)
        # the content reflows into whatever the sidebar leaves
        left = side.x + side.w + 32
        right = x + w - 32
        cv.rect(left, y + 30, (right - left) * 0.45, 26, demo.INK, radius=7, alpha=0.9)
        cols, gap = 3, 18
        cw = (right - left - gap * (cols - 1)) / cols
        for i in range(6):
            cx = left + (i % cols) * (cw + gap)
            cy = y + 84 + (i // cols) * 172
            cv.rect(cx, cy, cw, 156, '#23262e', radius=12)
            cv.rect(cx + 16, cy + 18, cw * 0.55, 12, demo.TEAL if i == 0 else demo.MUTED, radius=6, alpha=0.8)
            cv.rect(cx + 16, cy + 40, cw * 0.35, 9, demo.MUTED, radius=4, alpha=0.5)
    cv.outline(x, y, w, h, demo.LINE, width=2, radius=16)


CAPABILITY = Capability(
    id='sidebar-collapse-width',
    name='Sidebar collapse width',
    family='ui',
    group='Overlays & menus',
    aliases=('collapsible sidebar', 'nav rail collapse', 'mini sidebar', 'drawer shrink'),
    definition='A side navigation panel slides narrower until only its icons remain, its labels fading away, '
               'while the main content stretches to fill the gap.',
    phrasings=('shrink the side menu down to just the icons',
               'collapse the left nav so the page gets wider',
               'the sidebar folds into a thin icon strip and opens back up'),
    related=('split-screen-comparison', 'plus-to-close-rotate', 'hamburger-to-x', 'split-screen-transition',
             'toggle-switch-slide', 'crt-power-off-collapse'),
    api=('videobuilder.capabilities.ui.sidebar_collapse_width.draw_sidebar',
         'videobuilder.capabilities.ui.sidebar_collapse_width.sidebar_width'),
    demo=lambda: demo.film(draw),
)
