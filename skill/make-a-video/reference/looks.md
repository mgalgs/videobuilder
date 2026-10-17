# Looks: named art styles for any video

A look is a named art style -- pop art, woodblock print, 8-bit pixels --
that repaints a video's own picture and gives it a movement of its own. When
a note says "make it pop art", "paint it like a woodblock print" or "try a
few looks", reach for `videobuilder.looks` instead of restyling the film by
hand.

```python
from videobuilder import looks
looks.names()      # ('swirl', 'pointillism', 'woodblock', 'melt', 'bauhaus', 'pop-art', 'pixel', 'blueprint', ...)
looks.get('pop art').title   # any case or spacing, an alias ('8-bit', 'ukiyo-e') or the title
```

| look | what it looks like | what moves | options |
|---|---|---|---|
| `swirl` | thick round dabs of paint | sky dabs orbit two eddies, halo rings turn round the sun, the water's dabs ride waves | |
| `pointillism` | thousands of small dots | every dot shimmers, light bands roll through the water | |
| `woodblock` | flat colour, thick ink outlines, paper ground | a great wave rises and curls (on `age`), rain falls, clouds slide | |
| `melt` | dream gradients, soft shapes | buildings and figures sway like wax, the sun drips, stones float, a clock melts over the land's edge | |
| `bauhaus` | primary colours, circles, half-discs, blocks | the sun's quarters turn, half-discs roll, stars pulse on the beat | `Scene(bpm=)` |
| `pop-art` | loud flat colour, comic dots, black outlines | dots drift, a ray burst turns, a starburst pops every two beats | `sfx='POW!', font=vb.Font(...)`, `burst=(x, y)` |
| `pixel` | chunky pixels | everything steps at 8 fps, stars blink, lights flash | `block=` px |
| `blueprint` | chalk lines on a blue grid | the scene draws itself in (on `age`), dashes march, swells roll | `font=` for labels |

Published community looks are listed in your prompt with their `look.py`.

## The contract

A look paints a **scene description**, not pixels: a few shapes with
roles, the sun, a beacon and stars. The video describes its picture once in
this vocabulary; every look can then paint it its own way.

So a look **can't restyle a photo, a screen capture or footage** yet. When a
note asks for a look on a video built from those, say so as a shortfall
(the `shortfalls` block, kind "cannot") and offer the look on a drawn scene
instead: a title card, an end card, or a backdrop behind the footage.

```python
scene = looks.Scene(w, h, regions, horizon=None, sun=None, beacon=None, stars=None, bpm=120)
looks.paint(cv, name, scene, t, age=None, **options)
```

- **`regions`**: `looks.Region(role, points)`, back to front. `points` is a
  closed polygon in film pixels (`paths` helpers make good ones). Whatever
  no region covers is sky above `horizon` and water below it -- or all sky
  with no horizon.
- **Roles** (`looks.ROLES`): pick the one whose *job* fits, not the literal
  thing.
  - `land`: ground, hills, a cliff, a table top, a stage floor.
  - `building`: anything built and standing: a tower, a house, a phone on
    its stand, a bottle. Parts of one structure are separate regions
    stacked front to back (tower, then its gallery, then its roof).
  - `figure`: the subject that moves: a boat, a person, a car, the product.
  - `light`: something lit: a lantern, a window, a screen.
  - `sky`, `water`: only where they must sit *in front* of something.
- **Point features**: `sun=(x, y, r)` (sun or moon -- the swirl's halo,
  the Bauhaus wheel, the melt's drip turn round it); `beacon=(x, y)` (a
  point light that throws turning beams: a lamp, a headlight); `stars` (left
  as None, the scene scatters seeded ones over the sky).
- **`t`**: film time in seconds. A look's motion runs on it, so it carries
  on through cuts and wipes. **`age`**: seconds since this look came on
  screen, for one-off moves (the woodblock wave, the blueprint drawing in);
  it defaults to `t`.
- A look paints **every pixel** of the scene's `w` x `h`, draws no text of
  its own unless asked (`sfx`, `font`) and **marks nothing**: the video draws
  and marks its own words on top.

