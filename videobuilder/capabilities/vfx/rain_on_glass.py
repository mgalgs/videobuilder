"""Rain on glass: a scene seen through a wet window. The glass is fogged, so
the scene behind it reads soft; every droplet on it is a tiny lens showing a
sharp, upside-down copy of the scene. New drops keep landing, and once a drop
grows heavy enough it slides down in fits and starts, swallowing the drops in
its way and leaving a clear streak with a few beads behind it."""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image as PILImage, ImageFilter

from .. import _demo as demo
from ..schema import Technique
from ...canvas import Canvas, rgba


class _Drop:
    __slots__ = ('x', 'y', 'r', 'hold', 'vx')

    def __init__(self, x, y, r, hold=0):
        self.x, self.y, self.r, self.hold, self.vx = x, y, r, hold, 0.0


def _merge(a, b):
    """Fold drop `b` into `a`: areas add, and the centre moves toward `b` by its share."""
    area = a.r * a.r + b.r * b.r
    k = b.r * b.r / area
    a.x += (b.x - a.x) * k * 0.5          # a runner mostly keeps its line
    a.y += (b.y - a.y) * k * 0.5
    a.r = math.sqrt(area)


@lru_cache(maxsize=4)
def droplet_frames(frames, width=960, height=540, seed=3, count=150, rain=1.2, slide_at=11.0,
                   runners=((0.12, 0.08, 15.0, 6), (0.5, 0.02, 14.0, 22), (0.78, 0.12, 16.0, 2),
                            (0.32, 0.3, 13.0, 40), (0.9, 0.4, 13.5, 30))):
    """The droplets and cleared streaks on a `width` x `height` pane for every
    frame of a shot, as a tuple of `(drops, streaks)`: `drops` a tuple of
    `(x, y, rx, ry)` ellipses, `streaks` a tuple of `(x0, y0, x1, y1, width)`
    segments wiped clear so far. `count` drops sit on the glass at the start
    and about `rain` more land each frame; any drop at least `slide_at` px in
    radius slides down, pausing now and then, merging with what it meets and
    shedding small beads. `runners` seeds heavy drops `(x, y, r, start
    frame)` (x, y as fractions of the pane) so something slides early.
    Deterministic and cached: a film can ask for any frame in any order."""
    rng = random.Random(seed)

    def small():
        return 1.6 + rng.random() ** 2.2 * 8.5

    drops = [_Drop(rng.uniform(0, width), rng.uniform(0, height), small()) for _ in range(count)]
    drops += [_Drop(fx * width, fy * height, r, hold=start) for fx, fy, r, start in runners]
    streaks, out = [], []
    for _ in range(frames):
        landing = int(rain) + (rng.random() < rain - int(rain))
        for _ in range(landing):
            d = _Drop(rng.uniform(0, width), rng.uniform(0, height), small())
            for o in drops:
                if (o.x - d.x) ** 2 + (o.y - d.y) ** 2 < (o.r + d.r) ** 2 * 0.6:
                    _merge(o, d)
                    break
            else:
                drops.append(d)
        for d in [d for d in drops if d.r >= slide_at]:
            if d not in drops:
                continue                     # merged into another runner this frame
            if d.hold > 0:
                d.hold -= 1
                continue
            speed = (d.r - slide_at + 2.5) * 0.9 * (0.5 + rng.random())
            d.vx = d.vx * 0.8 + rng.uniform(-0.6, 0.6)
            x0, y0 = d.x, d.y
            d.x += d.vx
            d.y += speed
            streaks.append((x0, y0, d.x, d.y, d.r * 1.3))
            if rng.random() < 0.035:
                d.hold = rng.randint(3, 12)  # snags on the glass for a moment
            if rng.random() < speed / 30 and d.r > slide_at * 0.9:
                bead = _Drop(x0 + rng.uniform(-2, 2), y0, 1.5 + rng.random() * 2.2)
                d.r = math.sqrt(d.r * d.r - bead.r * bead.r)
                drops.append(bead)
            for o in list(drops):
                if o is not d and (o.x - d.x) ** 2 + (o.y - d.y) ** 2 < (o.r + d.r) ** 2 * 0.7:
                    _merge(d, o)
                    drops.remove(o)
            if d.y - d.r > height:
                drops.remove(d)
        out.append((tuple((d.x, d.y, d.r * (0.92 if d.r >= slide_at else 1.0),
                           d.r * (1.18 if d.r >= slide_at else 1.0)) for d in drops), tuple(streaks)))
    return tuple(out)


def _blurred(surface, radius):
    w, h = surface.get_width(), surface.get_height()
    surface.flush()
    pil = PILImage.frombuffer('RGBA', (w, h), bytes(surface.get_data()), 'raw', 'BGRA', 0, 1)
    data = bytearray(pil.filter(ImageFilter.GaussianBlur(radius)).tobytes('raw', 'BGRA'))
    return cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, w, h, w * 4)


