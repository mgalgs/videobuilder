"""Voxel build: a 3D model made of equal cubes assembles itself one cube at a
time, layer by layer from the ground up, each cube dropping into its grid
slot, while the camera circles slowly round so the volume reads."""
import math

import videobuilder as vb

from .. import _demo as demo
from ...compendium import kit
from ..schema import Technique

# The six faces of a unit cube: outward normal, then its four corners (offsets
# from the cube's minimum corner), wound consistently.
FACES = (
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
    ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
)
LIGHT = (-0.45, 0.8, 0.4)  # from the upper left, toward the viewer


class OrbitCamera:
    """An orthographic camera looking at the world origin from `pitch`
    radians above the horizon, turned `yaw` radians about the vertical axis.
    World y is up; one world unit is `scale` pixels; the origin lands on
    screen (cx, cy)."""

    def __init__(self, cx, cy, yaw, pitch=math.radians(30), scale=60.0):
        self.cx, self.cy, self.scale = cx, cy, scale
        self.cyaw, self.syaw = math.cos(yaw), math.sin(yaw)
        self.cp, self.sp = math.cos(pitch), math.sin(pitch)

    def view(self, x, y, z):
        """World point -> (right, up, toward-viewer) in camera space."""
        xr = x * self.cyaw - z * self.syaw
        zr = x * self.syaw + z * self.cyaw
        return xr, y * self.cp - zr * self.sp, y * self.sp + zr * self.cp

    def project(self, x, y, z):
        """World point -> screen (x, y)."""
        u, v, _ = self.view(x, y, z)
        return self.cx + u * self.scale, self.cy - v * self.scale

    def depth(self, x, y, z):
        """How near the viewer a world point is (larger is nearer)."""
        return self.view(x, y, z)[2]


def _face_shade(color, normal, cam):
    nx, ny, nz = normal
    xr = nx * cam.cyaw - nz * cam.syaw
    zr = nx * cam.syaw + nz * cam.cyaw
    lit = vb.clamp01(0.5 + 0.5 * (xr * LIGHT[0] + ny * LIGHT[1] + zr * LIGHT[2]) / 0.98)
    return kit.mix(color, '#ffffff', 0.25 * lit) if lit > 0.6 else kit.mix(color, '#000000', 0.45 * (1 - lit))


