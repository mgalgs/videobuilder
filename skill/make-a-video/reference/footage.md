# Footage with its own sound

A film has one music track (`Film.audio`), muxed in by `render` with a trim,
gain, fade-out and loudness normalisation. `vb.Clip` reads frames from a
video file, so footage can already be placed on screen, but it comes in
silent. `vb.Sound` is the missing piece: a clip's own audio, placed on the
film's timeline alongside the music, for commentary cuts — podcast or
hearing footage where the speakers are heard, interleaved with graphics,
over a quiet music bed.

## `Sound`

```python
vb.Sound(path, at=90, start=12.5, frames=150, gain_db=0, fade_in_frames=3, fade_out_frames=3)
```

- `path`: the source file (it needs an audio stream; a path that doesn't have
  one is a clear error at render time, not a silent drop).
- `at`: the film frame it starts on.
- `start`: seconds into `path` where it starts.
- `frames`: its length, in film frames.
- `fade_in_frames`/`fade_out_frames`: a short ramp (a few frames) at each
  edge, so a cut into or out of the sound doesn't click.

A `Sound` that runs outside the film's own frame range is clipped to it (its
`start` moves with a clipped head). Put as many as the film needs on
`Film.sounds`:

```python
FILM = vb.Film(draw=draw, timeline=TIMELINE, audio=vb.Audio('assets/music.wav'),
               sounds=(vb.Sound('assets/interview.mp4', at=90, start=12.5, frames=150),
                       vb.Sound('assets/interview.mp4', at=260, start=48.0, frames=90)))
```

A film can have sounds with no music at all (`audio=None`); it still renders
with audio, normalised to the same -14 LUFS default as music gets (see below).

## Ducking the music

`Audio.duck_db` drops the music while any sound plays, so the music doesn't
fight the speaker:

```python
vb.Audio('assets/music.wav', duck_db=-12)
```

The drop ramps over a few frames at each edge of a sound's span (using that
sound's own `fade_in_frames`/`fade_out_frames`), computed purely from the
sounds' spans — a deterministic gain envelope, not a sidechain compressor
reacting to the actual signal. `duck_db=0`, the default, means no ducking.

## One loudness target for the mix

`Audio.loudness` (default -14 LUFS) is the target for the music when a film
has no sounds, same as always. When a film has `sounds` and music, it's the
target for the *whole mix* (music plus sounds) instead, still measured over
the whole film — a partial render (`render(..., frames=(a, z))`) gets the
same gain as the full one. A film with sounds and no music has no `Audio` to
carry that target, so `Film.loudness` (same -14 LUFS default) takes over for
it instead — one knob or the other is ever in effect, never both. Set
`loudness=None` on whichever one applies to turn normalisation off (raw
passthrough, no limiter either).

## Keeping picture and sound in sync

Drawing the right source frame and placing the matching `Sound` both need
the same arithmetic: the source second for film frame `f` is `start + (f -
at) / fps`. `vb.footage` does it once:

```python
ft = vb.footage(TIMELINE, 'interview', start=12.5)   # a Segment or its name, + a source in-point
```

`ft.seconds_at(f)` is the source second to show at film frame `f`; feed it to
`Clip.frame_at(seconds)` for the source frame index. `ft.sound(path, **kw)`
builds the matching `Sound`, starting at the same source second segment's
first frame does.

Phone footage needs no special handling here: a rotated recording decodes
upright at its displayed size, and a variable-frame-rate recording presents
as constant-rate at its own average fps, so this same arithmetic still lines
up picture and sound.

```python
HERE = Path(__file__).resolve().parent
clip = vb.Clip(str(HERE / 'assets' / 'interview.mp4'))
footage_a = vb.footage(TIMELINE, 'interview', start=12.5)

def draw(n, cv):
    seg, f = TIMELINE.at(n)
    if seg.name == 'interview':
        pic = clip.frame(clip.frame_at(footage_a.seconds_at(n)))
        cv.image(pic, 0, 0, cv.width, cv.height)

FILM = vb.Film(draw=draw, timeline=TIMELINE,
               audio=vb.Audio(str(HERE / 'assets' / 'music.wav'), duck_db=-12),
               sounds=(footage_a.sound(str(HERE / 'assets' / 'interview.mp4'), gain_db=-3),))
```

Here, frame `f` of the `interview` segment shows source frame
`clip.frame_at(12.5 + (f - at) / fps)`, where `at` is the segment's first
film frame — and the `Sound` starts at that same source second, 12.5.
