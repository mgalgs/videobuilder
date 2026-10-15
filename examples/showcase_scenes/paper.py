"""Paper collage: the to-do list on paper gets retired, in three cuts, then
the wall rips open onto the next section. After
examples/capabilities/paper-collage.py, laid out for both shapes of this
film: close on a torn headline as it slaps down, close on the cut-paper
notepad lifting off the wall on its shadow as it's ticked, then wide as an
arrow is drawn and a rubber stamp slams; all held on twos. The rip is the
transition out (examples/showcase.py draws the next shot under the shards).

Its own palette (STYLE.md's style-card exception): wall grey-beige, scrap
off-white, ink, and one accent red."""
import math
import random
from functools import lru_cache

import cairo
from PIL import Image as PILImage, ImageChops, ImageDraw, ImageFilter

import videobuilder as vb
from videobuilder import paths, text

from . import kit
from .kit import rect_points, rounded_points

WALL = '#c3b9ac'
SCRAP = '#efebe3'
INK = '#1b1916'
RED = '#c75431'

HEAD_F = kit.font(78, 900, tracking=-0.035)
STAMP_F = kit.font(54, 900, tracking=0.02)
LABEL_F = kit.font(34, 800, tracking=-0.01)

# ---- timing (frames into the paper sequence: three cuts at 0, 45 and 105) ----
CUTS = (0, 45, 105, 165)
SCRAP_IN = (-4, 8)
PAD_IN = (44, 56)
TICKS = (61, 76, 91)
ARROW = (108, 126)
STAMP_AT = 135
RIP = (0, 13)        # frames into the next section, which the shards uncover
# How each cut frames the wall: zoom, and the point (in wall px) it centres on.
FRAMING = {
    True: ((1.6, (390, 155)), (1.3, (315, 440)), (1.0, (640, 360))),
    False: ((1.12, (360, 213)), (1.38, (360, 595)), (1.0, (360, 640))),
}


def step(n):
    """Stop-motion: paper only moves on even frames."""
    return n - n % 2


def boil(key, n, amount=1.0):
    r = random.Random(f'{key}:{step(n)}')
    return r.uniform(-1, 1) * amount, r.uniform(-1, 1) * amount, math.radians(r.uniform(-0.5, 0.5) * amount)


def progress(n, span, ease=vb.ease_out_back):
    a, z = span
    return ease(vb.clamp01((step(n) - a) / (z - a)))


def transform(ctx, cx, cy, angle, scale=1.0, dx=0.0, dy=0.0):
    ctx.translate(cx + dx, cy + dy)
    ctx.rotate(angle)
    if scale != 1:
        ctx.scale(scale, scale)
    ctx.translate(-cx, -cy)


def grain(cv, alpha, seed=1):
    ctx = cv.ctx
    ctx.set_source(vb.paper_grain(720, 720, seed=seed))
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.paint_with_alpha(alpha)
    ctx.set_operator(cairo.OPERATOR_OVER)


def paper_piece(cv, pts, color, rim=SCRAP, grain_alpha=0.55, seed=1):
    ctx = cv.ctx
    kit.poly(ctx, pts)
    ctx.set_source_rgba(*vb.rgba(color))
    ctx.fill_preserve()
    ctx.save()
    ctx.clip_preserve()
    ctx.set_source_rgba(*vb.rgba(rim, 0.85))
    ctx.set_line_width(3.0)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke_preserve()
    grain(cv, grain_alpha, seed)
    ctx.restore()
    ctx.new_path()