def _paint_device(ctx, surface, scale, alpha=1.0):
    ctx.save()
    ctx.scale(1 / scale, 1 / scale)
    ctx.set_source_surface(surface, 0, 0)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def draw_rain_on_glass(cv, scene, drops, streaks=(), blur=9.0, fog='#8fa3b8', fog_alpha=0.16, lens=0.32,
                       clear=0.75):
    """Draw `scene(cv)` (a full-frame draw function) as if through a wet
    pane of glass: the scene blurred by `blur` px and washed with `fog`, the
    `streaks` (see `droplet_frames`) wiped back to sharp at `clear` opacity,
    and each drop `(x, y, rx, ry)` a lens showing the scene sharp, shrunk by
    `lens` and turned upside down, with a dark rim, a bright lower edge and
    a glint."""
    s = cv.scale
    sharp = Canvas(cv.width, cv.height, scale=s, format=cv.format)
    scene(sharp)
    sharp.surface.flush()
    c = cv.ctx
    _paint_device(c, _blurred(sharp.surface, max(0.5, blur * s)), s)
    cv.fill(fog, alpha=fog_alpha)

    if streaks:
        c.save()
        # a stroke can't be a clip, so mask the sharp scene with a group of the strokes
        c.push_group_with_content(cairo.CONTENT_ALPHA)
        c.set_source_rgba(0, 0, 0, 1)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        for x0, y0, x1, y1, w in streaks:
            c.move_to(x0, y0)
            c.line_to(x1, y1)
            c.set_line_width(w)
            c.stroke()
        mask = c.pop_group()
        c.push_group()
        _paint_device(c, sharp.surface, s, clear)
        c.pop_group_to_source()
        c.mask(mask)
        c.restore()

    for x, y, rx, ry in drops:
        r = max(rx, ry)
        c.save()
        c.translate(x, y)
        c.scale(rx, ry)
        c.arc(0, 0, 1, 0, 2 * math.pi)
        c.restore()
        c.save()
        c.clip_preserve()
        # the lens: the scene around the drop, shrunk and turned over
        c.save()
        c.translate(x, y)
        c.scale(-lens, -lens)
        c.translate(-x, -y)
        _paint_device(c, sharp.surface, s)
        c.restore()
        g = cairo.RadialGradient(x, y - r * 0.15, 0, x, y, r)
        g.add_color_stop_rgba(0.0, 1, 1, 1, 0.06)
        g.add_color_stop_rgba(0.6, 0, 0, 0, 0.0)
        g.add_color_stop_rgba(1.0, 0, 0, 0, 0.55)
        c.set_source(g)
        c.fill()
        lo = cairo.RadialGradient(x, y + r * 0.55, 0, x, y + r * 0.55, r * 0.7)
        lo.add_color_stop_rgba(0, 1, 1, 1, 0.22)
        lo.add_color_stop_rgba(1, 1, 1, 1, 0)
        c.set_source(lo)
        c.paint()
        c.restore()
        if r > 2.5:
            c.save()
            c.translate(x - rx * 0.38, y - ry * 0.42)
            c.scale(rx * 0.22, ry * 0.15)
            c.arc(0, 0, 1, 0, 2 * math.pi)
            c.restore()
            c.set_source_rgba(1, 1, 1, 0.75)
            c.fill()


def _city(cv):
    """The demo's view out of the window: a dusk sky, a low sun and a row of
    lit towers, with enough contrast that the lenses read."""
    c, W, H = cv.ctx, demo.W, demo.H
    sky = cairo.LinearGradient(0, 0, 0, H)
    sky.add_color_stop_rgb(0, *rgba('#1d2a4a')[:3])
    sky.add_color_stop_rgb(0.62, *rgba('#c4614f')[:3])
    sky.add_color_stop_rgb(1, *rgba(demo.BG)[:3])
    c.rectangle(0, 0, W, H)
    c.set_source(sky)
    c.fill()
    glow = cairo.RadialGradient(W * 0.68, H * 0.5, 0, W * 0.68, H * 0.5, 240)
    glow.add_color_stop_rgba(0, *rgba('#ffd27a')[:3], 0.55)
    glow.add_color_stop_rgba(1, *rgba('#ffd27a')[:3], 0)
    c.set_source(glow)
    c.paint()
    demo.dot(cv, W * 0.68, H * 0.5, r=62, color='#ffcf6e')
    rng = random.Random(7)
    x = -10
    while x < W:
        w = rng.uniform(46, 110)
        top = H * rng.uniform(0.48, 0.72)
        cv.rect(x, top, w - 6, H - top, '#191c27')
        for wy in range(int(top) + 14, H - 10, 22):
            for wx in range(int(x) + 10, int(x + w - 18), 18):
                if rng.random() < 0.35:
                    cv.rect(wx, wy, 8, 10, rng.choice(('#ffd27a', '#ffe9b8', demo.TEAL)), alpha=0.9)
        x += w
    cv.rect(0, H - 40, W, 40, '#101118')


def draw(n, cv):
    frames = droplet_frames(round(demo.SECONDS * demo.FPS), demo.W, demo.H)
    drops, streaks = frames[min(n, len(frames) - 1)]
    draw_rain_on_glass(cv, _city, drops, streaks)
    cv.mark('pane', 0, 0, demo.W, demo.H)


TECHNIQUE = Technique(
    id='rain-on-glass',
    name='Rain on glass',
    family='vfx',
    group='Water & atmosphere',
    aliases=('window rain', 'droplets on glass', 'wet window', 'raindrops on a window'),
    definition='The scene is seen through a misted window dotted with water drops, each a tiny lens '
               'holding a sharp upside-down view, while heavy drops run down, gulp smaller ones and '
               'leave clear streaks.',
    phrasings=('make it look like we are watching the city through a rainy window',
               'put water droplets on the screen that slide down like rain on a car window',
               'a cosy rainy-day shot with drops running down the glass in front'),
    related=('rainfall', 'falling-letter-rain', 'glass-refraction', 'shatter', 'matrix-digital-rain',
             'falling-glyph-rain-reveal'),
    api=('videobuilder.techniques.vfx.rain_on_glass.draw_rain_on_glass',
         'videobuilder.techniques.vfx.rain_on_glass.droplet_frames'),
    demo=lambda: demo.film(draw),
)
