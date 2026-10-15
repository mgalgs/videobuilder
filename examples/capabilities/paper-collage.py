"""Capability: paper collage -- the cut-paper explainer look. A grey-beige
paper wall under still window light; a headline printed on a torn scrap
steps in on twos; a cut-paper battery with a white die-cut border slaps
down, its lift shadow following its outline; a hand-drawn arrow rises
while ticks land one by one; a red rubber stamp slams on; then the wall
rips open from the middle, its shards curling back to reveal the accent
red, and a phone is pasted onto that colour with two strips of tape.

    python -m videobuilder preview examples/capabilities/paper-collage.py

Not a loop: it runs one short story, enter to end card, like a scene of
the explainer it stands for. Paper moves in stop-motion -- each piece's
position is sampled on even frames only (15 fps on a 30 fps film), with a
tiny seeded jitter per step -- while the camera and the light stay still.
Everything static (the wall, the light, the first scene as it stands just
before the rip) is drawn once per preview scale and cached, so a frame is
a few paints, not a redraw of the collage.

Its own small palette (STYLE.md's style-card exception): wall grey-beige,
scrap off-white, ink, and one accent red -- the stamp, the charge bars and
the colour behind the wall are all the same red.
"""
import math
import random
import sys
from functools import lru_cache
from pathlib import Path

import cairo
from PIL import Image as PILImage, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import paths, text  # noqa: E402

FPS = 30
FRAMES = 120
W = H = 720

WALL = '#c3b9ac'
SCRAP = '#efebe3'
INK = '#1b1916'
ACCENT = '#c75431'

HEAD_F = _kit.font(70, 900, tracking=-0.035)
STAMP_F = _kit.font(44, 900, tracking=0.02)
LABEL_F = _kit.font(30, 800, tracking=-0.01)

# ---- timing (frames) ----
SCRAP_IN = (6, 18)
BATTERY_IN = (16, 26)
ARROW = (28, 46)
TICKS = (40, 46, 52)
STAMP_AT = 60
RIP = (72, 94)
PHONE_IN = (88, 98)
TAPE_AT = (100, 104)


def step(n):
    """Stop-motion: paper only moves on even frames (held on twos)."""
    return n - n % 2


def boil(key, n, amount=1.0):
    """A tiny seeded per-step jitter: (dx, dy, radians) for this piece at this step."""
    r = random.Random(f'{key}:{step(n)}')
    return r.uniform(-1, 1) * amount, r.uniform(-1, 1) * amount, math.radians(r.uniform(-0.5, 0.5) * amount)


def progress(n, span, ease=vb.ease_out_back):
    a, z = span
    return ease(vb.clamp01((step(n) - a) / (z - a)))


def rect_points(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def rounded_points(x, y, w, h, r, per_corner=8):
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for k in range(per_corner + 1):
            a = math.radians(a0 + 90 * k / per_corner)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def fill_points(ctx, pts):
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def grain(cv, alpha, seed=1):
    """Paper texture over the current clip."""
    ctx = cv.ctx
    ctx.set_source(vb.paper_grain(W, H, seed=seed))
    ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT)
    ctx.paint_with_alpha(alpha)
    ctx.set_operator(cairo.OPERATOR_OVER)


def paper_piece(cv, pts, color, rim=SCRAP, grain_alpha=0.55, seed=1):
    """A torn piece of paper: its fill, its grain, and the pale fibrous rim
    where the tear shows the paper's core."""
    ctx = cv.ctx
    fill_points(ctx, pts)
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


@lru_cache(maxsize=8)
def _surface_at(name, scale):
    """A static layer drawn once per preview scale, kept as a device-sized surface."""
    cv = vb.Canvas(W, H, scale=scale)
    {'wall': draw_wall, 'red': draw_red, 'light': draw_light, 'scene1': lambda c: draw_scene1(c, RIP[0] - 1)}[name](cv)
    cv.surface.flush()
    return cv.surface


def paint_surface(cv, surf, operator=cairo.OPERATOR_OVER):
    ctx = cv.ctx
    ctx.save()
    ctx.scale(1 / cv.scale, 1 / cv.scale)
    ctx.set_source_surface(surf, 0, 0)
    ctx.set_operator(operator)
    ctx.paint()
    ctx.restore()


# ---- the wall ----

