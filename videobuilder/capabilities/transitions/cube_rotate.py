"""Cube rotate: the two scenes sit on adjacent faces of a cube, which turns a
quarter turn about its vertical axis so the outgoing face swings away to one
side in perspective and the incoming one swings round to face the camera."""
import math

import cairo

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability

STRIPS = 64  # vertical slices per face: cairo maps images affinely, so perspective is built from thin strips


def _render(cv, scene):
    """`scene` drawn on its own canvas at `cv`'s pixel density; returns the cairo surface."""
    sub = vb.Canvas(cv.width, cv.height, scale=cv.scale_factor(), format=cv.format)
    scene(sub)
    sub.surface.flush()
    return sub.surface, sub.scale


def _face(cv, surface, density, project, shade, strips=STRIPS):
    """Paint `surface` (a whole frame) onto one cube face. `project(u)` gives
    (screen x, vertical scale) for the face's column at frame x `u`; the face
    is split into `strips` columns, each a plain affine stretch."""
    W, H = cv.width, cv.height
    cy = H / 2
    c = cv.ctx
    pad = 1 / cv.scale_factor()
    cols = [project(W * i / strips) for i in range(strips + 1)]
    if cols[-1][0] - cols[0][0] <= 0:
        return  # a flat face projects with one orientation: this one is edge-on or facing away, so hidden
    for i in range(strips):
        (x0, s0), (x1, s1) = cols[i], cols[i + 1]
        if x1 <= x0:
            continue  # this column is edge-on or facing away
        u0, u1 = W * i / strips, W * (i + 1) / strips
        s = (s0 + s1) / 2
        c.save()
        # Clip the strip's columns hard-edged, a device pixel wide of each side so neighbours overlap
        # without a seam; its top and bottom are the image's own (filtered) edges.
        c.set_antialias(cairo.ANTIALIAS_NONE)
        c.rectangle(x0 - pad, -H, x1 - x0 + 2 * pad, 3 * H)
        c.clip()
        c.set_antialias(cairo.ANTIALIAS_DEFAULT)
        c.translate(x0, cy - s * H / 2)
        c.scale((x1 - x0) / (u1 - u0), s)
        c.translate(-u0, 0)
        c.scale(1 / density, 1 / density)
        c.set_source_surface(surface, 0, 0)
        c.get_source().set_filter(cairo.FILTER_GOOD)
        c.paint()
        c.restore()
    if shade > 0:
        (xl, sl), (xr, sr) = cols[0], cols[-1]
        c.move_to(xl, cy - sl * H / 2)
        c.line_to(xr, cy - sr * H / 2)
        c.line_to(xr, cy + sr * H / 2)
        c.line_to(xl, cy + sl * H / 2)
        c.close_path()
        c.set_source_rgba(0, 0, 0, shade)
        c.fill()


def cube_rotate(cv, a, b, p, direction='left', ease=vb.ease_in_out_quart, depth=0.35, focal=1.6,
                backdrop='#000000', shading=0.55):
    """Draw the cube turn at progress `p` (0 -> 1): `a(cv)` on the front face
    turning away, `b(cv)` on the side face turning in. `direction='left'`
    turns the cube right-to-left (b enters from the right); `'right'` mirrors
    it. `depth` pulls the cube back from the camera mid-turn (as a fraction
    of the frame width) so its leading edge stays in frame; `focal` is the
    camera distance in frame widths (smaller is a stronger perspective);
    `shading` darkens a face as it turns away from the camera.

    In a film, call it while two shots are live in an overlap, e.g.
    `cube_rotate(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    W, H = cv.width, cv.height
    e = ease(vb.clamp01(p))
    theta = e * math.pi / 2
    sign = 1 if direction == 'left' else -1
    h = W / 2                                   # half the cube's edge: faces are frame-sized
    f = focal * W
    push = depth * W * math.sin(math.pi * e)    # back off mid-turn, land exactly on the frame
    ct, st = math.cos(theta), math.sin(theta)

    def projector(x_of, z_of):
        def project(u):
            x, z = x_of(u - h), z_of(u - h)     # the point, about the cube's centre
            xr, zr = x * ct + z * st * sign, -x * st * sign + z * ct
            k = f / (f + zr + h + push)        # front face at rest sits on the screen plane
            return W / 2 + xr * k, k
        return project

    # Face a: the front (z = -h). Face b: the side it turns towards, x = +h (or -h), facing outwards.
    front = projector(lambda v: v, lambda v: -h)
    side = projector(lambda v: sign * h, lambda v: v * sign)
    sa, da = _render(cv, a)
    sb, db = _render(cv, b)
    cv.fill(backdrop)
    # Each face's centre depth after the turn: front -h*cos, side -h*sin (smaller is nearer the camera).
    faces = [(-h * ct, sa, da, front, shading * (1 - ct)), (-h * st, sb, db, side, shading * (1 - st))]
    faces.sort(key=lambda face: -face[0])       # paint the farther face first, the nearer one last
    for _, surface, density, project, shade in faces:
        _face(cv, surface, density, project, shade)


CAPABILITY = Capability(
    id='cube-rotate',
    name='Cube rotate',
    family='transitions',
    group='Rotation and 3D',
    aliases=('cube spin', '3D cube transition', 'box rotate', 'cube turn'),
    definition='The two scenes behave like neighbouring sides of a box that turns a quarter turn, '
               'so the old one swings off to the side in perspective as the new one swings round to face you.',
    phrasings=('turn to the next scene like rotating a box',
               'spin the picture round on a 3D cube to reveal the next shot',
               'make the slides rotate like the sides of a cube'),
    related=('three-d-word-cube', 'turntable-rotation', 'tesseract-rotation', 'globe-spin', 'word-flip-in',
             'swirl'),
    api=('videobuilder.capabilities.transitions.cube_rotate.cube_rotate',),
    demo=lambda: demo.two_scenes(cube_rotate, start=1.3, length=1.5),  # poster (2.1 s) lands mid-turn
)
