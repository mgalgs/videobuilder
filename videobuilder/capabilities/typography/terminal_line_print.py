"""Terminal Line Print: videobuilder already has it as `vb.TerminalLog`, a
log whose kinds that aren't `typed` print each line whole at its time and
scroll once the box is full, so this entry only names it and demos it."""
import videobuilder as vb

from .. import _demo as demo
from ..schema import Technique

KINDS = {'cmd': vb.terminal.Kind(demo.mono(22, 700), demo.INK, prefix='$ ', prefix_color=demo.ACCENT),
         'out': vb.terminal.Kind(demo.mono(22, 500), demo.MUTED),
         'ok': vb.terminal.Kind(demo.mono(22, 600), demo.TEAL)}
LINES = (('cmd', 'build --release'), ('out', 'resolving 214 packages'), ('out', 'compiling core v2.4.1'),
         ('out', 'compiling render v0.9.0'), ('out', 'compiling audio v1.3.2'), ('out', 'linking videobuilder'),
         ('out', 'running 48 checks'), ('out', 'checks passed in 0.82s'), ('out', 'writing dist/app.tar.gz'),
         ('ok', 'done: build finished'))
LOG = vb.TerminalLog([(0.35 + 0.22 * i, k, s) for i, (k, s) in enumerate(LINES)], KINDS, gap=0.25)
PANEL = vb.Box(demo.W * 0.16, demo.H * 0.14, demo.W * 0.68, demo.H * 0.72)


def draw(n, cv):
    cv.shadow(*PANEL, radius=20, dy=12, blur=36, color=(0, 0, 0, 0.5))
    cv.rect(*PANEL, '#0d1113', radius=20)
    cv.outline(*PANEL, demo.LINE, width=2, radius=20)
    box = PANEL.pad(32)
    LOG.draw(cv, n / demo.FPS, (box.x, box.y, box.w, box.h))
    cv.mark('log', *box)


TECHNIQUE = Technique(
    id='terminal-line-print',
    name='Terminal line print',
    family='typography',
    group='Typewriter and terminal',
    aliases=('terminal output', 'console log reveal', 'line-by-line print', 'scrolling log'),
    definition='Monospace lines show up one whole line at a time, like output printing in a console, '
               'and the column scrolls upward once it fills.',
    phrasings=('make it look like a command printing its output line by line',
               'lines of log text pop in one after another and scroll up like a terminal',
               'show the text as console output that keeps coming in'),
    related=('wipe-reveal', 'per-line-fade-in', 'scroll-driven-text-reveal', 'per-character-fade-in',
             'ink-spread-reveal', 'scanline-wipe'),
    api=('videobuilder.TerminalLog', 'videobuilder.terminal.Kind', 'videobuilder.terminal.paced'),
    demo=lambda: demo.film(draw),
)
