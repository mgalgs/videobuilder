"""Bauhaus geometry: primary colours, circles, half-discs and blocks on a
cream ground. The sun's four quarters turn, rows of half-discs roll opposite
ways across the water, stars become shapes that pulse on the beat, and
buildings stack up as coloured blocks."""
import math

from . import kit
from .look import Look

CREAM = '#f1ebdc'
RED, YELLOW, BLUE, BLACK = '#d8342a', '#f2c230', '#1f4fa0', '#1c1c1c'
FILLS = {
    'land': (BLACK,),
    'building': None,        # stacked blocks, see below
    'figure': (BLACK, RED),
    'light': (YELLOW,),
    'sky': (CREAM,),
    'water': (BLUE,),
}


def paint(cv, scene, t, age):
    u = scene.u
    w, h = scene.w, scene.h
    sky_h = scene.sky_bottom
    cv.rect(0, 0, w, h, CREAM)
    x = 0.0
    while x < w:
        cv.line(x, sky_h * 0.35, x, sky_h, '#d8d0bc', width=2 * u)
        x += 180 * u
    mx, my, mr = scene.sun_or_default()
    spin = t * 1.4
    for i, col in enumerate((RED, YELLOW, BLUE, BLACK)):
        cv.sector(mx, my, mr + 40 * u, spin + i * math.pi / 2, spin + (i + 1) * math.pi / 2, col)
    kit.disc(cv, mx, my, mr * 0.4, CREAM)
    beat = kit.pulse(t, scene.bpm)
    for i, (sx, sy, _) in enumerate(scene.stars[:12]):
        s = (14 + 14 * beat * (1 if i % 2 == 0 else 0.4)) * u
        col = (BLUE, RED, YELLOW)[i % 3]
        if i % 2:
            cv.rect(sx - s, sy - s, 2 * s, 2 * s, col)
        else:
            kit.disc(cv, sx, sy, s, col)
    for pts, s in kit.beams(scene, t):
        kit.fill(cv, pts, YELLOW, 0.35 + 0.5 * s)
    if scene.horizon is not None:
        top = scene.horizon
        cv.rect(0, top, w, h - top, BLUE)
        r = 60 * u
        row = 0
        y = top + 70 * u
        while y - r < h:                             # rows of half-discs rolling, alternate ways
            off = (t * (90 if row % 2 else -90) * u) % (2 * r)
            for k in range(-1, int(w // (2 * r)) + 2):
                cv.sector(k * 2 * r + off, y, r, math.pi, 2 * math.pi, (CREAM, '#13306a')[row % 2])
            y += 130 * u
            row += 1
    seen = {}
    for region in scene.regions:
        k = seen.get(region.role, 0)
        seen[region.role] = k + 1
        if region.role == 'building':
            # a building is a stack of coloured blocks
            x0, y0, rw, rh = region.bbox
            if rh > 40 * u:
                kit.bands(cv, region.points, (RED, CREAM) if k % 2 == 0 else (BLUE, YELLOW), 74 * u, offset=y0)
                kit.outline(cv, region.points, BLACK, 3 * u)
            else:
                kit.fill(cv, region.points, BLACK)
            continue
        fills = FILLS[region.role]
        kit.fill(cv, region.points, fills[k % len(fills)])
    # a red dot that swells on every beat, in the open
    water = scene.open_water()
    dx = (water[0] + water[1]) / 2 if water else w * 0.76
    dy = (scene.horizon - 130 * u) if scene.horizon is not None else h * 0.8
    kit.disc(cv, dx, dy, (26 + 12 * beat) * u, RED)


LOOK = Look('bauhaus', 'Bauhaus geometry', 'shapes turn and roll on the beat', paint,
            aliases=('geometric', 'modernist', 'constructivist', 'primary colours', 'primary colors', 'mid-century'))
