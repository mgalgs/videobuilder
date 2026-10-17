"""Post-Impressionist swirl: thousands of short, loaded, round-capped strokes.
The sky's dabs orbit two vortices (inner rings faster), halo rings turn round
the sun, stars spin crowns of dabs, the water's dabs ride a wave field, and
every shape is laid in with strokes of its own."""
import math

import cairo

from . import kit
from .look import Look

SKY = '#1a2a66'
SKY_BLUES = [kit.rgb(c) for c in ('#1b2f78', '#24459c', '#3a63c4', '#5b86d8', '#1a2a5e')]
LIGHTS = [kit.rgb(c) for c in ('#9cc3f0', '#dfe9f2', '#6fa0e0', '#f3e7a6')]
SEA = [kit.rgb(c) for c in ('#1f4a8a', '#2c62a8', '#0f2347', '#9cc3f0')]
SUN_RING = [kit.rgb(c) for c in ('#f6e27a', '#fbf3c4', '#e9c64a')]
# role -> (base fill, dab colours)
STROKES = {
    'land': ('#24331f', ('#3f5a2a', '#5a6e2f', '#2a3a20', '#8a7a3a')),
    'building': ('#d8b45a', ('#f0d68a', '#b98d3a')),
    'figure': ('#3a2a1a', ('#e9d9a0', '#7a5a2a')),
    'light': ('#f7d94c', ('#fff3a8', '#f2c34a')),
    'sky': ('#1a2a66', ('#3a63c4', '#5b86d8')),
    'water': ('#152a55', ('#1f4a8a', '#2c62a8')),
}


def _vortices(scene):
    """Two eddies in the sky, laid out from the frame: a big one turning
    one way beside the sun, a smaller one the other way across from it."""
    sx, sy, _ = scene.sun_or_default()
    sky_h = scene.sky_bottom
    big = (scene.w * 0.5 + (sx - scene.w * 0.5) * -0.25, sky_h * 0.62, 0.23 * min(scene.w, sky_h * 1.4), 1)
    small = (scene.w * 0.14 if sx > scene.w / 2 else scene.w * 0.86, sky_h * 0.3, 0.17 * min(scene.w, sky_h * 1.4), -1)
    return big, small


def _sky_dabs(scene):
    """Each sky dab with the vortex it orbits (or None), worked out once per layout."""
    key = (scene.w, scene.h, scene.sky_bottom, scene.sun_or_default())
    cached = _CACHE.get(key)
    if cached:
        return cached
    u = scene.u
    vort = _vortices(scene)
    out = []
    for x, y, tone, ph, _ in kit.jittered_grid(scene.w, scene.sky_bottom, 19 * u, 6 * u, 3, extra=10 * u):
        home = None
        for vi, (vx, vy, vr, _) in enumerate(vort):
            r = math.hypot(x - vx, y - vy)
            if r < vr:
                home = (vi, r, math.atan2(y - vy, x - vx))
        out.append((x, y, home, tone, ph))
    if len(_CACHE) > 8:
        _CACHE.clear()
    _CACHE[key] = (vort, out)
    return vort, out


_CACHE = {}


def _region_strokes(cv, scene, region, t):
    u = scene.u
    c = cv.ctx
    base, cols = STROKES[region.role]
    kit.fill(cv, region.points, base)
    x0, y0, w, h = region.bbox
    with kit.clip_to(cv, region.points):
        if region.role in ('land', 'sky', 'water'):
            for x, y, tone, ph, _ in kit.jittered_grid(scene.w, scene.h, 18 * u, 5 * u, 7):
                if x0 - 20 * u < x < x0 + w + 20 * u and y0 - 20 * u < y < y0 + h + 20 * u:
                    ang = 1.1 + 0.25 * math.sin(t * 2.5 + ph)
                    kit.dab(c, x, y, ang, 20 * u, kit.rgb(cols[int(tone * len(cols))]), 8 * u)
        else:
            # stacked strokes across the shape, each wobbling on its own
            rows = max(2, int(h / (21 * u)))
            for i in range(rows + 1):
                yy = y0 + i * h / rows
                kit.dab(c, x0 + w / 2 + 6 * u * math.sin(i + t * 3), yy, 0.15 * math.sin(i * 1.7), w * 1.1,
                        kit.rgb(cols[i % len(cols)]), max(4 * u, min(9 * u, h / rows * 0.9)))
    if region.role == 'light':
        glow = 0.7 + 0.3 * math.sin(t * 6)
        kit.disc(cv, x0 + w / 2, y0 + h / 2, max(w, h) * 0.95, '#fbe98a', 0.3 * glow)


