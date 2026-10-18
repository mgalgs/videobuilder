# Films made of clips: `timeline.json`

A video can be a film made of clips. Each clip is built and rendered on its
own, and the video is an *assembly*: the clip renders cut together, plus Audio
lanes. A video is a film of clips when its root (beside `film.py` and
`requirements.txt`) has a `timeline.json`; a video without one renders exactly
as before.

The editor finds a film of clips by that root `film.py`, like any video (or
by its entry in `videobuilder.toml`), and for it serves the assembly, never
the root film's own render. So keep a small root film: a `FILM` with a
`Timeline` (a title card will do) at the timeline's `fps` and `formats`. The
clip directories the timeline names are not searched for videos, so a clip's
film is never listed as a video of its own.

The timeline file holds only what a person changes directly on the film:
clip order, trims, transitions, J/L cuts, and Audio lanes and their items.
Anything else (what a clip shows, its motion, its type, its own music) lives
in that clip's code and is changed by a note to the builder, never by adding
keys here. A file with an unknown key is refused, with a hint.

```
film.py                   the video's own film file: how the editor finds it
timeline.json
clips/
  01-opening/film.py      one clip: its own film, rendered on its own
  03-credits/film.py
shared/                   code any clip imports: from shared import palette
sources/                  uploaded footage and sounds (never committed)
```

```json
{
  "version": 1,
  "fps": 30,
  "formats": ["16x9", "9x16"],
  "clips": [
    {"id": "opening", "dir": "clips/01-opening"},
    {"id": "boat", "footage": "sources/boat.mp4", "in": 30, "out": 120,
     "head": 0, "tail": 6,
     "cut": {"transition": "dissolve", "frames": 12},
     "sound": {"gain_db": -2, "early": 6, "dialogue": true}},
    {"id": "credits", "dir": "clips/03-credits",
     "cut": {"transition": "wipe", "frames": 10, "direction": "left"}}
  ],
  "acts": [{"title": "The river", "clips": ["opening", "boat"]}],
  "lanes": [
    {"duck": true, "items": [
      {"sound": "sources/theme.mp4", "at": 0, "offset": 0, "frames": 240, "gain_db": -3}]}
  ]
}
```

Every time is a whole number of frames at `fps`. Every path is relative to
the video's root and stays inside it.

**Top level.** `version` (1), `fps` (default 30; every clip film must use the
same), `formats` (names from `16x9`, `9x16`, `1x1`; default `["16x9"]`; each
clip film must list each of them), `clips`, optional `acts` and `lanes`.

**Clips**, in order; `id` is lowercase letters, digits and dashes, unique.
Each clip is one of:

- a *clip directory*: `dir`, holding a film file (`film`, default `film.py`)
  with a module-level `FILM` like any video's. It renders on its own and is
  cached by its content: it re-renders only when its directory, `shared/` or
  `requirements.txt` change. It imports shared code as `from shared import ...`
  (the video's root is on its import path).
- a *footage clip*: `footage`, a file cut from frame `in` to frame `out`
  (exclusive, counted from the file's start at `fps`). No code, no render: it
  is scaled to cover the frame and centre-cropped at assembly.

On either: `head`/`tail` trim frames off the clip's start and end (the trims
either side of a cut are the outgoing clip's `tail` and the incoming clip's
`head`); `cut` is the cut *into* this clip from the one before (none on the
first clip): `transition` is `cut`, `dissolve` or `wipe` (with a `direction`:
left, right, up, down), and `frames` its length (none for `cut`). A dissolve
or wipe overlaps the two clips by its frames, so the film gets that much
shorter. `whip`, `flash` and `match` are reserved for later.

`sound` is the clip's own sound: `gain_db`; `early` frames it starts before
its picture (a J-cut) and `late` frames it runs on after (an L-cut). J/L
reveal sound from the trimmed head or tail (for footage, from the file beyond
`in`/`out`), so trim the picture first; where there is nothing trimmed there
is nothing to reveal. `dialogue: true` marks all of the sound as speech
(for a clip whose speech isn't its film's `Sound`s or its captions).

**Acts**: optional titles over runs of consecutive clips, in order.

**Lanes** are Audio lanes. They have no names in the file: they are called
"Audio 1", "Audio 2"... by position, everywhere. Each has `items`: a `sound`
file placed at timeline frame `at`, playing `frames` frames from `offset`
frames into the file, with `gain_db` and `fade_in`/`fade_out` frames (default
3). `duck: true` dips the lane by `duck_db` (default -12) while any clip
sound that is speech plays, each over its own span: the `Sound`s of a clip
directory's film (the spans its render reports, so a 2 s voice-over in a 10 s
clip dips the lane for 2 s), the caption cues of a footage clip with a caption
file beside its source (`sources/boat.vtt` beside `sources/boat.mp4`), or the
whole of a clip's sound when it is marked `dialogue`.

**Footage and big sounds** live in the video's `sources/`: uploaded to the
editor, linked into every checkout and render, and never committed. A small
committed sound file elsewhere in the repo works too.

Render it locally with

```
python -m videobuilder assemble . [--format 16x9|all] [--out film.mp4]
```

Clip renders are kept in `.vb-cache/clips/`; a second run renders only the
clips that changed, and a change to the timeline file alone renders none.
