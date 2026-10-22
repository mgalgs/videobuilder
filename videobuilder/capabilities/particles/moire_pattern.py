"""Moire pattern: two fine, regular gratings (concentric rings or parallel
lines) laid over each other; a small shift or twist of one against the other
makes broad, ghostly interference bands sweep across the overlap, far larger
and faster than anything either grating is doing on its own."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def grating(cv, x, y, w, h, cx, cy, pitch=14.0, angle=0.0, kind='rings', color=demo.INK, width=None,
            alpha=1.0):
    """Stroke one grating clipped to the box (x, y, w, h): `kind='rings'` is
    concentric circles `pitch` px apart about (cx, cy); `kind='lines'` is
    parallel lines `pitch` px apart through (cx, cy), tilted `angle` radians
    from vertical. `width` defaults to half the pitch, the line/gap balance
    that gives the strongest fringes."""
    c = cv.ctx
    c.save()
    c.rectangle(x, y, w, h)
    c.clip()
    c.new_path()
    # The farthest box corner from the centre bounds how far the grating must reach.
    reach = max(math.hypot(px - cx, py - cy) for px in (x, x + w) for py in (y, y + h))
    if kind == 'rings':
        for i in range(1, int(reach / pitch) + 2):
            c.new_sub_path()
            c.arc(cx, cy, i * pitch, 0, math.tau)
    elif kind == 'lines':
        ux, uy = math.cos(angle), math.sin(angle)  # across the lines
        vx, vy = -uy, ux  # along the lines
        k = int(reach / pitch) + 2
        for i in range(-k, k + 1):
            ox, oy = cx + ux * i * pitch, cy + uy * i * pitch
            c.move_to(ox - vx * reach, oy - vy * reach)
            c.line_to(ox + vx * reach, oy + vy * reach)
    else:
        raise ValueError(f'grating kind must be rings or lines, not {kind!r}')
    c.set_source_rgba(*vb.canvas.rgba(color, alpha))
    c.set_line_width(width if width is not None else pitch / 2)
    c.stroke()
    c.restore()
    return vb.Box(x, y, w, h)


def moire_pattern(cv, x, y, w, h, shift=(0.0, 0.0), twist=0.0, kind='rings', pitch=14.0, center=None,
                  color=demo.INK, top_color=None, width=None, alpha=1.0):
    """Draw a moire in the box (x, y, w, h): a fixed grating, then an
    identical one moved by `shift` (dx, dy px) and turned by `twist` radians
    (lines only). Animate `shift` or `twist` by a few pitches or degrees and
    the fringes race across the frame. `center` defaults to the box centre;
    `top_color` tints the moving grating (defaults to `color`). Returns the Box."""
    cx, cy = center if center else (x + w / 2, y + h / 2)
    grating(cv, x, y, w, h, cx, cy, pitch, 0.0, kind, color, width, alpha)
    grating(cv, x, y, w, h, cx + shift[0], cy + shift[1], pitch, twist, kind, top_color or color, width,
            alpha)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    # The second ring set slides out from dead centre, then circles round: the fringes open
    # from nothing into a fan of bands and then wheel about the frame.
    out = vb.ease_in_out_quart(demo.phase(n, 0.2, 1.4))
    turn = vb.ease_in_out_quart(demo.phase(n, 1.4, 3.0)) * math.pi
    d = 70 * out
    shift = (d * math.cos(turn), d * math.sin(turn) * 0.8)
    moire_pattern(cv, 0, 0, demo.W, demo.H, shift=shift, kind='rings', pitch=13, width=5.5)
    cv.mark('pattern', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='moire-pattern',
    name='Moire pattern',
    family='particles',
    group='Interaction fields',
    aliases=('moire', 'moire interference', 'interference fringes', 'beat pattern'),
    definition='Two fine repeating patterns of lines or rings sit on top of each other, and nudging one '
               'slightly makes large wavy bands of light and dark ripple across the whole picture.',
    phrasings=('overlap two sets of thin lines so they make those shimmering interference bands',
               'the wavy ghost pattern you get when two screens or fences line up',
               'concentric circles sliding over each other to make trippy swirling bands'),
    related=('interlace-combing', 'line-weave', 'sine-wave-distortion', 'scanline-jitter',
             'op-art-vibrating-pattern', 'scanline-tear'),
    api=('videobuilder.techniques.particles.moire_pattern.moire_pattern',
         'videobuilder.techniques.particles.moire_pattern.grating'),
    demo=lambda: demo.film(draw),
)
