"""Letter cloud: the letters start scattered through 3D space -- near and
far, turned every way, tinted by the accent the deeper they sit -- and fly
together on springs into the words, while the camera swings round from a
three-quarter view to face them. Through the hold the camera keeps
drifting a few degrees, so the words keep reading as things in space, and
a dust of small letters drifts through the depth behind them. On the exit
the letters burst past the camera.

The camera is title_extruded_3d's: a yaw and a pitch about the words'
centre and a perspective divide, here with a focal length taken from the
frame so every shape gets the same lens. The letters are billboards (a
letter turned on its own axis is drawn foreshortened), not solids, so a
whole cloud of them stays cheap.
"""
import math
from functools import lru_cache

from .. import text
from ..ease import damped, spring
from ..layout import Box
from ..text import Font
from . import kit
from .style import Style

DUST = 60


class Camera:
    def __init__(self, cx, cy, yaw, pitch, focal):
        self.cx, self.cy, self.f = cx, cy, focal
        self.cyw, self.syw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        self.cp, self.sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def project(self, x, y, z):
        """(screen x, screen y, scale, depth) of the world point (x, y, z):
        +z runs away from the camera."""
        x1 = x * self.cyw + z * self.syw
        z1 = -x * self.syw + z * self.cyw
        y2 = y * self.cp - z1 * self.sp
        z2 = y * self.sp + z1 * self.cp
        d = self.f / max(self.f * 0.08, self.f + z2)
        return self.cx + x1 * d, self.cy + y2 * d, d, z2


@lru_cache(maxsize=64)
def _layout(lines, box, family):
    """The font, the line height and every letter's resting centre (x, y)
    about the box's centre: [(line, index, char, x, y), ...]."""
    inner, w, h, k = kit.room(box, tall=(0.84, 0.46), wide=(0.72, 0.58), square=(0.78, 0.56))
    font = kit.fit(lines, lambda s: Font(family, s, weight=800, line_height=1.15), w, h)
    lh = text.line_height(font)
    top = -lh * len(lines) / 2
    out = []
    for i, line in enumerate(lines):
        xs, width = kit.advances(line, font)
        for j, ch in enumerate(line):
            if ch != ' ':
                out.append((i, j, ch, -width / 2 + xs[j] + text.measure(ch, font) / 2, top + i * lh + lh / 2))
    return font, lh, tuple(out)


@lru_cache(maxsize=64)
def _scatter(lines, w, h, hold, length, exit_t):
    """Per letter: where it starts (x, y, z), its spin (roll, turn), its
    delay, and where it bursts to on the exit."""
    rnd = kit.rng('letter-cloud', '|'.join(lines))
    m = max(w, h)
    n = sum(1 for ln in lines for ch in ln if ch != ' ')
    out = []
    for _ in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        r = m * rnd.uniform(0.35, 0.9)
        start = (math.cos(a) * r, math.sin(a) * r * 0.75, rnd.uniform(-0.45, 2.4) * m)
        spin = (rnd.uniform(-160, 160), rnd.uniform(-80, 80))
        delay = rnd.uniform(0, 0.4) * hold
        burst = (rnd.uniform(-1, 1) * m * 0.6, rnd.uniform(-1, 1) * m * 0.5, rnd.uniform(0, 0.4) * (length - exit_t))
        out.append((start, spin, delay, burst))
    return out


@lru_cache(maxsize=16)
def _dust(w, h, chars):
    rnd = kit.rng('letter-cloud-dust', w, h)
    m = max(w, h)
    return tuple((rnd.uniform(-1, 1) * m * 0.9, rnd.uniform(-1, 1) * m * 0.7, rnd.uniform(0.2, 3.0) * m,
                  rnd.choice(chars), rnd.uniform(-90, 90)) for _ in range(DUST))


def _letter(cv, font, ch, x, y, scale, roll, turn, colour, alpha):
    ctx = cv.ctx
    gw = text.measure(ch, font)
    lh = text.line_height(font)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(roll))
    ctx.scale(scale * max(0.06, abs(math.cos(math.radians(turn)))), scale)
    kit.glyphs(cv, ch, font, -gw / 2, -lh / 2, colour, alpha)
    ctx.restore()


