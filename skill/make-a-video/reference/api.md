# videobuilder API cheatsheet

`import videobuilder as vb` and `from videobuilder import Box, fr, per_format, text`.
Units are film pixels (1080×1920 for 9:16, 1920×1080 for 16:9, 1080×1080
for 1:1) and frames. Full prose: `$VB/README.md`. The source is small and
readable: `$VB/videobuilder/*.py`.

## Time: grid, segments, shots

```python
GRID = vb.Grid(fps=30, bpm=120, head_trim=0)   # 15 frames a beat
GRID.b(6.5)                # frame of beat 6.5 (round half up) -> 98
GRID.frames_per_beat       # 15.0
TIMELINE = vb.Timeline(GRID, [
    vb.Segment('title', 0, 8, data={'copy': ['Title', 'Supporting line'], 'copy_at': 0.5}),
    vb.Segment('list', 4, 10, children=vb.sequence(4, [('a', 2), ('b', 2), ('c', 2)])),
    vb.Segment('end', 10, 16, overlap=1),        # the list keeps drawing under it for a beat
], end=16)
```

- Segments are gap-free, in beats, each start on the half-beat grid.
  `Timeline` raises if not. A group's `children` fill it, gap-free.
- `TIMELINE.live(n)`: the `Shot`s drawing at frame `n`, back to front.
  A `Shot` has `name`, `data`, `segment`, `f` (frames into the segment),
  `length` (its frames), `group` / `group_f` (innermost group and frames into
  it, or None), and `exit` (frames since the next segment began over it, in
  an overlap; else None). In an overlap the outgoing shot keeps counting `f`
  past its `length`.
- `TIMELINE.frames`, `.at(n)` → (segment, f) of the front shot, `.span(name)`
  → (first, end) frames, `.start(name)`, `.find(name)`, `.leaves()`,
  `.walk()`, `.label(n)`, `.cut_frames()` (hard cuts: every non-overlapping
  start, at any level).
- **Trap:** never `round()` frame math (banker's rounding moves half-beat
  cuts); use `GRID.b(beat)` or `vb.round_half_up(x)`.

## Motion: easing and springs (pure functions)

```python
vb.clamp01(x)
vb.interpolate(f, [0, 12, 30], [0, 1, 0.5], ease=EASE)   # keyframes, clamped
EASE = vb.bezier(0.16, 1, 0.3, 1)                          # CSS cubic-bezier
vb.ease_out_expo(p), vb.ease_out_quint(p), vb.ease_in_out_quart(p)
vb.ease_in_expo(p), vb.ease_out_back(p)                       # back overshoots 1
vb.spring_at(f - delay, GRID.fps, stiffness=170, damping=12)   # 0 -> 1, bounces
vb.spring_at(f, GRID.fps, **vb.damped(0.7, hz=2.0))          # ratio and natural Hz
vb.spring_at(f, GRID.fps, **vb.critical(140))              # settles, no overshoot
vb.log_lerp(1.0, 1.3, p)                                   # even-feeling zoom
```

- Progress: `p = vb.clamp01((shot.f - start) / frames)`, then `EASE(p)`.
- An exit: `vb.interpolate(shot.f, [shot.length - 8, shot.length], [1, 0])`.
- A spring passes 1 when it bounces: `min(1, s)` for opacity.
- **Trap:** springs are real physics. Damping ratio
  `damping / (2*sqrt(stiffness*mass))` ≥ 1 is over-damped and crawls; use
  `vb.critical(k)` for "settle". (Remotion treats ≥ 1 as critical.)

## Canvas: drawing

