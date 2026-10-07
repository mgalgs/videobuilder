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

## 2. Plan before code

Write the storyboard first, in the film or a scratch note, and show it to
the user when there is one to show. See `reference/storyboard.md` for the
format and the numbers. In short:

1. **Length and formats** from the brief (default 9:16 and 16:9 if unsaid).
2. **BPM and fps, first**: the grid drives every cut. 30 fps; a tempo that
   makes your segment lengths whole or half beats (120 bpm = 15 frames a
   beat = 2 beats a second). If there's a music track, its tempo wins (§6).
3. **Segments in beats**: what's on screen, and **every line of copy**,
   word for word. A segment must last its read time: 1 s plus its words at
   3 words a second, at least. Cut copy before you stretch time.
4. **Motion per segment**: entrance, hold, exit, and which segments
   overlap (a transition) instead of cutting.

## 3. Scaffold the film

```sh
mkdir -p assets && cp $SKILL/template/film.py film.py
PYTHONPATH=$VB python film.py sheet --format all     # it runs as is
```

The template is a working 20 s film in 9:16 and 16:9. Keep its shape and
replace its content:

- `STORYBOARD`: `card(name, beats, copy)` per segment, `group(...)` for
  cards sharing one scene, `overlap=k` for a transition. The copy lives in
  the storyboard so `check.py` can time it.
- Draw every line of on-screen copy from `shot.data`, never a literal in a
  scene: a direct edit (`film.edits.toml`) can replace `Segment.data`
  strings only.
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
  `assets/*.otf|ttf`; set `FAMILY`, and pass `family=` to `font()` for a
  second family (a mono for code). With static files, vendor each weight
  you use. Never rely on what `Sans` resolves to on this machine.
- **Images**: `vb.Image.load(path)` (decoded once; fine to call in `draw`),
  drawn with `cv.image(img, *box.cover(img.w, img.h))` inside `cv.clip`.
- **Screen captures**: `cv.view(img, box, center, scale)` is a camera on a
  capture: animate `center` to pan, `scale` to zoom (`vb.log_lerp`). `pin`
  keeps a strip (a navbar) fixed. See `$VB/README.md`, "A camera on an image".
- **Generated imagery**: draw it with the canvas (`cv.ctx` is raw cairo), or
  make a PIL image once at import and wrap it with `vb.Image.from_pil`. Seed
  any randomness. No network fetches at render time: anything downloaded is
  vendored first, with its licence.
- Write `assets/README.md`: each file, where it came from, its licence
  (generated files: the command that made them, and "generated for this film").

## 5. The authoring loop

| step | command | use it for |
|---|---|---|
| preview | `PYTHONPATH=$VB python film.py preview` (serves `127.0.0.1:8000`) | when a human is watching: scrub, play, hot reload on save, `o` toggles the timeline overlay |
| sheet | `PYTHONPATH=$VB python film.py sheet --format all` | your main eyes: in/middle/out frame of every segment, labelled. Read the PNGs after every real change |
| still | `PYTHONPATH=$VB python film.py still 412 --format 16x9 --overlay` | one frame at full size: text edges, alignment, a mid-motion frame, a cut (`still c-1 c`) |
| check | `PYTHONPATH=$VB python $SKILL/scripts/check.py film.py` | storyboard table, read times, safe area and overlaps (needs `cv.mark`) |
| render | `PYTHONPATH=$VB python film.py render --format all` | the MP4s, once sheets and checks are clean. Seconds to a minute for a short film; if it stops with "render stalled", `still` one of the frames it names |

You can't watch the preview yourself: work from sheets and stills (read the
PNGs), and offer the preview command to the user. `sheet --every 5` or
`--frames a,b,c` show motion. `FILM.keyframes`, when set, *replace* the
sheet's default in/middle/out frames: list those too
(`$VB/examples/benchmark.py`'s `_keyframes()` does).

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

- **A track you're given**: `python $SKILL/scripts/tempo.py track.mp3` gives
  the BPM and the `Grid(..., head_trim=...)` that puts its first beat on
  frame 0. Lay the segments out on that grid.
- **No track**: `python $SKILL/scripts/make_track.py --bpm 120 --beats 40
  --out assets/music.wav` makes a placeholder bed on the grid. Tell the user
  it's a placeholder.
- `audio=vb.Audio('assets/music.wav', fade_out_frames=...)`; the trim
  defaults to the grid's `head_trim`, so set it once, on the `Grid`.
- Cuts land on beats; a half-beat (`at=6.5`) is fine for a quick cut.
  `check.py --video` reports where the music's onsets fall against the grid.

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

## 8. Review before calling it done

Render, then:

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

## 9. Traps (details in `reference/api.md`)

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
