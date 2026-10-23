"""Mandelbulb raymarch: the 3D Mandelbrot-like fractal, found by sphere-tracing
rays against its distance estimate and lit like a solid, so its lobed,
self-similar surface turns in space."""
import math

from PIL import Image as PILImage

import videobuilder as vb

from .. import _demo as demo
from ..schema import Capability


def _rgb(color):
    r, g, b, _ = vb.canvas.rgba(color)
    return r, g, b


def bulb_distance(x, y, z, power=8.0, iterations=7):
    """Distance estimate from (x, y, z) to the Mandelbulb of `power`, and an
    orbit trap in [0, 1] (how close the orbit came to the origin), for colour."""
    zx, zy, zz = x, y, z
    dr, r, trap = 1.0, 0.0, 1e9
    for _ in range(iterations):
        r = math.sqrt(zx * zx + zy * zy + zz * zz)
        if r > 2.0:
            break
        trap = min(trap, r)
        if r < 1e-9:
            return 0.0, 0.0
        theta = math.acos(zz / r) * power
        phi = math.atan2(zy, zx) * power
        rp = r ** power
        dr = power * rp / r * dr + 1.0
        st = math.sin(theta)
        zx = rp * st * math.cos(phi) + x
        zy = rp * st * math.sin(phi) + y
        zz = rp * math.cos(theta) + z
    return 0.5 * math.log(r) * r / dr if r > 1e-9 else 0.0, min(1.0, trap)


def mandelbulb(width, height, yaw=0.0, pitch=0.35, distance=2.6, power=8.0, fov=0.9,
               colors=('#4fc3b0', '#ef5b4c'), light=(0.6, 0.8, -0.5), steps=64, iterations=7):
    """A `width` x `height` RGBA PIL image of the Mandelbulb of `power`, raymarched
    from a camera `distance` from the centre at angle `yaw` round it and `pitch`
    above it (radians), with a vertical field of view `fov`. The surface shades
    from `colors[0]` (deep in the folds) to `colors[1]` (outer lobes); the rest
    is transparent, so it sits on any background. Pure Python: keep it small
    (a few hundred pixels across) and scale it up with `draw_mandelbulb`."""
    cp, sp, cy, sy = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    ex, ey, ez = distance * cp * sy, distance * sp, -distance * cp * cy        # eye
    fx, fy, fz = -ex / distance, -ey / distance, -ez / distance                # forward, at the origin
    rx, rz = cy, sy                                                           # right (level)
    ux, uy, uz = fy * rz, fz * rx - fx * rz, -fy * rx                         # up = forward x right
    ln = math.sqrt(sum(c * c for c in light))
    lx, ly, lz = (c / ln for c in light)
    deep, outer = _rgb(colors[0]), _rgb(colors[1])
    half = math.tan(fov / 2)
    eps = 0.6 * half * 2 / height                                             # about one pixel at unit range
    bound = 1.25                                                              # the bulb fits in this sphere
    data = bytearray(width * height * 4)
    for j in range(height):
        v = (1 - 2 * (j + 0.5) / height) * half
        for i in range(width):
            u = (2 * (i + 0.5) / width - 1) * half * width / height
            dx, dy, dz = fx + u * rx + v * ux, fy + v * uy, fz + u * rz + v * uz
            n = math.sqrt(dx * dx + dy * dy + dz * dz)
            dx, dy, dz = dx / n, dy / n, dz / n
            b = ex * dx + ey * dy + ez * dz                                   # ray against the bounding sphere
            c = ex * ex + ey * ey + ez * ez - bound * bound
            disc = b * b - c
            if disc < 0:
                continue
            t, far = max(0.0, -b - math.sqrt(disc)), -b + math.sqrt(disc)
            hit = False
            for k in range(steps):
                px, py, pz = ex + t * dx, ey + t * dy, ez + t * dz
                d, trap = bulb_distance(px, py, pz, power, iterations)
                if d < eps * t:
                    hit = True
                    break
                t += d
                if t > far:
                    break
            if not hit:
                continue
            h = eps * t                                                       # normal from the DE's gradient
            gx = bulb_distance(px + h, py, pz, power, iterations)[0] - bulb_distance(px - h, py, pz, power, iterations)[0]
            gy = bulb_distance(px, py + h, pz, power, iterations)[0] - bulb_distance(px, py - h, pz, power, iterations)[0]
            gz = bulb_distance(px, py, pz + h, power, iterations)[0] - bulb_distance(px, py, pz - h, power, iterations)[0]
            gn = math.sqrt(gx * gx + gy * gy + gz * gz) or 1.0
            nx, ny, nz = gx / gn, gy / gn, gz / gn
            diffuse = max(0.0, nx * lx + ny * ly + nz * lz)
            rim = (1 - max(0.0, -(nx * dx + ny * dy + nz * dz))) ** 3
            occlusion = 1 - k / steps                                          # many steps: a crevice
            m = vb.clamp01((trap - 0.6) / 0.35) ** 1.5
            shade = (0.12 + 0.88 * diffuse) * occlusion ** 1.5 + 0.35 * rim
            o = (j * width + i) * 4
            for ch in range(3):
                col = deep[ch] + (outer[ch] - deep[ch]) * m
                data[o + ch] = min(255, int(255 * col * shade))
            data[o + 3] = 255
    return PILImage.frombytes('RGBA', (width, height), bytes(data))


