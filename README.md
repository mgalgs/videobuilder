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

Inside `draw`, `canvas.width` and `canvas.height` are the format's size in film
pixels, and `canvas.format` says which format is being drawn. Formats are
layouts, not crops: lay each format out for its own shape, usually from a
per-format table (`per_format(table, canvas)`, with `'*'` as the fallback).

The film's directory goes on `sys.path`, so a film can import helper modules
that sit beside it. The preview reloads those too.

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
   `sheet film.py --format 9x16` lays out the first, middle and last frame
   of every segment. Use `--every N` or `--frames a,b,c` to choose others.
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

- `timeline`: `Grid(fps, bpm, head_trim)`, `Segment(name, at, until)` in
  beats, and `Timeline.at(frame)`. It also has `round_half_up`.
- `ease`: CSS `bezier`, `interpolate` over keyframes, `spring` and
  `spring_at` (closed form), `critical`, and `log_lerp`.
- `canvas`: `Canvas` with rects, images (mip-mapped), CSS-style shadows,
  clips, and `layer` groups with opacity and transform. `mark(name, *box)`
  tags content for checks: `canvas.marks` lists each visible mark's box where
  it landed in the frame, through any layer moves.
- `text`: Pango text. `Font` (variable `weight` and `tracking`), `wrap`
  (with CSS-style `balance`), `measure`, `block_size`, `draw` (returns the
  `Box` it drew), and `register` for fonts that aren't installed.
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
  Pango doesn't. When matching a browser layout, a tracked line here is one
  spacing narrower.

## Tests

    python -m unittest

These cover easing (including Remotion-parity springs), timeline rounding,
the chunk guard, layout, film loading, the CLI and the preview server.
Golden stills of the example film are compared by PSNR, since text
rasterisation varies a little between FreeType and Pango versions. After a
deliberate visual change, refresh them with
`VIDEOBUILDER_UPDATE_GOLDEN=1 python -m unittest tests.test_golden`, and
commit the new PNGs.
