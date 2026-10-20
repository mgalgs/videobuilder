# Type: named typography styles for any video

A type style is a short typography film you ask for by name: a departures
board, a typewriter, letters that bounce. When a note says "make the title a
split-flap board", "type it on like a terminal" or "make the slogan bounce",
reach for `vb.type` instead of hand-rolling it from `kinetic_title`,
`title_terminal` or `title_editorial_wipe`.

Every style takes **the same props** and runs the same way: the letters
**enter**, **hold** (still moving, never a still) and **exit**, all inside
`length` seconds. So any style can be a whole film, one segment of a film,
or a title over another picture, and you can swap one style for another
without touching anything else.

```python
import videobuilder as vb

vb.type.names()   # ('split-flap', 'typewriter', 'terminal', 'rubber', 'rack-focus', 'letter-cloud', 'editorial')
vb.type.get('departures board').name    # 'split-flap': any case or spacing, an alias or the title
```

## The styles

| style | what it is for | enter | hold | exit | sound |
|---|---|---|---|---|---|
| `split-flap` | times, places, a list, a quote that "arrives" | each letter flips through the alphabet and settles, cell by cell, row by row | blank cells flip now and then, a lamp per line pulses | every letter flips back to blank | flap clicks |
| `typewriter` | a quote, a letter, a confession, anything personal | letters strike in one by one, a little uneven, the caret riding the line | the caret blinks, the sheet drifts in | the sheet feeds up and away | key strikes, a bell at the end |
| `terminal` | a command, a question to a machine, a developer product | each line typed at a `>` prompt with a block cursor | the cursor blinks, a band rolls down the screen | every line deleted back to the prompt | key ticks |
| `rubber` | a slogan, a playful brand line, a kids' title | letters drop and squash, stretch and settle on springs | a hop runs along each line now and then | the letters squash flat and pop away | a soft pop per letter |
| `rack-focus` | a cinematic title, a line at a time, a reveal | lines pull out of a soft haze into focus one after another, the last one blurring back | the focus keeps racking between lines (one line breathes) | everything goes back into the haze | none |
| `letter-cloud` | a big launch title, an idea coming together | letters scattered in 3D fly together into the words as the camera swings round | the camera keeps drifting; small letters drift in the depth | the letters burst past the camera | none |
| `editorial` | a headline, a magazine or news cover, a bold claim | a hard block of the accent sweeps across each line and peels away, staggered | the halftone plate's dots drift, the lines slide | the blocks sweep back and carry the lines off | none |

`split-flap` and `editorial` set the lines in capitals. `split-flap`,
`typewriter` and `terminal` default to a monospace family, `rack-focus` to a
serif, the rest to a heavy sans.

## The props

```python
TITLE = vb.type.props(
    lines=['Gate 14', 'Now boarding'],     # 1 to 4 short lines, at most 24 characters each, never rewrapped
    ink='#f4f1ea',                         # the letters
    paper='#15161b',                       # the ground; None: no ground, over whatever is drawn already
    accent='#ffb000',                      # the one strong colour (a wipe, a lamp, a cursor, a shadow)
    length=6,                              # seconds, enter to exit: about 6 inside a film, up to 18 on its own
    sound=False,                           # True: vb.type.sounds / vb.type.film place the style's sound
    texture=True,                          # False: no paper grain or scanlines; the paper colour stays
    font=None,                             # a font family, or None for the style's own
)
```

`lines` may also be one string with newlines. `vb.type.props(TITLE,
length=18)` copies props with changes. A bad prop raises one
`vb.type.PropsError` (a `ValueError`) that says which and why:
"type props: line 2 is 31 characters; keep each line to 24 or split it".
Split long copy into lines yourself: where a line breaks is part of the
design.

Each style lays itself out for the frame shape: tall frames stack the lines
bigger and nearer the edges (a split-flap board grows blank rows above and
below), wide frames leave air at the sides (the editorial plate moves beside
the stack), square sits between. Lay out your copy, not the style: the same
props work in 9:16, 16:9 and 1:1.

## Using a style

