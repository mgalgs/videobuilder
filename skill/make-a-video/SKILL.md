---
name: make-a-video
description: Make a short video (a product launch, a feature explainer, a benchmark or result reel, a social clip) as an MP4 in code with the videobuilder Python framework, in one or more formats (9:16, 16:9, 1:1), with beat-locked music and review checks. Use when asked to make, render or edit a video, reel, explainer or animated clip.
---

# Make a video with videobuilder

A film is a Python file with a pure `draw(n, canvas)` and a beat timeline;
videobuilder previews it, renders it to MP4 and checks it. This skill is the
process. It teaches mechanisms, not a look: colours, typefaces and brand
rules come from the user or the brief. When you have none, choose them for
this film and say so; never present them as a house style.

Paths below: `$SKILL` is this skill's directory (the one holding this file),
and `$VB` is the videobuilder checkout it lives in, `$(realpath $SKILL/../..)`.
The framework's full manual is `$VB/README.md`; `$VB/examples/` has
complete films to read.

## 0. Is videobuilder the right tool?

Use it for films built from text, shapes, images, screen captures, charts
and music, cut to a beat. Use something else when the film is mostly a web
page in motion (HTML/CSS layout), or needs a web player, interactivity or
cloud rendering: Remotion fits those, if its licence covers the user. Say so
and stop rather than force it.

## 1. Set up

```sh
python $SKILL/scripts/doctor.py
```

It checks Python 3.11+, ffmpeg/ffprobe, pycairo, PyGObject with Pango, and
Pillow, and prints the install command for this OS when one is missing
(installing system packages needs the user: ask). If `videobuilder` isn't
installed, it prints the `PYTHONPATH` that makes the checkout importable.
**Your shell's environment doesn't persist between commands**, so put
`PYTHONPATH=$VB` at the front of every `python` command (or `pip install -e
$VB` once, if pip and the user allow).