```python
cv.width, cv.height, cv.format.name             # format being drawn
cv.fill(colour)
cv.rect(x, y, w, h, colour, radius=0, alpha=1)   # or cv.rect(*box, colour)
cv.outline(*box, colour, width=2, radius=0)
cv.line(x0, y0, x1, y1, colour, width=2)
cv.arc(cx, cy, r, a0, a1, colour, width=2, alpha=1)  # stroke, butt ends
cv.sector(cx, cy, r, a0, a1, colour, alpha=1)        # filled pie slice
cv.image(img, *box, alpha=1)                     # stretched to the box
cv.shadow(*box, radius=24, dy=18, blur=50, color=(0, 0, 0, 0.4))   # draw before the box
cv.shape_shadow(points, dx=4, dy=10, blur=18, color=(0, 0, 0, 0.4))  # same, following any closed outline
with cv.layer(opacity=0.5, dx=0, dy=40, scale=1.0): ...   # group: fades, moves, scales together
with cv.clip(*box, radius=24): ...
cv.mark('name', *box)                            # tag content for checks (records the moved box)
cv.ctx                                           # raw cairo context, for paths, arcs, gradients
vb.rgba(colour)                                  # -> cairo floats for cv.ctx.set_source_rgba(*...)
with cv.pixelated(8) as px:                      # body draws into px at 1/8 resolution,
    px.rect(...); text.draw(px, ...)             # painted back nearest-neighbour: blocky pixel art
ctx.set_source(vb.halftone_pattern(14, 5, angle=0.4, color='#000'))   # a repeating dot fill
ctx.paint()                                      # (a cairo pattern; use within a clip to fill a shape)
ctx.set_source(vb.paper_grain(cv.width, cv.height, seed=1))   # paper texture, mid-grey centred:
ctx.set_operator(cairo.OPERATOR_SOFT_LIGHT); ctx.paint_with_alpha(0.5)   # lightens and darkens
ctx.set_operator(cairo.OPERATOR_OVER)            # put the operator back afterwards
```

- `cv.pixelated(factor, x=0, y=0, w=None, h=None, background=None)`: a group, in the
  style of `layer`/`clip`, drawn with the *yielded* Canvas (not `cv`) at 1/`factor`
  resolution over the region (default the whole frame) and painted back with
  nearest-neighbour filtering. Any text or image drawn into it pixelates too. A film
  that never calls it renders exactly as before.
- `vb.halftone_pattern(pitch, radius, angle=0, color='#000')`: a cairo pattern of
  repeating dots (a Ben-Day halftone fill), `pitch` px between centres. There is no
  image-to-halftone conversion, only this generated dot fill.
- `cv.shape_shadow(points, dx=0, dy=0, blur=0, color=(0, 0, 0, 0.5))`: `cv.shadow` for
  a closed point list instead of a box (a torn scrap, a cut-out's outline), so a lift
  shadow follows the real shape. Its blurred mask is made once per shape and `blur` and
  cached: keep `points` fixed and move the piece with a `layer` or a cairo transform,
  not by rebuilding the points each frame, or every frame pays for a fresh blur.
- `vb.paper_grain(width, height, seed=0)`: a cairo pattern of paper texture (fine
  grain, short fibres, a faint mottle) in grey centred on 128, generated once per size
  and seed and cached; it tiles beyond its size. Paint it with
  `cairo.OPERATOR_SOFT_LIGHT` (128 leaves the colour alone) within a clip for one
  piece, or over the whole frame. Painting it full-frame costs ~10 ms at 720×720: for a
  static backdrop, draw backdrop and grain once into a cached surface instead.

## Paths: partial reveal, resampling and morphing

```python
from videobuilder import paths
paths.length(points, closed=False)                       # total arc length
paths.reveal(points, fraction, closed=False)              # the leading fraction, by arc length
paths.resample(points, n, closed=False)                   # n points evenly spaced by arc length
paths.morph(a, b, t, closed=False, n=None)                # a resampled/aligned lerp between two shapes
paths.jitter(points, seed, amount=1.0, wander=0.3)        # deterministic seeded hand-wobble
paths.torn(points, seed, amount=4.0, step=2.5, closed=True)   # a torn-paper edge, seeded
paths.draw(cv, points, colour, width=2, closed=False, fill=False, alpha=1.0)   # draw the point list
```

- Pure geometry on point lists (`[(x, y), ...]`, film px); nothing here keeps a cairo
  path around. `paths.draw` is the one function that touches a canvas.
- `reveal`: for a self-drawing line or a stroke-by-stroke diagram, `paths.draw(cv,
  paths.reveal(points, shot.f / total_frames), colour, width=4)`.
- `morph`: both shapes are resampled to the same point count (`n`, default the
  longer of the two); for a closed shape, `b` is rotated to the start point (and
  reversed if its winding differs) that best matches `a`'s, so corresponding points
  travel the short way round instead of visibly twisting. Ease `t` yourself (a
  bezier, or `6t^5 - 15t^4 + 10t^3` for a very soft start/stop) before calling it.
- `jitter`: bake it in once at import (`JITTERED = paths.jitter(points, seed=3)`),
  not per frame, so the same stroke wobbles the same way every frame it's drawn.
- `torn`: resamples the outline every ~`step` px and pushes each point in or out along
  the edge's normal by up to `amount` px of seeded fractal noise (a broad wander, smaller
  bites, a fine fibre fuzz), so the edge reads torn rather than zig-zag; a closed
  outline's noise wraps with no seam, `closed=False` tears an open line. Bake it in at
  import like `jitter`. Pair it with `cv.shape_shadow` for a scrap lifted off the wall.
