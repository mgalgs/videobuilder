# Planning a film: storyboard, grid, read times

Plan on paper first. Changing a storyboard line is cheap; re-timing a drawn
film is not.

## 1. Time first, then the grid

Pacing comes from the content, not from the beat. Time each segment in
**seconds** first, then snap its cuts to the grid:

1. **How long it needs**: its motion until it settles, plus a short hold
   (about 0.5–1 s), and never less than its read time (below). That number
   is the segment's length. A segment that holds still for more than about
   a second after its last move and its read time is too long.
2. **Snap**: convert to beats (seconds × BPM / 60) and round each cut to the
   nearest beat, or half beat. Round to the *nearest*, not up: never pad a
   segment to a whole bar or a round beat count, and never stretch one to
   fill the music. The film is as long as its segments add up to.

The grid is what cuts snap to:

- **fps**: 30 unless the brief says otherwise (24 for a filmic feel, 60 for
  fast screen motion).
- **BPM**: the music's tempo if there's a track (`scripts/tempo.py`).
  Without one, 120 bpm at 30 fps (15 frames a beat, 2 beats a second) snaps
  finely enough for anything; 100 bpm = 18 frames, 90 = 20, 150 = 12.

## 2. The storyboard

One line per segment: name, beats (snapped from its seconds), what's on
screen, the copy word for word, and the motion. For example (an invented
20 s film, 120 bpm, 40 beats):

| segment | beats | on screen | copy | motion |
|---|---|---|---|---|
| hook | 0–8 | headline alone | "Your notes, searchable in a blink" | words spring up line by line; fade out |
| points / 1 | 8–12 | first point, rule underneath | "Type to search" | rule draws once for the group |
| points / 2 | 12–16 | second point | "Every note, every tag" | hard cut on the beat |
| points / 3 | 16–20 | third point | "Offline, instant" | hard cut |
| proof | 20–30 | the result: chart / capture | "Search 50k notes in 40 ms" | panel settles, chart grows |
| end | 30–40 | name, call to action | "Try it free" | slides up over proof (overlap 1) |

It maps straight onto the template's `STORYBOARD`:
`card('hook', 8, 'Your notes, searchable in a blink')`,
`group('points', card('point 1', 4, ...), ...)`, `card('end', 10, ..., overlap=1)`.

Rules of thumb (process, not style):

- **One idea per segment**, and the copy for it. A segment with nothing to
  read still needs a reason to be there.
- **Read time**: a segment lasts at least 1 s plus its words at 3 words a
  second (`check.py` enforces this; `--wps` and `--lead` change it if the
  brief or audience calls for it). Text entering late in a segment has less
  time: count from when it's legible. A URL, a command or a number reads
  slower than its word count: give it extra time. When copy doesn't fit,
  cut words before adding beats. Read time is a floor, not a target: count
  only what the viewer actually reads (a chart key that repeats a label
  isn't new reading).
- **Cuts on beats**: snapped to the nearest whole beat by default; half
  beats (`6.5`) for a quick cut. A run of quick cuts is a `group` so one
  thing can carry across them.
- **Overlaps** (`overlap=k`) for transitions: the outgoing segment keeps
  drawing under the incoming one for `k` beats. A hard cut needs none.
- The hook and the end card carry the brief: what this is, and what to do
  next. Check both read in under their segment's length.

## 3. Per format

Note, per segment, anything that changes between formats: a side-by-side
layout in 16:9 that stacks in 9:16, a chart with fewer bars in portrait, a
capture cropped differently. Same timeline, same copy, different layout.
If a format would need different copy or timing, that's a separate film
(copy the file), not a layout table.

## Declaring copy and its entrance

Use `data={'copy': ['Product name', 'Try it free'], 'copy_at': 2.5}`,
or `card('end', 10, ['Product name', 'Try it free'], copy_at=2.5)`.
Every list entry counts toward the combined read time. `copy_at` is a finite,
nonnegative number of beats after this segment starts, default 0, when all
listed text is legible. For staggered entrances use the latest one; this is
conservative. The checker uses the grid-rounded entrance frame through the
segment's end, excluding any outgoing overlap extension. It fails when that
remaining hold is too short. The declaration does not animate the text.

With `copy`, other string-valued data keys are excluded and named in a warning:
include any on-screen words in the list, and judge off-screen metadata yourself.
Without `copy`, all data strings count. List copy is edited in Python; direct
edits currently replace only string-valued data keys.