def draw(cv, p, t, box, clock):
    box = Box(*box)
    lines = p.lines
    font, lh, letters = _layout(lines, box, STYLE.font_family(p))
    scatter = _scatter(lines, box.w, box.h, clock.hold, p.length, clock.exit)
    m = max(box.w, box.h)
    focal = m * 1.4
    settle = max(0.4, clock.hold * 0.6)
    spring_k = damped(0.72, hz=1.5 / settle)
    e = kit.smooth(t / clock.hold)
    held = max(0.0, t - clock.hold)
    yaw = 30 * (1 - e) + 6 * math.sin(2 * math.pi * held / 7.0) * min(1.0, held)
    pitch = 12 * (1 - e) + 3 * math.sin(2 * math.pi * held / 5.3) * min(1.0, held)
    cam = Camera(box.cx, box.cy, yaw, pitch, focal)
    draws = []
    # The dust: small letters drifting toward the camera, round and round.
    dust_font = Font(font.family, max(6, round(font.size * 0.4)), weight=600)
    for x, y, z, ch, turn in _dust(box.w, box.h, ''.join(c for c in ''.join(lines) if c != ' ') or 'A'):
        zz = (z - t * m * 0.12) % (m * 3.0) - m * 0.2
        sx, sy, d, depth = cam.project(x, y, zz)
        fade = min(1.0, (zz + m * 0.2) / (m * 0.5)) * max(0.0, 1 - depth / (m * 3.0))
        draws.append((depth, dust_font, ch, sx, sy, d, turn * 0.3, turn + t * 40, p.accent,
                      0.55 * fade * (1 - clock.leaving(t))))
    out_q = clock.leaving(t)
    line_boxes = {}
    settled = {i: True for i in range(len(lines))}
    for (i, j, ch, fx, fy), (start, (roll0, turn0), delay, burst) in zip(letters, scatter):
        q = spring(t - delay, **spring_k) if t > delay else 0.0
        x = start[0] + (fx - start[0]) * q
        y = start[1] + (fy - start[1]) * q
        z = start[2] * (1 - q)
        roll, turn = roll0 * (1 - q), turn0 * (1 - q)
        if abs(1 - q) > 0.02 or t - delay < settle:
            settled[i] = False
        if t > clock.exit:
            b = min(1.0, max(0.0, (t - clock.exit - burst[2]) / (p.length - clock.exit - burst[2]))) ** 2
            x, y, z = x + burst[0] * b, y + burst[1] * b, -focal * 0.9 * b
            roll += 90 * b
            settled[i] = False
        sx, sy, d, depth = cam.project(x, y, z)
        far = min(1.0, max(0.0, depth / (m * 1.6)))
        colour = kit.mix(p.ink, p.accent, min(1.0, far * 1.4))
        alpha = max(0.0, 1 - far * 0.55) * (1 - out_q) ** 2     # gone by p.length, as they reach the lens
        draws.append((depth, font, ch, sx, sy, d, roll, turn, colour, alpha))
        if q > 0.5:
            gw = text.measure(ch, font) * d
            bx = line_boxes.setdefault(i, [math.inf, math.inf, -math.inf, -math.inf])
            gh = font.size * 0.9 * d          # the letters' own height, not the line's: lines sit tight
            bx[0], bx[1] = min(bx[0], sx - gw / 2), min(bx[1], sy - gh / 2)
            bx[2], bx[3] = max(bx[2], sx + gw / 2), max(bx[3], sy + gh / 2)
    for depth, f, ch, sx, sy, d, roll, turn, colour, alpha in sorted(draws, key=lambda r: -r[0]):
        if alpha > 0.01 and d > 0:
            _letter(cv, f, ch, sx, sy, d, roll, turn, colour, alpha)
    for i, (x0, y0, x1, y1) in line_boxes.items():
        if settled[i]:
            cv.mark(f'line-{i}', x0, y0, x1 - x0, y1 - y0)


STYLE = Style('letter-cloud', 'Letter cloud', 'letters scattered through 3D space fly together into the words',
              draw, aliases=('cloud', 'letters assemble', 'assemble', 'fly together', '3d letters', 'scatter'))