## Adopting a look

Describe the scene from the frame's own size (so it fits every format), as
a function of time if anything moves, and paint it first in `draw`:

```python
import videobuilder as vb
from videobuilder import looks

def street(w, h, t):
    """A street at dusk: two buildings, a lamp post, someone walking past."""
    ground = h * 0.78
    walker = w * (0.15 + 0.7 * (t / 4 % 1))
    return looks.Scene(w, h, [
        looks.Region('land', [(0, ground), (w, ground), (w, h), (0, h)]),
        looks.Region('building', [(w * .05, ground), (w * .35, ground), (w * .35, h * .3), (w * .05, h * .3)]),
        looks.Region('light', [(w * .12, h * .4), (w * .2, h * .4), (w * .2, h * .5), (w * .12, h * .5)]),
        looks.Region('building', [(w * .6, ground), (w * .9, ground), (w * .9, h * .4), (w * .6, h * .4)]),
        looks.Region('figure', [(walker - 20, ground), (walker + 20, ground), (walker, ground - 110)]),
    ], sun=(w * .78, h * .2, min(w, h) * .07), beacon=(w * .48, h * .45))

def draw(n, cv):
    t = n / 30
    looks.paint(cv, 'woodblock', street(cv.width, cv.height, t), t)

FILM = vb.Film(draw=draw, fps=30, frames=120, formats=('16x9', '9x16'))
```

`looks.lighthouse(w, h, t)` is a complete scene to copy from: it is the one
every look's demo on the Capabilities page paints (`examples/capabilities/_looks.py`).

- **One look for the whole film**: paint it at the start of `draw`, then
  the video's copy, plaques and marks on top. Put copy on a dark or light
  plaque, since the look decides the colours underneath.
- **A look in one box**: `with cv.clip(*box): with cv.layer(dx=box.x, dy=box.y):`
  and paint `Scene(box.w, box.h, ...)`.
- **A look per segment**: pass `age` as seconds into the segment, so its
  one-off move plays each time it comes on.
- **"Try a few looks"**: `looks.relay(cv, scene, t, ['pop-art', 'woodblock', 'pixel'], hold=2.0, wipe=0.5)`
  paints each in turn, wiping from one to the next, and returns the name on
  screen (put it on a plaque so the director can say which they want).
- **Keep the look's motion**: it is what makes it read as that look. Don't
  freeze `t` to calm a look down; pick another look instead.

## Making a new look

A look is one function and one registration:

```python
from videobuilder import looks
from videobuilder.looks import kit     # fills, dabs, beams, beat pulses, seeded grids

def paint(cv, scene, t, age):
    ...   # paint every role, the sun, the stars; move something across a good part of the frame

LOOK = looks.register(looks.Look('stained-glass', 'Stained glass', 'panes glow as light passes', paint))
```

- Paint by **role**, never by one scene's coordinates; size strokes and
  spacing by `scene.u` (the short side over 1080) so it reads the same at
  every size; ask `scene.role_at(x, y)`, `scene.open_water()` and
  `scene.ledge()` where a move needs a place.
- Give it **one hero move** that covers a good part of the frame, and check
  the motion floor: `looks.motion_floor(FILM, start, end) >= looks.FLOOR`
  (at least a fifth of the frame's tiles visibly moving at every sample).
- Seed every random choice (`random.Random(seed)`, or `kit.jittered_grid`,
  worked out once and cached); only the motion is per frame. For spray that
  should change, seed from time: `random.Random(int(t * 10))`.
- `cv.pixelated(f, 0, 0, scene.w, scene.h)` yields its own canvas: draw
  with that one, not `cv`.
- Try it on `looks.lighthouse` and on your own scene, in a wide and a tall
  frame, with no sun and no horizon too.

A look made for one video lives in that video. To offer it to everyone, a
creator adds it on the Capabilities page with Add capability, "A new look":
a builder writes it as `look.py` with a demo on `looks.lighthouse`, and once
an admin publishes it, it appears in the Looks family and in every builder's
prompt.