def draw_voxel(cv, cam, x, y, z, color, size=1.0, outline=None, alpha=1.0):
    """One cube with its minimum corner at world (x, y, z), `size` units on
    a side, shaded per face; faces turned away from the camera are skipped."""
    ctx = cv.ctx
    for normal, corners in FACES:
        if cam.view(*normal)[2] - cam.view(0, 0, 0)[2] <= 1e-6:
            continue
        pts = [cam.project(x + a * size, y + b * size, z + c * size) for a, b, c in corners]
        ctx.move_to(*pts[0])
        for q in pts[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.set_source_rgba(*vb.rgba(_face_shade(color, normal, cam), alpha))
        if outline:
            ctx.fill_preserve()
            ctx.set_source_rgba(*vb.rgba(outline, alpha))
            ctx.set_line_width(max(1.0, cam.scale * 0.03))
            ctx.set_line_join(1)
            ctx.stroke()
        else:
            ctx.fill()


def voxel_build(cv, cam, voxels, p, spread=0.8, drop=4.0, ease=vb.ease_out_quint, outline=None):
    """Draw `voxels` -- (x, y, z, color) grid cells, y up -- assembling at
    progress `p` (0 -> 1). Cubes are placed bottom layer first (then back to
    front within a layer); each falls `drop` units into its cell over the
    last `1 - spread` of the run, starts spread across the first `spread`,
    fading in as it falls. Painted far to near through `cam` (an
    `OrbitCamera`), so turn the camera as it builds. Returns how many cubes
    have landed."""
    order = sorted(range(len(voxels)), key=lambda i: (voxels[i][1], voxels[i][0] + voxels[i][2], voxels[i][0]))
    n = max(1, len(voxels) - 1)
    live = []
    landed = 0
    for rank, i in enumerate(order):
        q = vb.clamp01((p - spread * rank / n) / (1 - spread)) if spread < 1 else float(p >= rank / n)
        if q <= 0:
            continue
        landed += q >= 1
        x, y, z, color = voxels[i]
        live.append((x, y + drop * (1 - ease(q)), z, color, min(1.0, q * 3)))
    live.sort(key=lambda v: cam.depth(v[0] + 0.5, v[1] + 0.5, v[2] + 0.5))
    for x, y, z, color, a in live:
        draw_voxel(cv, cam, x, y, z, color, outline=outline, alpha=a)
    return landed


def _house():
    """A little voxel house: a 5x4 block of walls with a door, under a stepped roof."""
    vox = []
    for y in range(3):
        for x in range(5):
            for z in range(4):
                if 0 < x < 4 and 0 < z < 3:
                    continue  # hollow inside
                door = z == 3 and x == 2 and y < 2
                window = y == 1 and ((z == 3 and x in (0, 4)) or (x == 4 and z in (1, 2)))
                if not door:
                    vox.append((x, y, z, '#f2b632' if window else demo.TEAL))
    for step in range(2):
        for x in range(step, 5 - step):
            for z in range(-1 + step, 5 - step):
                vox.append((x, 3 + step, z, demo.ACCENT))
    vox.append((2, 5, 2, demo.ACCENT))
    vox.append((2, 5, 1, demo.ACCENT))
    vox.append((3, 4, 0, '#7c83f2'))  # chimney
    vox.append((3, 5, 0, '#7c83f2'))
    return [(x - 2.5, y, z - 2.0, c) for x, y, z, c in vox]


HOUSE = _house()


def _floor(cv, cam, r=5):
    ctx = cv.ctx
    for i in range(-r, r + 1):
        for a, b in (((i, -r), (i, r)), ((-r, i), (r, i))):
            ctx.move_to(*cam.project(a[0], 0, a[1]))
            ctx.line_to(*cam.project(b[0], 0, b[1]))
    ctx.set_source_rgba(*vb.rgba(demo.LINE))
    ctx.set_line_width(2)
    ctx.stroke()


def draw(n, cv):
    t = n / demo.FPS
    yaw = math.radians(75 - 15 * t)  # a slow steady orbit the whole time
    cam = OrbitCamera(demo.W / 2, demo.H / 2 + 150, yaw, pitch=math.radians(28), scale=62)
    _floor(cv, cam)
    voxel_build(cv, cam, HOUSE, demo.phase(n, 0.2, 2.5), outline=demo.BG)
    cv.mark('model', demo.W / 2 - 330, demo.H / 2 - 300, 660, 560)


TECHNIQUE = Technique(
    id='voxel-build',
    name='Voxel build',
    family='camera',
    group='3D motion',
    aliases=('voxel assembly', 'block-by-block build', 'cube build', 'Minecraft-style build'),
    definition='A 3D model made of little cubes puts itself together one cube at a time, each dropping '
               'into its slot from the ground up, while the camera slowly circles it.',
    phrasings=('build the model out of blocks one cube at a time while we orbit around it',
               'have little 3D cubes stack up into a house like a block-building game',
               'assemble the object from voxels piece by piece with a turning camera'),
    related=('shape-stacking-drop', 'pyramid-build', 'shape-assemble-from-fragments', 'stacked-bar-build',
             'stacked-line-build', 'isometric-assembly'),
    api=('videobuilder.techniques.camera.voxel_build.voxel_build',
         'videobuilder.techniques.camera.voxel_build.OrbitCamera',
         'videobuilder.techniques.camera.voxel_build.draw_voxel'),
    demo=lambda: demo.film(draw),
)