# ---- the layout, one per shape, baked at import ----
class Layout:
    def __init__(self, wide):
        W, H = (1280, 720) if wide else (720, 1280)
        self.W, self.H = W, H
        self.centre = (W / 2, H / 2) if wide else (W / 2, H * 0.46)
        self.scrap = (110, 92, 560, 126) if wide else (90, 150, 540, 126)
        self.pad = (150, 262, 330, 340) if wide else (150, 380, 420, 430)
        self.stamp = (930, 420) if wide else (440, 1000)
        x, y, w, h = self.scrap
        self.scrap_pts = paths.torn(rect_points(x, y, w, h), seed=5, amount=6)
        px, py, pw, ph = self.pad
        self.pad_pts = paths.torn(rounded_points(px - 8, py - 8, pw + 16, ph + 16, 14), seed=7, amount=1.0, step=3)
        self.pad_body = rounded_points(px, py, pw, ph, 10)
        gap = ph / 4
        self.rows = [(px + 34, py + 70 + i * gap) for i in range(3)]
        self.boxes = [paths.jitter(paths.resample(rect_points(bx, by, 40, 40) + [(bx, by)], 24), seed=40 + i,
                                   amount=1.6, wander=0.4) for i, (bx, by) in enumerate(self.rows)]
        self.ticks = [paths.jitter(paths.resample([(bx + 6, by + 18), (bx + 18, by + 34), (bx + 50, by - 8)], 16),
                                   seed=50 + i, amount=1.4) for i, (bx, by) in enumerate(self.rows)]
        if wide:
            a0, a1, wob = (520, 600), (800, 300), 30
        else:
            a0, a1, wob = (300, 990), (620, 880), 10
        self.arrow = paths.jitter([(kit.lerp(a0[0], a1[0], t) + wob * math.sin(t * 6),
                                    kit.lerp(a0[1], a1[1], t * t)) for t in (k / 40 for k in range(41))],
                                  seed=31, amount=2.6, wander=0.35)
        self.edges = (
            (paths.torn([(-40, H * 0.78), (W * 0.22, H * 0.9), (W * 0.15, H + 40), (-40, H + 40)], seed=11, amount=7),
             '#cdc4b8'),
            (paths.torn([(W * 0.7, -40), (W + 40, -40), (W + 40, H * 0.08), (W * 0.86, H * 0.04)], seed=12, amount=7),
             '#b8ad9f'),
        )
        # The rip: radial tears from the centre, and the shards between them.
        cx, cy = self.centre
        self.angles = (-100, -38, 8, 62, 118, 176)
        far = 1800
        self.rays = [paths.torn([self.centre, (cx + far * math.cos(math.radians(a)), cy + far * math.sin(math.radians(a)))],
                                seed=60 + i, amount=10, closed=False) for i, a in enumerate(self.angles)]
        self.shards = []
        for i in range(len(self.angles)):
            a0, a1 = self.angles[i], self.angles[(i + 1) % len(self.angles)]
            if a1 < a0:
                a1 += 360
            rim = [(cx + far * math.cos(math.radians(a)), cy + far * math.sin(math.radians(a)))
                   for a in (a0 + (a1 - a0) * k / 6 for k in range(7))]
            mid = math.radians((a0 + a1) / 2)
            self.shards.append((self.rays[i] + rim + list(reversed(self.rays[(i + 1) % len(self.rays)])),
                                (math.cos(mid), math.sin(mid))))


LAYOUTS = {True: Layout(True), False: Layout(False)}