def draw_mandelbulb(cv, x, y, w, h, quality=0.25, **kw):
    """Draw a raymarched Mandelbulb filling the box (x, y, w, h), rendered at
    `quality` of the output's pixel size and scaled up smoothly. `kw` goes to
    `mandelbulb` (yaw, pitch, distance, power, colors ...). Returns the Box."""
    s = cv.scale_factor() * quality
    rw, rh = max(8, round(w * s)), max(8, round(h * s))
    cv.image(vb.Image.from_pil(mandelbulb(rw, rh, **kw)), x, y, w, h)
    return vb.Box(x, y, w, h)


def draw(n, cv):
    p = n / (demo.FPS * demo.SECONDS)
    w, h = demo.H * 1.2, demo.H
    x = (demo.W - w) / 2
    # A gentle push-in that stops well short of the frame: at 3.0 the bulb's
    # bounding sphere still spans under nine-tenths of the height.
    box = draw_mandelbulb(cv, x, 0, w, h, quality=0.4, yaw=0.3 + 1.6 * p, pitch=0.5 - 0.3 * p,
                          distance=3.3 - 0.3 * p, colors=(demo.TEAL, demo.ACCENT))
    cv.mark('bulb', *box)


CAPABILITY = Capability(
    id='mandelbulb-raymarch',
    name='Mandelbulb raymarch',
    family='particles',
    group='Fractals',
    aliases=('mandelbulb', '3d mandelbrot', 'raymarched fractal', 'fractal bulb'),
    definition='A lumpy three-dimensional fractal whose bulbs sprout smaller bulbs without end, '
               'rendered as a lit solid by stepping rays toward its surface, turning slowly in space.',
    phrasings=('a 3D fractal blob that slowly rotates',
               'that alien cauliflower-looking Mandelbrot thing but in 3D',
               'fly around a glowing fractal sculpture'),
    related=('raymarched-sdf-shapes', 'penrose-tiling', 'fractal-brownian-motion', 'solid-drawing',
             'god-rays', 'tessellation-triangle-flip'),
    api=('videobuilder.capabilities.particles.mandelbulb_raymarch.draw_mandelbulb',
         'videobuilder.capabilities.particles.mandelbulb_raymarch.mandelbulb',
         'videobuilder.capabilities.particles.mandelbulb_raymarch.bulb_distance'),
    demo=lambda: demo.film(draw),
)
