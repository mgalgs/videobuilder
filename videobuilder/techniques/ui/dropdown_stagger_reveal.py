"""Dropdown Stagger Reveal: a menu panel unrolls down from its trigger and
its items drop in one after another, each sliding a little and fading up."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def stagger(i, n, p, spread=0.5):
    """Progress 0 -> 1 of item `i` of `n` at overall progress `p`: each item
    runs for `1 - spread` of the whole, the starts spaced evenly across the
    first `spread`, so the first starts at 0 and the last finishes at 1."""
    span = 1 - spread
    start = spread * i / max(1, n - 1)
    return vb.clamp01((p - start) / span)


def draw_dropdown(cv, x, y, w, items, font, p, row=56, pad=10, color=demo.LINE, ink=demo.INK,
                  panel=0.35, drop=18, ease=vb.ease_out_quint, active=None, accent=demo.ACCENT):
    """Draw a dropdown panel hanging from (x, y) at progress `p` (0 closed,
    1 open). The panel's height unrolls over the first `panel` of the
    reveal; the rows in `items` follow staggered over the rest, each easing
    down `drop` px into place while fading in. `active` (an index) draws
    that row highlighted in `accent`. Returns the Box of the open panel."""
    h_full = pad * 2 + row * len(items)
    if p <= 0:
        return vb.Box(x, y, w, h_full)
    h = h_full * ease(vb.clamp01(p / panel))
    cv.shadow(x, y, w, h, radius=14, dy=12, blur=30, color=(0, 0, 0, 0.5))
    cv.rect(x, y, w, h, color, radius=14)
    rest = vb.clamp01((p - panel * 0.4) / (1 - panel * 0.4))
    with cv.clip(x, y, w, h, radius=14):
        for i, label in enumerate(items):
            q = ease(stagger(i, len(items), rest))
            if q <= 0:
                continue
            ry = y + pad + row * i - drop * (1 - q)
            with cv.layer(opacity=q):
                if i == active:
                    cv.rect(x + 8, ry + 4, w - 16, row - 8, accent, radius=9)
                tw, th = vb.text.block_size([label], font)
                vb.text.draw(cv, [label], font, x + 28, ry + (row - th) / 2, ink)
    cv.mark('dropdown', x, y, w, h)
    return vb.Box(x, y, w, h_full)


ITEMS = ('Profile', 'Projects', 'Billing', 'Settings', 'Sign out')


def draw(n, cv):
    w, bx, by = 300, demo.W / 2 - 150, 70
    press = demo.phase(n, 0.4, 0.55)
    cv.rect(bx, by, w, 60, demo.TEAL if press > 0 else demo.LINE, radius=14)
    f = demo.font(26, 700)
    vb.text.draw(cv, ['Account'], f, bx + 28, by + 14, demo.BG if press > 0 else demo.INK)
    cx, cy = bx + w - 36, by + 30
    flip = vb.ease_out_quint(press)
    cv.line(cx - 8, cy - 4 * (1 - 2 * flip), cx, cy + 4 * (1 - 2 * flip), demo.BG if press > 0 else demo.INK, width=3)
    cv.line(cx, cy + 4 * (1 - 2 * flip), cx + 8, cy - 4 * (1 - 2 * flip), demo.BG if press > 0 else demo.INK, width=3)
    cv.mark('button', bx, by, w, 60)
    active = 1 if n / demo.FPS > 2.3 else None
    draw_dropdown(cv, bx, by + 72, w, ITEMS, demo.font(24, 600), demo.phase(n, 0.5, 1.9), active=active)


TECHNIQUE = Technique(
    id='dropdown-stagger-reveal',
    name='Dropdown stagger reveal',
    family='ui',
    group='Overlays & menus',
    aliases=('staggered dropdown', 'cascading menu reveal', 'menu item stagger'),
    definition='A menu opens downward from its button, the panel growing first and then each option '
               'sliding and fading into place a beat after the one above it.',
    phrasings=('when the menu opens, have the options drop in one by one',
               'animate the dropdown so its items cascade in instead of appearing at once',
               'the list unfolds under the button with each row arriving slightly later'),
    related=('staggered-cascade-reveal', 'fade-up-scroll-reveal', 'linear-stagger', 'edge-in-stagger',
             'center-out-stagger', 'hamburger-to-x'),
    api=('videobuilder.techniques.ui.dropdown_stagger_reveal.draw_dropdown',
         'videobuilder.techniques.ui.dropdown_stagger_reveal.stagger'),
    demo=lambda: demo.film(draw),
)