```python
FPS = 30

def draw(n, cv):
    t = n / FPS
    vb.type.draw(cv, 'split-flap', TITLE, t)          # the whole frame, t = seconds since it started
```

- **As a film of its own**: `FILM = vb.type.film('typewriter', TITLE,
  length=18)` (all three formats, its sound when `sound=True`, a keyframe
  mid-hold).
- **As a segment**: pass the seconds since the segment started,
  `vb.type.draw(cv, name, TITLE, (n - SEG_START) / FPS)`, and give the
  segment `TITLE.length` seconds. Outside `0..length` a style draws only its
  ground.
- **Over another picture**: draw the picture first, then the style with no
  ground, in a box if it should keep to part of the frame:

  ```python
  def draw(n, cv):
      t = n / FPS
      draw_the_product_shot(cv, t)
      vb.type.draw(cv, 'rubber', vb.type.props(TITLE, paper=None), t - 2.0,
                   box=(0, cv.height * 0.6, cv.width, cv.height * 0.4))   # the bottom 40%
  ```

  `split-flap` keeps its board (the flaps are the style), `editorial` its
  plate, `terminal` its prompt and cursor; the others draw only letters and
  their accent. Pick an `ink` that reads on the picture.
- **Try a few**: `vb.type.relay(cv, ['split-flap', 'rubber', 'editorial'],
  TITLE, t, each=3.0)` plays each in turn and returns the one on screen;
  `vb.type.relay_sounds(names, TITLE, each=3.0)` its sounds.

## Sound

`split-flap` (flap clicks), `typewriter` (key strikes and a bell) and
`terminal` (key ticks) and `rubber` (a soft pop as each letter lands) have
an obvious sound; the others have none. It is off until `sound=True`:

```python
TITLE = vb.type.props(lines=[...], sound=True)
FILM = vb.Film(..., sounds=vb.type.sounds('split-flap', TITLE, at=SEG_START_FRAME))  # or vb.type.film(...)
```

The sounds come from the sound-effects pack (`reference/sfx.md`): each
style tries its own sounds first and falls back on the nearest role the pack
has. Without the pack the style still draws, silent, and logs one note
saying so (run `python -m videobuilder sfx fetch`). A board's clatter is
thinned to one click per 1/25 s, so it never turns into noise.

## How to ask for one

The director never has to know the names. Read the note for what it wants
the words to do:

| the note says | style |
|---|---|
| "a departures board", "flip it in", "like an airport sign" | `split-flap` |
| "type it out", "like a typewriter", "letter by letter" | `typewriter` |
| "like a terminal", "a command line", "as if typed into code" | `terminal` |
| "bounce", "jelly", "squishy", "playful" | `rubber` |
| "come into focus", "cinematic", "out of a blur" | `rack-focus` |
| "fly together", "assemble", "3D letters" | `letter-cloud` |
| "magazine", "editorial", "headline", "wipe it on" | `editorial` |
| "try a few type styles", "show me some options" | `vb.type.relay` |

## Writing a style of your own

A style is `vb.type.Style(name, title, line, draw, aliases=(), events=None,
sound=None, clock=None, family='sans-serif')`, registered with
`vb.type.register(STYLE)` (the same style imported afresh, as the preview
does on every edit, replaces itself; another style's name is refused); the built-ins in `videobuilder/type/` are worked
examples. `draw(cv, p, t, box, clock)` sets `p.lines` inside `box` at `t`
seconds, entering until `clock.hold`, holding until `clock.exit` and leaving
by `p.length` (`vb.type.Clock(length)` splits a run about 40/45/15, or
give the style its own `clock(p)`). Mark each line `cv.mark('line-<i>',
...)` once it can be read, inside the box. Its hold must keep moving:
`vb.type.motion_floor(FILM, start, end) >= vb.type.FLOOR` (a tenth of the
frame's tiles change; the Looks' check, at a bar for a frame that is mostly
paper). `events(p, clock)` lists its sounds as `(seconds, kind)`, and
`sound={kind: (ids, roles, gain_db)}` says which.
