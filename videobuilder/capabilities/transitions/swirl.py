"""Swirl: the outgoing scene twists into a whirlpool about the centre, the
twist strongest in the middle and easing off toward the edges; at the peak
the incoming scene takes over, already twisted, and unwinds to rest."""
import math

import cairo
from PIL import Image

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _smooth(t):
    t = vb.clamp01(t)
    return t * t * (3 - 2 * t)


def _pixels(cv, draw):
    """`draw(c)` on a fresh canvas the size and scale of `cv`, as a PIL RGB image."""
    c = vb.Canvas(cv.width, cv.height, scale=cv.scale, format=cv.format)
    draw(c)
    s = c.surface
    s.flush()
    im = Image.frombuffer('RGBA', (s.get_width(), s.get_height()), bytes(s.get_data()), 'raw', 'BGRA',
                          s.get_stride(), 1)
    return im.convert('RGB')


def _mirrored(im):
    """`im` in the middle of a 3 x 3 tiling of itself, each neighbour flipped
    to meet it edge to edge."""
    w, h = im.size
    fx = im.transpose(Image.FLIP_LEFT_RIGHT)
    row = Image.new('RGB', (3 * w, h))
    for i, t in enumerate((fx, im, fx)):
        row.paste(t, (i * w, 0))
    out = Image.new('RGB', (3 * w, 3 * h))
    fy = row.transpose(Image.FLIP_TOP_BOTTOM)
    for j, t in enumerate((fy, row, fy)):
        out.paste(t, (0, j * h))
    return out


def twirl(im, angle, cx, cy, radius, cells=48):
    """`im` (PIL) twisted about (cx, cy), in its pixels: a point at distance
    r < `radius` turns by `angle` radians times (1 - r/radius)^2, so the
    centre turns most and the rim not at all. A mesh warp of `cells` across;
    where the twist reaches past the edge it picks up the picture mirrored,
    never black."""
    w, h = im.size
    if abs(angle) < 1e-4:
        return im
    src_im = _mirrored(im)
    nx = cells
    ny = max(1, round(cells * h / w))

    def src(x, y):
        dx, dy = x - cx, y - cy
        r = math.hypot(dx, dy)
        if r >= radius:
            return w + x, h + y
        a = -angle * (1 - r / radius) ** 2  # where this output point was before the twist
        ca, sa = math.cos(a), math.sin(a)
        return w + cx + dx * ca - dy * sa, h + cy + dx * sa + dy * ca

    xs = [w * i / nx for i in range(nx + 1)]
    ys = [h * j / ny for j in range(ny + 1)]
    grid = [[src(x, y) for x in xs] for y in ys]
    mesh = []
    for j in range(ny):
        for i in range(nx):
            box = (round(xs[i]), round(ys[j]), round(xs[i + 1]), round(ys[j + 1]))
            (ax, ay), (bx, by) = grid[j][i], grid[j + 1][i]
            (qx, qy), (dx, dy) = grid[j + 1][i + 1], grid[j][i + 1]
            mesh.append((box, (ax, ay, bx, by, qx, qy, dx, dy)))
    return src_im.transform((w, h), Image.MESH, mesh, Image.BILINEAR)


def swirl(cv, a, b, p, turns=1.25, center=None, radius=None, blend=0.3):
    """Draw the swirl at progress `p` (0 -> 1). `a(cv)` winds up to `turns`
    full turns at the centre by the midpoint; `b(cv)` dissolves in over the
    middle `blend` fraction, wound the same way, and unwinds to still by 1.
    `center` (film px, default the frame centre) is the eye of the whirl;
    `radius` (default reaching the corners) is where the twist dies out.

    In a film, call it while two shots are live in an overlap, e.g.
    `swirl(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / overlap_frames)`."""
    s = cv.scale
    cx, cy = center or (cv.width / 2, cv.height / 2)
    R = radius or 1.05 * math.hypot(max(cx, cv.width - cx), max(cy, cv.height - cy))
    twist = 2 * math.pi * turns * math.sin(math.pi * vb.clamp01(p)) ** 2  # 0 -> peak -> 0, still at both ends
    mix = _smooth((p - (0.5 - blend / 2)) / blend) if blend > 0 else float(p >= 0.5)
    args = (cx * s, cy * s, R * s)
    out = None
    if mix < 1:
        out = twirl(_pixels(cv, a), twist, *args)
    if mix > 0:
        im_b = twirl(_pixels(cv, b), twist, *args)
        out = im_b if out is None else Image.blend(out, im_b, mix)
    data = bytearray(out.tobytes('raw', 'BGRX'))
    surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_RGB24, out.width, out.height, out.width * 4)
    c = cv.ctx
    c.save()
    c.identity_matrix()
    c.set_source_surface(surf, 0, 0)
    c.paint()
    c.restore()


CAPABILITY = Capability(
    id='swirl',
    name='Swirl',
    family='transitions',
    group='Organic and Fluid',
    aliases=('twirl', 'vortex', 'whirl', 'whirlpool', 'spiral warp', 'twirl transition', 'rotational warp'),
    definition='The first scene twists around its centre like water going down a drain, hardest in the middle, '
               'and the second scene unwinds out of the same whirl.',
    phrasings=('swirl from this shot into the next one',
               'twist the picture into a whirlpool and come out on the new scene',
               'a vortex transition between the two scenes'),
    related=('twirl-warp-text', 'spin', 'animated-gradient-sweep', 'spiral-wipe', 'rotoscope-look',
             'globe-spin'),
    api=('videobuilder.capabilities.transitions.swirl.swirl',
         'videobuilder.capabilities.transitions.swirl.twirl'),
    demo=lambda: demo.two_scenes(swirl, start=0.6, length=1.8),
)
