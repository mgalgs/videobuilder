# videobuilder

A small, dependency-light Python framework for making videos in code: product
reels, explainers, benchmark and result videos. A film is a Python file with a
pure `draw(n, canvas)`; videobuilder gives it a beat-aware timeline, easing and
springs, real-font text, layout, a live preview, and a parallel renderer that
pipes frames to ffmpeg.

It provides mechanisms, not a style. Palettes, type, brand rules and visual
conventions belong to your films.

## Install

You need Python 3.11 or newer, plus some system packages: ffmpeg, cairo, and
Pango with GObject introspection. The Python packages are pycairo, PyGObject
and Pillow.

**Arch Linux**

    sudo pacman -S python python-cairo python-gobject python-pillow pango ffmpeg

**Debian / Ubuntu**

    sudo apt install python3 python3-venv python3-cairo python3-gi python3-pil \
        gir1.2-pango-1.0 ffmpeg

To have pip build pycairo and PyGObject in a virtualenv instead of using
the distro's copies, also install `pkg-config python3-dev libcairo2-dev` and
`libgirepository-2.0-dev`. On releases older than Debian 13 or Ubuntu 24.04,
install `libgirepository1.0-dev` instead.

**macOS (Homebrew)**

    brew install python pango pygobject3 py3cairo ffmpeg

Then, from a checkout:

    pip install -e .            # or use it in place: PYTHONPATH=. python -m videobuilder ...

With the distro packages above, a virtualenv made with
`python -m venv --system-site-packages` can see pycairo and PyGObject.

## Hello, world

`hello.py`:

```python
import videobuilder as vb
from videobuilder import Box, per_format

GRID = vb.Grid(fps=30, bpm=120)                  # 15 frames a beat
TIMELINE = vb.Timeline(GRID, [vb.Segment('hello', 0, 4), vb.Segment('bye', 4, 6)], end=6)
FONT = {'*': vb.Font('Sans', 120, weight=700), '16x9': vb.Font('Sans', 160, weight=700)}


def draw(n, cv):
    seg, f = TIMELINE.at(n)                      # the live segment, and frames into it
    font = per_format(FONT, cv)                  # each format can lay out differently
    words = 'Hello, world' if seg.name == 'hello' else 'Goodbye'
    lines = vb.text.wrap(words, font, cv.width * 0.8, balance=True)
    box = Box.of(cv).center(*vb.text.block_size(lines, font))
    s = vb.spring_at(f, GRID.fps)                # 0 -> 1, with a little bounce
    with cv.layer(opacity=min(1, s), dy=(1 - s) * 60):
        vb.text.draw(cv, lines, font, box.x, box.y, '#ffffff', align='center')


FILM = vb.Film(draw=draw, timeline=TIMELINE, formats=('16x9', '9x16', '1x1'), background='#1d2b53')
```

    python -m videobuilder preview hello.py              # http://127.0.0.1:8000/
    python -m videobuilder render hello.py --format all  # hello-16x9.mp4, hello-9x16.mp4, hello-1x1.mp4

`examples/tour.py` is a fuller example (12 s, three formats, a generated
picture and click track). Its font, Cantarell, is vendored with its OFL
licence in `examples/assets/`.

## The film file

A film file is a Python module that defines `FILM = videobuilder.Film(...)`:

| field | |
|---|---|
| `draw(n, canvas)` | Paints frame `n`. It must be **pure**: the same `n` and format always give the same pixels, with no state carried between calls. Chunked parallel rendering, stills and the preview all draw frames alone and out of order. |
| `fps`, `frames` | Frame rate and length. Both may be omitted when a `timeline` supplies them. |
| `timeline` | Optional `Timeline`. It gives the preview and stills its segments and beats, and supplies fps and frames. |
| `formats` | Format names (`'9x16'` 1080×1920, `'16x9'` 1920×1080, `'1x1'` 1080×1080) or `Format(name, w, h)`. The first is the default. |
| `background` | Colour painted before `draw`, or `None` for transparent. Default black. |
| `audio` | Optional `Audio(path, trim_frames=0, gain_db=0, fade_out_frames=0)`, muxed in by `render`. |
| `keyframes` | Optional frames worth reviewing: frame numbers or `(frame, label)` pairs. `sheet` shows them, labelled, by default. |

Inside `draw`, `canvas.width` and `canvas.height` are the format's size in film
pixels, and `canvas.format` says which format is being drawn. Formats are
layouts, not crops: lay each format out for its own shape, usually from a
per-format table (`per_format(table, canvas)`, with `'*'` as the fallback).

For a flat table of a few values (a font size, a column count), a `'*'` base
with small per-format overrides is fine; dict entries merge one level deep.
For a real layout, nested and computed from the frame's boxes, write one
full table per format, each from a function, and let `per_format` only pick:

```python
def layout_9x16():
    safe = Box(60, 220, 880, 1320)
    return dict(safe=safe, title=dict(size=110, measure=safe.w), card=safe.pad(0, 0, 400, 0))


def layout_16x9():
    safe = Box(0, 0, 1920, 1080).pad(54)
    return dict(safe=safe, title=dict(size=132, measure=1200), card=safe.row(fr, fr, gap=40)[1])


LAYOUTS = {'9x16': layout_9x16(), '16x9': layout_16x9()}
L = per_format(LAYOUTS, cv)
```

