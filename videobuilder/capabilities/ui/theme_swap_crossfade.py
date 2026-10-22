"""Theme Swap Crossfade: flipping between a dark and a light colour scheme,
every surface, line and piece of text slides smoothly from its old colour to
its new one instead of snapping."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

DARK = {'bg': '#1d1f24', 'surface': '#2a2d35', 'line': '#3a3e48', 'ink': '#eef0f3',
        'muted': '#8a909c', 'track': '#454a56', 'knob': '#f4f4f2'}
LIGHT = {'bg': '#eceef1', 'surface': '#ffffff', 'line': '#d4d8df', 'ink': '#16181d',
         'muted': '#6d7380', 'track': '#16181d', 'knob': '#ffffff'}


def mix_color(c0, c1, p):
    """The colour `p` (0 -> 1) of the way from `c0` to `c1`, as an (r, g, b, a)
    tuple of 0-255 channels and 0-1 alpha. Takes any colour `vb.rgba` does."""
    a, b = vb.rgba(c0), vb.rgba(c1)
    r, g, bl, al = (x + (y - x) * p for x, y in zip(a, b))
    return (255 * r, 255 * g, 255 * bl, al)


def theme_at(old, new, p, ease=vb.ease_in_out_quart):
    """The theme `p` (0 -> 1) of the way through a swap from `old` to `new`:
    a dict of the same role names (`'bg'`, `'ink'`, ...) with every colour
    eased together, so the whole scheme moves as one. Roles only in `new`
    appear at once; `ease` shapes the swap (pass `vb.linear` for a plain fade).

    In a film, draw every element from the returned dict, e.g.
    `t = theme_at(DARK, LIGHT, f / swap_frames); cv.fill(t['bg'])`."""
    e = ease(vb.clamp01(p))
    return {k: mix_color(old[k], c, e) if k in old else c for k, c in new.items()}


def _panel(cv, t, knob):
    """A settings card drawn in theme `t`, its toggle knob `knob` (0 -> 1) of the way across."""
    cx, cy, w, h = demo.W / 2, demo.H / 2 + 50, 460, 250
    x, y = cx - w / 2, cy - h / 2
    cv.shadow(x, y, w, h, radius=20, dy=12, blur=30, color=(0, 0, 0, 0.25))
    cv.rect(x, y, w, h, t['surface'], radius=20)
    cv.outline(x, y, w, h, t['line'], width=2, radius=20)
    cv.rect(x + 36, y + 40, 210, 16, t['ink'], radius=8)
    cv.rect(x + 36, y + 72, 300, 11, t['muted'], radius=5.5)
    cv.rect(x + 36, y + 94, 250, 11, t['muted'], radius=5.5)
    cv.line(x + 36, y + 136, x + w - 36, y + 136, t['line'], width=2)
    cv.rect(x + 36, y + 170, 140, 44, demo.ACCENT, radius=22)
    tw, th = 84, 44
    tx, ty = x + w - 36 - tw, y + 30
    cv.rect(tx, ty, tw, th, t['track'], radius=th / 2)
    kr = th / 2 - 5
    demo.dot(cv, tx + th / 2 + (tw - th) * vb.ease_out_quint(knob), ty + th / 2, kr, t['knob'])
    cv.mark('toggle', tx, ty, tw, th)
    cv.mark('card', x, y, w, h)


def draw(n, cv):
    knob = demo.phase(n, 0.9, 1.25)
    t = theme_at(DARK, LIGHT, demo.phase(n, 0.95, 1.95))
    cv.fill(t['bg'])
    demo.word(cv, 'Appearance', demo.W / 2, 110, size=64, color=t['ink'])
    _panel(cv, t, knob)


CAPABILITY = Capability(
    id='theme-swap-crossfade',
    name='Theme swap crossfade',
    family='ui',
    group='Theme',
    aliases=('dark mode fade', 'color scheme transition', 'light/dark mode transition'),
    definition='When the interface switches between dark and light mode, the background, cards and text '
               'all ease from their old colours to their new ones together rather than flipping instantly.',
    phrasings=('flip the toggle and have the whole screen fade from dark mode to light mode',
               'smoothly blend the UI colours when the theme changes',
               'animate the switch to dark mode instead of a hard cut'),
    related=('palette-shift-transition', 'typeface-crossfade', 'lyric-line-crossfade', 'cross-dissolve',
             'scroll-linked-background-shift', 'cross-processing'),
    api=('videobuilder.capabilities.ui.theme_swap_crossfade.theme_at',
         'videobuilder.capabilities.ui.theme_swap_crossfade.mix_color'),
    demo=lambda: demo.film(draw),
)
