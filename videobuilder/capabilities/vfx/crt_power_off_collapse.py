"""CRT power-off collapse: the picture squashes vertically into a glowing
horizontal line, the line pinches in to a bright dot, and the dot fades out,
the way an old tube television goes dark."""
import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Capability


def crt_power_off(cv, scene, p, squash=0.45, pinch=0.3, backdrop='#000000', beam='#ffffff',
                  line=8, dot=20, glow=36):
    """Draw `scene` (a `scene(cv)` callable drawing the whole frame) switching
    off at progress `p` (0 -> 1), centred on the frame, over a `backdrop` fill.

    Over the first `squash` of `p` the picture flattens toward a `line` px
    strip, washing out to `beam` as it goes; over the next `pinch` that strip
    shrinks sideways to a `dot` px point; over the rest the dot fades away.
    `glow` is the blur of the halo around the line and dot. At 0 the scene is
    drawn untouched; at 1 only the backdrop is left.

    In a film, call it on the last shot before a cut, e.g.
    `crt_power_off(cv, lambda c: shot(c), shot.f / off_frames)`, then cut to black or the next scene."""
    if p <= 0:
        scene(cv)
        return
    w, h = cv.width, cv.height
    cx, cy = w / 2, h / 2
    cv.fill(backdrop)
    if p < squash:
        q = (p / squash) ** 2
        sh = h + (line - h) * q                   # picture height, frame -> one line
        sw = w * (1 - 0.06 * q)                   # a touch of horizontal pull-in, like the tube's
        if q > 0.5:                               # the halo builds behind the flattening picture
            k = (q - 0.5) / 0.5
            _halo(cv, cx - sw / 2, cy - sh / 2, sw, sh, beam, glow, k)
        c = cv.ctx
        c.save()
        c.rectangle(cx - sw / 2, cy - sh / 2, sw, sh)
        c.clip()
        c.translate(cx, cy)
        c.scale(sw / w, sh / h)
        c.translate(-cx, -cy)
        scene(cv)
        c.restore()
        # The picture blows out toward white as the beam concentrates.
        cv.rect(cx - sw / 2, cy - sh / 2, sw, sh, beam, alpha=0.9 * q ** 1.5)
        return
    if p < squash + pinch:
        q = vb.ease_in_out_quart((p - squash) / pinch)
        lw = w * 0.94 + (dot - w * 0.94) * q      # line width -> dot size
        lh = line + (dot - line) * q
        _beam(cv, cx, cy, lw, lh, beam, glow, 1.0)
        return
    q = (p - squash - pinch) / max(1e-6, 1 - squash - pinch)
    _beam(cv, cx, cy, dot * (1 - 0.6 * q), dot * (1 - 0.6 * q), beam, glow, 1 - q * q)


def _beam(cv, cx, cy, bw, bh, color, glow, alpha):
    """The glowing strip or point left on the tube, centred at (cx, cy)."""
    if alpha <= 0:
        return
    x, y = cx - bw / 2, cy - bh / 2
    _halo(cv, x, y, bw, bh, color, glow, alpha)
    cv.rect(x, y, bw, bh, color, radius=bh / 2, alpha=alpha)


def _halo(cv, x, y, w, h, color, glow, alpha):
    """A soft bloom of `color` around the box (x, y, w, h): a wide faint one and a tight bright one."""
    r, g, b, _ = (255 * v for v in rgba(color))
    rad = min(w, h) / 2
    cv.shadow(x, y, w, h, radius=rad, blur=glow * 2, spread=glow * 0.3, color=(r, g, b, 0.3 * alpha))
    cv.shadow(x, y, w, h, radius=rad, blur=glow * 0.5, color=(r, g, b, 0.7 * alpha))


def draw(n, cv):
    p = demo.phase(n, 0.6, 2.5)
    crt_power_off(cv, demo.scene_a, p, backdrop=demo.BG)
    if p <= 0:
        cv.mark('screen', 0, 0, demo.W, demo.H)


CAPABILITY = Capability(
    id='crt-power-off-collapse',
    name='CRT power-off collapse',
    family='vfx',
    group='CRT & display',
    aliases=('TV turn-off', 'CRT shutdown', 'screen collapse'),
    definition='The image flattens into a thin glowing line across the middle of the screen, '
               'the line shrinks to a single bright point, and the point winks out.',
    phrasings=('turn the screen off like an old tube TV',
               'squash the picture into a white line and a dot, then black',
               'end the shot with a retro television switch-off'),
    related=('crumple', 'sidebar-collapse-width', 'accordion-fold', 'interruptible-motion',
             'circular-clip-reveal', 'pulldown-judder'),
    api=('videobuilder.capabilities.vfx.crt_power_off_collapse.crt_power_off',),
    demo=lambda: demo.film(draw),
)