Each format's numbers then sit together and come from its own geometry, and
nothing is half-inherited: a deep merge of `'*'` would have to guess whether a
nested dict is a group of overrides or one value (a shadow, a font spec).

The film's directory goes on `sys.path`, so a film can import helper modules
that sit beside it. The preview reloads those too.

End a film with `if __name__ == '__main__': videobuilder.main(__file__)` and
it runs the CLI on itself: `python film.py render --format all` is
`python -m videobuilder render film.py --format all`.

A tool that checks a film (a safe-area check, a parity script) often needs
the film's own data too, its layout tables say. `videobuilder.load_module(path)`
imports the film file afresh and returns the module: `mod.FILM` is the film
and every other module-level name is there. (`load(path)` returns just `FILM`.)

## Text in a box

A label, chip or button is text with padding around it: the CSS box model.
`text.box(text, font, padding, x=0, y=0)` gives its border box, sized from the
text's measured width and line boxes plus the padding (CSS shorthand, in px),
so layout can use the size before anything is drawn. `text.draw_in(cv, box,
text, font, color, padding)` draws the text at the padding offset.

```python
font = vb.Font('Sans', 40, 800, line_height=1.1)
pad = (40 * 0.15, 40 * 0.3)                       # 0.15em 0.3em
chip = text.box('New', font, pad, x=100, y=200)
cv.rect(*chip, '#ffffff', radius=8)
text.draw_in(cv, chip, 'New', font, '#000000', pad)
```

## A camera on an image

Product films show screen captures through windows, panning and zooming.
`cv.view(img, box, center, scale, radius=0, background=None)` draws `img`
clipped to `box` with the image point `center` (image px) at the box's centre,
`scale` display px per image px. Animate `center` to pan and `scale` to zoom
(`log_lerp` keeps a zoom even). The defaults show the image's centre, covering
the box.

`view.pin(src, img=None, x=None, y=None)` draws the part `src` (a `Box` in
image px) of the same image, or another one at the same scale, inside the
window at canvas point (x, y). Leave either as None and it stays where the
camera puts it, so `y=box.y` pins a navbar strip to the window's top while it
still pans sideways with the page:

```python
page = vb.Image.load('capture-full.jpg')
s = box.w / page.w
v = cv.view(page, box, (page.w / 2, 900 + scroll), s, radius=24, background='#ffffff')
v.pin(Box(0, 0, page.w, 128), y=box.y)            # the site's sticky navbar
```

`view.to_screen(px, py)` and `view.image_box()` say where image points land,
for marks or for drawing over the capture.

## Timelines: groups and overlaps

A `Timeline` is gap-free segments, in beats. Two things give it structure:

- **Groups.** A segment with `children` holds segments that fill it, gap-free.
  `sequence(at, parts)` lays children back to back from `(name, beats[, data])`.
- **Overlaps.** `Segment(..., overlap=k)` starts on its own beat, but the
  segment before it keeps drawing under it for `k` more beats: a transition,
  not a cut.

`timeline.live(n)` gives every segment drawing at frame `n` as `Shot`s, back
to front, so `draw` can be a loop:

```python
TIMELINE = vb.Timeline(GRID, [
    vb.Segment('title', 0, 4),
    vb.Segment('quick cuts', 4, 8, children=vb.sequence(4, [('a', 2), ('b', 1), ('c', 1)])),
    vb.Segment('wall', 8, 12),
    vb.Segment('end card', 12, 16, overlap=1),     # slides in over the wall for a beat
], end=16)


def draw(n, cv):
    for shot in TIMELINE.live(n):                  # in an overlap: wall, then end card
        SCENES[shot.group.name if shot.group else shot.name](cv, shot)
```

A `Shot` has the `segment` (and its `name`, `data`), `f` (frames into it),
`length` (its frames), and for a group's child `group` and `group_f` (frames
into the group: a chip that springs in once across all the quick cuts keys off
`group_f`). A segment still drawing under the next one's overlap keeps counting
`f` past its `length`, and `exit` says how many frames ago the next one began
(it is `None` otherwise). `timeline.at(n)` is the frontmost `(segment, f)`.

Hard cuts (`cut_frames()`) are every segment start, at any level, except
starts that overlap. The preview, the timeline overlay and sheet labels show
groups' children by name ("quick cuts / b", "wall > end card" in an overlap),
and `sheet`'s default frames are the in, middle and out frame of each child.
`timeline.start(name)` and `span(name)` give a segment's frames, for keyframes
and checks. Every start, children's too, must be on the half-beat grid, and
frames round half up.

## The authoring loop

1. **Preview.** `python -m videobuilder preview film.py` serves a page with
   a scrubber, play/pause, frame/time/beat/segment readouts and a format
   switch. Keys: space plays, ←/→ step a frame, shift+←/→ step a beat,
   `[`/`]` jump between segments, `o` toggles the timeline overlay (beat
   ticks, segment names, frame number), `f` cycles the format. Saving the
   film file, or any `.py` file beside it, reloads it. A failed reload keeps
   the last good film on screen and shows the traceback. The server binds
   to 127.0.0.1 because it runs your film's code on request.
