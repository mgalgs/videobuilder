"""Capability: stick figure. A character drawn entirely in code -- a round
white head with a face, a small white body, thin black limbs -- that acts:
it walks in with a coffee, stops, is surprised by something, then breaks
into a smile and raises the mug in a cheer, the mug in its hand the whole
time. No pictures: `vb.Stick` draws every frame from ten joint angles.

    python -m videobuilder preview examples/capabilities/stick-figure.py

A walk (the feet planted while the body passes over them), an expression
change (neutral, surprised, happy), a pose blend with overlap (stand into
cheer: a small dip first, the body leads, the arms trail and overshoot, the
head settles last), and a held prop. It breathes and blinks in every hold.

A style card: black ink on paper, the reverse of the kit's dark palette,
because that is the format's look (see STYLE.md, style-card exceptions).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import stick, text  # noqa: E402

FPS = 30
TOTAL = 180          # 6.0 s
STOP = 60            # it stops on a double support, both feet down
CHEER = 96

PAPER = '#f4f1ea'
INK = '#16171b'
MUTED = '#5d616b'

GROUND_Y = 560
FIG = vb.Stick(height=300, ink=INK, fill='#ffffff', fps=FPS, seed=2)
MUG = stick.prop('mug')
CX = 300             # where it stops
X0 = CX - FIG.speed('walk') * STOP

ACT = [(0, 'walk'), (STOP, 'stand', 10), (CHEER, 'cheer', 14)]
FACES = [(0, 'neutral'), (74, 'surprised', 4), (CHEER - 2, 'happy', 8)]

TITLE_F = _kit.font(32, 700)
CAPTION_F = _kit.font(22, 600)


def draw(n, cv):
    cv.fill(PAPER)
    s = _kit.safe(cv, 64)
    _kit.text_marked(cv, 'title', text.wrap('Stick figure', TITLE_F, s.w), TITLE_F, s.x, s.y, INK)
    stick.ground(cv, FIG, GROUND_Y, s.x - 64, s.right + 64)
    x = X0 + FIG.gait(min(n, STOP), 'walk').x
    stick.shadow(cv, FIG, x, GROUND_Y)
    FIG.draw(cv, FIG.act(n, ACT), x, GROUND_Y, face=FIG.face_at(n, FACES), blink=FIG.blink(n), prop=MUG,
             mark='figure')
    _kit.text_marked(cv, 'caption', text.wrap('Drawn in code: every pose is ten angles', CAPTION_F, s.w),
                     CAPTION_F, s.x, GROUND_Y + 40, MUTED)


FILM = vb.Film(draw=draw, fps=FPS, frames=TOTAL, formats=(_kit.FORMAT,), background=PAPER,
               keyframes=((30, 'walking'), (STOP + 8, 'stopped'), (80, 'surprised'), (CHEER + 30, 'cheering'),
                          (170, 'held')))

if __name__ == '__main__':
    vb.main(__file__)
