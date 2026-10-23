"""Press depress: a raised button sinks into its base while a pointer holds it
down, its drop shadow tightening to almost nothing, then springs back up when
let go."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

CURSOR = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (26, 24)]  # an arrow pointer, tip at (0, 0)


def press_depth(t, down, up, sink=0.07, ratio=0.35, hz=4.0):
    """How far a button is pushed in at `t` seconds: 0 at rest, 1 fully down.
    It goes down over `sink` seconds from `down`, holds, and from `up` springs
    back (damping `ratio`, `hz` cycles/s), overshooting a little above rest
    before it settles."""
    if t < down:
        return 0.0
    if t < up:
        return vb.ease_out_quint(vb.clamp01((t - down) / sink))
    held = vb.ease_out_quint(vb.clamp01((up - down) / sink))  # released before it bottomed out
    return held * (1 - vb.spring(t - up, **vb.damped(ratio, hz=hz)))


def draw_press_button(cv, cx, cy, w, h, depth, color=demo.ACCENT, base=None, label=None, ink=demo.INK,
                      font=None, lift=24, radius=None, dim=0.12):
    """A raised button whose base sits centred at (cx, cy), pushed in by
    `depth` (0 up, 1 flush; a little below 0 lifts it past rest). The face
    rides `lift` px above a darker base; pressing slides it down onto the
    base, shrinks the drop shadow's offset and blur, and dims the face by up
    to `dim` toward black. Returns the face's Box."""
    radius = h / 2 if radius is None else radius
    base = base or _darker(color)
    rise = lift * (1 - depth)
    x, y = cx - w / 2, cy - h / 2
    fy = y - rise
    up = max(0.0, 1 - depth)
    cv.shadow(x, y, w, h, radius=radius, dy=4 + 22 * up, blur=6 + 30 * up, color=(0, 0, 0, 0.3 + 0.4 * up))
    cv.rect(x, y, w, h, base, radius=radius)
    cv.rect(x, fy, w, h, color, radius=radius)
    if dim and depth > 0:
        cv.rect(x, fy, w, h, '#000000', radius=radius, alpha=dim * min(1.0, depth))
    if label:
        f = font or demo.font(round(h * 0.38), 800)
        lw, lh = vb.text.block_size([label], f)
        vb.text.draw(cv, [label], f, cx - lw / 2, fy + (h - lh) / 2, ink)
    return vb.Box(x, fy, w, h)


def _darker(color, k=0.62):
    r, g, b, a = vb.rgba(color)  # 0-1 floats; a tuple colour wants 0-255 channels back
    return (round(255 * r * k), round(255 * g * k), round(255 * b * k), a)


def _cursor(cv, x, y, s=1.6):
    pts = [(x + px * s, y + py * s) for px, py in CURSOR]
    cv.shape_shadow(pts, dx=2, dy=4, blur=6, color=(0, 0, 0, 0.45))
    ctx = cv.ctx
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(*vb.rgba(demo.INK))
    ctx.fill_preserve()
    ctx.set_source_rgba(*vb.rgba(demo.BG))
    ctx.set_line_width(2)
    ctx.stroke()


def draw(n, cv):
    t = n / demo.FPS
    cx, cy, w, h = demo.W / 2, demo.H / 2 + 20, 420, 130
    depth = press_depth(t, 1.0, 1.7)
    # A lighter panel under the button, so its shadow has something to darken.
    cv.rect(cx - w / 2 - 150, cy - h / 2 - 120, w + 300, h + 220, demo.LINE, radius=36)
    face = draw_press_button(cv, cx, cy, w, h, depth, label='Press')
    cv.mark('button', *face)
    # The pointer glides onto the button, rides down with it, and drifts off after release.
    tx, ty = cx + w * 0.22, cy + h * 0.1
    arrive = vb.interpolate(t, [0.2, 0.9], [0, 1], ease=vb.ease_out_expo)
    leave = vb.interpolate(t, [2.2, 2.8], [0, 1], ease=vb.ease_in_out_quart)
    px = tx + 340 * (1 - arrive) + 160 * leave
    py = ty + 260 * (1 - arrive) + 120 * leave + 24 * depth
    with cv.layer(opacity=1 - leave):
        _cursor(cv, px, py)


CAPABILITY = Capability(
    id='press-depress',
    name='Press depress',
    family='ui',
    group='Buttons',
    aliases=('active press', 'tactile press', 'button press', 'pressed state'),
    definition='A raised button sinks down into its base as it is pushed, its shadow shrinking flat, '
               'and pops back up with a small spring when let go.',
    phrasings=('the button physically pushes in when you click it',
               'make the button sink down and bounce back up on tap',
               'a clicky 3D button that goes down under the cursor'),
    related=('subscribe-button-press', 'drag-lift-with-shadow', 'drop-shadow-breathing', 'drop-shadow-lift',
             'swipe-to-dismiss', 'speed-dial-fan'),
    api=('videobuilder.capabilities.ui.press_depress.press_depth',
         'videobuilder.capabilities.ui.press_depress.draw_press_button'),
    demo=lambda: demo.film(draw),
)