def paint(cv, scene, t, age):
    c = cv.ctx
    u = scene.u
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    cv.rect(0, 0, scene.w, scene.h, SKY)
    vort, dabs = _sky_dabs(scene)
    span = scene.w + 40 * u
    for x, y, home, tone, ph in dabs:
        if home:
            vi, r, a0 = home
            vx, vy, vr, vd = vort[vi]
            spin = 1.1 * (1.15 - r / vr)      # the inner rings turn faster
            a = a0 + vd * spin * t
            px, py = vx + r * math.cos(a), vy + r * math.sin(a) * 0.82
            ang = a + vd * math.pi / 2
            ring = int(r / (34 * u)) % 3
            col = LIGHTS[int(tone * 4)] if ring == 0 or tone > 0.78 else SKY_BLUES[int(tone * 5)]
        else:
            px = (x + 46 * u * t) % span - 20 * u
            py = y
            ang = 0.5 * math.sin(y / (80 * u) + px / (160 * u) + t * 0.8)
            col = SKY_BLUES[int(tone * 5)] if tone < 0.85 else LIGHTS[0]
        kit.dab(c, px, py, ang, 25 * u, col, 8 * u)
    # the sun in its halo rings, each ring turning
    if scene.sun:
        mx, my, mr = scene.sun
        for k, f in enumerate((1.75, 1.45, 1.16)):
            rr = mr * f
            n = max(8, int(rr / (7 * u)))
            for i in range(n):
                a = 2 * math.pi * i / n + (0.6 if k % 2 else -0.6) * t
                kit.dab(c, mx + rr * math.cos(a), my + rr * math.sin(a), a + math.pi / 2, 20 * u,
                        SUN_RING[(i + k) % 3], 9 * u)
        kit.disc(cv, mx, my, mr - 6 * u, '#f7d94c')
        for i in range(18):
            a = 2 * math.pi * i / 18 + 0.4 * t
            kit.dab(c, mx + mr * 0.53 * math.cos(a), my + mr * 0.53 * math.sin(a), a + 1.2, 22 * u,
                    kit.rgb('#fff3a8'), 8 * u)
    for x, y, ph in scene.stars:
        pulse = 1 + 0.25 * math.sin(2 * math.pi * t / 1.2 + ph)
        kit.disc(cv, x, y, 9 * u * pulse, '#fbe98a')
        for i in range(8):
            a = 2 * math.pi * i / 8 + 1.5 * t + ph
            kit.dab(c, x + 21 * u * pulse * math.cos(a), y + 21 * u * pulse * math.sin(a), a + math.pi / 2,
                    11 * u, kit.rgb('#f3e7a6', 0.85), 5 * u)
    # water: horizontal dabs riding a wave field
    if scene.horizon is not None:
        top = scene.horizon
        cv.rect(0, top, scene.w, scene.h - top, '#152a55')
        sea_span = scene.w + 60 * u
        for x, y, tone, ph, _ in kit.jittered_grid(scene.w, scene.h - top, 21 * u, 6 * u, 4):
            px = (x + 34 * u * t) % sea_span - 30 * u
            ang = 0.35 * math.sin(px / (60 * u) + y / (45 * u) - t * 2.2)
            kit.dab(c, px, top + y, ang, 26 * u, SEA[int(tone * 4)], 8 * u)
    for pts, s in kit.beams(scene, t):
        kit.fill(cv, pts, '#f7e27a', 0.28 * s)
    for region in scene.regions:
        _region_strokes(cv, scene, region, t)


LOOK = Look('swirl', 'Post-Impressionist swirl', 'the sky turns in thick dabs', paint,
            aliases=('post-impressionist', 'impressionist', 'brushstrokes', 'painterly'))