2. **Stills and contact sheets.** `still film.py 120 240 --format all --out
   stills/` writes PNGs, and `--overlay` adds the timeline overlay.
   `sheet film.py --format 9x16` lays out the film's `keyframes`, or else
   the first, middle and last frame of every segment (each group's children). Use `--every N` or
   `--frames a,b,c` to choose others. From Python,
   `cli.contact_sheet(film, frames, fmt, decorate=fn)` calls `fn(canvas, n)`
   on each frame so a check can draw over it (its marks, a safe area).
   Check the cuts and text here before you render.
3. **Render.** `render film.py --format all [--jobs N] [--out film.mp4]`
   writes H.264/AAC MP4s. Check them with ffprobe.

```
python -m videobuilder render  film.py [--format 9x16|16x9|1x1|all] [--jobs N] [--out FILE] [--frames a:b]
python -m videobuilder still   film.py FRAME [FRAME ...] [--format F|all] [--out PATH] [--overlay] [--scale S]
python -m videobuilder sheet   film.py [--format F|all] [--every N | --frames a,b,c] [--cols 6] [--width 360]
python -m videobuilder preview film.py [--host 127.0.0.1] [--port 8000] [--open]
```

## Modules

- `timeline`: `Grid(fps, bpm, head_trim)`, `Segment(name, at, until, data,
  children, overlap)` in beats, `sequence`, and `Timeline` with `live(frame)`
  (`Shot`s), `at`, `cut_frames`, `walk`, `leaves`, `span`. It also has
  `round_half_up`.
- `ease`: CSS `bezier`, `interpolate` over keyframes, `spring` and
  `spring_at` (closed form), `critical`, and `log_lerp`.
- `canvas`: `Canvas` with rects, images (mip-mapped; `Image.load(path)` decodes
  a file once and is safe to call in `draw`), `view` (a camera on an image in
  a window, with `pin`), `outline` and `line` strokes, CSS-style shadows,
  clips, and `layer` groups with opacity and transform. Colours anywhere are
  `'#rgb'`, `'#rgba'`, `'#rrggbb'`, `'#rrggbbaa'` or an `(r, g, b[, a])` tuple
  (0-255, alpha 0-1); `rgba(colour)` turns one into cairo floats for raw
  `canvas.ctx` drawing, and a bad colour raises an error naming it. A CSS
  shadow list is one `canvas.shadow(...)` call per shadow; CSS paints the
  first on top, so call them last to first to match a browser exactly. `mark(name, *box)`
  tags content for checks: `canvas.marks` lists each visible mark's box where
  it landed in the frame, through any layer moves.
- `text`: Pango text. `Font` (variable `weight` and `tracking`), `wrap`
  (with CSS-style `balance`; a `'\n'` is a forced break, and each part wraps
  on its own), `measure`, `block_size`, `draw` (returns the
  `Box` it drew), `box` and `draw_in` for text in a box, and `register` for
  fonts that aren't installed.
- `layout`: `Box` with `pad`, `row`, `column`, `grid`, `center`, `anchor`
  and `fit` (`contain`, `cover`, `fill`, `none`, `scale-down`), and
  `contains` / `intersects` for checks; `fr` shares; and `per_format` tables.
- `film`: `Film`, `Format`, `FORMATS`, `Audio` and `load`.
- `render`: chunked parallel rendering and the ffmpeg concat and mux.
- `preview` and `overlay`: the live preview and the timeline overlay.

## Known traps

videobuilder handles each of these, but you should know about them:

- **Springs are real physics.** Remotion's `spring()` treats any damping
  ratio ≥ 1 as critical. Ours doesn't, so an over-damped spring here crawls.
  For Remotion's "settle" curve, use `spring(t, **critical(stiffness))`.
- **Python's `round()` rounds halves to even** (`round(502.5) == 502`),
  which moves a half-beat cut by a frame. Use `round_half_up` for frame
  math. `Grid.b()` already does.
- **ffmpeg concat drift.** The concat demuxer keeps time in microseconds,
  so chunks whose length isn't a whole number of µs (20 frames at 30 fps)
  drift at every join. The renderer rejects such chunk sizes. The default,
  15, is safe at 24/25/30/60 fps.
- **Letter-spacing.** CSS adds letter-spacing after the last letter too, and
  Pango doesn't, so a tracked line here is one spacing narrower than in a
  browser, and centred lines sit half a spacing off. When matching a browser
  layout, use `Font(..., css_tracking=True)`.

## Tests

    python -m unittest

These cover easing (including Remotion-parity springs), timeline rounding,
the chunk guard, layout, film loading, the CLI and the preview server.
Golden stills of the example film are compared by PSNR, since text
rasterisation varies a little between FreeType and Pango versions. After a
deliberate visual change, refresh them with
`VIDEOBUILDER_UPDATE_GOLDEN=1 python -m unittest tests.test_golden`, and
commit the new PNGs.
