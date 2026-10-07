# Music and beat-locking

The film's timeline is a beat grid; the music has to be on the same grid.
Two numbers tie them: the track's **BPM**, and **head_trim**, the frames cut
from the head of the track so its first beat lands on frame 0.

## A track you're given

1. Vendor it into `assets/` (and note its licence in `assets/README.md`).
2. Find its tempo and first beat:

       python $SKILL/scripts/tempo.py assets/track.mp3 --fps 30

   It lists tempo candidates (half or double the best is common: pick the
   pulse you'd clap to) and prints `Grid(fps=30, bpm=..., head_trim=...)`.
   If you know the BPM, pass `--bpm` and it only finds the first beat.
3. To skip an intro, start at a later beat (a downbeat, k beats in):
   `head_trim = round((first_beat_s + k * 60 / bpm) * fps)`.
4. Set it on the grid: `vb.Grid(fps=30, bpm=..., head_trim=...)`. `Audio`
   takes its trim from the grid; don't set `trim_frames` too.
5. A tempo that isn't a round number is fine (`bpm=117.5`): frames are
   rounded half up per beat, so cuts stay within half a frame of the music.

## No track

Make a placeholder bed exactly on the grid:

    python $SKILL/scripts/make_track.py --bpm 120 --beats 40 --out assets/music.wav

`--beats` is the film's `TIMELINE.end`. `--loop minor|major|drone` and
`--voices kick,hat,bass,pad` change its character; drop `kick,hat` for a
calmer bed. It starts on beat 1 at 0 s, so `head_trim=0`. Tell the user it's
a placeholder; real music is their call (and their licence). In
`assets/README.md`, record it as generated for this film, with the command.

## In the film

```python
FILM = vb.Film(..., audio=vb.Audio(str(HERE / 'assets' / 'music.wav'),
                                   gain_db=-3, fade_out_frames=round(2 * GRID.frames_per_beat)))
```

- A fade-out over the last beat or two avoids a hard stop; the track may be
  longer than the film (it's cut at the last frame) but not shorter (it's
  padded with silence).
- Build the film's path from `HERE` (the film's directory), not the cwd.

## Cutting on the beat

- Cuts are segment starts, so they're on beats by construction. A half-beat
  start (`at=12.5`) is a quick cut between beats.
- Motion that "hits" a beat: start the entrance a few frames early so it
  peaks on the beat (`appear(f, delay=-3)`), or key a pulse off the beat
  phase `(n / GRID.frames_per_beat) % 1`.

## Checking alignment

After a render:

    PYTHONPATH=$VB python $SKILL/scripts/check.py film.py --video

reports where the music's onsets land against the grid. Within half a frame
is aligned. Off by a steady amount: it prints the `head_trim` to use. "No
clear beat": the track has soft onsets; check by ear and with
`still --overlay` frames on the cuts.