EDGE_SHEETS = (  # torn layers of the same paper, lying near the edges
    (paths.torn([(-40, 560), (230, 640), (160, 760), (-40, 760)], seed=11, amount=7), '#cdc4b8'),
    (paths.torn([(500, -40), (760, -40), (760, 60), (620, 26)], seed=12, amount=7), '#b8ad9f'),
    (paths.torn([(676, 300), (760, 270), (760, 520), (690, 470)], seed=13, amount=6), '#cbc2b5'),
)
CREASES = (
    paths.jitter(paths.resample([(40, 300), (210, 160)], 30), seed=21, amount=1.2),
    paths.jitter(paths.resample([(520, 700), (700, 610)], 30), seed=22, amount=1.2),
)


def draw_wall(cv):
    cv.fill(WALL)
    grain(cv, 0.45, seed=3)
    for pts, color in EDGE_SHEETS:
        cv.shape_shadow(pts, dx=2, dy=3, blur=9, color=(40, 30, 20, 0.35))
        paper_piece(cv, pts, color, rim='#e4ddd2', grain_alpha=0.45, seed=4)
    for line in CREASES:
        paths.draw(cv, line, '#f3eee6', width=1.6, alpha=0.35)
        paths.draw(cv, [(x + 1.2, y + 1.6) for x, y in line], '#5a4f43', width=1.2, alpha=0.22)


