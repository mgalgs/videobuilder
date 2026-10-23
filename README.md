# videobuilder

Direct a video in plain words. Write a note ("make the title bigger at 0:03",
"use 0:32–0:47 of my podcast upload, with captions"), and an AI builder makes
the next version. You watch it, then send the next note. Every version is
kept, so you can compare them and go back.

The editor is a self-hostable web app: a video library with accounts, a player
you can pin notes to, source video uploads, reference attachments, a music
picker, and API keys for scripting. Run it on one machine with Docker Compose
([deploy/compose/README.md](deploy/compose/README.md)), or on Kubernetes (see
[Deploying the editor on Kubernetes](#deploying-the-editor-on-kubernetes)). The
builder is Claude Code, working in a sandbox.

The builder knows hundreds of capabilities by name, from a dip to black to
an odometer roll. Each one has a short demo clip, and the gallery plays them
all: https://mgalgs.io/videobuilder/

Under the editor is a small, dependency-light Python framework for making
videos in code, which is what the builder writes. You need it only to write
films by hand or to work on videobuilder itself. A film is a Python file with
a pure `draw(n, canvas)`; videobuilder gives it a beat-aware timeline, easing
and springs, real-font text, layout, a live preview, and a parallel renderer
that pipes frames to ffmpeg. It provides mechanisms, not a style: palettes,
type, brand rules and visual conventions belong to your films.

## Install

You need Python 3.11 or newer, plus some system packages: ffmpeg, cairo, and
Pango with GObject introspection. The Python packages are pycairo, PyGObject
and Pillow.

**Arch Linux**

    sudo pacman -S python python-cairo python-gobject python-pillow pango ffmpeg

**Debian / Ubuntu** (Pango 1.56 or newer: Debian 13 or Ubuntu 25.04 or later;
on older releases, such as Ubuntu 24.04, use the Docker image instead)

    sudo apt install python3 python3-venv python3-cairo python3-gi python3-gi-cairo python3-pil \
        gir1.2-pango-1.0 ffmpeg

To have pip build pycairo and PyGObject in a virtualenv instead of using
the distro's copies, also install `pkg-config python3-dev libcairo2-dev` and
`libgirepository-2.0-dev`. On releases older than Debian 13 or Ubuntu 24.04,
install `libgirepository1.0-dev` instead.

**macOS (Homebrew)**

    brew install python pango pygobject3 py3cairo ffmpeg

Then, from a checkout, install it into a virtualenv that can see the distro's
pycairo and PyGObject (current Debian and Ubuntu refuse a system-wide
`pip install`):

    python3 -m venv --system-site-packages ~/.venvs/videobuilder
    ~/.venvs/videobuilder/bin/pip install -e .
    ~/.venvs/videobuilder/bin/python skill/make-a-video/scripts/doctor.py   # checks everything above

Activate it (`source ~/.venvs/videobuilder/bin/activate`) to use `python` below.
To use the checkout without installing, run `PYTHONPATH=<checkout> python -m videobuilder ...`.
Don't run films from the directory that contains the checkout: with a
`videobuilder/` folder there, Python imports that folder instead of the
installed package and fails with `cannot import name ... (unknown location)`.

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

`examples/showcase.py` is the place to start: videobuilder's product film,
everything it can do in under 90 s, cut on the beat of a generated music
bed. It counts every capability and puts them all on one wall, gives each
family a beat with a few of its demos playing, and then cuts a launch film
for a made-up app from the hand-written capabilities, every shot tagged
with the capabilities it shows. The counts, families and wall are read from
the capabilities API when it renders, so it stays true as capabilities land
(it's also the film at the top of `/capabilities`, re-rendered by
`capabilities build`). `examples/tour.py` is a smaller example (12 s, three
formats, a generated picture and click track). `examples/benchmark.py` is a
20 s benchmark reel with a bar chart drawn on the canvas, made by an agent
with the make-a-video skill. Their fonts are vendored with their OFL licences in
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
  its first beat on frame 0 (a wrapper around `python -m videobuilder beats`,
  which also prints the `beats` key for a reel's `timeline.json`).
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

**New video** asks only for a name and, optionally, a project, then opens the
editor; the first note sent in its chat starts the build. Everything else is
set in the editor. **Film details** (a link under "Nothing built yet", at the
foot of Sources, and in the timeline's tools) sets the look, length, world
and characters with pictures; Save writes them to the video's bible
(`bible/bible.md`, `bible/characters/`) as one version, and a video's first
note tells the builder about them. A video not built yet can also start as a
film of clips there, or with **Add as a clip** on a video file in the
composer. A film of clips' timeline adds clips after the last one, plans a
clip (a title and a line, shown as a card until the builder makes it),
starts and renames acts, and takes an uploaded song from an Audio lane's
menu. **Make a copy** is on each video's card in the library.

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

**Source videos.** A video's own footage -- a podcast or hearing clip, say --
persists until deleted, instead of expiring like an attachment: upload it
once from the video's **Sources** panel (`POST /api/sources?video=V&filename=F`,
streamed, plus an optional caption with `POST /api/sources/<name>/caption`),
then write a note such as "use 0:32 to 0:47 from interview" and the builder
cuts that span, sound included unless the note says otherwise. `mp4`, `mov`
and `webm` are accepted, checked by magic bytes and then probed to make sure
there is a video stream; a name is a slug, unique per video, defaulting to
the file's stem. `GET /api/sources?video=V` lists them, `GET
/api/sources/<name>?video=V` streams one back for the picker's player (byte
Range included), and `POST /api/sources/<name>/delete` removes it. Limits are
enforced as the upload streams in, never after it's buffered:
`--source-max-mb` (library mode) / `source_max_mb` (single-project, default
2048 MiB) per file, `--source-max-total-mb` / `source_max_total_mb` (default
8192 MiB) per video. Every source lands, read-only, at `sources/<name>.<ext>`
relative to its video's own directory -- the editor's own previews and
renders see it there with no extra step; film code reaches it with a path
built from the film file's own directory
(`os.path.join(os.path.dirname(__file__), 'sources', '<name>.<ext>')`),
since the working directory itself differs between a preview, a render and
a builder's sandbox. In the background, right after an upload, the editor
makes a small preview copy of it (H.264/AAC, short side at most 360px, the
source's own frame rate, stereo AAC around 96 kbps, named identically to
the original) for a backend that can't share the editor's filesystem; a
note on a video with sources gets the ready ones' preview copies, plus
captions, under its own `/attachments/sources/`, added in name order up to
the note's overall 200 MiB attachment budget. A source whose preview copy
isn't ready yet, or that didn't fit, is still named in the builder's
prompt, marked as not in its sandbox -- the builder can still write code
for it, and the editor's own preview and render always use the full-quality
original. The builder's prompt lists each source (name, duration,
resolution, audio, caption, and whether it's in the sandbox) when a video
has any; with none, the prompt is unchanged. Nothing under a video's
`sources/` may ever be committed; a builder branch that does is refused and
reported like any other out-of-scope change.

**Importing footage from archive.org.** Besides uploading your own footage, the
Sources panel has an "Import from archive.org" search over the Internet
Archive's Prelinger collection -- thousands of mostly, not entirely, public
domain ephemeral films -- on by default, needing no configuration. Pick a
result and the editor downloads the best MP4 derivative of that item that
fits the video's source-size limits, landing exactly as an upload would (same
caps, same preview pipeline, same everything), except that it also carries
that item's own licence and credit (title, creator, year, a link to its
archive.org page) -- shown in the Sources panel, and in the builder's prompt
beside that source, so the builder can write a credit for it if the video
ends with one. The editor never fetches from anywhere but archive.org itself
for this (`archive.org` and its own `*.archive.org` download mirrors; a
redirect elsewhere is refused, the same way `xpost.py`'s media fetch is), and
the import still runs through the per-file/per-video-total source limits, so
nothing lands if it wouldn't fit. Nothing here reaches the builder's own
sandbox, which stays offline exactly as it does for an upload.

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
cached. A track an entry-point source returns may also carry its own
`license` (overriding the source's for that one track), `creator`, `year`,
`item_url` and `disputed`; the picker shows a track's own licence when it has
one, the source's otherwise, and marks a `disputed` track plainly instead of
implying a settled licence.

**Pictures.** Pass `--artbox-url URL` (both modes) to add a Pictures button
beside the composer's attach and music buttons. It opens a sheet where the
creator describes a picture, picks how many (1-4) and whether to cut out the
background, and the editor asks an artbox image service at `URL` to make them.
The service is batch and its GPU is shared, so a set can wait in line for
hours: each video's sets are kept in the editor's state dir
(`pictures/<video>/jobs.json`), polled in the background (every 5 s at first,
backing off to every 30 s, resumed after a restart) and given up after 12
hours. Finished pictures are copied into a per-video store beside them (500
MiB per video, oldest sets dropped first); tapping one adds it to the note
being written as an ordinary attachment. A cut-out is made from the prompt
plus ", on a plain mid-grey background", since cut-outs lose faint white
parts against white. Limits: a description up to 1,000 characters, at most
two sets on the way per video, and a per-account cap of pictures per rolling
24 hours (`--account-daily-picture-cap N`, default 40, or `[editor]
account_daily_picture_cap` in single-project mode; across every project in a
library; never for an admin account). The editor only ever talks to `URL`:
file URLs are built from it, a validated job id and a validated, url-quoted
file name, redirects are refused, and every read is capped and timed out.
With no `--artbox-url`, there is no button and the routes answer 404.

**Suggestions while typing.** Pass `--suggest-url URL` (both modes) and set
`$VIDEOBUILDER_SUGGEST_KEY` in the environment to suggest capabilities, looks,
type styles, fonts, sound effects and music while a director types a note:
about 600 ms after they stop, a strong match shows as a card (a chip on a
phone) above the composer, related ones as chips the director can open into a
full picker; picking one rewrites the note's own words with the thing's
unique name (`Ctrl+Z` undoes it, same as any typing). `URL` is any
OpenAI-compatible chat endpoint -- OpenRouter, Anthropic's own compatible
endpoint, a local vLLM or llama.cpp -- asked with `--suggest-model` (default
`anthropic/claude-haiku-5.5`) and the key, never a flag, only the
environment variable (never logged, never in a response). The model reads a
static, cached catalog (the capabilities catalog, the font list, the sound
pack and, where configured, the music list) plus the specific video's bible
and timeline summary, and answers JSON only; every id and span it returns is
checked against the real lists before it ever reaches a browser, capped at 5
strong and 8 related items, and cached briefly per (video, clip, note) so
retyping or undoing is instant. A slow or failing endpoint never shows an
error -- it gives up silently after about 8 s, the same request a new
keystroke would have cancelled anyway. Token usage is recorded per account
(not limited yet). With no `--suggest-url`, or without the key set, only the
six static family chips show once a note has words, nothing is marked
"Suggested", and no request is ever made.

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
attachment_zip_max_bytes = 200          # MiB, a single .zip upload
attachment_zip_max_members = 50         # members kept from a .zip
attachment_zip_max_unpacked_bytes = 300 # MiB, total decompressed size
start_video_attachment_max_files = 50   # replaces attachment_max_files for a video's first note
start_video_attachment_max_message = 300 # MiB, replaces attachment_max_message for that note
source_max_mb = 2048                     # MiB, a single source video upload
source_max_total_mb = 8192               # MiB, one video's total source-video storage
# account_daily_note_cap = 20            # unset by default: no cap on new notes per account per day
# account_daily_cost_cap_usd = 5         # unset by default: no cap on recorded cost per account per day
compendium_for_builder = true            # tell the builder about videobuilder/compendium/ and its votes
```

`compendium_for_builder` adds a "Start from the compendium" section to the
builder's prompt, pointing it at `videobuilder/compendium/`'s pre-built
components and the owner's up/down votes from `/compendium`, so it reuses one
instead of drawing from scratch where one fits. It's left out anyway for a
video whose pinned videobuilder predates the compendium, or whose backend
can't tell which source it will render with. Set to false for the half of a
bake-off that should build from scratch. It isn't one of the `[editor]` keys
a library-hosted repo's own `videobuilder.toml` can set (see below), so a
project can't pick its own experiment arm; in `--library` mode, set
`--compendium-for-builder`/`--no-compendium-for-builder` on the command line
instead.

Each builder run can report what it cost (`cost_usd`) and the tokens it used,
stored on the note once the run is final; a backend that never reports them
leaves both null, not zero. Only admin accounts see cost, in the notes API,
the director and `GET /api/usage` (403 for anyone else, 401 signed out); with
no accounts configured, nobody is gated and everyone sees it, the same way
the builder's live log already shows cost (see `/api/notes/<id>/log` above).
`account_daily_note_cap` and `account_daily_cost_cap_usd` each cap one
account to that many new notes, or that much recorded cost, over a rolling
24 hours, across every project in the library and by account rather than by
key (a key's notes count toward the account it belongs to); hitting either
refuses a new note -- an ordinary one, a video's first note, a retry, or a
follow-up from answering a question -- with 429 and a plain-language message,
in the server's local time, naming when the account can send another. Admin
accounts are never capped; where there are no accounts at all, nobody is
exempt, so a cap set there binds everyone, including the operator.

In `--library` mode, a hosted repo's own config can't set these two keys (see
below), so set library-wide defaults with `--account-daily-note-cap N` and
`--account-daily-cost-cap-usd X` on the command line instead; both are
refused outside `--library`, and unset still means no cap. Source-video
limits work the same way: `--source-max-mb`/`--source-max-total-mb` in
`--library` mode (refused outside it), `source_max_mb`/`source_max_total_mb`
in `[editor]` for single-project mode. An admin can also
give one account its own override from `/account`'s **Usage limits** section
(visible to admins only), or `POST /api/admin/limits
{user,kind:"default"|"custom"|"unlimited",notes?,cost_usd?}`: `"default"`
goes back to the library-wide caps; `"custom"` sets the account's own
`notes`/`cost_usd`, either left `null` for no cap on that one thing;
`"unlimited"` lifts both. `GET /api/admin/limits` lists the library-wide
defaults and, for every account, its limit and its trailing-24h usage. Both
routes are admin-only (403 for anyone else, 401 signed out) and the override
is stored with the account, so it survives a restart.

The generic command backend still receives a request JSON and markdown note.
Fork-sandbox submissions add `--attach-dir` only for notes with attachments
or a ready source-video preview copy to stage under it.
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

**Delete this video** (the video page's Share tab; its owner or an admin, or
anyone without accounts) moves the bare repository, checkout and state dir to
`DIR/trash/<flat name>--<UTC stamp>/` as `repo.git`, `checkout` and `state`,
beside a `deleted.json` recording the owner, collaborators, who deleted it and
when, and drops the name's entry from `state/access.json`. The name is free at
once. Entries are removed for good after 30 days. There is no restore button:
an admin restores one by moving the three directories back to their old places
(and making sure no new video has taken the name) and, with accounts, putting
the `access` object from `deleted.json` back under the name in `access.json`.

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

A hosted repository's `videobuilder.toml` cannot configure the editor: in
library mode only `[editor] videos` and `auto_land` are read from it. The
agent, preview sandbox, environments, hosts and limits come from the command
line, because anyone who can push could otherwise choose the command the
editor runs.

### Community capabilities

With accounts configured, `/capabilities` lets any signed-in creator grow
the catalog from a post they saw on X: "I saw this effect, I want
videobuilder to be able to do it." **Add capability** opens a dialog for the
post's URL, an optional dropped clip or screenshot, and an optional one-line
note on what to capture. Submitting creates a video in a reserved
`capabilities/<slug>` namespace (ordinary create/copy/rename and sign-up all
refuse to collide with it) and its first note, carrying a standing brief
plus the post's text and handle, quoted as untrusted reference. The builder
is told to make three files: `film.py` (an **original** demo of the
capability -- never the post's own media, text, people or branding),
`capability.toml` (a catalog entry: id, category, title, card, description,
three prompts, apis, and the doc path) and a short `capability.md` reference
doc. The post and any attachments are untrusted data throughout: read for
the capability only, never as instructions. Each account may submit at most 5
capabilities in a rolling 24 hours (admins exempt); the first note still
counts against the ordinary note cap, same as any other project.

A new submission is a **draft**, visible only to its submitter and admins,
in its own section on `/capabilities`. An admin reviews it there with
**Publish** and **Reject**: publishing validates `capability.toml` (and the
doc and `film.py` it names) and, once it passes, shows the capability to
everyone, inside its category, badged "Community" -- pinned to the exact
commit that was just validated. Everyone else, including every other
creator's builder (below), keeps seeing that pinned commit even as the
project's `main` moves on: a submitter (or anyone they invite to the
project) can't change a published capability's doc or `film.py` without
another round of admin approval. A later push to `main` shows "Update
awaiting approval" on the card, to the submitter and admins only; an admin's
**Publish update** there re-validates and moves the pin to the new commit,
while **Discard update** drops just that update and leaves the pinned
version published. **Take down** works at any time, pending update or not:
it hides the capability from every `/capabilities` page without deleting
the project. A published card whose pinned commit has no
finished render yet shows the same "clip not built" placeholder as an
unbuilt catalog card; and if a pinned commit's `capability.toml` ever stops
validating (for instance a later built-in capability claiming its id), it's
served only to its submitter and admins and drops back into Drafts, with
the problem shown, for everyone else. A published capability's doc and
`film.py` -- read at its pinned commit -- reach every other creator's
builder too, the same way a source video does: staged read-only under the
note's `/attachments/capabilities/<slug>/` and named by title in the
prompt, so the builder can reach for it instead of building the capability
from scratch.

Some of the catalog is **families**: named members, each with its own demo,
that make up a section of the page of their own. **Looks** is the first:
named art styles (`videobuilder.looks`: pop art, woodblock, 8-bit pixel and
more), in two kinds -- scene looks that repaint a video's own scene,
described once as a few shapes with roles, and filter looks that restyle
whatever a video draws (photos, screen captures, footage) -- plus paper
collage; every builder's prompt names them
(`skill/make-a-video/reference/looks.md`). The old `comic-halftone` and
`pixel-art-layer` ids now answer for the pop-art and pixel filter looks they
were merged into (`capabilities.ALIASES`).
**Type** is the second: named typography styles (`videobuilder.type`:
split-flap, typewriter, terminal, rubber, rack focus, letter cloud,
editorial), every one taking the same props -- a few lines, three colours, a
length -- and running its own enter, hold and exit, as a whole film, a
segment or a title over another picture
(`skill/make-a-video/reference/type.md`).
The dialog's first choice is **A new capability** or a new member of a
family (**A new look**, **A new type style**); each family's brief and the
file its member ships (`look.py`, `style.py`) come from its own entry
(`capabilities._member`). A look
submission is briefed for one reusable look (`look.py`, following the look
contract) with a demo on the shared lighthouse scene that passes the motion
floor, a `capability.toml` with `family = "looks"`, and a doc. Publishing
also checks the family matches what was submitted, `look.py` is there and
within its size cap, and the id isn't a built-in look's name. A published
look appears in the Looks section beside the built-in scene looks, and
reaches every builder beside the built-in looks, its `look.py` staged
read-only with its doc and demo.

Reading the post is optional and sandboxed: the editor only ever calls
`https://cdn.syndication.twimg.com/tweet-result` for the post's public JSON
and downloads media only from `pbs.twimg.com`/`video.twimg.com`, each capped
in size and time, following no redirect off those hosts. Pass
`--no-capability-fetch` to turn this off entirely; the dialog then asks only
for a dropped file, and a failed or refused read always falls back to that
instead of blocking the submission.

Because a capability needs a more thorough build than an ordinary note, the
agent gets a heavier default: a review loop plus a maintainer loop, pinned
to the `--model` given to `--agent-extra-arg` if any. Set
`--capability-agent-extra-arg` (repeatable, like `--agent-extra-arg`) to
replace that default with your own arguments, appended after the ordinary
`--agent-extra-arg` list; both flags are refused outside `--library` mode,
and (like `--maintainer-loop`) only mean anything to the `fork-sandbox`
agent.

### What's new

A library has a What's new page (`/whats-new`), linked from the app bar
with a dot until the viewer has opened the newest entry (kept in the
browser, not on the server). It lists, newest first:

- **The project's named releases.** Each ships in the package as a text file
  in `videobuilder/release_notes/` (see [docs/RELEASES.md](docs/RELEASES.md)),
  shown once the instance runs that release's version. Its video is an asset
  of the project's GitHub release: the server downloads it once, the first
  time someone opens the page, into `<state-dir>/whats-new-cache/` and serves
  it itself, so viewers' browsers never contact GitHub. A download has a
  timeout and a size cap, and a failed one waits an hour before another try;
  until then the entry shows its text only. Pass `--no-whats-new-videos` to
  never download them (the entries keep their text), or `--whats-new-repo
  OWNER/NAME` to take them from a fork's releases.
- **This instance's own entries**, for notes of your own. They live in
  `<state-dir>/whats-new/<id>/` (`entry.json` beside `9x16.mp4`, `16x9.mp4`
  and `1x1.mp4`), never in git; the id is the entry's date (`2026-10-18`,
  then `2026-10-18-02`). An admin (anyone, without accounts) adds and
  removes them on the page, with uploads capped at 300 MB per video, or on
  the server:

      python -m videobuilder whats-new add --state DIR3 --title "New fonts" \
          --versions "0.1.88" --notes notes.txt --video 9x16=v.mp4 --video 16x9=w.mp4
      python -m videobuilder whats-new list --state DIR3
      python -m videobuilder whats-new remove --state DIR3 2026-10-18

Viewers see the 9:16 video on a phone and the 16:9 one on a wide screen.

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
    [--account-daily-note-cap N] [--account-daily-cost-cap-usd X]
    [--artbox-url URL] [--account-daily-picture-cap N]
    [--suggest-url URL] [--suggest-model MODEL]
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
- `speech`: narration. `python -m videobuilder say` (needs the `speech` extra,
  `pip install -e '.[speech]'`, and the Kokoro model files) makes a voiceover
  WAV with phrase-timed `.vtt`/`.json` sidecars, once; `speech.load` reads them
  at render time (captions, a `Sound`, a per-frame mouth-open signal) without the model.
- `sfx`: sound effects. `vb.sfx.sound(id, at=frame)` puts a sound from the
  sound-effects pack (earshot's bank, MIT) on a frame by its peak or onset;
  `python -m videobuilder sfx fetch` downloads the pack (checked against
  `videobuilder/sfx-pack.sha256`) to `$VIDEOBUILDER_SFX_DIR` or
  `~/.cache/videobuilder/vb-sfx-1`; `sfx list`, `sfx play-path`. The pack is
  built from a rendered bank by `scripts/build_sfx_pack.py`.
- `pictures`: `--artbox-url` generated pictures for the director's Pictures sheet.
- `fonts`: the font list (family, where it comes from, a one-line character) the
  suggest layer's prompt and Fonts picker share.
- `suggest_client`: a client for one OpenAI-compatible chat endpoint.
- `suggest`: `--suggest-url` capability suggestions while a director types a note.

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

These cover easing (springs checked against the textbook damped-oscillator solution), timeline rounding,
the chunk guard, layout, film loading, direct edits, the CLI, the
preview server and the editor (in temporary git repos). Golden stills of the example films are compared by PSNR, since text
rasterisation varies a little between FreeType and Pango versions. After a
deliberate visual change, refresh them with
`VIDEOBUILDER_UPDATE_GOLDEN=1 python -m unittest tests.test_golden`, and
commit the new PNGs.

## Self-host with Docker Compose

The simplest way to run the editor for other people: on any Linux machine with
Docker, `deploy/compose/` builds one container with the video library,
accounts and the AI builder, sandboxed by bubblewrap inside it. Set an admin,
a password and a Claude token, run `docker compose up -d`, and put a TLS
reverse proxy in front. `deploy/compose/README.md` is the step-by-step guide,
including upgrades and troubleshooting.

## Deploying the editor on Kubernetes

The example in `deploy/k8s/editor.yaml` runs one replica with `Recreate`, a
PVC for the library, checkouts, editor state and fork-sandbox scratch, a Service,
Ingress and `/healthz` probes. It sets `terminationGracePeriodSeconds: 60`:
on SIGTERM the editor refuses new writes and gives those under way up to 45
seconds before it exits, and `/healthz` answers 503 meanwhile. No `preStop` is
needed. Replace every `example.com` value, image,
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
missing or differs. To ship before the tests finish, build with
`--build-arg GATE=runtime`, then run the same checks on the same tree with
`docker build -f deploy/Dockerfile --target gated .`. `python3 -m videobuilder frames --hash
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

## Licence

videobuilder is released under the MIT licence; see `LICENSE`. The fonts in
`examples/assets/` are not: each is under the SIL Open Font License 1.1, with
its licence file beside it, as `examples/assets/README.md` lists. The
sound-effects pack (not in the repo; a few of its takes are in
`tests/fixtures/sfx-pack/`) is earshot's bank, under the MIT licence, with
its own `LICENSE-earshot` and `CREDITS.md`.
