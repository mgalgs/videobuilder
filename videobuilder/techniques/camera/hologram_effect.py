"""Hologram effect: a subject drawn in one glowing tint, see-through and cut
by fine horizontal scanlines, with a bright scan band rolling over it and a
flicker as the projection catches -- a projected sci-fi image."""
import math
import random

import cairo

import videobuilder as vb
from videobuilder.canvas import rgba

from .. import _demo as demo
from ..schema import Technique
from ...type import kit as tk


def hologram_flicker(t, warmup=0.8, seed=0, slot=(0.03, 0.09), dropout=0.04):
    """The projection's brightness 0 -> 1 at `t` seconds after it is switched
    on: 0 before, a seeded stutter of short slots (dark, dim or lit, lit more
    often later) across `warmup` seconds, then steady near 1 with a rare
    brief dip (`dropout` is the chance per 1/30 s). The same `seed` gives the
    same flicker, frame for frame."""
    if t < 0:
        return 0.0
    if t < warmup:
        r = random.Random(f'holo:{seed}')
        at = 0.0
        while True:
            at += r.uniform(*slot)
            roll = r.random()
            if t < at:
                k = at / warmup
                return 1.0 if roll < 0.2 + 0.6 * k else (0.35 if roll < 0.5 + 0.4 * k else 0.0)
    roll = random.Random(f'holo:{seed}:{int(t * 30)}').random()
    return 0.45 if roll < dropout else 0.92 + 0.08 * roll


def hologram(cv, paint, box, color, level=1.0, t=0.0, gap=4, scan_speed=0.45, glow=14, jitter=0.0, seed=0):
    """Draw `paint(c, color)` as a hologram inside `box` (the subject's
    bounds). `paint` draws the subject in the single tint it is given; this
    adds a soft halo of that tint, cuts dark scanlines every `gap` px (rolling
    slowly with `t` seconds), sweeps a brighter band down the subject every
    1 / `scan_speed` seconds, and fades the lot by `level` (0 -> 1, e.g. from
    `hologram_flicker`). `jitter` px nudges thin slices of the image sideways
    on random frames, like a weak signal. Returns `box`."""
    if level <= 0:
        return box
    ctx = cv.ctx
    tk.blurred(cv, box, glow, lambda c: paint(c, color), alpha=0.7 * level)

    ctx.save()
    ctx.push_group()
    paint(cv, color)
    # brighten a band rolling top to bottom, only where the subject is
    band = box.y - box.h * 0.2 + (t * scan_speed % 1.0) * box.h * 1.4
    grad = cairo.LinearGradient(0, band - box.h * 0.12, 0, band + box.h * 0.12)
    hot = rgba(tk.mix(color, '#ffffff', 0.6))
    grad.add_color_stop_rgba(0, *hot[:3], 0)
    grad.add_color_stop_rgba(0.5, *hot[:3], 0.55)
    grad.add_color_stop_rgba(1, *hot[:3], 0)
    ctx.set_operator(cairo.OPERATOR_ATOP)
    ctx.rectangle(box.x - glow, box.y - glow, box.w + 2 * glow, box.h + 2 * glow)
    ctx.set_source(grad)
    ctx.fill()
    # scanlines: knock out a thin line every `gap` px, drifting downward
    ctx.set_operator(cairo.OPERATOR_DEST_OUT)
    ctx.set_source_rgba(0, 0, 0, 0.6)
    y = box.y - glow + (t * 12 % gap)
    while y < box.y + box.h + glow:
        ctx.rectangle(box.x - glow, y, box.w + 2 * glow, gap * 0.45)
        y += gap
    ctx.fill()
    ctx.set_operator(cairo.OPERATOR_OVER)
    pattern = ctx.pop_group()
    ctx.restore()

    r = random.Random(f'holo-jit:{seed}:{int(t * 30)}')
    slices = [(box.y - glow, box.y + box.h + glow, 0.0)]
    if jitter and r.random() < 0.25:  # a weak-signal frame: one slice slips sideways
        s0 = box.y + r.uniform(0, 0.85) * box.h
        s1 = s0 + r.uniform(0.04, 0.15) * box.h
        slices = [(box.y - glow, s0, 0.0), (s0, s1, r.choice((-1, 1)) * jitter), (s1, box.y + box.h + glow, 0.0)]
    for y0, y1, dx in slices:
        ctx.save()
        ctx.rectangle(box.x - glow - abs(dx), y0, box.w + 2 * glow + 2 * abs(dx), y1 - y0)
        ctx.clip()
        ctx.translate(dx, 0)
        ctx.set_source(pattern)
        ctx.paint_with_alpha(level)
        ctx.restore()
    return box


