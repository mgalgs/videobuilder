# Looks: named art styles for any video

A look is a named art style -- pop art, woodblock print, 8-bit pixels --
that restyles a video and gives it a movement of its own. When a note says
"make it pop art", "paint it like a woodblock print" or "try a few looks",
reach for `videobuilder.looks` instead of restyling the film by hand.

There are two kinds, and **the video decides which one you use**:

- A **scene look** (`looks.paint`) repaints a picture the video *describes*
  as a few shapes with roles (a `looks.Scene`). Use it when the picture is
  drawn: a title card, an illustrated scene, a backdrop. It has the richer
  moves (a wave that curls, a clock that melts, a burst with a word in it).
- A **filter look** (`looks.filter`) restyles *pixels*: whatever the film
  draws inside the block -- a photo, a screen capture, footage, charts,
  anything. Use it for every video that isn't a described scene: "make my
  product demo pop art" is a filter.

The two share names where the style carries over (`pop-art`, `pixel`,
`woodblock`, `blueprint`, `pointillism`), so the same words find both: the
call you make decides the kind. `looks.get`/`looks.names` are the scene
looks, `looks.get_filter`/`looks.filters` the filter looks, and every name,
alias and title of a scene look ("comic", "8-bit", "ukiyo-e") also finds its
filter. `swirl`, `melt` and `bauhaus` are scene looks only.

```python
from videobuilder import looks
looks.names()      # scene looks: ('swirl', 'pointillism', 'woodblock', 'melt', 'bauhaus', 'pop-art', 'pixel', 'blueprint', ...)
looks.filters()    # filter looks: ('pop-art', 'pixel', 'woodblock', 'blueprint', 'pointillism', ...)
looks.get('pop art').title          # 'Pop-art halftone' -- any case or spacing, an alias or the title
looks.get_filter('comic').title     # 'Pop-art filter'
```

## Scene looks

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

## The scene contract

A scene look paints a **scene description**, not pixels: a few shapes with
roles, the sun, a beacon and stars. The video describes its picture once in
this vocabulary; every scene look can then paint it its own way. (For a
photo, a capture or footage, use a filter look instead: see below.)

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

## Filter looks

| filter | what it looks like | what moves | options |
|---|---|---|---|
| `pop-art` | the picture posterized to a loud flat palette, Ben-Day dots in a deeper shade of each area (biggest in the shadows), thick dark outlines | the dots drift | |
| `pixel` | a chunky grid in a 16-colour game palette, faint scan lines | a rolling bar steps down the screen at 8 fps, its rows slipping a block | `block=` px at 1080 (12) |
| `woodblock` | flat inks (indigo, vermilion, ochre, sage) on cream paper, every strong edge inked | the paper grain and the ink lines boil on twos | |
| `blueprint` | edges only, as chalk lines on a blue grid | the lines draw in from the top (on `age`), then a scan line sweeps, the grid shimmers, the chalk boils | |
| `pointillism` | the picture rebuilt from seeded dots of its own colours on a pale ground | every dot circles a little and shimmers warmer and cooler | `pitch=` px at 1080 (14) |

```python
with looks.filter(cv, name, t, age=None, box=None, **options):
    ...   # draw the picture as usual, on cv
# copy that must stay readable goes here, after the block
```

- Everything on `cv` when the block ends is treated, every pixel -- what
  the body drew *and* what was drawn before it -- and painted back. `box=(x,
  y, w, h)` treats only that part of the frame (a filtered window in an
  otherwise plain frame).
- The body draws on `cv` exactly as it would without the filter (the block
  also yields it: `as c`), so wrapping an existing `draw` is one line.
- **Draw words after the block**, on a plaque: a filter outlines, dots or
  pixelates text like everything else, and small copy stops reading.
- **`t`** runs the filter's own motion; **`age`** (seconds since the filter
  came on, default `t`) runs one-off moves (blueprint's drawing in). Each
  filter moves on its own, so a screenshot held for the whole demo still
  reads as alive: keep it, don't freeze `t`.
- **`pixel` steps at 8 fps.** To step the picture underneath with it, draw
  it at `looks.get_filter('pixel').step(t)` (every filter has `step`; the
  smooth ones give `t` back).
- A filter is per frame: about 30-220 ms a frame at 1080x1920 (pointillism
  and woodblock the slowest). A preview at a smaller scale is cheaper.
- **One filter per segment** or **try a few**: switch the name on time; to
  wipe between two, filter the frame twice, the second inside a
  `cv.clip` of the wiping part.

A product demo in pop art, its caption outside the filter:

```python
import videobuilder as vb
from videobuilder import looks

def capture(cv, t):
    """The stand-in screen: a page, a header bar, a chart whose bars grow in."""
    w, h = cv.width, cv.height
    cv.fill('#f4f6fa')
    cv.rect(0, 0, w, h * 0.12, '#1b2333')
    for i in range(6):
        bar = h * (0.12 + 0.06 * i) * min(1.0, t / 1.5)
        cv.rect(w * (0.12 + 0.13 * i), h * 0.85 - bar, w * 0.09, bar, ('#3a6ff0', '#f0644a')[i % 2], radius=8)

def draw(n, cv):
    t = n / 30
    with looks.filter(cv, 'pop-art', t):
        capture(cv, t)
    cv.rect(40, 40, 260, 70, (14, 16, 22, 0.86), radius=14)   # the caption's plaque goes here, unfiltered

FILM = vb.Film(draw=draw, fps=30, frames=90, formats=('16x9', '9x16'))
```

What a filter can't do: it sees pixels, not things, so it has none of the
scene looks' object moves (the woodblock wave, the melting clock, the
pop-art burst on the beat) -- for those, describe the picture as a Scene.
`swirl`, `melt` and `bauhaus` have no filter yet; for a photo or footage in
one of those, say so as a shortfall (the `shortfalls` block, kind
"cannot") and offer the nearest filter or the scene look on a drawn card.

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

A filter look is the same: one function and one registration. `treat`
takes the frame as a PIL RGB image and returns it treated, the same size;
`videobuilder.looks.fx` has the pieces the built-in filters are made of
(posterize to a palette, halftone screens, edges, seeded noise, a shimmer
band). Pillow and cairo only -- never numpy -- and cache whatever doesn't
depend on the frame:

```python
from videobuilder import looks
from videobuilder.looks import fx

def treat(im, t, age, u):
    ...   # return a new image the size of im; size strokes by u (the short side over 1080)

FILTER = looks.register_filter(looks.Filter('stained-glass', 'Stained glass filter', 'panes glow', treat))
```

A look made for one video lives in that video. To offer it to everyone, a
creator adds it on the Capabilities page with Add capability, "A new look":
a builder writes it as `look.py` with a demo on `looks.lighthouse`, and once
an admin publishes it, it appears among the Looks and in every builder's
prompt. That flow takes scene looks only; a filter look is offered by adding
it to `videobuilder.looks` itself.