- **Trap:** `resample`/`morph` take a plain list of `(x, y)` tuples, not a `Box` or
  a cairo path; build the point list yourself (a rect's corners, a circle's samples).

- Arc/sector angles are radians from the positive x axis, increasing clockwise
  in canvas coordinates (Cairo convention). `0` to `2 * math.pi` makes a circle.
  Radius and stroke width are film pixels; layers and clips apply as usual.
- `cv.fill` and `ctx.paint()` fill the whole clip and ignore a layer's
  `dx`/`dy`: a background that should slide with a layer is
  `cv.rect(0, 0, cv.width, cv.height, colour)` (or a `ctx.rectangle` path).
- Colours: `'#rgb'`, `'#rgba'`, `'#rrggbb'`, `'#rrggbbaa'`, or `(r, g, b[, a])`
  with 0–255 channels and 0–1 alpha.
- `layer(scale=s)` scales about (0, 0) of the current space: to scale about a
  box's centre, `with cv.layer(dx=b.cx * (1 - s), dy=b.cy * (1 - s), scale=s)`.
- Raw cairo: `ctx.save()` / `ctx.restore()` around transforms; `ctx.new_path()`
  before a path; `cairo.LinearGradient` for gradients (`import cairo`).
- **Trap:** a CSS shadow list paints its first shadow on top: call
  `cv.shadow` for them last to first.

## Parallax: flat layers with depth

```python
from videobuilder import parallax, paths
HILLS = parallax.ridge(720, 120, seed=2)                 # at import: a skyline tile whose ends meet
def hills(cv, x):                                        # one tile, left edge at x
    paths.draw(cv, [(x + px, 380 + py) for px, py in HILLS + [(720, 300), (0, 300)]], '#3a4458', fill=True)
LAYERS = (parallax.Layer(0.2, 720, hills), parallax.Layer(0.5, 360, trees),
          parallax.Layer(1.0, 240, ground), parallax.Layer(1.7, 900, foreground))
parallax.draw(cv, LAYERS[:3], camera_x)                  # far first
FOX.draw(cv, pose, fox_x - camera_x, ground_y)           # on the ground layer: moves with it
parallax.draw(cv, LAYERS[3:], camera_x)                  # the foreground passes in front
```

- `depth`: px a layer moves per px of pan. 0 is pinned to the sky, 1 the
  ground, over 1 a foreground. Hazier, lighter colours far away and darker
  ones near sell the depth as much as the speeds do.
- A tile's right edge must meet its left (`ridge` waves fit a whole number
  of times); overlap a fill by a px each side so tiles show no hairline.
- For a seamless loop, the camera's travel x each layer's depth is a whole
  number of its tile widths, or pan out and back.
- Lay each format out from its own table (`per_format`): the ground's height,
  the hills' size and the pan differ between 9:16 and 16:9.

## Impact frames

```python
from videobuilder import impact
HIT = impact.Hit(at=60)               # push=6, hold=2, settle=14, flash=5, linger=20, zoom=1.15, shake=16, seed=0
def draw(n, cv):
    HIT.draw(cv, n, lambda c: scene(c, n), lambda c: fox(c, n), centre=(x, y))
```

- `scene(cv)` draws the whole ordinary frame; `subject(cv)` only the thing
  hit, painted as a flat `ink` silhouette on the `hold` held frames, inside a
  seeded burst of speed lines on `paper`. Outside `HIT.span` it is just `scene`.
- One hit is one full-frame flash. Keep hits at least a second apart, and
  never more than two in a second: photosensitive viewers. `check.py --video`
  counts flashes.
- The pieces: `impact.speed_lines(cv, cx, cy, seed, inner)`,
  `impact.silhouette(cv, draw, colour)`, `impact.shake(n, at, frames, amount, seed)`.

## Images and captures

