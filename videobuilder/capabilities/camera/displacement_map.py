"""Displacement map: a greyscale image pushes the points of a flat plane out
of it -- white lifts most, black stays put -- so the picture becomes a relief
the camera can look across."""
import math

from PIL import Image, ImageDraw, ImageFilter

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability
from ...compendium import kit


def height_sampler(img):
    """A greyscale `PIL.Image` (any mode; converted to 'L') as a function
    `(u, v) -> 0..1`, u and v from 0 to 1 across and down the image,
    sampled bilinearly so a coarse mesh still reads smooth."""
    g = img.convert('L')
    w, h = g.size
    px = g.load()

    def at(u, v):
        x, y = min(max(u, 0.0), 1.0) * (w - 1), min(max(v, 0.0), 1.0) * (h - 1)
        x0, y0 = int(x), int(y)
        x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
        fx, fy = x - x0, y - y0
        top = px[x0, y0] + (px[x1, y0] - px[x0, y0]) * fx
        bot = px[x0, y1] + (px[x1, y1] - px[x0, y1]) * fx
        return (top + (bot - top) * fy) / 255
    return at


def displacement_mesh(height, cols=48, rows=32, size=(900, 600), amount=160.0):
    """The plane as a `(rows + 1) x (cols + 1)` grid of world points
    `(x, y, z)`, centred on the origin, `size` wide (x) and deep (z), each
    lifted along -y by `amount * height(u, v)`. The image's top edge is the
    far edge (+z), so seen from the front the relief reads like the map. `height` is a function of
    `(u, v)` in 0..1 (see `height_sampler`), or a PIL image."""
    if not callable(height):
        height = height_sampler(height)
    sw, sd = size
    return [[((c / cols - 0.5) * sw, -amount * height(c / cols, r / rows), (0.5 - r / rows) * sd)
             for c in range(cols + 1)] for r in range(rows + 1)]


def draw_displacement(cv, mesh, center=None, yaw=0.0, pitch=0.6, distance=1400.0, focal=1100.0,
                      low=demo.LINE, high=demo.TEAL, light=(-0.4, -1.0, -0.5), lines=None):
    """Draw `mesh` (from `displacement_mesh`) as a shaded surface seen by a
    camera `distance` from its centre, turned `yaw` about the vertical and
    tilted `pitch` radians down onto it, projected with `focal` px around
    `center` (default: the frame's centre). Each cell is filled from `low`
    to `high` by how far it is lifted and lit from `light`; `lines`, a
    colour, also strokes the grid like a wireframe. Cells are painted back
    to front, so ridges hide what lies behind them."""
    cx, cy = center or (cv.width / 2, cv.height / 2)
    cyaw, syaw, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    lx, ly, lz = light
    ll = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ll, ly / ll, lz / ll
    top = min(p[1] for row in mesh for p in row)
    lift = -top if top < 0 else 1.0

    def view(p):
        x, y, z = p
        x, z = x * cyaw - z * syaw, x * syaw + z * cyaw
        y, z = y * cp - z * sp, y * sp + z * cp
        return x, y, z + distance

    cam = [[view(p) for p in row] for row in mesh]
    scr = [[(cx + focal * x / z, cy + focal * y / z) for x, y, z in row] for row in cam]
    cells = []
    for r in range(len(mesh) - 1):
        for c in range(len(mesh[0]) - 1):
            a, b, d, e = mesh[r][c], mesh[r][c + 1], mesh[r + 1][c + 1], mesh[r + 1][c]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = e[0] - a[0], e[1] - a[1], e[2] - a[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            shade = 0.45 + 0.75 * max(0.0, -(nx * lx + ny * ly + nz * lz) / nl)
            h = -(a[1] + b[1] + d[1] + e[1]) / (4 * lift)
            depth = (cam[r][c][2] + cam[r][c + 1][2] + cam[r + 1][c + 1][2] + cam[r + 1][c][2]) / 4
            quad = (scr[r][c], scr[r][c + 1], scr[r + 1][c + 1], scr[r + 1][c])
            cells.append((depth, quad, h, shade))
    cells.sort(key=lambda cell: -cell[0])
    ctx = cv.ctx
    ctx.save()
    ctx.set_line_join(1)  # round joins: no spikes on thin cells
    for _, quad, h, shade in cells:
        rgb = kit.mix(low, high, min(max(h, 0.0), 1.0))
        r, g, b = (min(1.0, ch / 255 * shade) for ch in rgb)
        ctx.new_path()
        ctx.move_to(*quad[0])
        for q in quad[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.set_source_rgb(r, g, b)
        ctx.fill_preserve()
        if lines:
            ctx.set_source_rgba(*vb.rgba(lines, 0.55))
        ctx.set_line_width(1.0 if lines else 0.8)  # same-colour edge closes hairline seams
        ctx.stroke()
    ctx.restore()


_MAP = None


def _demo_map():
    """The demo's greyscale map, drawn in code: a soft dome, a ring and a
    ridge, blurred so the relief has slopes rather than cliffs."""
    global _MAP
    if _MAP is None:
        w, h = 240, 160
        im = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(im)
        d.ellipse((30, 40, 100, 110), fill=255)
        d.ellipse((128, 22, 214, 108), outline=200, width=12)
        d.polygon(((40, 140), (200, 128), (205, 146), (45, 152)), fill=150)
        _MAP = im.filter(ImageFilter.GaussianBlur(7))
    return _MAP


def draw(n, cv):
    t = n / demo.FPS
    amount = 190 * vb.ease_in_out_quart(demo.phase(n, 0.3, 1.7))
    mesh = displacement_mesh(_demo_map(), cols=54, rows=36, size=(880, 590), amount=amount)
    draw_displacement(cv, mesh, center=(demo.W / 2 + 100, demo.H / 2 + 50), yaw=-0.3 + 0.24 * t / demo.SECONDS,
                      pitch=0.7, distance=1500, focal=1100, low='#3a3e4a', high=demo.TEAL, lines=demo.BG)
    m = _demo_map()  # the map itself, inset, so the relief reads as driven by it
    iw, ih = 240, 160
    cv.rect(36, 36, iw + 12, ih + 46, demo.BG, radius=10, alpha=0.85)
    cv.image(vb.Image.from_pil(m.convert('RGB')), 42, 42, iw, ih)
    cv.outline(42, 42, iw, ih, demo.MUTED, width=2)
    vb.text.draw(cv, ['height map'], demo.mono(22, 600), 46, 42 + ih + 8, demo.MUTED)
    cv.mark('map', 42, 42, iw, ih)


CAPABILITY = Capability(
    id='displacement-map',
    name='Displacement map',
    family='camera',
    group='3D motion',
    aliases=('height map', 'displace', 'depth displacement', 'bump to relief'),
    definition='A greyscale image raises a flat surface point by point, light areas pushing up and dark '
               'ones staying low, so the flat picture grows into a 3D relief.',
    phrasings=('use this black-and-white image to push the plane up into hills',
               'turn the flat picture into a 3D landscape based on its brightness',
               'grow a relief out of the surface where the map is bright'),
    related=('wireframe-terrain', 'dot-grid-displacement', 'parallax-occlusion-mapping', 'ripple-displacement',
             'two-point-five-d-photo-parallax', 'solid-drawing'),
    api=('videobuilder.capabilities.camera.displacement_map.draw_displacement',
         'videobuilder.capabilities.camera.displacement_map.displacement_mesh',
         'videobuilder.capabilities.camera.displacement_map.height_sampler'),
    demo=lambda: demo.film(draw),
)
