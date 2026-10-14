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

**Debian / Ubuntu** (Pango 1.56 or newer: Debian 13 or later)

    sudo apt install python3 python3-venv python3-cairo python3-gi python3-gi-cairo python3-pil \
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
picture and click track). `examples/benchmark.py` is a 20 s benchmark reel
with a bar chart drawn on the canvas, made by an agent with the
make-a-video skill. Their fonts are vendored with their OFL licences in
`examples/assets/`.

## The make-a-video skill

`skill/make-a-video/` is a Claude Code skill that teaches an agent to make
a film with videobuilder: setup, a storyboard, a template film, the
authoring loop, music and beat-locking, formats, and review checks. Its
scripts work without the skill too:

- `scripts/check.py film.py [--video]`: the storyboard with read times,
  marks against each format's safe area and each other, cuts landing on
  content, and for the renders ffprobe facts, picture cuts against the
  grid, and music onsets against the beats.
- `scripts/tempo.py track.mp3`: a track's BPM and the `head_trim` that puts
  its first beat on frame 0.
- `scripts/make_track.py --bpm 120 --beats 40 --out music.wav`: a
  placeholder music bed exactly on the grid.
- `scripts/fontinfo.py`: a font file's family name, weights and licence;
  which face Pango really draws; an OFL licence file for a vendored font.
- `scripts/doctor.py`: are the dependencies here, and is videobuilder
  importable.

## The film file

A film file is a Python module that defines `FILM = videobuilder.Film(...)`:

| field | |
|---|---|
| `draw(n, canvas)` | Paints frame `n`. It must be **pure**: the same `n` and format always give the same pixels, with no state carried between calls. Chunked parallel rendering, stills and the preview all draw frames alone and out of order. |
| `fps`, `frames` | Frame rate and length. Both may be omitted when a `timeline` supplies them. |
| `timeline` | Optional `Timeline`. It gives the preview and stills its segments and beats, and supplies fps and frames. |
| `formats` | Format names (`'9x16'` 1080×1920, `'16x9'` 1920×1080, `'1x1'` 1080×1080) or `Format(name, w, h)`. The first is the default. |
| `background` | Colour painted before `draw`, or `None` for transparent. Default black. |
| `audio` | Optional `Audio(path, trim_frames=None, gain_db=0, fade_out_frames=0)`, muxed in by `render`. `trim_frames` (frames cut from the file's head) defaults to the timeline's `Grid.head_trim`. The fade is linear over the `fade_out_frames` frames before the last and silent from the last frame's start, so Remotion's `interpolate(f, [D - m, D - 1], [1, 0])` is `fade_out_frames=m - 1`. |
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
Segment names are unique across the timeline, groups and children included:
they are the ids that direct edits key on.

## Direct edits (`<film>.edits.toml`)

A reviewer who doesn't write Python can still move a cut or change a line of
copy. Those edits are data, in a file named for the film beside it
(`film.py` → `film.edits.toml`), and videobuilder applies them as the film's
`Timeline` is built:

```toml
[segments.intro]
until = 6.5            # roll the cut at the end of intro to beat 6.5

[segments.intro.data]
title = "New copy"     # replace the string intro.data['title']
```

- **`until` is a roll.** The segment's end and its next sibling's start move
  together, so the film's length and every other cut stay put. The new end
  must be on the half-beat grid, strictly between the segment's start and
  the sibling's end, and leave room for both segments' overlaps. The segment
  needs a next sibling at its own level, and neither side may be a group.
- **`data` replaces a string.** Only an existing key whose value is a `str`.
- Anything else (an unknown segment or key, a rule broken) is an error that
  names the segment and the rule. With no edits file, nothing changes.

The edits apply while the film is imported (`load`, `load_module`, the
preview, the CLI), to the first `Timeline` the film builds, so values the
film derives from its timeline at module level (`T.span('x')`) see them. A
Timeline built outside a film load sees none. `timeline.edits` holds what
was applied. The preview reloads when the edits file changes, and its `/info`
gives each segment's `copy` (its `data` strings) and `rollable`, and the
edits with their path (`null` with no file).

Draw on-screen copy from `Segment.data` (`shot.data`) and it is editable
this way. Each film has its own edits file, so several films can share a
directory; a plain `edits.toml` is ignored.

To write edits, use the CLI or `videobuilder.edits.roll(film, segment,
until)` and `set_copy(film, segment, key, value)`. Each loads the film
with the new edits first and leaves the file unchanged if that fails. The
file is written the same way every time, with segments sorted. Setting a
segment's own value removes its entry, and the file goes when it's empty:

    python -m videobuilder edit roll film.py intro 6.5
    python -m videobuilder edit copy film.py intro title 'New copy'

## The editor (`python -m videobuilder editor`)

A web editor for people who review a video and change it without writing
Python. It runs on your machine, against a *project*: a directory, usually
a git repo, holding one or more videos, each a film file in a directory of
its own.

    python -m videobuilder editor path/to/project [--port 8100] [--host 127.0.0.1] [--state-dir DIR]

Each video may pin videobuilder in its directory's `requirements.txt`. The
editor finds the nearest such file up to the project root. It builds an
environment under `<state-dir>/envs/` once per pin contents and Python version,
then runs that video's preview, edits and note frames in a sandboxed worker.
Environment creation uses `pip install -r` and may need the network; workers
have no network. A pin older than 0.1.2 cannot provide the worker protocol and
must be upgraded to open. With no pin, the editor's interpreter is used and
the video list says "editor's own". Set `[editor] envs = "current"` or pass
`--envs current` to ignore pins during development; `pinned` is the default.

Open `http://127.0.0.1:8100/` and pick a video. Each video opens in
**director mode**. The newest rendered MP4 plays in a format matched to the
film. Tap the player to pause or play, choose a format, or download the current
version. While a render is queued, the current frame appears in its place.

Use **Chat** to tell the builder what to change. A timestamp from the current
playhead is included by default; remove it for a general note. Attach images,
video, audio, PDF or text files before sending. The note list shows the
builder's reply and a Watch button when a new version lands. **Versions** lets
you watch an older version or restore it as a new commit. The player follows
new versions automatically until you choose an older one; then a toast offers
a Watch action. The director name is shared between videos in the browser.

**Fine tuning** opens the original timeline and copy editor. It starts
collapsed. You can drag rollable cut handles, edit copy, and undo the last
change there. Each direct edit commits a new version. If `auto_land = false`,
Fine tuning also shows the manual draft preview, Accept and Drop controls.
The timeline's keyboard shortcuts remain available while Fine tuning has focus:
←/→ step a frame, shift+←/→ a beat, `[`/`]` jump between segments, and space
plays its frame preview.

**Finding videos.** If the project has a `videobuilder.toml` listing them,
exactly those:

```toml
[editor]
videos = ["launch/film.py", "promo/promo.py"]   # relative to the project
state_dir = ".vb-editor"                        # optional
```

Otherwise, every `*.py` file under the project that assigns a module-level
`FILM` and mentions `Timeline`, found by reading the source (nothing is run
until you open the video). Dot-directories and `tests`, `test`, `vendor`,
`node_modules`, `__pycache__`, `build`, `dist`, `venv` and `site-packages`
are skipped. A video's id is its path without `.py` (`launch/film`).

**Git.** Each direct edit is one commit in the project's repo that touches
only that film's edits file (`git commit -- launch/film.edits.toml`), with
the author from your git config and a message like
`edit(launch/film): roll intro to beat 6.5` or
`edit(launch/film): copy intro.title`. Nothing else is staged, and nothing is
pushed. If the project isn't in a git repo, or the edits file already has
uncommitted changes, the edit is still written, but not committed; the
editor says so in its header and after the edit.

**Director backend.** A version is a first-parent commit on `main`. The
versions endpoint numbers commits from the root; in a multi-video project it
lists only commits touching that video's directory. An old version can be
restored without rewriting history: restore makes a new `main` commit with
that video's old content. Direct edits carry `Version-kind: edit` and
`Directed-by` trailers. Builder turns carry `Version-kind: builder`, `Note`,
and `Directed-by`; restores carry `Version-kind: restore`, `Restores`, and
`Directed-by`. Commits without trailers appear as `push` versions.

The editor renders the first format after a new `main` commit and renders
other formats on demand. It uses the video's pinned `python -m videobuilder
render` in the preview's no-network bwrap sandbox, from a detached worktree.
Only the output scratch directory is writable. Rendered MP4s are cached by
commit and format, with one render running at a time. The newest 20 commits
per video remain cached. Requests return `202` while queued or rendering,
`500` with a log tail on failure, and MP4 bytes with byte Range support and
an ETag when ready. A failed render can be requeued with the player Retry button or
`POST /api/video/retry` for a main commit and format.

Notes can use a `time` in seconds; then the matching frame and PNG are saved.
Omit `time` and `frame` for a general note with no PNG. Upload attachments as
raw bodies, one at a time, then pass their ids in the note's `attachments`
list. Allowed extensions are PNG/JPEG/WebP/GIF, MP4/MOV/WebM, MP3/WAV/M4A/AAC/
OGG, PDF, TXT and MD; the editor checks magic bytes and stores sanitized
names. The default caps are 25 MiB per file, 10 files and 100 MiB per note.
Unused uploads expire after 24 hours. For fork-sandbox, each note receives
copies of its attachments at `/attachments`; the builder must copy anything
used in the video into the video's assets and commit it.

**Music sources.** Pass `--music-sources FILE` (works in both single-project and
`--library` mode) to add a music button beside the composer's attach button. It
opens a picker over a configured music library: search, preview, and attach a
track to the note being written, the same way an uploaded file attaches. With
no `--music-sources`, there is no button and nothing changes. The module knows
nothing about any particular service; whoever deploys the editor configures
real sources separately. `FILE` is TOML with a list of sources, each needing `id`
(kebab-case), `name` (shown in the picker) and `license` (a free-text label,
e.g. `"CC BY-NC 4.0"`, shown in the picker's header and next to each track's Use
button — videos never credit it; the editor adds no attribution anywhere), and
either a mapping source, fetched as JSON over HTTP:

```toml
[[sources]]
id = "example-library"
name = "Example Library"
license = "CC BY-NC 4.0"
url = "https://music.example.com/api/tracks.json"
[sources.fields]
tracks = "tracks"            # dotted path to the list; "" for a top-level list
id = "id"
title = "title"
audio_url = "download_url"
tags = "tags"                # optional
duration = "length_ms"       # optional
duration_unit = "ms"         # "ms" or "s" (default "s")
```

or an entry-point source, a Python callable that fetches and normalises its
own tracks:

```toml
[[sources]]
id = "example-catalog"
name = "Example Catalog"
license = "Public domain"
entry_point = "example_catalog.music:list_tracks"
```

`list_tracks(source_config)` is called with that source's own TOML table and
returns an iterable of `{id, title, audio_url}` dicts, plus optional `tags`
(a list of strings) and `duration` (seconds). A source must be exactly one of
these two kinds; a bad file, including a source missing `license`, is a
startup error naming the problem. A track missing `id`, `title` or
`audio_url`, or whose `audio_url` isn't http(s), is skipped rather than
breaking the list. The track list is fetched with a timeout and a size cap and
cached per source for ten minutes; a refetch failure serves the stale list
when there is one. There is no upstream search, so the picker filters the
cached list itself. Attaching a track fetches its `audio_url` server-side and
stores it through the same attachment store as an upload — the picker never
tells the server a URL to fetch, only a source and track id it already has
cached.

When a builder turn finishes, the editor applies the same scope guard as
manual Accept. Out-of-scope changes are refused and the draft is reset to
`main`; the next note tells the builder what was refused. A clean turn is
rebased onto current `main`, squashed to one version, and the draft advances
to that version. On a rebase conflict, one automatic rebase request is sent to
the agent. A second conflict ends in `conflict` with a director-facing message.
A reply without commits stays `replied`. The server polls runs and advances
the queue every few seconds, so a turn lands with no page open; listing notes
polls too. Per-video sessions survive restarts. Manual Accept/Drop routes stay
available when `auto_land = false`.

The name used for notes, edits and restores comes from `request_hook`, then
the `vb_name` cookie, then `anonymous`. `/api/name` sets the cookie for one
year at `/`, so it works across every video in library mode. This is LAN
trust, not authentication.

```toml
[editor]
auto_land = true
render_jobs = 4             # default: min(4, cpu_count)
render_keep = 20
attachment_max_file = 25    # MiB
attachment_max_files = 10
attachment_max_message = 100 # MiB
```

The generic command backend still receives a request JSON and markdown note.
Fork-sandbox submissions add `--attach-dir` only for notes with attachments.
A note with a playhead time includes a line such as `At 0:12 (frame 360,
segment "sizes")`; the final reply line should be `Summary: <one line>`.

**Trust.** Main and draft film code runs in isolated workers, with the checkout
and installed environment read-only, a scrubbed environment, and no network.
Without a working bubblewrap, the editor refuses to run film code unless
`unsandboxed_previews` is enabled. In that mode use repos you trust. The editor binds to 127.0.0.1 unless
told otherwise, and it has no login. `videobuilder.editor.request_hook` is
where a check of a reverse proxy's identity header belongs (the identity
it returns becomes a note's author). Edits must be JSON POSTs from the
page's own origin, so another site can't make edits through your browser.

The complete HTTP API, including versions, restore, MP4 Range responses,
attachments and names, is listed in `videobuilder/editor.py`.

## Hosting videos

Run `python -m videobuilder editor --library DIR` to host one git repository
per video. Bare repositories live at `DIR/repos/<name>.git`; the editor makes
one checkout per repository in `DIR/checkouts/` and keeps notes and agent
state in `DIR/state/`. Set `--checkouts DIR2` and `--state-dir DIR3` to move
those directories. Checkouts and state use flat names: `acme/launch` becomes
`acme--launch`. Names have one or two lower-case path parts, for example
`launch` or `acme/launch`; the first part is only a listing namespace.

The index at `/` lists repositories, clone URLs, and links to each video page
at `/v/<name>/`. Its API is at `/v/<name>/api/…`. Git is served at
`http://HOST/git/<name>.git`: use that URL with ordinary `git clone`,
`git fetch`, and `git push`. The first push to a valid unused name creates
the bare repository. Until it has `main`, the index lists it as empty and
the video page cannot open. Non-fast-forward pushes and deletion of `main`
are refused. The index's **New video from…** form creates a new repository
with one fresh commit containing the source `main` tree.

The editor hosts these remotes and does not push to a forge. To keep a forge
copy, configure any forge that supports HTTP Git pull mirroring to pull from
the editor's Git URL. Anyone who can reach the editor can push, under the same
LAN trust model as the UI. The `request_hook` in `videobuilder.editor` is the
place to authenticate requests behind a proxy; the host allowlist still
applies to Git URLs. Single-project mode still supports `sync_remote`.

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
   the first, middle and last frame of every segment (each group's children).
   Tiles default to 360 px, 6 across, for portrait formats and 480 px, 4
   across, for the rest, so `--format all` gives each format a sheet that
   reads; `--width` and `--cols` override both. Use `--every N` or
   `--frames a,b,c` to choose others. `--cuts [N]` shows the first N frames
   at each hard cut, including frame zero (default 3); combine with
   `--format all` to review every format. From Python,
   `cli.contact_sheet(film, frames, fmt, decorate=fn)` calls `fn(canvas, n)`
   on each frame so a check can draw over it (its marks, a safe area).
   Check the cuts and text here before you render.
3. **Render.** `render film.py --format all [--jobs N] [--out film.mp4]`
   writes H.264/AAC MP4s. Check them with ffprobe. Progress is a counter
   on a terminal and a line per tenth of the chunks in a log. If no chunk finishes
   for `--stall` seconds (default 600), the render stops with an error
   naming the frames still pending, rather than waiting forever.

```
python -m videobuilder render  film.py [--format 9x16|16x9|1x1|all] [--jobs N] [--out FILE] [--frames a:b] [--stall S]
python -m videobuilder still   film.py FRAME [FRAME ...] [--format F|all] [--out PATH] [--overlay] [--scale S]
python -m videobuilder sheet   film.py [--format F|all] [--every N | --frames a,b,c | --cuts [N]] [--cols C] [--width W]
python -m videobuilder preview film.py [--host 127.0.0.1] [--port 8000] [--open]
python -m videobuilder edit roll film.py SEGMENT UNTIL
python -m videobuilder edit copy film.py SEGMENT KEY VALUE
python -m videobuilder editor PROJECT-DIR [--host 127.0.0.1] [--port 8100] [--state-dir DIR] [--open]
python -m videobuilder editor --library DIR [--checkouts DIR2] [--state-dir DIR3] [--open]
```

## Modules

- `timeline`: `Grid(fps, bpm, head_trim)`, `Segment(name, at, until, data,
  children, overlap)` in beats, `sequence`, and `Timeline` with `live(frame)`
  (`Shot`s), `at`, `cut_frames`, `walk`, `leaves`, `span`. It also has
  `round_half_up`.
- `ease`: CSS `bezier`, `interpolate` over keyframes, `spring` and
  `spring_at` (closed form), `critical`, and `log_lerp`.
- `canvas`: `Canvas` with rects, images (mip-mapped; `Image.load(path)` decodes
  a file once and is safe to call in `draw`; an edited file is decoded again
  and its old decode dropped), `view` (a camera on an image in
  a window, with `pin`), `outline`, `line` and `arc` strokes, filled `sector` slices, CSS-style shadows,
  clips, and `layer` groups with opacity and transform (an invisible layer
  draws nothing but keeps its transform). Colours anywhere are
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
- `layout`: `Box` with `pad`, `row`, `column`, `grid`, `center`, `anchor`,
  `stack(heights, gap=0, align='top')` (boxes and occupied height)
  and `fit` (`contain`, `cover`, `fill`, `none`, `scale-down`), and
  `contains` / `intersects` for checks; `fr` shares; and `per_format` tables.
- `film`: `Film`, `Format`, `FORMATS`, `Audio` and `load`.
- `render`: chunked parallel rendering and the ffmpeg concat and mux.
- `preview` and `overlay`: the live preview and the timeline overlay.
- `editor`, `project` and `notes`: the editor, finding a project's videos and
  committing edits, and review notes with their `AgentBackend`.
- `edits`: direct edits, `<film>.edits.toml`: `roll`, `set_copy` and `rollable`.
- `music`: pluggable `--music-sources` for the director's music picker.

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
- **Pango after fork.** Pango loads fonts on a worker thread, and the
  renderer's forked workers don't inherit it, so a worker's first new font
  load (text at a size the parent hadn't drawn, as in a scaled layer) hung.
  Each forked worker now gets its own font map, with the `text.register`ed
  fonts added again.
- **Letter-spacing.** CSS adds letter-spacing after the last letter too, and
  Pango doesn't, so a tracked line here is one spacing narrower than in a
  browser, and centred lines sit half a spacing off. When matching a browser
  layout, use `Font(..., css_tracking=True)`.

## Tests

    python -m unittest

These cover easing (including Remotion-parity springs), timeline rounding,
the chunk guard, layout, film loading, direct edits, the CLI, the
preview server and the editor (in temporary git repos). Golden stills of the example films are compared by PSNR, since text
rasterisation varies a little between FreeType and Pango versions. After a
deliberate visual change, refresh them with
`VIDEOBUILDER_UPDATE_GOLDEN=1 python -m unittest tests.test_golden`, and
commit the new PNGs.

## Deploying the editor

The example in `deploy/k8s/editor.yaml` runs one replica with `Recreate`, a
PVC for the library, checkouts, editor state and fork-sandbox scratch, a Service,
Ingress and `/healthz` probes. Replace every `example.com` value, image,
Secret and Role name for your site. The editor binds to loopback by default;
the example explicitly uses `--host 0.0.0.0` and `--allow-host editor.example.com`.
The host allowlist is the v1 LAN trust boundary; put the Ingress on a trusted
network. **Never set `unsandboxed_previews` in a pod holding credentials.**

Build with `docker build -f deploy/Dockerfile .`. The base must ship Pango
1.56 or newer (Debian 13 or later); `--build-arg BASE=...` overrides it. To
drive fork-sandbox from the pod, build fork-sandbox's postmaster layer
(`kubectl` and its scripts) on top of this image, passing this image as that
layer's base; see fork-sandbox's cluster postmaster documentation for the
layer and the client Role setup. The example RoleBinding names that client Role. Set
`[editor.agent] backend = "fork-sandbox"` and `extra_args = ["--k8s"]` in
each video's `videobuilder.toml`. Set `context_root` to a directory under
`/var/tmp/claude-scratch/forks/` and `context_mount = "/work/context"`.
Video checkouts live under `/home/editor/src/` for fork-sandbox's project root
rule. The library and `--state-dir` live on the PVC under
`/var/tmp/claude-scratch` for resumable agent runs. The start script starts
library mode and sets the git author from `GIT_AUTHOR_NAME` and
`GIT_AUTHOR_EMAIL`. The optional `editor-forge-ssh` Secret supplies
`id_ed25519` and `known_hosts` only when a video's pin needs a private Git
source; read access is enough. Mount an agent credential Secret separately,
as in the example.

Bubblewrap needs a node-installed Localhost seccomp profile. Obtain Moby's
Apache-2.0 `profiles/seccomp/default.json` from its source repository,
then run `python3 deploy/seccomp/mkprofile.py default.json >
videobuilder-bwrap.json`. Install the output at
`<kubelet seccomp root>/profiles/videobuilder-bwrap.json` on every eligible
node and use the example pod's `seccompProfile`. The generator downloads
nothing. It targets amd64 and a restricted pod with no capabilities.

The image build runs the full unittest suite and compares exact PNG hashes
for fixed tour and benchmark frames in every format. These hashes depend on
the image's cairo/Pango. To create the first manifest, run
`docker build -f deploy/Dockerfile --target frames-export --output type=local,dest=deploy/ .`,
then move `deploy/frames.sha256` into the committed source tree. Inspect any
changed frames before accepting a new manifest; repeat that command and
commit the new file deliberately. A normal build fails if the manifest is
missing or differs. `python3 -m videobuilder frames --hash
examples/tour.py examples/benchmark.py` prints the image-specific values.

Set `[editor] sync_remote = "origin"` or `--sync-remote origin` to fetch
main on project/video opens and before an edit or Accept, and push after a
commit. The editor fast-forwards clean local checkouts, rebases local-only
commits when main diverges, and retries a rejected push up to three times.
On a rebase conflict, it aborts the rebase, resets main to the fetched
remote, preserves the old commits under `refs/vb-sync/rescue-*`, and reports
the diff in the error. Draft branches remain local. This mode expects one
editor process and a clean main checkout.

For agent source staging, set `[editor.agent] context_root` under
`/var/tmp/claude-scratch/forks/`. Each pinned version is cloned once under
`v<version>/videobuilder` from the pin's git URL and tag. For a `==` pin,
set `[editor.agent] videobuilder_repo` to the source repository URL.
`context_mount` defaults to the local staging path; set it to
`/work/context` for a fork-sandbox Kubernetes run. `--agent-context-root`,
`--agent-context-mount` and `--agent-videobuilder-repo` set the same three
keys from the command line, so a deployment can keep them out of the
project repo.