Work in a directory of its own (a project's `video/`, or a new one); the
film, its `assets/`, renders and sheets go there.

### Running in a sandbox

If `import videobuilder` fails and a checkout is provided, run each command
with `PYTHONPATH=<checkout>`. Read the skill directly from that checkout's
`skill/make-a-video/`; a global skill installation or network is unnecessary.
When the real track is unavailable, use `scripts/make_track.py --bpm 120
--beats 40 --out assets/music.wav` for a placeholder bed (choose the film's
BPM and beat count). Swap in the real track later, checking its BPM and
setting `Grid.head_trim` to its first beat; a tempo change requires retiming.
The generated bed starts at beat zero with `head_trim=0`. Render-time network
fetches remain forbidden: all assets must already be local.

## 2. Plan before code

Write the storyboard first, in the film or a scratch note, and show it to
the user when there is one to show. See `reference/storyboard.md` for the
format and the numbers. In short:

1. **Length and formats** from the brief (default 9:16 and 16:9 if unsaid).
2. **Segments in seconds, from their content**: what's on screen, and
   **every line of copy**, word for word. Each segment lasts as long as its
   motion takes to settle plus a short hold (about 0.5–1 s), and at least
   its read time (1 s plus its words at 3 words a second). Anything longer
   lingers. Cut copy before you stretch time.
3. **Then snap to the grid**: 30 fps and the music's tempo (§6), or 120 bpm
   without music. Round each cut to the *nearest* beat or half beat. Never
   pad a segment to a round beat count or a bar, or stretch it to fill the
   music: the timing comes from the content, and the grid only aligns it.
4. **Motion per segment**: entrance, hold, exit, and which segments
   overlap (a transition) instead of cutting.

Read `reference/motion.md` when assigning motion numbers, checking a move with `vb motion`, or locking a director note into `EXPECT`; choose one hero move per shot.

While planning, read `reference/capabilities.md`: the catalog of what videobuilder can already do, each entry with a worked example film to read. Reach for one of these before inventing an effect.

## 3. Scaffold the film

```sh
mkdir -p assets && cp $SKILL/template/film.py film.py
PYTHONPATH=$VB python film.py sheet --format all     # it runs as is
```

Keep a committed `STYLE.md` beside `film.py`; read it before every director note and add rejected defaults to its bans (`reference/motion.md`).

The template is a working 20 s film in 9:16 and 16:9. Keep its shape and
replace its content:

- `STORYBOARD`: `card(name, beats, copy)` per segment, `group(...)` for
  cards sharing one scene, `overlap=k` for a transition. The copy lives in
  the storyboard so `check.py` can time it. Use a string or a list of strings
  for `copy`: every listed line counts. Other string keys beside `copy`
  produce a warning naming what was excluded. Set `copy_at=2.5` for copy
  legible 2.5 beats after the segment starts (default 0); for staggered
  lines use the latest entrance. This declares timing; animate it yourself.
- Draw every line of on-screen copy from `shot.data`, never a literal in a
  scene: a direct edit (`film.edits.toml`) can replace `Segment.data`
  strings only; list-valued copy currently requires editing Python.
- `layout_9x16()`, `layout_16x9()` (add `layout_1x1()` for square): one full
  table per format, each computed from its own frame and safe area.
- `SCENES`: segment (or group) name → scene function `(cv, shot, L)`.
- `draw`: loops over `TIMELINE.live(n)`; you rarely touch it.
- Every colour, font and size in it is a placeholder: replace them all.

`reference/api.md` is the API cheatsheet (timeline, easing, canvas, text,
layout, images, views) with the traps each part hides.

## 4. Assets

- **Fonts**: vendor the font files into `assets/` *with their licence*.
  `python $SKILL/scripts/fontinfo.py --ofl /usr/share/fonts/*/*.[ot]tf`
  lists the OFL families on this machine, one line each (`--family NAME`
  shows one family's files: the family name to use in `Font`, weights or
  variable axes, copyright, licence), read from the font itself. Go by
  that, not a distro's licence file (some ship the wrong text), and use the
  family name it prints: a variable file's often differs from its static
  siblings'. `$VB/examples/assets/` has three vendorable OFL variable fonts
  (Cantarell, Inter, Source Code Pro). After copying a font into `assets/`,
  `fontinfo.py --write-ofl assets/X.otf` writes its `<Family>-OFL.txt`, and
  `fontinfo.py --resolve 'Family' 700 assets/*` shows the face Pango really
  draws (it flags a fallback). The template registers every
  `assets/**/*.otf|ttf` recursively (including `assets/fonts/`); set `FAMILY`, and pass `family=` to `font()` for a
  second family (a mono for code). With static files, vendor each weight
  you use. Never rely on what `Sans` resolves to on this machine.
- **Images**: `vb.Image.load(path)` (decoded once; fine to call in `draw`),
  drawn with `cv.image(img, *box.cover(img.w, img.h))` inside `cv.clip`.
- **Screen captures**: `cv.view(img, box, center, scale)` is a camera on a
  capture: animate `center` to pan, `scale` to zoom (`vb.log_lerp`). `pin`
  keeps a strip (a navbar) fixed. See `$VB/README.md`, "A camera on an image".
- **Redrawn UI**: when captures are unusable, see `reference/redrawn-ui.md`
  for faithful vector screens and measured blocks stacked per format.
- **Generated imagery**: draw it with the canvas (`cv.ctx` is raw cairo), or
  make a PIL image once at import and wrap it with `vb.Image.from_pil`. Seed
  any randomness. No network fetches at render time: anything downloaded is
  vendored first, with its licence.
- **Looks** (a named art style: "make it pop art", "a woodblock print",
  "try a few looks"): read `reference/looks.md`. Describe the picture once
  as a `looks.Scene` (a few shapes with roles, the sun, a beacon) and paint
  it with `looks.paint(cv, name, scene, t)`; `looks.names()` lists every look,
  and your note's prompt names them too. Don't hand-restyle what a look does.
- **Type** (a named typography style: "make the title a split-flap board",
  "type it on like a terminal", "make the letters bounce"): read
  `reference/type.md`. Every style takes the same props (a few `lines`,
  `ink`, `paper`, `accent`, a `length`) and enters, holds and exits on its
  own: `vb.type.draw(cv, name, vb.type.props(lines=[...]), t)`, over another
  picture with `paper=None`. Don't hand-roll what a type style does.
- **3D shots**: build a ManimGX shot to `assets/name.mp4`, commit it, and
  draw its frames with `vb.Clip`. Match its frame count to its storyboard
  segment. See `reference/3d.md` for the build command and the GPU stop rule.
- **Footage with its own sound**: read `reference/footage.md` when the video
  uses source clips whose sound should play (an interview, a podcast): it
  places the clip's audio on the timeline, keeps it in sync with the picture
  and dips the music under the speech.
- **Captions**: read `reference/captions.md` when the video shows spoken
  words on screen: captions from a subtitle file, timed word by word.
- **Narration** (a voiceover, or a character that talks): use
  `$VB`'s `python -m videobuilder say assets/voice.txt --out assets/voice.wav`
  (text to speech) once, then commit the WAV, its `.vtt` and `.json`, and the
  script next to them; the film loads those, never the model. It gives
  phrase-timed captions and a mouth-open signal. Read `reference/narration.md`.
- **Stick figure** (an explainer acted out by a simple character: "a stick
  figure runs into a wall, then thinks"): `vb.Stick`, drawn in code with a
  face, named poses and expressions, walks and runs, props and a matching
  scene kit; it can talk with the narration. Read `reference/stick.md`.
- **Sound effects** (a whoosh on a whip pan, a click on a press, a hit on
  an impact frame): `vb.sfx`, ready-made sounds put on an exact frame. See
  §6 and `reference/sfx.md`.
- Write `assets/README.md`: each file, where it came from, its licence
  (generated files: the command that made them, and "generated for this film").
- Commit every file `film.py` reads. `.gitignore` only render outputs by path
  (preview frames, `*.mp4` renders, caches), never a whole file type such as
  `*.png`, and check the commit loads from a clean checkout before you hand it on.

## 5. The authoring loop

| step | command | use it for |
|---|---|---|
| preview | `PYTHONPATH=$VB python film.py preview` (serves `127.0.0.1:8000`) | when a human is watching: scrub, play, hot reload on save, `o` toggles the timeline overlay |
| sheet | `PYTHONPATH=$VB python film.py sheet --format all` | your main eyes: in/middle/out frame of every segment, labelled. Read the PNGs after every real change |
| still | `PYTHONPATH=$VB python film.py still 412 --format 16x9 --overlay` | one frame at full size: text edges, alignment, a mid-motion frame, a cut (`still c-1 c`) |
| check | `PYTHONPATH=$VB python $SKILL/scripts/check.py film.py` | storyboard table, read times, safe area and overlaps (needs `cv.mark`) |
| render | `PYTHONPATH=$VB python film.py render --format all` | the MP4s, once sheets and checks are clean. Seconds to a minute for a short film; if it stops with "render stalled", `still` one of the frames it names |

You can't watch the preview yourself: work from sheets and stills (read the
PNGs), and offer the preview command to the user. When a human reviews the
video, they can do it in the editor (`python -m videobuilder editor
<project-dir>`, see `$VB/README.md`): it moves cuts and changes
`Segment.data` copy as git commits to the film's edits file, and keeps
their notes. `sheet --every 5` or `--frames a,b,c` show motion.
`FILM.keyframes`, when set, *replace* the sheet's default in/middle/out
frames: list those too (`$VB/examples/benchmark.py`'s `_keyframes()` does).

**Cuts must land on something.** A hard cut reads on the beat only if the
new segment's first frame shows it: start entrances a few frames in (the
template's `appear` is `ENTER` frames in at `f = 0`). `check.py` warns
on a cut onto a frame with nothing marked on it. Settle motion by a segment's middle (the checks and default sheet
look there), or add the settled frames to `FILM.keyframes`.

**Motion on a beat** (a bar that grows on beat 10): key it off the beat's
frame, already `ENTER` frames in as it lands, e.g.
`vb.spring_at(shot.group_f - GRID.b(2) + ENTER, GRID.fps, ...)` for two
beats into a group. Check with `sheet --frames` around that frame.

Draw rules that keep frames pure (any frame renders alone, in any order):
no state across frames, no `random` without a fixed seed, no clock, no
I/O except cached loads. Animate from `shot.f` (frames into the segment),
`shot.group_f` (into the group) or `n`.

For a chart (a benchmark, a result), read `$VB/examples/benchmark.py`: a
bar chart drawn with `cv.rect`, `cv.line` and `text.draw`, bars growing on
beats, numbers counting up, horizontal in 9:16 and columns in 16:9.

## 6. Music and beat-locking

See `reference/music.md`. In short:

- **A track you're given**: `python -m videobuilder beats track.mp3` gives
  the BPM and the `Grid(..., head_trim=...)` that puts its first beat on
  frame 0 (`scripts/tempo.py` prints the same). Lay the segments out on
  that grid.
- **No track**: `python $SKILL/scripts/make_track.py --bpm 120 --beats 40
  --out assets/music.wav` makes a placeholder bed on the grid. Tell the user
  it's a placeholder.
- `audio=vb.Audio('assets/music.wav', fade_out_frames=...)`; the trim
  defaults to the grid's `head_trim`, so set it once, on the `Grid`.
- Cuts land on beats; a half-beat (`at=6.5`) is fine for a quick cut.
  `check.py --video` reports where the music's onsets fall against the grid.

### Sound effects

`vb.sfx.sound(id, at=frame)` puts a sound from the sound-effects pack on a
frame, its peak there (`align='onset'` for where it starts), into
`Film(sounds=...)`; `python -m videobuilder sfx fetch` gets the pack once,
`sfx list --role whoosh` shows what's in it. Read `reference/sfx.md`
before choosing. In short:

- **Which role:** whoosh on a whip pan or fast move (peak on its fastest
  frame), hit on an impact or a logo lock, click or tap on a UI press, riser
  into a reveal (its end on the reveal), downlifter out of one, shimmer on a
  sparkle, pluck or ding on a notification.
- **Restraint:** not every cut; a few moments that matter. Keep them quiet
  under speech (they dip with the music; `gain_db` around -6 to -12). One
  family per film (`designed`, `classic` or `fitted`).
- **Aim:** key `at` off the same frame the motion uses (the impact frame,
  the press, the pan's middle), never a guess; `dur=` picks the nearest
  length for a move, `note=` a tuned sound's note.
- `check.py --video` fails a sound effect that lands more than a frame off.

## 7. Formats

- Each format is its own layout, not a crop or a scaled copy: build each
  table from its own frame. 16:9 usually goes side by side where 9:16 stacks;
  a square needs its own type sizes. When a scene's idea doesn't fit a shape
  (a wide chart in 9:16), recompose it for that format (fewer bars, a
  vertical chart, a different crop); don't shrink it.
- Put `safe` in every table: the area text and key content stay inside
  (platform UI covers the edges of vertical video; use the platform's own
  numbers when the user names one, else keep the template's placeholder
  margins and say so). `cv.mark(name, *box)` every block of
  copy, chart and image; `text.draw` returns the box it drew. Name marks
  by what they are (`'headline'`, `'chart'`, `'cta'`): every pair is checked
  for overlap, same names included. One mark for a whole chart is enough.
- Checks: `check.py` fails a mark outside `safe` or two marks overlapping on
  held frames. List deliberate overlaps in the film: `OVERLAP_OK = {('chart',
  'label')}`.

## 8. Films made of clips

For a longer film, a story in scenes, or a mix of drawn shots and footage,
make a *film made of clips*: each clip its own small film, built and
rendered on its own, cut together by a `timeline.json`. One note can then
change one clip without re-rendering the rest. A single short film doesn't
need one. Read `reference/films.md` for the file format.

From scratch:

- At the video's root, a small `film.py`: a `FILM` with a `Timeline` (a
  title card will do) at the timeline's fps and formats. It is how the
  editor finds the video; the clips are what it shows.
- `timeline.json`: the clips in order, with their cuts, trims and transitions,
  optional acts, and Audio lanes for music under the whole film.
- A directory per clip, `clips/01-opening/film.py` and so on, each a film
  like any other at the same fps and in every format the timeline lists.
  Start its docstring with one line saying what the clip is for: builders
  are shown it.
- `shared/` for code more than one clip uses (palette, fonts, a character's
  drawing): `from shared import palette`.
- `bible/`, optional: `bible.md` for the look, world, tone and outline, and
  `characters/<name>.md`, each with pictures beside it if you have them.
  Read it before every clip; nothing renders it.

Keep the clip edges consistent: a clip begins where the one before it leaves
off and ends where the next picks up (characters, colours, light, framing),
so the cuts read as one film. Still the last frame of one clip and the first
of the next and look at them side by side.

**A reel** is a film of clips cut to a song: footage clips (several from
one file if it has several good moments), the song on an Audio lane, and a
`beats` key naming it, with every cut on a beat. A video started from
dropped clips and a song asks for one in its first note. Follow "Cutting a
reel" in `reference/films.md`: find the song's beats (`python -m
videobuilder beats sources/song.mp3`), look at every source (a sheet of
frames, stills), choose each clip's moment and its length in whole beats
or bars, set `in`/`out` so every cut lands on a beat, then check with
`assemble . --check` (it warns of each cut off the beat; `--snap` moves
them on) before rendering. Hard cuts carry a reel; a `whip` or a `flash`
marks an accent.

Check it: `python -m videobuilder assemble . --check` validates the timeline
file and the clip directories it names without rendering;
`python -m videobuilder assemble .` renders the whole film, re-rendering
only the clips that changed. A clip imports `shared` with the video's root
on its import path: `PYTHONPATH=. python -m videobuilder still
clips/01-opening/film.py 0`.

## 9. Review before calling it done

Review each note at named frames with stills and a sheet; use `check.py --motion` for mark trajectories (`reference/motion.md`). Render, then:

```sh
PYTHONPATH=$VB python $SKILL/scripts/check.py film.py --video
PYTHONPATH=$VB python film.py sheet --format all
```

and go through `reference/review.md`. `check.py` exits 1 on any FAIL:
ffprobe (H.264, yuv420p, size, fps, exact frame count and duration, AAC as
long as the picture), read times, safe area, overlaps. It WARNs on picture
jumps off the cut grid and on music off the beat: judge those with stills.
Then read every contact sheet yourself: clipped or colliding text, an empty
or unintended frame, a format that's a squashed copy of another.

Report to the user: the MP4 paths, length and formats, the storyboard, what
you chose (fonts, colours, music) and anything placeholder, and the check
results. Don't call it done with a FAIL standing.

## 10. Traps (details in `reference/api.md`)

- Frame math: `vb.round_half_up` (or `GRID.b(beat)`), never `round()`.
- Springs are real physics: `vb.critical(k)` for a settle with no
  overshoot; high damping in a hand-made spring crawls.
- `--chunk` must be a whole number of microseconds at the fps; the
  default is safe.
- Tracking (letter-spacing) matching a browser: `Font(..., css_tracking=True)`.
- A CSS shadow list paints first-on-top: call `cv.shadow` last to first.
- `Image.load` caches decodes; generate images once at import, not per frame.
- `text.wrap` caches on its arguments: pass a `Font`, a width and a string;
  a `'\n'` forces a break.
