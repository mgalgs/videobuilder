"""Loading State Morph: a pressed button squeezes in from both sides into a
circle, a spinner turns inside it while the work runs, then it widens back
out into a finished label."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

CURSOR = ((0, 0), (0, 27), (7, 21), (12, 32), (17.5, 29.5), (12.5, 19), (21, 19))


def morph_state(t, press, finish, morph=0.4):
    """The button's state at time `t` (seconds, or any one unit) as
    `(shrink, done)`: `shrink` eases 0 -> 1 over `morph` after `press` (full
    button to circle), holds at 1, then eases back to 0 over `morph` after
    `finish`; `done` is true from `finish` on, so the widening button shows
    its finished label."""
    if t < finish:
        return vb.ease_in_out_quart(vb.clamp01((t - press) / morph)), False
    return 1 - vb.ease_out_quint(vb.clamp01((t - finish) / morph)), True


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _oklch(color):
    r, g, b = (_lin(c) for c in vb.rgba(color)[:3])
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(A, B), math.atan2(B, A)


def _mix(a, b, p):
    """`a` -> `b` at `p` through OKLCH (lightness, chroma, short way round the
    hue), so the blend stays saturated instead of passing through grey."""
    (la, ca, ha), (lb, cb, hb) = _oklch(a), _oklch(b)
    dh = (hb - ha + math.pi) % (2 * math.pi) - math.pi
    L, C, H = la + (lb - la) * p, ca + (cb - ca) * p, ha + dh * p
    A, B = C * math.cos(H), C * math.sin(H)
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    rgb = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960350 * l - 0.7034186147 * m + 1.7076146010 * s)
    return tuple(round(255 * _gam(c)) for c in rgb)


def _check(cv, x, y, s, color, alpha):
    pts = [(x, y + 0.05 * s), (x + 0.35 * s, y + 0.4 * s), (x + s, y - 0.3 * s)]
    vb.paths.draw(cv, pts, color, width=max(2.0, s * 0.16), alpha=alpha)


def draw_loading_morph(cv, cx, cy, shrink, label, done=False, done_label=None, spin=0.0, w=380, h=104,
                       color=demo.ACCENT, done_color=demo.TEAL, ink=demo.INK, font=None):
    """Draw the button centred at (cx, cy) at morph amount `shrink` (0: the
    full `w` x `h` pill with its label; 1: an `h`-wide circle with a spinner
    turned to `spin` radians). With `done`, the label is `done_label` behind a
    tick and the fill is `done_color` -- feed it `morph_state` so the button
    collapses on the press and widens into the result. Returns the Box."""
    s = vb.clamp01(shrink)
    bw = w - (w - h) * s
    x, y = cx - bw / 2, cy - h / 2
    # The done colour comes in over the first half of the widening, while the button is still small.
    fill = _mix(color, done_color, vb.clamp01((1 - s) / 0.5)) if done else color
    cv.shadow(x, y, bw, h, radius=h / 2, dy=8, blur=24, color=(0, 0, 0, 0.4))
    cv.rect(x, y, bw, h, fill, radius=h / 2)
    # The label goes in the first part of the squeeze and comes back early in the widening.
    text_a = vb.clamp01(1 - s / (0.6 if done else 0.35))
    if text_a > 0:
        f = font or demo.font(round(h * 0.36), 800)
        text = (done_label or label) if done else label
        tw, th = vb.text.block_size([text], f)
        with cv.clip(x, y, bw, h, radius=h / 2):
            if done:
                cs = th * 0.62
                gap = cs * 0.6
                left = cx - (tw + cs + gap) / 2
                _check(cv, left, cy, cs, ink, text_a)
                vb.text.draw(cv, [text], f, left + cs + gap, cy - th / 2, ink, alpha=text_a)
            else:
                vb.text.draw(cv, [text], f, cx - tw / 2, cy - th / 2, ink, alpha=text_a)
    # The spinner fades in once the button is (nearly) round.
    spin_a = vb.clamp01((s - 0.7) / 0.3)
    if spin_a > 0:
        r = h * 0.28
        cv.arc(cx, cy, r, 0, 2 * math.pi, ink, width=h * 0.09, alpha=0.3 * spin_a)
        cv.arc(cx, cy, r, spin, spin + 1.6 * math.pi * (0.35 + 0.25 * math.sin(spin * 0.7)), ink,
               width=h * 0.09, alpha=spin_a)
    return vb.Box(x, y, bw, h)


def _cursor(cv, x, y, scale=1.6, alpha=1.0):
    pts = [(x + px * scale, y + py * scale) for px, py in CURSOR]
    with cv.layer(opacity=alpha):
        cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
        vb.paths.draw(cv, pts, demo.INK, fill=True)
        vb.paths.draw(cv, pts, demo.BG, width=2, closed=True)


# The button is round by ~1.05 s, spins until 1.65 s and has settled as 'Sent' by ~2 s, before the 70% poster.
PRESS, FINISH = 0.6, 1.65


def draw(n, cv):
    t = n / demo.FPS
    cx, cy = demo.W / 2, demo.H / 2
    shrink, done = morph_state(t, PRESS, FINISH, morph=0.45)
    # A quick press-in as the cursor clicks.
    tap = math.sin(math.pi * vb.clamp01((t - PRESS + 0.08) / 0.16))
    h = 128 * (1 - 0.06 * tap)
    box = draw_loading_morph(cv, cx, cy, shrink, 'Submit', done=done, done_label='Sent',
                             spin=(t - PRESS) * 2 * math.pi * 1.3, w=480 * (1 - 0.03 * tap), h=h)
    cv.mark('button', *box)
    # The cursor glides in, clicks, then drifts aside.
    arrive = vb.ease_out_expo(demo.phase(n, 0.1, PRESS - 0.05))
    leave = vb.ease_in_out_quart(demo.phase(n, PRESS + 0.3, PRESS + 1.0))
    px = cx + 560 + (140 - 560) * arrive + 170 * leave
    py = cy + 300 + (30 - 300) * arrive + 90 * leave
    _cursor(cv, px, py, alpha=1 - 0.6 * leave)


CAPABILITY = Capability(
    id='loading-state-morph',
    name='Loading state morph',
    family='ui',
    group='Buttons',
    aliases=('button to spinner', 'submit morph', 'loading button'),
    definition='A clicked button pinches in from both ends into a round spinner while it works, '
               'then stretches back out into a button that shows the result.',
    phrasings=('the submit button turns into a spinner and then says it is done',
               'when you click send the button shrinks to a loading circle and opens back up',
               'button collapses into a loader, then expands with a check mark'),
    related=('loading-to-success-morph', 'icon-state-morph', 'shape-morph-loader', 'spinner-ring',
             'play-pause-morph', 'cursor-state-change'),
    api=('videobuilder.capabilities.ui.loading_state_morph.draw_loading_morph',
         'videobuilder.capabilities.ui.loading_state_morph.morph_state'),
    demo=lambda: demo.film(draw),
)