@lru_cache(maxsize=1)
def stamp_image():
    tw, th = text.block_size(['RETIRED'], STAMP_F)
    pw, ph = round(tw + 70), round(th + 38)
    cv = vb.Canvas(pw, ph)
    cv.outline(5, 5, pw - 10, ph - 10, RED, width=7, radius=10)
    cv.outline(14, 14, pw - 28, ph - 28, RED, width=2, radius=6)
    text.draw(cv, 'RETIRED', STAMP_F, (pw - tw) / 2, (ph - th) / 2, RED)
    pil = kit.to_pil(cv)
    rnd = random.Random(9)
    speck = PILImage.frombytes('L', (pw // 3, ph // 3), rnd.randbytes((pw // 3) * (ph // 3)))
    speck = speck.resize((pw, ph), PILImage.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    fine = PILImage.frombytes('L', (pw, ph), rnd.randbytes(pw * ph)).filter(ImageFilter.GaussianBlur(0.7))
    wear = PILImage.blend(speck, fine, 0.4).point(lambda v: 0 if v < 92 else (255 if v > 108 else (v - 92) * 16))
    r, g, b, a = pil.split()
    a = ImageChops.multiply(a, wear).point(lambda v: v * 0.92)
    return vb.Image.from_pil(PILImage.merge('RGBA', (r, g, b, a)))


# ---- cached layers: the wall, the light, and the wall as it stands before the rip ----
@lru_cache(maxsize=16)
def _surface(name, wide, scale):
    L = LAYOUTS[wide]
    cv = vb.Canvas(L.W, L.H, scale=scale, format=kit.F16 if wide else kit.F9)
    if name == 'wall':
        draw_wall(cv, L)
    elif name == 'light':
        draw_light(cv, L)
    else:
        draw_scene1(cv, L, CUTS[-1] - 1, marks=False)
    cv.surface.flush()
    return cv.surface


def draw_wall(cv, L):
    cv.fill(WALL)
    grain(cv, 0.45, seed=3)
    for pts, colour in L.edges:
        cv.shape_shadow(pts, dx=2, dy=3, blur=9, color=(40, 30, 20, 0.35))
        paper_piece(cv, pts, colour, rim='#e4ddd2', grain_alpha=0.45, seed=4)


def draw_light(cv, L):
    s = 4
    w, h = L.W // s, L.H // s
    m = PILImage.new('L', (w, h), 104)
    d = ImageDraw.Draw(m)
    for x0, width in ((-90, 70), (-8, 62), (66, 46)):
        d.polygon([(x0, 0), (x0 + width, 0), (x0 + width + h * 0.55, h), (x0 + h * 0.55, h)], fill=170)
    m = m.filter(ImageFilter.GaussianBlur(3.5)).resize((L.W, L.H), PILImage.BICUBIC)
    ramp = PILImage.linear_gradient('L').rotate(45, expand=True).resize((L.W, L.H)).point(lambda v: 150 - v * 44 // 255)
    m = PILImage.blend(m, ramp, 0.3)
    cv.image(vb.Image.from_pil(PILImage.merge('RGB', (m, m, m))), 0, 0, L.W, L.H)


# ---- scene one ----
def draw_scrap(cv, L, n, marks):
    if step(n) < SCRAP_IN[0]:
        return
    t = progress(n, SCRAP_IN)
    x, y, w, h = L.scrap
    cx, cy = x + w / 2, y + h / 2
    jx, jy, jr = boil('scrap', n) if step(n) < SCRAP_IN[1] + 2 else (0, 0, 0)
    lift = 4 + (1 - t) * 14
    ctx = cv.ctx
    ctx.save()
    transform(ctx, cx, cy, math.radians(-3) + (1 - t) * math.radians(9) + jr, dx=jx, dy=-(1 - t) * 300 + jy)
    cv.shape_shadow(L.scrap_pts, dx=lift * 0.5, dy=lift, blur=10 + lift, color=(35, 25, 15, 0.42))
    paper_piece(cv, L.scrap_pts, SCRAP, rim='#fbf9f5', grain_alpha=0.6, seed=6)
    tw, th = text.block_size(['TO-DO LISTS'], HEAD_F)
    box = text.draw(cv, ['TO-DO LISTS'], HEAD_F, cx - tw / 2, cy - th / 2 + 2, INK)
    if marks:
        cv.mark('headline', *box)
    ctx.restore()


def draw_pad(cv, L, n, marks):
    if step(n) < PAD_IN[0]:
        return
    t = progress(n, PAD_IN)
    x, y, w, h = L.pad
    cx, cy = x + w / 2, y + h / 2
    jx, jy, jr = boil('pad', n, 1.2) if step(n) < PAD_IN[1] + 2 else (0, 0, 0)
    lift = 5 + (1 - t) * 22
    ctx = cv.ctx
    ctx.save()
    transform(ctx, cx, cy, math.radians(2.5) + jr, scale=1 + (1 - t) * 0.22, dx=jx - (1 - t) * 40, dy=jy)
    cv.shape_shadow(L.pad_pts, dx=lift * 0.5, dy=lift, blur=10 + lift, color=(35, 25, 15, 0.42))
    paper_piece(cv, L.pad_pts, '#fbf9f5', rim='#ffffff', grain_alpha=0.4, seed=8)
    kit.poly(ctx, L.pad_body)
    ctx.set_source_rgba(*vb.rgba('#f3e7b5'))
    ctx.fill()
    for k in range(1, 9):
        cv.rect(x + 14, y + k * h / 9 + 10, w - 28, 2, '#d8c98f')
    cv.rect(x, y, w, 26, RED, radius=6)
    for i, ((bx, by), word) in enumerate(zip(L.rows, ('Email Sam', 'Plan launch', 'Buy milk'))):
        paths.draw(cv, L.boxes[i], INK, width=3.5, closed=True)
        text.draw(cv, word, LABEL_F, bx + 58, by + 20 - text.line_height(LABEL_F) / 2, INK)
        k = vb.clamp01((step(n) - TICKS[i]) / 4)
        if k > 0:
            paths.draw(cv, paths.reveal(L.ticks[i], k), RED, width=6)
    if marks:
        cv.mark('notepad', x - 8, y - 8, w + 16, h + 16)
    ctx.restore()


def draw_arrow(cv, L, n, marks):
    t = vb.clamp01((step(n) - ARROW[0]) / (ARROW[1] - ARROW[0]))
    if t <= 0:
        return
    paths.draw(cv, paths.reveal(L.arrow, vb.ease_in_out_quart(t)), INK, width=7)
    if t >= 1:
        hx, hy = L.arrow[-1]
        px, py = L.arrow[-5]
        a = math.atan2(hy - py, hx - px)
        for side in (-1, 1):
            b = a + math.pi - side * 0.5
            paths.draw(cv, [(hx + 34 * math.cos(b), hy + 34 * math.sin(b)), (hx, hy)], INK, width=7)
        if marks:
            xs, ys = [p[0] for p in L.arrow], [p[1] for p in L.arrow]
            cv.mark('arrow', min(xs) - 20, min(ys) - 30, max(xs) - min(xs) + 40, max(ys) - min(ys) + 34)


def draw_stamp(cv, L, n, marks):
    if n < STAMP_AT:
        return
    img = stamp_image()
    scale = 1.12 if n - STAMP_AT < 2 else 1.0
    cx, cy = L.stamp
    ctx = cv.ctx
    ctx.save()
    transform(ctx, cx, cy, math.radians(-11), scale=scale)
    cv.image(img, cx - img.w / 2, cy - img.h / 2, img.w, img.h)
    if marks:
        cv.mark('stamp', cx - img.w / 2, cy - img.h / 2, img.w, img.h)
    ctx.restore()


def draw_scene1(cv, L, n, marks=True):
    kit.paint_surface(cv, _surface('wall', L.W > L.H, cv.scale))
    draw_pad(cv, L, n, marks)
    draw_arrow(cv, L, n, marks)
    draw_scrap(cv, L, n, marks)
    draw_stamp(cv, L, n, marks)


def _paint_at(cv, name, wide, zoom, operator=cairo.OPERATOR_OVER):
    """A cached wall-sized layer, drawn at the device scale it's seen at, so a close-up stays sharp."""
    k = cv.scale * zoom
    surf = _surface(name, wide, round(k, 3))
    ctx = cv.ctx
    ctx.save()
    ctx.scale(1 / k, 1 / k)
    ctx.set_source_surface(surf, 0, 0)
    ctx.set_operator(operator)
    ctx.paint()
    ctx.restore()


def collage(cv, s, st):
    """One of the three cuts: the wall as it stands at frame `n` of the sequence, framed for this cut."""
    L = LAYOUTS[st.wide]
    n = s.group_f
    cut = max(i for i, c in enumerate(CUTS[:3]) if n >= c)
    zoom, (fx, fy) = FRAMING[st.wide][cut]
    half_w, half_h = L.W / (2 * zoom), L.H / (2 * zoom)   # keep the wall filling the frame
    fx, fy = min(max(fx, half_w), L.W - half_w), min(max(fy, half_h), L.H - half_h)
    with cv.layer(dx=st.frame.w / 2 - fx * zoom, dy=st.frame.h / 2 - fy * zoom, scale=zoom):
        _paint_at(cv, 'wall', st.wide, zoom)
        # A close-up marks only its subject; the rest is cropped by the framing, on purpose.
        draw_pad(cv, L, n, cut != 0)
        draw_arrow(cv, L, n, cut == 2)
        draw_scrap(cv, L, n, cut != 1)
        draw_stamp(cv, L, n, cut == 2)
        _paint_at(cv, 'light', st.wide, zoom, cairo.OPERATOR_SOFT_LIGHT)


# ---- the rip ----
def clip_half(pts, fx, fy, nx, ny, far=True):
    sign = 1 if far else -1
    side = [sign * ((x - fx) * nx + (y - fy) * ny) for x, y in pts]
    out = []
    for i, p in enumerate(pts):
        q, sq, sp = pts[(i + 1) % len(pts)], side[(i + 1) % len(pts)], side[i]
        if sp >= 0:
            out.append(p)
        if (sp >= 0) != (sq >= 0):
            t = sp / (sp - sq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def reflect(pts, fx, fy, nx, ny):
    out = []
    for x, y in pts:
        d = 2 * ((x - fx) * nx + (y - fy) * ny)
        out.append((x - d * nx, y - d * ny))
    return out


def _half_plane(ctx, fx, fy, nx, ny):
    px, py = -ny * 4000, nx * 4000
    ctx.new_path()
    ctx.move_to(fx + px, fy + py)
    ctx.line_to(fx - px, fy - py)
    ctx.line_to(fx - px + nx * 4000, fy - py + ny * 4000)
    ctx.line_to(fx + px + nx * 4000, fy + py + ny * 4000)
    ctx.close_path()


def draw_shards(cv, L, n):
    scene = _surface('scene1', L.W > L.H, cv.scale)
    ctx = cv.ctx
    cx, cy = L.centre
    t = vb.clamp01((step(n) - RIP[0]) / (RIP[1] - RIP[0]))
    for i, (pts, (ux, uy)) in enumerate(L.shards):
        r = random.Random(70 + i)
        peel = vb.ease_out_quint(vb.clamp01(t / 0.5))
        fly = vb.clamp01((t - 0.35 * r.uniform(0.8, 1.2)) / 0.6)
        fold = 20 + r.uniform(170, 240) * peel + 200 * fly
        travel = 16 * peel + 1300 * fly ** 2.2
        spin = math.radians(r.uniform(-1, 1) * 22) * fly ** 2
        skew = math.radians(r.uniform(-16, 16))
        nx = ux * math.cos(skew) - uy * math.sin(skew)
        ny = ux * math.sin(skew) + uy * math.cos(skew)
        fx, fy = cx + ux * fold, cy + uy * fold
        flat = clip_half(pts, fx, fy, nx, ny, far=True)
        flap = reflect(clip_half(pts, fx, fy, nx, ny, far=False), fx, fy, nx, ny)
        jx, jy, jr = boil(f'shard{i}', n, 1.2)
        ctx.save()
        transform(ctx, fx, fy, spin + jr, dx=ux * travel + jx, dy=uy * travel + jy)
        ctx.save()
        _half_plane(ctx, fx + 7, fy + 13, nx, ny)
        ctx.clip()
        cv.shape_shadow(pts, dx=7, dy=13, blur=28, color=(60, 12, 0, 0.5))
        ctx.restore()
        if len(flat) >= 3:
            ctx.save()
            kit.poly(ctx, flat)
            ctx.clip()
            kit.paint_surface(cv, scene)
            ctx.restore()
        if len(flap) >= 3:
            cv.shape_shadow(flap, dx=8, dy=12, blur=18, color=(40, 20, 5, 0.45))
            ctx.save()
            kit.poly(ctx, flap)
            ctx.clip()
            far = max((x - fx) * nx + (y - fy) * ny for x, y in flap)
            g = cairo.LinearGradient(fx, fy, fx + nx * far, fy + ny * far)
            for stop, colour in ((0, '#8a7f72'), (0.18, '#d6cfc3'), (0.55, '#efeae1'), (1, '#d9d1c4')):
                g.add_color_stop_rgba(stop, *vb.rgba(colour))
            ctx.set_source(g)
            ctx.paint()
            grain(cv, 0.45, seed=5)
            ctx.restore()
        ctx.restore()


def rip(cv, out, st):
    """The wall tearing open from the middle, its shards curling back and
    flying off; drawn over whatever the next shot has under it. `out.exit`
    counts frames since the next shot started."""
    L = LAYOUTS[st.wide]
    draw_shards(cv, L, out.exit)


SCENES = {'paper-head': collage, 'paper-pad': collage, 'paper-stamp': collage}
