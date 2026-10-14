# Motion direction in frames

Use the film's fps: `round(seconds * GRID.fps)` for offsets, and `GRID.b(beat)` for beat positions. Animate from `shot.f`, `shot.group_f`, or `n`, so any frame can render alone. These are starting values, not a substitute for reading the frames. Adapted from the [Opus 5.5 Motion Lab](https://x.com/flxrnc/status/2105311836190978392).

## Translate the note

| Director note | First edit to try |
|---|---|
| “Make it pop” | On the beat, scale 1.00 → 1.08 → 1.00 over 6 frames; use `vb.ease_out_back` for a small position or size accent. |
| “Premium” | Enter with `vb.ease_out_quint` over 0.6–0.9 s; use `vb.damped(0.8)` for objects, `vb.ease_out_quint` for text. Keep the text's scale at or below 1. |
| “It drags” | Re-time every segment, not just the one named: measure in seconds when its motion settles and its text is read, add a 0.5–1 s hold, snap that to the nearest beat, and move the cut there. Speed up a move that is itself slow (a spring's `hz`, a long ease). Then recheck read time. |
| “Too busy” | Keep one hero move per shot. Start secondary motion 100–200 ms later, at 50–70% of the hero's travel. Hold other marks still. |
| “Looks like AI/generic” | Identify the repeated effect, add it to this film's `STYLE.md` bans, replace it with a move tied to the product or story. |
| “Abrupt ending” | Add about 36 frames of hold at 30 fps, with at most a 2% camera push; settle any moving object with `vb.damped(0.8)`. |

## Motion tokens

| Token | Use |
|---|---|
| `vb.ease_out_expo` `(0.16, 1, 0.3, 1)` | Fast entrance that settles early. |
| `vb.ease_out_quint` `(0.22, 1, 0.36, 1)` | Smooth, restrained entrance. |
| `vb.ease_in_out_quart` `(0.76, 0, 0.24, 1)` | Travel across the screen, with soft start and finish. |
| `vb.ease_in_expo` `(0.7, 0, 0.84, 0)` | Exit; give exits 40–50% fewer frames than entrances. |
| `vb.ease_out_back` `(0.34, 1.56, 0.64, 1)` | Small overshoot of object position or size. It exceeds 1. |
| `vb.linear` | Rotation, progress meters, and phase in a continuous loop only. |

`vb.spring_at(shot.f - start, GRID.fps, **vb.damped(ratio, hz=2))` uses an undamped natural frequency of 2 Hz. Ratio 1.0 has no bounce; 0.7–0.85 feels restrained; 0.4–0.6 is playful; below 0.3 is cartoonish. Let position and size bounce. Ease opacity and colour monotonically; never feed an overshooting spring into them.

UI feedback: 100–200 ms. UI moves: 200–500 ms. Hero reveals: 600–900 ms. Stagger letters by 1 frame, words by 60–120 ms, list items by 40–80 ms; start each when the prior move is 30–50% complete. Hold text for at least 0.3 s per word plus 0.5 s; the storyboard read-time check is stricter for some segments. While text is read, keep it still. A slow 2% camera push can keep the frame alive. For a capture, use `cv.view` with `vb.log_lerp` for zoom; move near layers farther than distant layers for parallax, but keep the text plane fixed. Keep text contrast at least 4.5:1 and no more than 3 flashes per second.

| Principle | Frame-level starting point |
|---|---|
| Anticipation | Crouch or pull back for 11 frames, scale about 1.2 × 0.75, hold 3 frames, then release. |
| Squash and stretch | At takeoff 0.85 × 1.28; at landing 1.25 × 0.70, returning to 1 × 1. |
| Overlap | Let appendages or secondary marks lag the hero by 4–6 frames. |
| Follow-through | After the body stops, settle the trailing part with `vb.damped(0.22, hz=2.2)`; keep copy still. |
| Arcs | Add a measured perpendicular offset at mid-flight (for example 10% of travel), zero at both ends. |
| Slow in/out | Use `vb.ease_in_out_quart` across a shot, or `vb.damped(0.55)` for a physical landing. |
| Timing | Start with 25 frames airborne and 18 frames of wind-up for a heavy hop; change counts to fit the beat grid. |

## Style contract for each film

Create `STYLE.md` beside `film.py` and commit it with the video. Record palette and font choices, safe-area and contrast rules, signature motion tokens, camera rules, and effects the director rejected. Read it before every note and add one line whenever the director rejects a default. Unless a brief explicitly calls for them, ban glow, floating decorative particles, every element fading in together, fade-and-slide-up on every element, centred-everything layouts, moving text while read, and purple/blue gradients.

Mesh gradients, glass (frosted, translucent) cards and gradient text are each fine on their own, but together they read as an AI-template look -- use at most one per film. A deep blue-to-purple palette reads as generic AI output; tie the palette to the brand or subject instead.

## Review a note at frames

Name the affected frames in the note: start, beat, peak, hold, exit, and one on either side of a problem. Render `python film.py still 83 84 85 --overlay` and `python film.py sheet --frames 0,24,48,72`; inspect each format. Run `check.py film.py --video` for flashes, loop seam, audio and beat checks, and `check.py film.py --motion` for mark trajectories. Judge WARNs against the stills before replying with frame numbers and the exact change.

| Symptom | Fix |
|---|---|
| Random jitter | Seed randomness once, or derive it from the frame number; keep `draw` pure. |
| Loop seam hiccup | Set `LOOP = True`; render 0 through N−1 and make the phase `n / N` periodic. Inspect N−2, N−1, 0, 1. |
| Text moves before it can be read | Hold at least 0.3 s per word plus 0.5 s; keep the text plane stationary. |
| Everything moves together | Pick one hero; delay secondaries 100–200 ms and reduce travel to 50–70%. |
| Drift off the beat | Calculate every beat with `GRID.b(k)`; never sum rounded beat lengths. |

## Lock in a director note

After fixing a concrete note, add a module-level `EXPECT` entry that would have caught the old behavior. Copy the director's words into `note=`; `check.py film.py` checks it on every format and prints a FAIL with the note if it regresses. Prefer `vb.seg('outro')`, `vb.seg('land', 3)`, `vb.seg('land', 'end', -1)` (the last frame), or `vb.seg('hold', 'mid')` over absolute frames, so roll edits keep the check attached to the scene.

```python
EXPECT = [
    vb.visible('logo', vb.seg('outro'), note='Show the logo at the start of the outro'),
    vb.touches('feet', 'pad', vb.seg('land', 3), tolerance=2,
               note='The feet should meet the landing pad'),
    vb.at_rest_by('headline', vb.seg('hold', 4), speed=0.5,
                  note='Let the headline settle before it is read'),
]
```

Run `python -m videobuilder motion film.py --from land --to hold --mark feet --onion 3 -o motion.png` before replying to a motion note. Read the speed curve for steady-rate runs, abrupt edges, and a late settle; the onion skin shows the image and marked path. Inspect the affected formats too.