def icosahedron(r):
    """The 12 vertices and 20 triangular faces (vertex indices) of an
    icosahedron of circumradius `r` about the origin."""
    g = (1 + 5 ** 0.5) / 2
    raw = [(-1, g, 0), (1, g, 0), (-1, -g, 0), (1, -g, 0), (0, -1, g), (0, 1, g), (0, -1, -g), (0, 1, -g),
           (g, 0, -1), (g, 0, 1), (-g, 0, -1), (-g, 0, 1)]
    k = r / math.sqrt(1 + g * g)
    verts = [(x * k, y * k, z * k) for x, y, z in raw]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
             (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    return verts, faces


def wire_solid(cv, verts, faces, cx, cy, yaw, pitch, color, width=1.6, distance=800, fill=0.12):
    """Paint a see-through wireframe solid in one `color`: `verts` (x, y, z)
    turned `yaw` then `pitch` radians and projected in perspective about
    (cx, cy); every edge drawn, hidden ones fainter, the silhouette (the rim)
    thickest, and faces filled at `fill` alpha. Suits `hologram`'s `paint`."""
    cy_, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    pts = []
    for x, y, z in verts:
        x, z = x * cy_ + z * sy, -x * sy + z * cy_
        y, z = y * cp - z * sp, y * sp + z * cp
        f = distance / (distance + z)
        pts.append((cx + x * f, cy + y * f))
    ctx = cv.ctx
    front = {}
    for fc in faces:
        (ax, ay), (bx, by), (qx, qy) = (pts[i] for i in fc)
        front[fc] = (bx - ax) * (qy - ay) - (by - ay) * (qx - ax) < 0
        ctx.new_path()
        ctx.move_to(ax, ay)
        ctx.line_to(bx, by)
        ctx.line_to(qx, qy)
        ctx.close_path()
        ctx.set_source_rgba(*rgba(color, fill))
        ctx.fill()
    edges = {}
    for fc in faces:
        for i in range(3):
            e = tuple(sorted((fc[i], fc[(i + 1) % 3])))
            edges.setdefault(e, []).append(front[fc])
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for (i, j), facing in edges.items():
        rim = len(set(facing)) == 2
        alpha, w = (1.0, width * 1.8) if rim else ((0.85, width) if any(facing) else (0.35, width * 0.7))
        ctx.move_to(*pts[i])
        ctx.line_to(*pts[j])
        ctx.set_source_rgba(*rgba(color, alpha))
        ctx.set_line_width(w)
        ctx.stroke()


TINT = '#5ec8ff'


def draw(n, cv):
    t = n / demo.FPS
    cx, cy, r = demo.W / 2, demo.H / 2 - 30, 150
    level = hologram_flicker(t - 0.15, warmup=0.9, seed=4)
    # the projector it is cast from: an emitter disc and a faint cone of light
    base_y = cy + r + 70
    ctx = cv.ctx
    cone = cairo.LinearGradient(0, base_y, 0, cy - r)
    c = rgba(TINT)
    cone.add_color_stop_rgba(0, *c[:3], 0.18 * level)
    cone.add_color_stop_rgba(1, *c[:3], 0)
    ctx.move_to(cx - 50, base_y)
    ctx.line_to(cx - r * 1.1, cy - r)
    ctx.line_to(cx + r * 1.1, cy - r)
    ctx.line_to(cx + 50, base_y)
    ctx.close_path()
    ctx.set_source(cone)
    ctx.fill()
    ctx.save()
    ctx.translate(cx, base_y)
    ctx.scale(1, 0.22)
    ctx.arc(0, 0, 64, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(*rgba('#2a3340'))
    ctx.fill()
    ctx.save()
    ctx.translate(cx, base_y)
    ctx.scale(1, 0.22)
    ctx.arc(0, 0, 40, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(*rgba(tk.mix(TINT, '#ffffff', 0.5), 0.3 + 0.7 * level))
    ctx.fill()

    verts, faces = icosahedron(r)
    yaw, pitch = 0.5 + t * 0.9, 0.35 + 0.15 * math.sin(t * 1.3)
    box = vb.Box(cx - r, cy - r, 2 * r, 2 * r)
    hologram(cv, lambda c, col: wire_solid(c, verts, faces, cx, cy, yaw, pitch, col), box, TINT,
             level=level, t=t, jitter=10, seed=4)
    cv.mark('hologram', *box)


TECHNIQUE = Technique(
    id='hologram-effect',
    name='Hologram effect',
    family='camera',
    group='3D motion',
    aliases=('holographic projection', 'scanline hologram', 'holographic scanline', 'projected light scan',
             'sci-fi projection'),
    definition='An object rendered in a single glowing colour, partly see-through and striped with fine '
               'scanlines, that flickers like light beamed into the air.',
    phrasings=('make it look like a sci-fi hologram projected above a table',
               'a see-through glowing blue model with scan lines that flickers on',
               'show the 3D shape as a flickering holographic projection'),
    related=('op-art-vibrating-pattern', 'gooch-shading', 'lens-distortion', 'solarization', 'heat-haze',
             'lens-flare'),
    api=('videobuilder.techniques.camera.hologram_effect.hologram',
         'videobuilder.techniques.camera.hologram_effect.hologram_flicker',
         'videobuilder.techniques.camera.hologram_effect.wire_solid',
         'videobuilder.techniques.camera.hologram_effect.icosahedron'),
    demo=lambda: demo.film(draw),
)
