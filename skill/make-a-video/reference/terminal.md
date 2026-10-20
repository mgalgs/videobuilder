# Terminal log: a transcript that types, prints and scrolls

For a terminal or chat transcript that keeps growing: an agent's thinking,
the commands it types, their output. `vb.TerminalLog` draws it in a box you
give it, wraps long lines, and once the box is full eases up a line at a
time, old lines leaving at the top. For a one-to-four-line title typed at a
prompt, use the `terminal` type style instead (`type.md`).

```python
import videobuilder as vb

MONO = 'SourceCodeVF'   # any monospace family you've registered
KINDS = {
    'think': vb.terminal.Kind(vb.Font(MONO, 34, style='italic'), '#8d929c'),
    'cmd': vb.terminal.Kind(vb.Font(MONO, 34, weight=620), '#f4f4f2', prefix='$ ', prefix_color='#4fc3b0',
                            typed=True),
    'out': vb.terminal.Kind(vb.Font(MONO, 34), '#d9b76a'),
}
EVENTS = vb.terminal.paced([
    ('think', 'The build is red. Start with the failing test.'),
    ('cmd', 'pytest -q'),
    ('out', '1 failed, 5 passed', 0.25),      # a third item: seconds to wait first (default `gap`)
], KINDS, start=0.5, gap=0.4)
LOG = vb.TerminalLog(EVENTS, KINDS)

def draw(n, cv):
    cv.fill('#14151a')
    LOG.draw(cv, n / FPS, (60, 400, cv.width - 120, 900))   # x, y, w, h

FILM = vb.Film(draw=draw, fps=FPS, frames=round((LOG.end + 2) * FPS), sounds=LOG.sounds(at=0, fps=FPS))
```

- **Events** are `(t, kind, text)`: the line starts at `t` seconds. Write
  them by hand, or let `vb.terminal.paced` start each one a beat after the
  last finished typing. `LOG.finish(i)` is when event `i` is all there,
  `LOG.end` when the last one is.
- **Kinds** name a look: a `font` (italic with `style='italic'`), a `color`,
  a `prefix` (a prompt, in `prefix_color`), and `typed=True` to type the line
  on key by key with the typewriter styles' uneven rhythm (`per_char`
  seconds a key on average, 0.055). Any other kind appears whole.
- **Options**: `vb.TerminalLog(events, kinds, gap=0.35, scroll=0.22,
  cursor=True, fade=24)`: space before each line in ems, the scroll's
  seconds, a blinking block cursor on the line being typed, and the px at
  the top over which leaving lines fade.
- **Sound**: `LOG.sounds(at=frame, fps=FPS)` gives a key on every keystroke
  (the terminal type style's key) on the frame its letter shows, and a soft
  tick per printed line (`ticks=False` drops them; `Kind(sound=False)` for
  a quiet kind). A long session is hundreds of sounds; that is fine, keep
  them as they are.

## Traps

- A typed line must finish before the next event starts; `TerminalLog`
  raises naming both if it doesn't. `paced` never overlaps.
- The font size is yours: pick it per format so a phone can read it (about
  34-40 px on a 1080-wide 9:16 frame) and make a `TerminalLog` per format
  if the size differs. The events and the sounds are the same for each.
- The box clips: anything you want on top of the log (a window bar, a
  title) goes outside the box or is drawn after `draw`.
- `draw` depends only on `t`, so any frame can be drawn alone: build the log
  once at module level, never inside `draw`.
