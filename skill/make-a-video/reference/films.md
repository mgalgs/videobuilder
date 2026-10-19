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
clip order, trims, transitions, J/L cuts, Audio lanes and their items, and
a reel's beat grid.
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
bible/                    optional: what every clip's builder reads first
  bible.md
  characters/mara.md
  characters/mara.png
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
      {"sound": "sources/theme.mp4", "at": 0, "offset": 0, "frames": 240, "gain_db": -3},
      {"sfx": "pro_impact/short", "at": 96, "gain_db": -6}]}
  ],
  "beats": {"lane": 1, "item": 1, "bpm": 120, "first": 12}
}
```

Every time is a whole number of frames at `fps`. Every path is relative to
the video's root and stays inside it.

**Top level.** `version` (1), `fps` (default 30; every clip film must use the
same), `formats` (names from `16x9`, `9x16`, `1x1`; default `["16x9"]`; each
clip film must list each of them), `clips`, optional `acts`, `lanes` and
`beats`.

**Clips**, in order; `id` is lowercase letters, digits and dashes, unique.
Each clip is one of:

- a *clip directory*: `dir`, holding a film file (`film`, default `film.py`)
  with a module-level `FILM` like any video's. It renders on its own and is
  cached by its content: it re-renders only when its directory, `shared/` or
  `requirements.txt` change. It imports shared code as `from shared import ...`
  (the video's root is on its import path).
- a *footage clip*: `footage`, a file cut from frame `in` to frame `out`
  (exclusive, counted from the file's start at `fps`). No code, no render: it
  is scaled to cover the frame and centre-cropped at assembly. One file can
  give several clips: each range of it is its own footage clip, with its own
  id (`boat`, `boat-2`), anywhere in the order.

On either: `head`/`tail` trim frames off the clip's start and end (the trims
either side of a cut are the outgoing clip's `tail` and the incoming clip's
`head`); `cut` is the cut *into* this clip from the one before (none on the
first clip): `transition` is `cut`, `dissolve`, `wipe`, `whip` or `flash`,
and `frames` its length (none for `cut`). A wipe and a whip take a
`direction`, the way the picture moves: left (default), right, up, down. A
whip is a whip pan: a fast slide with motion blur (6 to 10 frames). A flash
is a short cut through white (4 to 8 frames), white at its middle. Every
transition overlaps the two clips by its frames, so the film gets that much
shorter. `match` is reserved for later.

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
whole of a clip's sound when it is marked `dialogue`. `mute: true` leaves a
lane out of the mix, items and all, without removing it.

**Sound effects** from the pack (`vb.sfx`, see `sfx.md`) go on a lane too:
an item with `sfx`, a sound's id, in place of `sound`:

```json
{"sfx": "whoosh_fast/tight", "at": 96, "frames": 15, "gain_db": -8}
{"sfx": "pro_notify/ding_2045", "note": "G5", "at": 130, "align": "onset"}
```

`at` is the timeline frame its peak lands on (`align: "onset"`: where it
starts); `variant` names a take (`"0.8s"`, `"C5"`), `note` a tuned sound's
note, and `frames`, optional, a length: the take nearest it, cut to it with
a short fade when longer (without, the take plays whole). No `offset` or
fades: a sound effect plays from its start. It dips under speech with its
lane when the lane ducks, unless `"through": true`. A sound effect can't be
the `beats` item.

A cut can ask for one too, landing on the cut (a hard cut's first frame, a
transition's middle): `"sound": "auto"` gives a whip a whoosh
(`whoosh_fast/tight`, about two whips long) and a flash a hit
(`pro_impact/short`), both at -6 dB (a `gain_db` adds to it); or name one,
`"sound": "pro_impact/short"`, or give the lane item's keys without `at`,
`"sound": {"sfx": "pro_impact/short", "gain_db": -4}`. It dips under speech
by -12 dB unless `through`. `assemble --check` names a sound or take the
installed pack hasn't, and says when the pack isn't installed.

**Beats** make the film a *reel*, cut to a song: `lane` and `item` name the
Audio lane item that plays the song, counted from 1 as the editor shows
them ("Audio 1", its item 1); `bpm` is the song's tempo; `first` the frame
of its first beat, counted from the start of its file at `fps`; `bar` its
beats to a bar (default 4). Beat k is `first + k × fps × 60 / bpm` frames
into the file (rounded half up), so on the timeline at the item's `at -
offset` plus that, from where the item starts playing to where it stops.
`python -m videobuilder beats sources/song.mp3` finds `bpm` and `first`
and prints the key. A timeline without `beats` is not a reel and nothing
about it changes.

On a reel every cut belongs on a beat. Where a cut is: a hard cut, the
first frame of the clip it cuts to; a transition, its middle (its first
frame plus half its frames, rounded down). A cut off the beat is not an
error: `assemble` and `assemble --check` print it as a warning
(`off the beat: clips[3] "boat": the cut into it is at frame 239, 2 frames
after beat 16 (frame 237); put it on 237 or 252`, at 120 bpm with `first`
12), and the editor marks it.
The editor's trims step a beat at a time on a reel; an off-beat cut there
is something a person asks for in a note.

**Footage and big sounds** live in the video's `sources/`: uploaded to the
editor, linked into every checkout and render, and never committed. A small
committed sound file elsewhere in the repo works too.

Render it locally with

```
python -m videobuilder assemble . [--format 16x9|all] [--out film.mp4]
```

Clip renders are kept in `.vb-cache/clips/`; a second run renders only the
clips that changed, and a change to the timeline file alone renders none.

To check the timeline file without rendering anything, add `--check`: it
validates the file and that every clip directory it names has its film
file, and lists footage and sounds that aren't on disk (fine for uploads
that aren't in this checkout). On a reel it also warns of every cut off a
beat, as far as it knows clip lengths without rendering (footage, and clip
directories with a cached render). `--snap` moves every off-beat cut onto
the nearest beat (or the one on its other side when the clip can't reach
it) by changing how long the clip before it runs (a footage clip's `out`,
after giving back its `tail`; a clip directory's `tail`), writes
`timeline.json` and prints what moved. A clip directory imports `shared` with the
video's root on its import path, so run its own tools that way:
`PYTHONPATH=. python -m videobuilder still clips/01-opening/film.py 0`.

## Cutting a reel

A video started from dropped clips and a song is a film of clips with one
footage clip per file, each the whole file, in the order they were dropped,
and the song on Audio 1. Its first note says "Cut these clips to the song":
make it a reel, the good moments of each clip cut to the song, every cut on
a beat. You change only `timeline.json` for it.

1. **The song's beats.** `python -m videobuilder beats sources/song.mp3`
   (add `--fps` if the timeline isn't 30) prints the tempo candidates, the
   first beat, and the `beats` key. Half or double the best tempo is common:
   pick the pulse you'd clap to; pass `--bpm` if you know it. Put the key in
   the timeline. To skip an intro, start the song later: set the item's
   `offset` to `first` (the first beat lands on the item's `at`) or to a
   later downbeat (`first` plus a whole number of bars, in frames, rounded).
2. **Look at every source.** For each file, a sheet of frames:
   `ffmpeg -i sources/a.mp4 -vf "fps=1,scale=320:-2,tile=6x4" -frames:v 1
   a-sheet.jpg` (one frame a second; `fps=2` for a short clip), and stills
   at the moments you want (`ffmpeg -ss 12.4 -i sources/a.mp4 -frames:v 1
   a-12.jpg`). Note each clip's good moments as frame ranges: action that
   peaks, a face that turns, a reveal, movement that carries across a cut.
   Skip the shaky starts, the dead air, the camera finding its subject.
3. **Plan the cut in beats.** Give each moment a length in whole beats, in
   bars where you can (1 bar, 2 bars; 2 beats for a quick run), in the
   order that builds: calmer clips while the song builds, the best moments
   and the shortest cuts where it peaks, a held shot to close. A long
   source can give several clips: each range is its own footage clip (copy
   the entry, give it a new id like `boat-2`), anywhere in the order. A
   clip you don't use comes out of `clips` (and out of its act).
4. **In and out points.** A clip n beats long starting at the timeline's
   beat k runs from beat k to beat k + n; its length in frames is the
   difference of the two beats' frames (`frame(k + n) - frame(k)`, which
   isn't always n times one beat's frames when a beat isn't a whole number
   of frames). Set `in` to the moment's first frame in the file and `out`
   to `in` plus that length. The first clip starts at frame 0: with the
   song's first beat on the item's `at` (step 1), the first cut is on beat
   n; with an intro under the first clip, make the first cut on the song's
   first beat or on a later downbeat. `vb.beats.BeatGrid` (and
   `timeline_file.beat_grid(timeline)`) gives `frame(k)`, `snap(frame)` and
   `step(frame, n)` if you script it.
5. **Transitions.** Hard cuts carry a reel. Use a whip or a flash on an
   accent (a drum fill, the drop) and few of them; their middle is the
   cut, so it is what lands on the beat. Dissolves slow a reel down.
6. **The song's length.** Set the song item's `frames` to the film's
   length (end on a downbeat, the last clip held to it) and a `fade_out`
   of a beat or two.
7. **Check.** `python -m videobuilder assemble . --check` warns of every
   cut off the beat; `--snap` puts them on the nearest beat for you (run
   `--check` again after). Then render it, `python -m videobuilder assemble
   .`, and watch the MP4: still frames either side of a few cuts
   (`ffmpeg -ss <s> -i film-16x9.mp4 -frames:v 1 cut.jpg`), and check the
   cuts fall on the beats you hear.

## The bible

An optional `bible/` directory at the video's root describes the film as a
whole, for every builder that works on it: `bible.md` (the look, the world,
the tone, the outline: what each clip is for, in order) and
`characters/<name>.md`, one per character, each optionally with pictures
beside it (`characters/mara.png`). Builders read it first and keep the
characters and the look consistent with it; nothing renders it. A clip's
film file starts its docstring with one line saying what the clip is for;
builders are shown that line too.

## Notes on a film of clips

A note in the editor is about one clip (`clip`, a clip id in `timeline.json`
on main) or about the whole video.

- **A clip note** tells the builder which clip (its id, its number, its act),
  what it is for, the cuts either side of it, and, as `/attachments/
  previous-clip-last-frame.png` and `/attachments/next-clip-first-frame.png`,
  the last frame of the clip before it and the first frame of the clip after
  it, as the film shows them (trims applied), when those renders are cached
  (a footage clip's frame comes from its source). The builder changes files
  only under that clip's directory. It may change `shared/` too, only when
  the note asks for something every clip uses: that re-renders every clip.
  It never changes `timeline.json`, the bible or another clip in a clip
  note. A note on a footage clip may change only that clip's entry in
  `timeline.json`, or turn it into a clip directory that reads the footage.
- **A whole-video note** may edit `timeline.json`, add, split or remove clip
  directories, and edit `shared/` and `bible/`, checking the timeline file
  before it commits with the videobuilder the video renders with:
  `timeline_file.load` on any version, and `assemble --check` where that
  version has it.