```python
img = vb.Image.load('assets/shot.png')          # decoded once per process; fine inside draw
pic = vb.Image.from_pil(pil_image)               # generated in code, once, at import
clip = vb.Clip('assets/orbit.mp4')                # ffmpeg video asset; construct once
clip.frames, clip.fps, clip.size                 # frame count, rate, (width, height)
pic = clip.frame(local_frame)                   # random access; IndexError outside clip
with cv.clip(*box, radius=20):
    cv.image(img, *box.cover(img.w, img.h))      # fill the box, crop the overflow
cv.image(img, *box.contain(img.w, img.h))        # whole image, letterboxed
v = cv.view(img, box, center=(cx, cy), scale=s, radius=20, background='#fff')   # a camera
v.pin(Box(0, 0, img.w, 120), y=box.y)            # keep the top strip fixed while panning
v.to_screen(px, py), v.image_box()               # where image points land
```

- **Trap:** don't build or decode images inside `draw` per frame (slow); make
  them at import or use `Image.load`.

### A cut-out character in poses

```python
FOX = vb.Puppet({'idle': 'assets/fox/idle.png', 'talk': 'assets/fox/talk.png',
                 'point': 'assets/fox/point.png'}, height=380)   # at import: decoded and downscaled once
pose, age = FOX.pose_at(n, [(0, 'idle'), (20, 'talk'), (24, 'idle'), (45, 'point')])   # held poses
sx, sy = FOX.breath(n, 60)                          # a slow breath, so a hold never freezes
FOX.draw(cv, pose, x, ground_y, sx=sx, sy=sy, lean=0.03, angle=0, mark='fox')   # feet at (x, ground_y)
```

- Every transform pivots on the feet, so squash and stretch keeps the
  character on the ground. `height` is the first pose's character (its
  opaque pixels) in px; all poses share its scale.
- Each pose is placed by its own feet (the middle of its lowest opaque
  rows), so poses drawn a little off each other don't jump on a swap. A
  pose whose feet are raised (a jump) lands on the ground line too: draw
  it lifted.
- The pictures must have their backgrounds cut out; `age` is 0 on the
  frame a pose snaps in, for a 2-3 frame pop.

### A walk without leg drawings

```python
STEP = GRID.frames_per_beat / 2                     # two steps a beat
g = FOX.walk(n, STEP, rise=0.035, squash=0.05, lean=0.04)   # Gait(lift, sx, sy, lean, phase)
FOX.draw(cv, 'idle', x, ground_y - g.lift, sx=-g.sx, sy=g.sy, lean=g.lean)   # -sx: mirrored to face the way
parallax.draw(cv, LAYERS, n * STRIDE / STEP)        # the ground passes one stride a step
```

- The bounce-walk of cut-out TV animation: down with a squash on each
  contact (`phase` 0), up `rise` x its height on the passing position,
  leaning forward. It stays put; the ground scrolling past at a steady
  speed is what makes it walk. Say so if asked for a real leg cycle:
  that needs leg drawings.
- A whole number of steps across a loop, and the scroll's travel a whole
  number of each layer's tiles, keep the seam clean.

## Text

```python
text.register('assets/Font.otf')                 # once, at import
F = vb.Font('Family', 64, weight=700, tracking=-0.01, line_height=1.1)   # px, em, multiple
lines = text.wrap('copy', F, max_width, balance=True)    # tuple of lines; '\n' forces a break
w, h = text.block_size(lines, F)
text.measure('one line', F)                      # width
text.line_height(F)
box = text.draw(cv, lines, F, x, y, colour, align='center', width=w)   # returns the Box drawn
chip = text.box('New', F, padding=(8, 16), x=100, y=200)               # label size incl. padding
text.draw_in(cv, chip, 'New', F, colour, padding=(8, 16))
```

- `text.draw` draws top-down from (x, y); `align` is within `width`.
- `weight` takes any value on a variable font's axis.
- **Trap:** CSS adds letter-spacing after the last letter too; Pango doesn't.
  To match a browser layout, `Font(..., css_tracking=True)`.
- **Trap:** a `Font` whose family isn't registered or installed logs one warning per family per
  process when used, then falls back to a system font, and a weight a static family doesn't have
  falls back to the nearest file. `$SKILL/scripts/fontinfo.py assets/*`
  prints each file's family name and weight; look at a still to confirm.
- Two families: `vb.Font('Family A', ...)` and `vb.Font('Family B', ...)`;
  register both files.

## Layout

