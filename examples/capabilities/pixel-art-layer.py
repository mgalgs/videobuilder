"""Capability: pixel-art layer. A small scene -- sky, ground, sun, a walking
character, a HUD label -- is drawn with `cv.pixelated` at 1/8 resolution and
scaled back up with nearest-neighbour filtering, blocky like an 8-bit game.
Its motion is stepped at 15 fps (each pose held two frames of this 30fps
film), and the HUD text is drawn into the same layer, so it pixelates along
with everything else -- no pixel font is bundled, it's the same Inter used
everywhere else in the catalog, just rendered at a fraction of the size.

    python -m videobuilder preview examples/capabilities/pixel-art-layer.py

LOOP = True: the one hero move -- the character walking in place -- is a
true period (its phase is `n % CYCLE`), so frame 0 and the frame just past
the last are the same point in the step cycle by construction.

Its own small palette (STYLE.md's style-card exception): sky, ground, sun,
the character, and a dark outline/HUD ink -- 5 colours.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
FPS = 30
STEP = 2            # hold each pose this many 30fps frames -> 15fps motion
CYCLE_STEPS = 36     # poses in one walk cycle
CYCLE = CYCLE_STEPS * STEP
PERIOD = CYCLE

SKY = '#8fd3f4'
GROUND = '#3a7d44'
SUN = '#f4d35e'
CHAR = '#e8432f'
DARK = '#1d1f28'

TITLE_F = _kit.font(32, 700)
HUD_F = _kit.font(52, 700)

SCENE_W, SCENE_H = 480, 320
FACTOR = 8
GROUND_H = 70


def stepped(n):
    return (n // STEP) * STEP


def draw_scene(px, n):
    px.fill(SKY)
    px.rect(0, SCENE_H - GROUND_H, SCENE_W, GROUND_H, GROUND)
    px.rect(SCENE_W - 90, 30, 56, 56, SUN, radius=28)

    phase = (stepped(n) % CYCLE) / CYCLE
    swing = math.sin(phase * 2 * math.pi)
    bob = abs(swing) * 6

    cx, feet_y = SCENE_W / 2, SCENE_H - GROUND_H - bob
    px.rect(cx - 18, feet_y - 70, 36, 46, CHAR, radius=4)      # body
    px.rect(cx - 13, feet_y - 92, 26, 26, CHAR, radius=6)      # head
    leg_w, leg_h = 12, 34
    px.rect(cx - 20 + swing * 8, feet_y - 24, leg_w, leg_h, DARK, radius=3)
    px.rect(cx + 8 - swing * 8, feet_y - 24, leg_w, leg_h, DARK, radius=3)

    text.draw(px, ['1-1  x3'], HUD_F, 16, 10, DARK)


def draw(n, cv):
    cv.fill(_kit.BG)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Pixel-art layer', TITLE_F, s.w), TITLE_F, s.x, s.y, _kit.INK)

    box = Box(s.cx - SCENE_W / 2, s.y + 100, SCENE_W, SCENE_H)
    with cv.pixelated(FACTOR, x=box.x, y=box.y, w=box.w, h=box.h) as px:
        draw_scene(px, n)
    cv.outline(*box, _kit.LINE, width=2)
    cv.mark('scene', *box)
    _kit.label(cv, 'caption', 'Stepped motion, blocky scale', s.x, box.bottom + 24, align='left')


FILM = vb.Film(draw=draw, fps=FPS, frames=PERIOD, formats=(_kit.FORMAT,), background=_kit.BG,
               keyframes=(0, PERIOD // 4, PERIOD // 2))

if __name__ == '__main__':
    vb.main(__file__)
