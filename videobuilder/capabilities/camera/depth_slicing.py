"""Depth slicing: a volume shown as a stack of parallel cross-sections, each
slice switching on at the next depth while the camera pushes forward into
the stack, so the inside of the thing is laid open layer by layer."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique


def slice_scale(z, camera_z, focal=1.0, near=0.05):
    """The on-screen scale of a slice at depth `z` seen from `camera_z`: a
    pinhole projection, `focal / (z - camera_z)`, kept finite as the slice
    reaches the camera (`near`)."""
    return focal / max(z - camera_z, near)


def slice_shown(i, count, reveal, soft=1.0):
    """How far slice `i` of `count` has appeared (0 -> 1) at `reveal` (0 -> 1
    across the whole stack): the slices switch on one after another, each
    fading in over `soft` slots."""
    return vb.clamp01((reveal * (count + soft - 1) - i) / soft)


def draw_slices(cv, slices, camera_z, reveal, cx, cy, focal=1.0, camera_xy=(0.0, 0.0), near=0.6,
                ease=vb.ease_out_quint):
    """Draw a stack of depth slices, far first, with the camera at depth
    `camera_z` looking down the stack from (`cx`, `cy`) on screen.

    `slices` lists `(z, draw)` pairs in the order they should appear;
    `draw(cv, x, y, scale, alpha)` paints one cross-section centred at
    (x, y) at `scale` (1 is its size one unit in front of the camera, times
    `focal`). `reveal` runs 0 -> 1 as the slices switch on one by one (see
    `slice_shown`); each one eases in, settling forward from slightly deeper.
    `camera_xy` shifts the camera sideways in world units so the slices
    parallax. A slice fades out as it comes within `near` of the camera, so
    a push-in can fly through the front of the stack."""
    count = len(slices)
    order = sorted(range(count), key=lambda i: -slices[i][0])
    for i in order:
        z, paint = slices[i]
        shown = ease(slice_shown(i, count, reveal))
        if shown <= 0:
            continue
        dist = z - camera_z + (1 - shown) * 0.25
        if dist <= 0:
            continue
        s = slice_scale(z + (1 - shown) * 0.25, camera_z, focal)
        alpha = shown * vb.clamp01(dist / near)
        if alpha <= 0.01:
            continue
        paint(cv, cx - camera_xy[0] * s, cy - camera_xy[1] * s, s, alpha)


# -- demo: an organic body cut into eight slices, with two tubes running through it

SLICES = 8
FRONT, BACK = 2.0, 4.8          # world depth of the first and last slice
FOCAL = 520.0


def _outline(t, n=72):
    """The body's cross-section at depth fraction `t` (0 front -> 1 back),
    as a closed point list around (0, 0) in world units: a lumpy ring that
    is widest in the middle of the body."""
    r = 0.25 + 0.75 * math.sin(math.pi * (0.12 + 0.76 * t))
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        wob = 1 + 0.12 * math.sin(3 * a + 2.2 * t) + 0.06 * math.sin(5 * a - 1.3 * t + 1)
        pts.append((r * wob * math.cos(a), 0.82 * r * wob * math.sin(a)))
    return pts, r


def _cores(t):
    """Where the tubes inside the body cut slice `t`: ((x, y), radius) each."""
    return (((-0.28 + 0.2 * t, 0.12 - 0.3 * t), 0.13 + 0.05 * math.sin(math.pi * t)),
            ((0.35 - 0.1 * t, -0.18 + 0.22 * t), 0.09 + 0.04 * t))


def _slice(t):
    pts, r = _outline(t)
    cores = _cores(t)

    def paint(cv, x, y, s, alpha):
        ring = [(x + px * s, y + py * s) for px, py in pts]
        vb.paths.draw(cv, ring, demo.TEAL, fill=True, closed=True, alpha=0.10 * alpha)
        vb.paths.draw(cv, ring, demo.TEAL, width=2.5, closed=True, alpha=0.9 * alpha)
        for (ox, oy), cr in cores:
            if cr < r * 0.9:
                demo.dot(cv, x + ox * s, y + oy * s, cr * s, demo.ACCENT, alpha=0.35 * alpha)
                cv.arc(x + ox * s, y + oy * s, cr * s, 0, 2 * math.pi, demo.ACCENT, width=2, alpha=alpha)
    return paint


STACK = [(FRONT + (BACK - FRONT) * i / (SLICES - 1), _slice(i / (SLICES - 1))) for i in range(SLICES)]


def draw(n, cv):
    reveal = demo.phase(n, 0.2, 2.5)
    push = vb.ease_in_out_quart(demo.phase(n, 0.0, 3.0))
    camera_z = 1.1 * push
    drift = (0.08 * push, -0.05 * push)
    draw_slices(cv, STACK, camera_z, reveal, demo.W / 2, demo.H / 2, focal=FOCAL, camera_xy=drift)
    cv.mark('stack', demo.W / 2 - 200, demo.H / 2 - 160, 400, 320)


TECHNIQUE = Technique(
    id='depth-slicing',
    name='Depth slicing',
    family='camera',
    group='Depth',
    aliases=('Z-slice reveal', 'layer stack reveal', 'cross-section stack'),
    definition='An object is shown as a stack of flat cross-sections that switch on one at a time at '
               'increasing depth while the camera glides forward into them, exposing what is inside.',
    phrasings=('cut the object into layers and fly the camera through them one by one',
               'show the inside as a pile of stacked slices that pop in as we push in',
               'like an MRI scan, reveal each cross-section in turn going deeper'),
    related=('x-ray-view', 'pointer-parallax-layers', 'corner-wipe', 'zoom-out-reveal', 'exploded-view',
             'extrusion-depth-reveal'),
    api=('videobuilder.techniques.camera.depth_slicing.draw_slices',
         'videobuilder.techniques.camera.depth_slicing.slice_scale',
         'videobuilder.techniques.camera.depth_slicing.slice_shown'),
    demo=lambda: demo.film(draw),
)
