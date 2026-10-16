"""Capability: pose swaps. A cartoon fox in a handful of drawn poses, held
and snapped from one to the next on the beat, the way limited animation
does it: it talks (idle and talk flapping on the syllables), points,
gasps, hops up cheering and lands back in idle, blinking now and then.
Each snap gets a 2-3 frame pop (a squash, then an overshoot) and, on the
big ones, a few speed lines; a slow breath runs under every hold, so a held
pose never freezes.

    python -m videobuilder preview examples/capabilities/pose-swaps.py

LOOP = True: the film starts and ends on the idle pose at rest, and the
breath runs two whole periods, so the last frame leads into the first.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import text  # noqa: E402

LOOP = True
FPS = 30
GRID = _kit.grid()
FPB = round(GRID.frames_per_beat)   # 15
TOTAL = 8 * FPB              # 4.0 s

FOX_DIR = _kit.ASSETS / 'fox'
POSES = ('idle', 'talk', 'blink', 'point', 'surprised', 'cheer')
FOX = vb.Puppet({name: FOX_DIR / f'{name}.png' for name in POSES}, height=340)

# Mouth open on each syllable of "Hey, look at this!", shut between.
SYLLABLES = ((15, 19, 'Hey,'), (22, 26, 'look'), (29, 32, 'at'), (35, 40, 'this!'))
POINT, GASP, CHEER, LAND = 3 * FPB, 4 * FPB, 5 * FPB, 6 * FPB
HOLDS = ([(0, 'idle'), (8, 'blink'), (10, 'idle')]
         + [h for a, z, _ in SYLLABLES for h in ((a, 'talk'), (z, 'idle'))]
         + [(POINT, 'point'), (GASP, 'surprised'), (CHEER, 'cheer'), (LAND, 'idle'), (104, 'blink'), (107, 'idle')])
POPS = {POINT, GASP, CHEER}      # the swaps that pop; talk and blink swap in place
POP = ((1.07, 0.93), (0.96, 1.05), (1.015, 0.985))   # squash, overshoot, settle: one per frame
HOP = 70                         # the cheer leaves the ground on its beat and lands on the next
LAND_SPRING = vb.damped(0.3, hz=2.6)
SQUASH = (1.12, 0.88)
SPEECH_OUT = GASP                # the words clear when the fox gasps

GROUND_Y = 560
BREATH = 60

TITLE_F = _kit.font(32, 700)
SPEECH_F = _kit.font(30, 650)
TICK_F = _kit.font(20, 600)


def body_at(n):
    """(pose, sx, sy, lift) at frame n."""
    pose, age = FOX.pose_at(n, HOLDS)
    sx, sy = FOX.breath(n, BREATH)
    swap = n - age
    if swap in POPS and age < len(POP):
        px, py = POP[age]
        sx, sy = sx * px, sy * py
    lift = 0.0
    if CHEER <= n < LAND:
        p = (n - CHEER) / (LAND - CHEER)
        lift = HOP * 4 * p * (1 - p)
    if n >= LAND:
        sp = vb.spring_at(n - LAND, FPS, **LAND_SPRING)
        sx *= SQUASH[0] + (1 - SQUASH[0]) * sp
        sy *= SQUASH[1] + (1 - SQUASH[1]) * sp
    return pose, sx, sy, lift


def strokes(cv, x, y, segments, alpha):
    for (x0, y0), (x1, y1) in segments:
        cv.line(x + x0, y + y0, x + x1, y + y1, _kit.INK, width=4, alpha=alpha)


def speed_lines(cv, pose, age, x, y):
    """A few lines for the first frames after a big snap: behind the pointing
    hand, or around the gasp."""
    if age > 2 or pose not in ('point', 'surprised'):
        return
    alpha = (1.0, 0.7, 0.35)[age]
    k = FOX.factor
    if pose == 'point':
        # Swooshes under the arm's swing up from the side, about the shoulder; where the
        # picture puts the shoulder and hand, in source px from the feet.
        sx, sy = x + 166 * k, y - 392 * k
        reach = 256 * k
        for i, r in enumerate((reach * 0.98, reach * 0.8)):
            cv.arc(sx, sy, r, math.radians(-17 + 6 * i), math.radians(18), _kit.INK, width=4, alpha=alpha)
    else:
        b = FOX.box('surprised')
        cy = y + b.y + b.h * 0.24
        segs = []
        for side in (-1, 1):
            for a in (-12, 8, 28):
                t = math.radians(a)
                r0, r1 = b.w / 2 + 6, b.w / 2 + 32
                segs.append(((side * r0 * math.cos(t), r0 * math.sin(t)), (side * r1 * math.cos(t), r1 * math.sin(t))))
        strokes(cv, x, cy, segs, alpha)


def speech(cv, n, cx, y):
    """The line as it's said: each word on its syllable, held until the gasp."""
    if n < SYLLABLES[0][0] or n >= SPEECH_OUT:
        return
    words = [w for a, _, w in SYLLABLES if n >= a]
    full = ' '.join(w for *_, w in SYLLABLES)
    tw, _ = text.block_size([full], SPEECH_F)
    x = cx - tw / 2
    _kit.text_marked(cv, 'speech', [' '.join(words)], SPEECH_F, x, y, _kit.INK)


def ticker(cv, pose, s):
    """The pose names along the bottom, the held one lit and underlined."""
    gap = 26
    widths = [text.measure(p, TICK_F) for p in POSES]
    x = s.cx - (sum(widths) + gap * (len(POSES) - 1)) / 2
    y = s.bottom - text.line_height(TICK_F) - 10
    for p, w in zip(POSES, widths):
        on = p == pose
        _kit.text_marked(cv, f'pose-{p}', [p], TICK_F, x, y, _kit.INK if on else _kit.MUTED)
        if on:
            cv.rect(x, y + text.line_height(TICK_F) + 4, w, 4, _kit.ACCENT, radius=2)
        x += w + gap


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Pose swaps', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)
    cv.line(s.x, GROUND_Y, s.right, GROUND_Y, _kit.LINE, width=2)

    pose, sx, sy, lift = body_at(n)
    _, age = FOX.pose_at(n, HOLDS)
    k = 1 - 0.4 * lift / HOP
    ctx = cv.ctx
    ctx.save()
    ctx.translate(s.cx, GROUND_Y + 2)
    ctx.scale(140 * k * sx, 13 * k)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.set_source_rgba(0, 0, 0, 0.45 * k)
    ctx.fill()
    ctx.restore()

    FOX.draw(cv, pose, s.cx, GROUND_Y - lift, sx=sx, sy=sy, mark='fox')
    speed_lines(cv, pose, age, s.cx, GROUND_Y - lift)
    speech(cv, n, s.cx, s.y + 66)
    ticker(cv, pose, s)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=((5, 'idle'), (38, 'talking'), (52, 'point'), (67, 'gasp'), (82, 'cheer'), (112, 'idle')))

if __name__ == '__main__':
    vb.main(__file__)
