"""Flip: the whole frame turns over like a card about its centre line, in
perspective, and the incoming scene is printed on its back."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

_turn = vb.bezier(0.6, 0, 0.35, 1)


def _face(cv, scene):
    """`scene` drawn on its own canvas the size and pixel scale of `cv`."""
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    scene(sub)
    sub.surface.flush()
    return sub.surface


def _turned(cv, surf, angle, shrink, axis, focal, strips, shade):
    """Draw the face `surf` (a frame of `cv`'s size) turned `angle` radians
    (|angle| < pi/2) about the frame's centre line, `axis` 'y' (a vertical
    line: the card turns left/right) or 'x' (a horizontal one: it tumbles),
    scaled by `shrink` and seen from `focal` px away. The face is cut into
    `strips` slices across the turn, each drawn at its own depth's size, which
    is cairo's affine stand-in for a perspective warp."""
    c = cv.ctx
    vertical = axis == 'y'
    length = cv.width if vertical else cv.height    # the run across the turn
    span = cv.height if vertical else cv.width      # the run along the axis
    cx, cy = cv.width / 2, cv.height / 2
    cos, sin = math.cos(angle), math.sin(angle)

    def project(u):  # source offset from the axis -> (screen offset, size at that depth)
        k = focal / (focal + u * sin)
        return u * cos * k * shrink, k * shrink

    darken = shade * (1 - cos)
    seam = 1.5 / cv.scale_factor()  # each strip runs on under the next by 1.5 device px: no hairline gaps
    for i in range(strips):
        u0, u1 = length * (i / strips - 0.5), length * ((i + 1) / strips - 0.5)
        x0, _ = project(u0)
        x1, _ = project(u1)
        _, k = project((u0 + u1) / 2)
        run = max(x1 - x0, 1e-6)
        c.save()
        if vertical:
            c.rectangle(cx + x0, cy - span * k / 2, run + seam, span * k)
            c.clip()
            c.translate(cx + x0, cy)
            c.scale(run / (u1 - u0), k)
            c.translate(-(u0 + length / 2), -span / 2)
        else:
            c.rectangle(cx - span * k / 2, cy + x0, span * k, run + seam)
            c.clip()
            c.translate(cx, cy + x0)
            c.scale(k, run / (u1 - u0))
            c.translate(-span / 2, -(u0 + length / 2))
        c.scale(1 / cv.scale, 1 / cv.scale)
        c.set_source_surface(surf, 0, 0)
        c.get_source().set_filter(cairo.FILTER_GOOD)
        c.paint()
        c.restore()
    if darken > 0:  # once over the whole face: per-strip fills would stack where strips overlap
        (e0, k0), (e1, k1) = project(-length / 2), project(length / 2)
        quad = ((e0, -span * k0 / 2), (e1, -span * k1 / 2), (e1, span * k1 / 2), (e0, span * k0 / 2))
        c.new_path()
        for along, across in quad:
            c.line_to(cx + along, cy + across) if vertical else c.line_to(cx + across, cy + along)
        c.close_path()
        c.set_source_rgba(0, 0, 0, darken)
        c.fill()


def flip(cv, a, b, p, axis='y', direction=1, depth=0.16, focal=None, strips=96, shade=0.55,
         backdrop=demo.BG, ease=_turn):
    """Draw the flip at progress `p` (0 -> 1): the frame showing `a(cv)` turns
    half a revolution about its centre line, `axis` 'y' (a vertical line, it
    turns sideways) or 'x' (a horizontal one, it tumbles), `direction` +1 or
    -1 choosing which way; past edge-on its back shows `b(cv)` turning into
    place. The card backs off by `depth` of its size mid-turn so its corners
    stay in frame, it darkens by up to `shade` as it turns edge-on, and
    `backdrop` fills the frame behind it. `focal` (default twice the frame's
    width) sets how strong the perspective is; `ease` shapes the turn.

    In a film, call it while two shots are live in an overlap, e.g.
    `flip(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    p = vb.clamp01(p)
    if p <= 0:
        return a(cv)
    if p >= 1:
        return b(cv)
    theta = math.pi * ease(p)
    shrink = 1 - depth * math.sin(math.pi * p)
    focal = focal or 2.0 * cv.width
    cv.fill(backdrop)
    if theta < math.pi / 2:
        face, angle = _face(cv, a), theta
    else:
        face, angle = _face(cv, b), theta - math.pi
    _turned(cv, face, direction * angle, shrink, axis, focal, strips, shade)


TECHNIQUE = Technique(
    id='flip',
    name='Flip',
    family='transitions',
    group='Rotation and 3D',
    aliases=('card flip', 'flip card', 'turnover', '3D flip', 'Y-axis flip', 'reveal back'),
    definition='The whole picture turns over like a playing card about its middle, '
               'and the next scene is waiting on the other side.',
    phrasings=('flip the shot over to show the next one',
               'turn the screen around like a card to reveal the next scene',
               'a 3D flip from this slide to the next'),
    related=('character-3d-flip', 'tile-flip', 'word-flip-in', 'logo-3d-spin-reveal',
             'layout-animation-flip', 'coin-flip'),
    api=('videobuilder.techniques.transitions.flip.flip',),
    demo=lambda: demo.two_scenes(flip, start=0.7, length=1.6),
)
