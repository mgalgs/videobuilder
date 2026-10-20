"""Capability: terminal-log. An agent's session in a terminal window: its
thinking in italic grey, a command typed at a prompt, the output appearing
whole, and the window easing up a line at a time once it's full.

    python -m videobuilder preview examples/capabilities/terminal-log.py

LOOP = True by enter/hold/exit: the window starts empty and the log fades
out over the last few frames, so both ends are the same empty window.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import videobuilder as vb  # noqa: E402
from videobuilder import Box, text  # noqa: E402

LOOP = True
FPS = 30
FORMATS = (_kit.FORMAT, vb.Format('9x16', 540, 960), vb.Format('16x9', 960, 540))
AMBER = '#d9b76a'


def kinds(size):
    def mono(weight, **kw):
        return _kit.font(size, weight, family=_kit.MONO, line_height=1.3, **kw)
    return {'think': vb.terminal.Kind(mono(380, style='italic'), _kit.MUTED),
            'cmd': vb.terminal.Kind(mono(620), _kit.INK, prefix='$ ', prefix_color=_kit.TEAL, typed=True,
                                    per_char=0.045),
            'out': vb.terminal.Kind(mono(430), AMBER)}


SESSION = [('think', 'Tests are red. Look before changing anything.'),
           ('cmd', 'pytest -q', 0.25),
           ('out', '..F.. 1 failed', 0.2),
           ('think', 'An off-by-one in the frame count.', 0.35),
           ('cmd', 'git apply fix.patch && pytest -q', 0.25),
           ('out', '..... 5 passed', 0.2)]
EVENTS = vb.terminal.paced(SESSION, kinds(22), start=0.3, gap=0.3)
FRAMES = round((EVENTS[-1][0] + 1.2) * FPS)
OUT = 0.4   # seconds the log takes to fade out at the end
SIZES = {'cap': 26, '9x16': 22, '16x9': 20}
ROWS = 5.3   # the window's height in lines: the session is longer, so it scrolls
LOGS = {name: vb.TerminalLog(EVENTS, kinds(size), gap=0.3) for name, size in SIZES.items()}


def draw(n, cv):
    t = n / FPS
    cv.fill(_kit.BG)
    s = _kit.safe(cv, pad=48 if cv.format.name == 'cap' else 32)
    lh = text.line_height(LOGS[cv.format.name].kinds['out'].font)
    win = s.pad(40, 0, 0, 0).anchor(s.w, ROWS * lh + 40, at='center')
    _kit.label(cv, 'title', 'Terminal log', s.x, win.y - 40)
    cv.rect(*win, '#1b1d23', radius=14)
    cv.mark('window', *win)
    with cv.layer(opacity=min(1.0, (FRAMES - 1 - n) / (OUT * FPS))):
        LOGS[cv.format.name].draw(cv, t, win.pad(20))


FILM = vb.Film(draw=draw, fps=FPS, frames=FRAMES, formats=FORMATS, background=_kit.BG,
               sounds=LOGS['cap'].sounds(at=0, fps=FPS), keyframes=(round(EVENTS[3][0] * FPS), FRAMES - 20))

if __name__ == '__main__':
    vb.main(__file__)