```python
frame = Box.of(cv)                    # or Box(0, 0, 1080, 1920)
safe = frame.pad(200, 60, 360, 60)    # CSS order: top, right, bottom, left
left, right = safe.row(fr, 1.5 * fr, gap=40)       # px or fr shares
top, mid, bottom = safe.column(200, fr, 120, gap=24)
boxes, total = safe.stack([120, 260, 80], gap=24, align='top')  # measured heights
cells = safe.grid(3, 2, gap=20)        # cols, rows; row-major
safe.center(w, h), safe.anchor(w, h, 'bottom-left', margin=20)
safe.contain(16, 9), safe.cover(w, h), safe.fit(w, h, 'scale-down')
b.x, b.y, b.w, b.h, b.right, b.bottom, b.cx, b.cy, b.moved(dx, dy), b.scaled(s)
safe.contains(box), a.intersects(b)    # for checks
L = per_format(LAYOUTS, cv)            # the table for the format being drawn ('*' falls back)
```

## Film

```python
FILM = vb.Film(draw=draw, timeline=TIMELINE, formats=('9x16', '16x9'), background='#000',
               audio=vb.Audio('assets/music.wav', gain_db=0, fade_out_frames=60),
               keyframes=((75, 'title held'), 300))
if __name__ == '__main__':
    vb.main(__file__)                  # python film.py render|still|sheet|preview ...
```

- `Audio.trim_frames` defaults to the grid's `head_trim`. The fade is linear
  over the `fade_out_frames` before the last frame.
- `Audio.loudness=-14.0` brings the trimmed, gained and faded audio toward
  that integrated LUFS with one gain, then a lookahead limiter at -3 dBFS
  catches the transients it pushes over, so the decoded MP4 stays at or below
  -1 dBTP. The gain is capped so the limiter takes at most 1 dB off the
  loudest peak: a peaky track comes out quieter than the target rather than
  compressed. The limiter is delay-compensated: hits stay on their frames.
  `None` keeps the fixed `gain_db` only.
- `sounds=(...)`: `vb.Sound`s on the film's clock (footage, narration) and
  sound effects, `vb.sfx.sound('whoosh_fast/tight', at=frame, dur=0.5,
  gain_db=-8)`, each with its peak on its frame (`reference/sfx.md`).
  The music ducks under the sounds, never under the sound effects.
- `vb.load_module('film.py')` imports a film afresh for a check script; its
  `FILM`, `LAYOUTS` and other names are attributes.
- Custom size: `vb.Format('4x5', 1080, 1350)` in `formats`.

## CLI

```
python film.py render  [--format F|all] [--jobs N] [--out FILE] [--frames a:b]
python film.py still   FRAME [FRAME ...] [--format F|all] [--out PATH] [--overlay] [--scale S]
python film.py sheet   [--format F|all] [--every N | --frames a,b,c | --cuts [N]] [--cols C] [--width W]
python film.py preview [--port 8000] [--open]
```

- **Trap:** `render --chunk N` must be a whole number of µs at the fps (ffmpeg
  concat drift); the default 15 is safe at 24/25/30/60 fps.

## Declared frame checks

Put `EXPECT = [...]` beside `FILM`. `check.py` runs each entry in every format by default. Every constructor takes `formats=('9x16',)` to restrict formats and `note='director words'` to print on failure.

```python
EXPECT = [
    vb.visible('logo', vb.seg('outro')),                  # present and inside safe area, or frame
    vb.hidden('logo', vb.seg('intro')),                   # absent on this frame
    vb.touches('feet', 'pad', vb.seg('land', 3), tolerance=2),
    vb.apart('logo', 'copy', vb.seg('hold'), min_gap=20),
    vb.still('headline', (vb.seg('hold', 2), vb.seg('hold', 'end', -1))),
    vb.at_rest_by('headline', vb.seg('hold', 4), speed=0.5),
]
```

A frame is an integer or `vb.seg(name, place='start', offset=0)`. `place` is `start`, `mid`, or `end`; `vb.seg('land', 3)` means three frames after its start, and `end` is the exclusive segment end, so `vb.seg('land', 'end', -1)` is its last frame. Ranges include both endpoints. `touches` measures the shortest box-edge gap; small overlap up to its tolerance also passes. `apart` requires the shortest box gap to meet `min_gap`. `still` compares position and size exactly. `at_rest_by` measures translation plus size change in px/frame from the preceding frame through the segment's end. A missing mark fails; even `hidden` requires that mark to occur somewhere in the film.

`python -m videobuilder motion film.py [--format F] [--mark NAME ...] [--from FRAME|SEG --to FRAME|SEG] [--onion N] -o out.png` writes a speed graph with cuts, beats, warning markers, and direct series labels. `--onion N` adds a frame composite every N frames with mark trails. The command prints each mark's peak speed and first frame after which it stays below 0.5 px/frame in the chosen range.