def draw_light(cv):
    """Window light as a soft-light map: grey 128 leaves the frame alone, lighter
    panes brighten, the darker mullion shadows between them dim it."""
    s = 4  # draw small, blur, scale up
    w, h = W // s, H // s
    m = PILImage.new('L', (w, h), 104)
    d = ImageDraw.Draw(m)
    slope = 0.55
    for x0, width in ((-70, 62), (2, 54), (66, 40)):   # panes, across the diagonal
        d.polygon([(x0, 0), (x0 + width, 0), (x0 + width + h * slope, h), (x0 + h * slope, h)], fill=170)
    m = m.filter(ImageFilter.GaussianBlur(3.5)).resize((W, H), PILImage.BICUBIC)
    # A broad falloff: brighter top left, dimmer bottom right.
    ramp = PILImage.linear_gradient('L').rotate(45, expand=True).resize((W, H)).point(lambda v: 150 - v * 44 // 255)
    m = PILImage.blend(m, ramp, 0.3)
    img = vb.Image.from_pil(PILImage.merge('RGB', (m, m, m)))
    cv.image(img, 0, 0, W, H)


# ---- scene one: headline scrap, battery, arrow, ticks, stamp ----

SCRAP_BOX = (76, 74, 392, 108)
SCRAP_PTS = paths.torn(rect_points(*SCRAP_BOX), seed=5, amount=5.5)
SCRAP_TILT = math.radians(-3.0)

BAT = (104, 290, 156, 290)   # body box; the nub sits on top
BAT_BODY = rounded_points(*BAT, 18)
NUB_X = BAT[0] + BAT[2] / 2 - 27
BAT_NUB = rounded_points(NUB_X, BAT[1] - 26, 54, 34, 8)
DIECUT = 7


def battery_outline(grow):
    """The battery's silhouette (body + nub) grown by `grow` px, as one polygon."""
    x, y, w, h = BAT
    body = rounded_points(x - grow, y - grow, w + 2 * grow, h + 2 * grow, 18 + grow)
    nub = rounded_points(NUB_X - grow, y - 26 - grow, 54 + 2 * grow, 40 + 2 * grow, 8 + grow)
    # rounded_points runs clockwise from the top-right corner and ends on the body's
    # top-left, so the nub's upper half (its top-left then top-right corner) goes last.
    k = len(nub) // 4
    return body + [(NUB_X - grow, y - grow)] + nub[3 * k:] + nub[:k] + [(NUB_X + 54 + grow, y - grow)]


BAT_DIECUT = paths.torn(battery_outline(DIECUT), seed=7, amount=0.8, step=3)
BOLT = [(BAT[0] + BAT[2] / 2 + bx, BAT[1] + BAT[3] / 2 + by)
        for bx, by in ((8, -92), (-32, 2), (-4, 2), (-22, 70), (30, -24), (0, -24), (18, -92))]

ARROW_PTS = paths.jitter([(296 + 140 * t + 22 * math.sin(t * 7.0), 588 - 300 * t * t - 40 * t)
                          for t in (k / 40 for k in range(41))], seed=31, amount=2.6, wander=0.35)
ARROW_HEAD = (paths.jitter([(-34, -17), (0, 0)], seed=32, amount=1.5), paths.jitter([(-30, 19), (0, 0)], seed=33, amount=1.5))

CHECK_X, CHECK_Y, CHECK_GAP = 500, 272, 72
CHECK_WORDS = ('Sleep', 'Focus', 'Energy')
BOXES = [paths.jitter(paths.resample(rect_points(CHECK_X, CHECK_Y + i * CHECK_GAP, 36, 36), 24, closed=True),
                      seed=40 + i, amount=1.6, wander=0.4) for i in range(3)]
TICK_PTS = [paths.jitter(paths.resample([(CHECK_X + 6, CHECK_Y + i * CHECK_GAP + 16), (CHECK_X + 16, CHECK_Y + i * CHECK_GAP + 30),
                                         (CHECK_X + 44, CHECK_Y + i * CHECK_GAP - 6)], 16), seed=50 + i, amount=1.4)
            for i in range(3)]

STAMP_C = (512, 566)
OVERLAP_OK = (('stamp', 'arrow'),)   # a stamp is slammed across whatever is there
STAMP_TILT = math.radians(-11)


@lru_cache(maxsize=1)
def stamp_image():
    """The stamp's ink, drawn once and distressed: a seeded speckle knocks holes in it."""
    tw, th = text.block_size(['START NOW'], STAMP_F)
    pw, ph = round(tw + 64), round(th + 34)
    cv = vb.Canvas(pw, ph)
    cv.outline(5, 5, pw - 10, ph - 10, ACCENT, width=6, radius=10)
    cv.outline(13, 13, pw - 26, ph - 26, ACCENT, width=2, radius=6)
    text.draw(cv, ['START NOW'], STAMP_F, (pw - tw) / 2, (ph - th) / 2, ACCENT)
    cv.surface.flush()
    pil = PILImage.frombuffer('RGBA', (pw, ph), bytes(cv.surface.get_data()), 'raw', 'BGRA', 0, 1)
    rnd = random.Random(9)
    speck = PILImage.frombytes('L', (pw // 3, ph // 3), rnd.randbytes((pw // 3) * (ph // 3)))
    speck = speck.resize((pw, ph), PILImage.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))
    fine = PILImage.frombytes('L', (pw, ph), rnd.randbytes(pw * ph)).filter(ImageFilter.GaussianBlur(0.7))
    wear = PILImage.blend(speck, fine, 0.4).point(lambda v: 0 if v < 92 else (255 if v > 108 else (v - 92) * 16))
    r, g, b, a = pil.split()
    a = ImageChops.multiply(a, wear).point(lambda v: v * 0.92)
    return vb.Image.from_pil(PILImage.merge('RGBA', (r, g, b, a)).convert('RGBA'))


def transform(ctx, cx, cy, angle, scale=1.0, dx=0.0, dy=0.0):
    ctx.translate(cx + dx, cy + dy)
    ctx.rotate(angle)
    if scale != 1:
        ctx.scale(scale, scale)
    ctx.translate(-cx, -cy)


def draw_scrap(cv, n):
    t = progress(n, SCRAP_IN)
    if step(n) < SCRAP_IN[0]:
        return
    x, y, w, h = SCRAP_BOX
    cx, cy = x + w / 2, y + h / 2
    moving = step(n) < SCRAP_IN[1] + 2
    jx, jy, jr = boil('scrap', n, 1.0) if moving else (0, 0, 0)
    dy = -(1 - t) * 260
    lift = 4 + (1 - t) * 14   # higher off the wall while it falls
    ctx = cv.ctx
    ctx.save()
    transform(ctx, cx, cy, SCRAP_TILT + (1 - t) * math.radians(9) + jr, dx=jx, dy=dy + jy)
    cv.shape_shadow(SCRAP_PTS, dx=lift * 0.5, dy=lift, blur=10 + lift, color=(35, 25, 15, 0.42))
    paper_piece(cv, SCRAP_PTS, SCRAP, rim='#fbf9f5', grain_alpha=0.6, seed=6)
    tw, th = text.block_size(['RECHARGE'], HEAD_F)
    box = text.draw(cv, ['RECHARGE'], HEAD_F, cx - tw / 2, cy - th / 2 + 2, INK)
    cv.mark('headline', *box)
    ctx.restore()


def draw_battery(cv, n, charge):
    if step(n) < BATTERY_IN[0]:
        return
    t = progress(n, BATTERY_IN)
    x, y, w, h = BAT
    cx, cy = x + w / 2, y + h / 2
    moving = step(n) < BATTERY_IN[1] + 2
    jx, jy, jr = boil('battery', n, 1.2) if moving else (0, 0, 0)
    scale = 1 + (1 - t) * 0.22   # slapped down from above the wall
    lift = 5 + (1 - t) * 22
    ctx = cv.ctx
    ctx.save()
    transform(ctx, cx, cy, math.radians(2.5) + jr, scale=scale, dx=jx - (1 - t) * 40, dy=jy)
    cv.shape_shadow(BAT_DIECUT, dx=lift * 0.5, dy=lift, blur=10 + lift, color=(35, 25, 15, 0.42))
    paper_piece(cv, BAT_DIECUT, '#fbf9f5', rim='#ffffff', grain_alpha=0.4, seed=8)
    for pts in (BAT_BODY, BAT_NUB):
        fill_points(ctx, pts)
        ctx.set_source_rgba(*vb.rgba(INK))
        ctx.fill()
    # Charge bars: cut from red card, stepping up as the arrow rises.
    for i in range(3):
        if i < charge:
            by = y + h - 18 - (i + 1) * 78 + 4
            cv.rect(x + 16, by, w - 32, 68, ACCENT, radius=4)
    fill_points(ctx, BOLT)
    ctx.set_source_rgba(*vb.rgba(SCRAP))
    ctx.fill()
    cv.mark('battery', x - DIECUT, y - 26 - DIECUT, w + 2 * DIECUT, h + 26 + 2 * DIECUT)
    ctx.restore()


def draw_arrow(cv, n):
    t = vb.clamp01((step(n) - ARROW[0]) / (ARROW[1] - ARROW[0]))
    if t <= 0:
        return
    pts = paths.reveal(ARROW_PTS, vb.ease_in_out_quart(t))
    paths.draw(cv, pts, INK, width=7)
    if t >= 1:
        hx, hy = ARROW_PTS[-1]
        px, py = ARROW_PTS[-5]
        a = math.atan2(hy - py, hx - px)
        ca, sa = math.cos(a), math.sin(a)
        for barb in ARROW_HEAD:
            paths.draw(cv, [(hx + bx * ca - by * sa, hy + bx * sa + by * ca) for bx, by in barb], INK, width=7)
        xs, ys = [p[0] for p in ARROW_PTS], [p[1] for p in ARROW_PTS]
        cv.mark('arrow', min(xs) - 4, min(ys) - 30, max(xs) - min(xs) + 8, max(ys) - min(ys) + 34)


def draw_checks(cv, n):
    if step(n) < BATTERY_IN[1]:
        return
    for i, word in enumerate(CHECK_WORDS):
        paths.draw(cv, BOXES[i], INK, width=3.5, closed=True)
        by = CHECK_Y + i * CHECK_GAP
        box = text.draw(cv, [word], LABEL_F, CHECK_X + 50, by + 17 - text.line_height(LABEL_F) / 2, INK)
        cv.mark(f'check-{i}', CHECK_X - 4, by - 8, box.x + box.w - CHECK_X + 4, 50)
        t = vb.clamp01((step(n) - TICKS[i]) / 4)
        if t > 0:
            paths.draw(cv, paths.reveal(TICK_PTS[i], t), ACCENT, width=6)


def draw_stamp(cv, n):
    if n < STAMP_AT:
        return
    img = stamp_image()
    k = n - STAMP_AT
    scale = {0: 1.12, 1: 1.12}.get(k, 1.0)
    cx, cy = STAMP_C
    ctx = cv.ctx
    ctx.save()
    transform(ctx, cx, cy, STAMP_TILT, scale=scale)
    cv.image(img, cx - img.w / 2, cy - img.h / 2, img.w, img.h)
    cv.mark('stamp', cx - img.w / 2, cy - img.h / 2, img.w, img.h)
    ctx.restore()


def charge_at(n):
    return sum(1 for f in (32, 38, 44) if step(n) >= f)


def draw_scene1(cv, n):
    paint_surface(cv, _surface_at('wall', cv.scale))
    draw_battery(cv, n, charge_at(n))
    draw_arrow(cv, n)
    draw_checks(cv, n)
    draw_scrap(cv, n)
    draw_stamp(cv, n)


# ---- the rip ----

RIP_C = (352, 372)
RIP_ANGLES = (-100, -38, 8, 62, 118, 176)   # where the radial tears run, degrees
RAYS = [paths.torn([RIP_C, (RIP_C[0] + 900 * math.cos(math.radians(a)), RIP_C[1] + 900 * math.sin(math.radians(a)))],
                   seed=60 + i, amount=9, closed=False) for i, a in enumerate(RIP_ANGLES)]


def _shard(i):
    a0, a1 = RIP_ANGLES[i], RIP_ANGLES[(i + 1) % len(RIP_ANGLES)]
    if a1 < a0:
        a1 += 360
    far = [(RIP_C[0] + 950 * math.cos(math.radians(a)), RIP_C[1] + 950 * math.sin(math.radians(a)))
           for a in (a0 + (a1 - a0) * k / 6 for k in range(7))]
    ray0, ray1 = RAYS[i], RAYS[(i + 1) % len(RAYS)]
    mid = math.radians((a0 + a1) / 2)
    return ray0 + far + list(reversed(ray1)), (math.cos(mid), math.sin(mid))


SHARDS = [_shard(i) for i in range(len(RIP_ANGLES))]


def clip_half(pts, fx, fy, nx, ny, far=True):
    """The part of polygon `pts` on one side of the line through (fx, fy) with
    normal (nx, ny): the far side (`far`) is where the normal points."""
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


def rip_motion(i, n):
    """Shard `i` at frame `n`: (fold distance from the centre, outward travel, spin)."""
    r = random.Random(70 + i)
    t = vb.clamp01((step(n) - RIP[0]) / (RIP[1] - RIP[0]))
    peel = vb.ease_out_quint(vb.clamp01(t / 0.5))   # the flaps curl back first...
    fly = vb.clamp01((t - 0.35 * r.uniform(0.8, 1.2)) / 0.6)
    fold = 20 + r.uniform(150, 210) * peel + 160 * fly
    travel = 14 * peel + 820 * fly ** 2.2   # ...then the shards are torn away, outwards
    spin = math.radians(r.uniform(-1, 1) * 22) * fly ** 2
    return fold, travel, spin, math.radians(r.uniform(-16, 16))


def draw_shards(cv, n):
    scene = _surface_at('scene1', cv.scale)
    ctx = cv.ctx
    cx, cy = RIP_C
    for i, (pts, (ux, uy)) in enumerate(SHARDS):
        fold, travel, spin, skew = rip_motion(i, n)
        # The fold line's normal: the shard's axis, turned a little so no two folds are alike.
        nx = ux * math.cos(skew) - uy * math.sin(skew)
        ny = ux * math.sin(skew) + uy * math.cos(skew)
        fx, fy = cx + ux * fold, cy + uy * fold
        flat = clip_half(pts, fx, fy, nx, ny, far=True)
        flap = reflect(clip_half(pts, fx, fy, nx, ny, far=False), fx, fy, nx, ny)
        jx, jy, jr = boil(f'shard{i}', n, 1.2)
        ctx.save()
        transform(ctx, fx, fy, spin + jr, dx=ux * travel + jx, dy=uy * travel + jy)
        # The shard's lift shadow, only where the shard still lies flat.
        sx, sy = 7, 13
        ctx.save()
        _half_plane(ctx, fx + sx, fy + sy, nx, ny)
        ctx.clip()
        cv.shape_shadow(pts, dx=sx, dy=sy, blur=28, color=(60, 12, 0, 0.5))
        ctx.restore()
        if len(flat) >= 3:
            ctx.save()
            fill_points(ctx, flat)
            ctx.clip()
            paint_surface(cv, scene)   # the picture is printed on the shard, so it travels with it
            ctx.restore()
        if len(flap) >= 3:
            cv.shape_shadow(flap, dx=8, dy=12, blur=18, color=(40, 20, 5, 0.45))
            ctx.save()
            fill_points(ctx, flap)
            ctx.clip()
            # The back of the paper, curling: dark in the crease, catching light where it lifts.
            far = max((x - fx) * nx + (y - fy) * ny for x, y in flap)
            g = cairo.LinearGradient(fx, fy, fx + nx * far, fy + ny * far)
            g.add_color_stop_rgba(0, *vb.rgba('#8a7f72'))
            g.add_color_stop_rgba(0.18, *vb.rgba('#d6cfc3'))
            g.add_color_stop_rgba(0.55, *vb.rgba('#efeae1'))
            g.add_color_stop_rgba(1, *vb.rgba('#d9d1c4'))
            ctx.set_source(g)
            ctx.paint()
            grain(cv, 0.45, seed=5)
            ctx.restore()
        ctx.restore()


def _half_plane(ctx, fx, fy, nx, ny):
    """A big quad: the side of the line through (fx, fy) that its normal (nx, ny) points to."""
    px, py = -ny * 3000, nx * 3000
    ctx.new_path()
    ctx.move_to(fx + px, fy + py)
    ctx.line_to(fx - px, fy - py)
    ctx.line_to(fx - px + nx * 3000, fy - py + ny * 3000)
    ctx.line_to(fx + px + nx * 3000, fy + py + ny * 3000)
    ctx.close_path()


# ---- scene two: the phone on red ----

PHONE = (236, 128, 248, 470)
PHONE_PTS = rounded_points(*PHONE, 38)
TAPES = (
    (paths.torn(rect_points(-56, -17, 112, 34), seed=81, amount=2.2, step=2), (PHONE[0] + 30, PHONE[1] + 18), math.radians(-38)),
    (paths.torn(rect_points(-56, -17, 112, 34), seed=82, amount=2.2, step=2),
     (PHONE[0] + PHONE[2] - 26, PHONE[1] + PHONE[3] - 20), math.radians(-34)),
)


def draw_phone(cv, n):
    if step(n) < PHONE_IN[0]:
        return
    t = progress(n, PHONE_IN)
    x, y, w, h = PHONE
    cx, cy = x + w / 2, y + h / 2
    moving = step(n) < PHONE_IN[1] + 2
    jx, jy, jr = boil('phone', n, 1.2) if moving else (0, 0, 0)
    lift = 8 + (1 - t) * 26
    ctx = cv.ctx
    ctx.save()
    transform(ctx, cx, cy, math.radians(4) + jr + (1 - t) * math.radians(-10), scale=1 + (1 - t) * 0.25,
              dx=jx, dy=jy + (1 - t) * 60)
    cv.shape_shadow(PHONE_PTS, dx=lift * 0.5, dy=lift, blur=14 + lift, color=(50, 10, 0, 0.5))
    fill_points(ctx, PHONE_PTS)
    ctx.set_source_rgba(*vb.rgba(INK))
    ctx.fill()
    sx, sy, sw, sh = x + 12, y + 12, w - 24, h - 24
    cv.rect(sx, sy, sw, sh, SCRAP, radius=28)
    with cv.clip(sx, sy, sw, sh, 28):
        grain(cv, 0.35, seed=9)
    # A placeholder app: a title bar, a charge ring, three rows.
    cv.rect(sx + 66, sy + 14, sw - 132, 18, INK, radius=9)   # notch
    cv.rect(sx + 22, sy + 58, 120, 16, INK, radius=8)
    rx, ry, rr = sx + sw / 2, sy + 190, 72
    cv.arc(rx, ry, rr, 0, 2 * math.pi, '#d9d2c6', width=20)
    cv.arc(rx, ry, rr, -math.pi / 2, -math.pi / 2 + 2 * math.pi * 0.82, ACCENT, width=20)
    for i in range(3):
        cv.rect(sx + 22, sy + 300 + i * 34, sw - 44 - i * 40, 16, '#bdb4a7', radius=8)
    cv.mark('phone', x, y, w, h)
    ctx.restore()
    for i, (pts, (tx, ty), ang) in enumerate(TAPES):
        if step(n) < TAPE_AT[i]:
            continue
        ctx.save()
        transform(ctx, 0, 0, ang, dx=tx, dy=ty)
        cv.shape_shadow(pts, dx=1, dy=2, blur=4, color=(40, 10, 0, 0.25))
        fill_points(ctx, pts)
        ctx.set_source_rgba(*vb.rgba('#ece6d6', 0.82))
        ctx.fill()
        ctx.restore()


def draw_red(cv):
    cv.fill(ACCENT)
    grain(cv, 0.4, seed=2)


def draw_scene2(cv, n):
    paint_surface(cv, _surface_at('red', cv.scale))
    draw_phone(cv, n)


def draw(n, cv):
    if n < RIP[0]:
        draw_scene1(cv, n)
    else:
        draw_scene2(cv, n)
        if step(n) < RIP[1]:
            draw_shards(cv, n)
    paint_surface(cv, _surface_at('light', cv.scale), cairo.OPERATOR_SOFT_LIGHT)


FILM = vb.Film(draw=draw, fps=FPS, frames=FRAMES, formats=(_kit.FORMAT,), background=WALL,
               keyframes=((24, 'headline'), (58, 'checks'), (68, 'stamp'), (112, 'phone')))

if __name__ == '__main__':
    vb.main(__file__)
