"""A scrolling terminal log: an agent fixing a failing test, 13 s.

    python -m videobuilder sfx fetch            # once: the sound-effects pack (the keys and ticks)
    python -m videobuilder render examples/terminal_log_demo.py --format 9x16

The agent's thinking in italic grey, its commands typed at a prompt, the
output appearing whole in another colour; once the window is full it eases
up a line at a time, old lines leaving at the top. One `vb.TerminalLog`
per format (the font size is the film's choice; the events are shared), and
its `sounds()` put a key on every keystroke and a soft tick on every output
line: some two hundred sound effects.
"""
from pathlib import Path

import videobuilder as vb
from videobuilder import Box, text

HERE = Path(__file__).resolve().parent
for _f in sorted((HERE / 'assets').glob('*.[ot]tf')):
    text.register(_f)

FPS = 30
BG, WINDOW, BAR = '#14151a', '#1b1d23', '#24262e'
INK, MUTED, TEAL, AMBER, RED = '#f4f4f2', '#8d929c', '#4fc3b0', '#d9b76a', '#ef6b5c'
MONO = 'SourceCodeVF'

SESSION = [
    ('think', 'The build is red on main. Start with the failing test, not the diff.'),
    ('cmd', 'pytest -q tests/test_mix.py'),
    ('out', 'collected 6 items', 0.25),
    ('out', 'F.....', 0.2),
    ('err', 'FAILED test_mix.py::test_many_sounds - ffmpeg: Too many open files', 0.15),
    ('think', 'Five hundred clicks, one ffmpeg input each. Count them first.', 0.6),
    ('cmd', "grep -c 'sfx.sound' film.py"),
    ('out', '512', 0.25),
    ('think', 'Mix the plain ones into one stem, and keep each one checkable.', 0.6),
    ('cmd', 'git apply premix.patch && pytest -q'),
    ('out', '......................................', 0.3),
    ('out', '38 passed in 4.1s', 0.15),
    ('think', 'Green. Render it and listen.', 0.5),
    ('cmd', 'python -m videobuilder render film.py'),
    ('out', '9x16: chunks 66/66', 0.5),
    ('out', 'film.mp4: 512 of 512 sound effects within a frame of their frames', 0.2),
]


def kinds(size):
    mono = vb.Font(MONO, size, weight=430, line_height=1.32)
    return {'think': vb.terminal.Kind(vb.Font(MONO, size, weight=380, line_height=1.32, style='italic'), MUTED),
            'cmd': vb.terminal.Kind(vb.Font(MONO, size, weight=620, line_height=1.32), INK, prefix='$ ',
                                    prefix_color=TEAL, typed=True),
            'out': vb.terminal.Kind(mono, AMBER),
            'err': vb.terminal.Kind(mono, RED)}


EVENTS = vb.terminal.paced(SESSION, kinds(30), start=0.6, gap=0.45)
FRAMES = round((EVENTS[-1][0] + 2.0) * FPS)

# The type size per frame shape: big enough for a phone, the window a dozen lines high.
SIZES = {'9x16': 36, '16x9': 30, '1x1': 32}
LOGS = {name: vb.TerminalLog(EVENTS, kinds(size)) for name, size in SIZES.items()}


def window(cv):
    """(the window, the log's box inside it) for this frame shape."""
    b = Box.of(cv)
    if cv.format.name == '9x16':
        win = Box(b.x + 48, b.y + b.h * 0.27, b.w - 96, b.h * 0.42)
    elif cv.format.name == '16x9':
        win = Box(b.cx - b.w * 0.33, b.y + b.h * 0.17, b.w * 0.66, b.h * 0.66)
    else:
        win = Box(b.x + 80, b.y + b.h * 0.15, b.w - 160, b.h * 0.7)
    bar = win.h * 0.075 if cv.format.name != '9x16' else win.h * 0.06
    return win, bar, Box(win.x + 36, win.y + bar + 24, win.w - 72, win.h - bar - 48)


def draw(n, cv):
    t = n / FPS
    cv.fill(BG)
    win, bar, box = window(cv)
    cv.rect(*win, WINDOW, radius=18)
    cv.rect(win.x, win.y, win.w, bar, BAR, radius=18)
    cv.rect(win.x, win.y + bar - 18, win.w, 18, BAR)
    for k, c in enumerate(('#ef6b5c', '#e6b450', '#5cc47a')):
        r = bar * 0.16
        cv.sector(win.x + bar * 0.6 + k * r * 3.2, win.y + bar / 2, r, 0, 6.2832, c)
    label = vb.Font('Inter', bar * 0.36, weight=600)
    title = 'agent — ~/videobuilder'
    text.draw(cv, [title], label, win.cx - text.measure(title, label) / 2, win.y + (bar - text.line_height(label)) / 2,
              MUTED)
    cv.mark('window', *win)
    LOGS[cv.format.name].draw(cv, t, box)


FILM = vb.Film(draw=draw, fps=FPS, frames=FRAMES, formats=(vb.Format('9x16', 1080, 1920), vb.Format('16x9', 1920, 1080),
                                                             vb.Format('1x1', 1080, 1080)),
               background=BG, sounds=LOGS['9x16'].sounds(at=0, fps=FPS),
               keyframes=((round(3.0 * FPS), 'typing'), (round(8.5 * FPS), 'scrolled'), (FRAMES - 30, 'end')))

if __name__ == '__main__':
    vb.main(__file__)
