"""8-bit pixel: the whole scene drawn at a fraction of the resolution and
scaled back up hard-edged, every move stepped at 8 frames a second. The
water's rows shift a block at a time, stars blink with crosses, lights
flash, and the beacon's beams turn in steps.

Options: `block` -- the size of one pixel in film px (12 at 1080)."""
import math

from . import kit
from .look import Look

NIGHT = ('#14123a', '#1c1a52', '#2a2266', '#3a2a74')
FILLS = {
    'land': ('#2a6a3a', '#3a7a44'),
    'building': ('#e8e8e8', '#d83a3a', '#8a8ab8'),
    'figure': ('#8a4a2a', '#f4f0c8'),
    'light': ('#fff07a',),
    'sky': ('#2a2266',),
    'water': ('#1a3a8a',),
}


def paint(cv, scene, t, age, block=None):
    u = scene.u
    w, h = scene.w, scene.h
    ts = math.floor(t * 8) / 8                 # motion stepped at 8 frames a second
    factor = block or max(3.0, round(12 * u))
    sky_h = scene.sky_bottom
    with cv.pixelated(factor, 0, 0, w, h) as px:
        px.rect(0, 0, w, h, NIGHT[0])
        for band, col in enumerate(NIGHT[1:]):
            px.rect(0, sky_h * (0.62 + band * 0.1), w, sky_h * 0.1 + 1, col)
        if scene.sun:
            mx, my, mr = scene.sun
            kit.disc(px, mx, my, mr, '#f4f0c8')
            px.rect(mx - mr * 0.46, my - mr * 0.35, mr * 0.28, mr * 0.28, '#d8d0a0')
            px.rect(mx + mr * 0.12, my + mr * 0.23, mr * 0.42, mr * 0.28, '#d8d0a0')
        s = 6 * u
        for x, y, ph in scene.stars:
            if math.sin(ts * 5 + ph * 3) > -0.2:
                px.rect(x - s, y - s, 2 * s, 2 * s, '#ffffff')
                if math.sin(ts * 5 + ph * 3) > 0.7:
                    px.rect(x - 3 * s, y - s / 2, 6 * s, s, '#a8b8ff')
                    px.rect(x - s / 2, y - 3 * s, s, 6 * s, '#a8b8ff')
        if scene.horizon is not None:
            top = scene.horizon
            px.rect(0, top, w, h - top, '#1a3a8a')
            row, y = 0, top + 30 * u
            while y < h:
                step = int(ts * 8) * 12 * u * (1 if row % 2 else -1)
                period = 150 * u
                for k in range(-2, int(w / period) + 3):
                    x = (k * period + row * 40 * u + step) % (w + period) - period / 2
                    px.rect(x, y, 84 * u, 24 * u, ('#4a7ad8', '#2a5ab8')[row % 2])
                y += 64 * u
                row += 1
        blink = int(ts * 2) % 2
        for pts, s in kit.beams(scene, ts * 1.5):          # the beams turn in steps
            kit.fill(px, pts, '#fff07a', 0.3 + 0.4 * s)
        turn = kit.Turns(FILLS, {'building': '#3a3a5a'}, thin=30 * u)
        first_building = True
        for region in scene.regions:
            colour = turn(region)
            if region.role == 'light':
                colour = '#fff07a' if blink else '#c8a83a'
            kit.fill(px, region.points, colour)
            x0, y0, rw, rh = region.bbox
            if region.role == 'land':                 # a grass edge along the top
                with kit.clip_to(px, region.points):
                    px.rect(x0, y0, rw, 24 * u + 0.05 * rh, '#4a9a4a')
            elif region.role == 'building' and first_building and rh > 140 * u:
                kit.bands(px, region.points, (colour, '#d83a3a'), 74 * u, offset=y0)   # a striped tower
            if region.role == 'building':
                first_building = False


LOOK = Look('pixel', '8-bit pixel', 'the sea steps, stars blink', paint,
            aliases=('8-bit', '8bit', 'pixel art', 'pixelated', 'retro game', 'retro', 'arcade'))
