"""Circular clip reveal: a new screen opens out of the control that was
pressed, a circle centred on it growing until the new screen fills the view,
as when a light/dark theme toggle floods the page with the other theme."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

GROW = vb.bezier(0.4, 0.0, 0.2, 1.0)


def reach(cv, cx, cy):
    """The radius a circle centred at (cx, cy) needs to cover the whole
    canvas: the distance to its farthest corner."""
    return max(math.hypot(x - cx, y - cy) for x in (0, cv.width) for y in (0, cv.height))


def circular_reveal(cv, a, b, p, center=None, r0=0.0, ease=GROW):
    """Draw `b(cv)` opening over `a(cv)` through a circle at progress `p`
    (0 -> 1). The circle is centred on `center` (x, y) -- the trigger, e.g. the
    button that was pressed; default the frame's centre -- and grows from
    radius `r0` to just past the farthest corner, eased by `ease`.

    In a film, call it while two shots are live in an overlap, e.g.
    `circular_reveal(cv, dark_page, light_page, f / overlap_frames, center=toggle.center)`."""
    cx, cy = center if center is not None else (cv.width / 2, cv.height / 2)
    p = vb.clamp01(p)
    a(cv)
    if p <= 0:
        return
    r = r0 + (reach(cv, cx, cy) + 2 - r0) * ease(p)
    ctx = cv.ctx
    ctx.save()
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.clip()
    b(cv)
    ctx.restore()


# ---- demo: a dark page, a theme toggle is clicked, the light page opens out of it ----

BTN = (demo.W - 80, 66)   # the toggle's centre
BTN_R = 24


def _page(cv, bg, ink, panel, accent, icon):
    cv.fill(bg)
    cv.rect(0, 0, demo.W, 132, panel)
    demo.word(cv, 'Dashboard', 170, 66, size=36, color=ink)
    for i, c in enumerate((accent, panel, panel)):
        demo.card(cv, 190 + i * 290, 290, w=240, h=150, color=c)
    cv.rect(70, 420, demo.W - 140, 14, panel, radius=7)
    cv.rect(70, 452, (demo.W - 140) * 0.6, 14, panel, radius=7)
    x, y = BTN
    demo.dot(cv, x, y, BTN_R, accent)
    icon(cv, x, y)


def _moon(cv, x, y):
    demo.dot(cv, x, y, 11, demo.INK)
    demo.dot(cv, x + 5, y - 4, 9, demo.ACCENT)


def _sun(cv, x, y):
    demo.dot(cv, x, y, 7, '#1d1f24')
    for k in range(8):
        t = k * math.pi / 4
        cv.line(x + 11 * math.cos(t), y + 11 * math.sin(t), x + 16 * math.cos(t), y + 16 * math.sin(t),
                '#1d1f24', width=3)


def dark(cv):
    _page(cv, demo.BG, demo.INK, '#2a2d34', demo.ACCENT, _moon)


def light(cv):
    _page(cv, '#ece8df', '#1d1f24', '#d6d1c6', demo.TEAL, _sun)


def _cursor(cv, x, y, s=1.0):
    pts = [(0, 0), (0, 23), (6, 17.5), (10.5, 27.5), (14.5, 25.5), (10, 16), (18, 16)]
    ctx = cv.ctx
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(*pts[0])
    for pt in pts[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba('#ffffff'))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba('#000000'))
    ctx.set_line_width(1.5)
    ctx.stroke()
    ctx.restore()


def draw(n, cv):
    move = vb.ease_in_out_quart(demo.phase(n, 0.15, 0.75))
    press = demo.phase(n, 0.75, 0.85) - demo.phase(n, 0.85, 0.95)
    circular_reveal(cv, dark, light, demo.phase(n, 0.85, 2.15), center=BTN, r0=BTN_R)
    x0, y0 = demo.W * 0.55, demo.H * 0.7
    _cursor(cv, x0 + (BTN[0] + 3 - x0) * move, y0 + (BTN[1] + 2 - y0) * move, 1 - 0.15 * press)
    cv.mark('toggle', BTN[0] - BTN_R, BTN[1] - BTN_R, 2 * BTN_R, 2 * BTN_R)


TECHNIQUE = Technique(
    id='circular-clip-reveal',
    name='Circular clip reveal',
    family='ui',
    group='Overlays & menus',
    aliases=('circle reveal', 'iris reveal', 'clip-path circle reveal', 'radial theme transition',
             'theme iris wipe'),
    definition='Pressing a control makes the next screen open out of it as a growing circle, '
               'which spreads from that spot until the new screen covers the whole view.',
    phrasings=('when I tap the dark-mode button, have the new theme spread out from it in a circle',
               'the next page should grow out of the button as an expanding circle',
               'a round reveal that starts at the click and fills the screen'),
    related=('iris-wipe', 'star-wipe', 'spiral-wipe', 'corner-wipe', 'scroll-linked-clip-reveal',
             'zoom-out-reveal'),
    api=('videobuilder.techniques.ui.circular_clip_reveal.circular_reveal',
         'videobuilder.techniques.ui.circular_clip_reveal.reach'),
    demo=lambda: demo.film(draw),
)
