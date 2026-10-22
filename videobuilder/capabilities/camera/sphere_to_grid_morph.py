"""Sphere-to-grid morph: a cloud of small tiles arranged on a turning 3D
sphere flies apart and reassembles as a flat grid facing the camera, each
tile travelling its own path through depth."""
import math

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def sphere_points(count, radius):
    """`count` points spread evenly over a sphere of `radius` px about the
    origin (a Fibonacci spiral), top to bottom, as (x, y, z) tuples."""
    golden = math.pi * (3 - math.sqrt(5))
    out = []
    for i in range(count):
        y = 1 - 2 * (i + 0.5) / count
        r = math.sqrt(1 - y * y)
        out.append((radius * r * math.cos(i * golden), -radius * y, radius * r * math.sin(i * golden)))
    return out


def grid_points(cols, rows, spacing):
    """A flat `cols` x `rows` grid in the z = 0 plane, centred on the
    origin, row by row from the top, as (x, y, z) tuples."""
    return [((c - (cols - 1) / 2) * spacing, (r - (rows - 1) / 2) * spacing, 0.0)
            for r in range(rows) for c in range(cols)]


def pair_up(sphere, cols):
    """`sphere` (from `sphere_points`) reordered so index i lands on grid
    cell i: latitude bands become rows, left to right within each, so tiles
    travel short paths and never cross the whole frame."""
    out = []
    for r in range(0, len(sphere), cols):
        out += sorted(sphere[r:r + cols], key=lambda q: q[0])
    return out


def morph_positions(start, end, p, stagger=0.35, ease=vb.ease_in_out_quart, lift=0.0):
    """Each point of `start` moved toward its partner in `end` at progress
    `p` (0 -> 1). Points set off one after another across `stagger` of the
    run, so the shape peels apart rather than sliding as one; `lift` px
    bows each path toward the camera mid-flight, adding depth."""
    n = len(start)
    out = []
    for i, (a, b) in enumerate(zip(start, end)):
        delay = stagger * i / max(1, n - 1)
        t = ease(vb.clamp01((p - delay) / (1 - stagger)))
        bow = -lift * math.sin(math.pi * t)
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t + bow))
    return out


def project(points, cx, cy, yaw=0.0, pitch=0.0, distance=1200):
    """3D `points` turned `yaw` radians about the vertical axis and `pitch`
    about the horizontal one, then put in perspective about (cx, cy). Returns
    (x, y, scale, depth) per point; larger depth is farther away."""
    cy_, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    out = []
    for x, y, z in points:
        x, z = x * cy_ + z * sy, -x * sy + z * cy_
        y, z = y * cp - z * sp, y * sp + z * cp
        f = distance / (distance + z)
        out.append((cx + x * f, cy + y * f, f, z))
    return out


def draw_sphere_to_grid(cv, cx, cy, p, cols=16, rows=10, radius=200, spacing=34, yaw=0.0, pitch=0.0,
                        size=10, color=demo.TEAL, accent=demo.ACCENT, every=7, distance=1200, lift=160):
    """Draw `cols` x `rows` tiles morphing from a sphere of `radius` px
    (p = 0) to a flat grid of `spacing` px (p = 1), centred at (cx, cy).
    `yaw` and `pitch` turn the whole formation (ease them to 0 so the grid
    lands face-on); far tiles are smaller and dimmer, drawn first. Every
    `every`-th tile is `accent` so single tiles can be followed. Returns
    the Box the tiles cover."""
    sphere = pair_up(sphere_points(cols * rows, radius), cols)
    pts = morph_positions(sphere, grid_points(cols, rows, spacing), p, lift=lift)
    flat = project(pts, cx, cy, yaw, pitch, distance)
    order = sorted(range(len(flat)), key=lambda i: -flat[i][3])
    reach = max(radius, lift, 1)
    for i in order:
        x, y, f, z = flat[i]
        s = size * f
        dim = 0.35 + 0.65 * vb.clamp01(0.5 - z / (2 * reach))
        cv.rect(x - s / 2, y - s / 2, s, s, accent if i % every == 3 else color, radius=s * 0.2, alpha=dim)
    xs, ys = [q[0] for q in flat], [q[1] for q in flat]
    return vb.Box(min(xs) - size, min(ys) - size, max(xs) - min(xs) + 2 * size, max(ys) - min(ys) + 2 * size)


START, LENGTH, SPIN = 0.7, 1.8, 1.2  # morph start and length in s; the sphere's spin in rad/s


def draw(n, cv):
    t = n / demo.FPS
    p = demo.phase(n, START, START + LENGTH)
    settle = (1 - p) ** 3                       # cubic ease-out of the remaining turn, starting at full speed
    yaw = SPIN * LENGTH / 3 * settle + SPIN * max(0.0, START - t)
    box = draw_sphere_to_grid(cv, demo.W / 2, demo.H / 2, p, yaw=yaw, pitch=0.35 * settle)
    cv.mark('tiles', *box)


CAPABILITY = Capability(
    id='sphere-to-grid-morph',
    name='Sphere-to-grid morph',
    family='camera',
    group='3D motion',
    aliases=('table-sphere morph', 'layout morph', 'sphere to plane morph'),
    definition='Many small tiles sitting on the surface of a turning ball fly through depth and settle '
               'into a flat, evenly spaced grid that faces the viewer.',
    phrasings=('the dots on a spinning globe unwrap into a neat flat grid',
               'scatter the sphere of tiles and have them rearrange into rows and columns',
               'morph the 3D ball of items into a flat table layout'),
    related=('projection-morph', 'shape-morph', 'text-to-shape-morph', 'particle-morph', 'globe-spin',
             'liquid-morph'),
    api=('videobuilder.capabilities.camera.sphere_to_grid_morph.draw_sphere_to_grid',
         'videobuilder.capabilities.camera.sphere_to_grid_morph.morph_positions',
         'videobuilder.capabilities.camera.sphere_to_grid_morph.sphere_points',
         'videobuilder.capabilities.camera.sphere_to_grid_morph.grid_points',
         'videobuilder.capabilities.camera.sphere_to_grid_morph.pair_up',
         'videobuilder.capabilities.camera.sphere_to_grid_morph.project'),
    demo=lambda: demo.film(draw),
)
