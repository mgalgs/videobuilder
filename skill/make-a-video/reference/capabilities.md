<!-- GENERATED from videobuilder/capabilities.py by `sheet_markdown()`. Do not hand-edit;
     regenerate with `python -m videobuilder capabilities sheet > skill/make-a-video/reference/capabilities.md` after changing the catalog. -->
# Capabilities catalog

What videobuilder can already do, with a worked example for each. Reach for one of these before inventing an effect. Adding a capability later means adding one entry to `CATALOG` in `videobuilder/capabilities.py` and one demo film beside the others in `examples/capabilities/`; this file and the `/capabilities` page are both generated from that single catalog.

## Motion

### Eased entrances

**What it looks like:** The named motion tokens, compared side by side. Five named easing curves — videobuilder's motion tokens — each sliding a chip into place on its own row, so their character is easy to tell apart: a fast settle, a restrained glide, a small overshoot.

**When to use it:** reach for this when a director says something like:
- "Ease this in with ease_out_expo"
- "Use a restrained entrance (ease_out_quint), nothing bouncy"
- "Give the exit ease_in_expo and make it quicker than the entrance"

**How to build it:**
- `vb.ease_out_expo`
- `vb.ease_out_quint`
- `vb.ease_in_out_quart`
- `vb.ease_out_back`
- `vb.ease_in_expo`
- `vb.interpolate(f, keys, values, ease=...)`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/eased-entrances.py` — read it before writing something similar from scratch.

### Springs with character

**What it looks like:** One spring, three damping ratios: firm to playful. The same spring drop at three damping ratios — 1.0 (no bounce), 0.6 (restrained) and 0.3 (playful) — landing side by side so the difference in character is visible, not just described.

**When to use it:** reach for this when a director says something like:
- "Drop this in with a playful spring, a bit of bounce"
- "Use a firm, no-overshoot settle (critical damping)"
- "Make the bounce more cartoonish — lower the damping ratio"

**How to build it:**
- `vb.spring_at(f, fps, **vb.damped(ratio, hz=2.0))`
- `vb.critical(stiffness)`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/springs-with-character.py` — read it before writing something similar from scratch.

### Staggered reveals

**What it looks like:** A list that cascades in, one item after the next. List chips reveal in sequence, each starting while the one before it is still mid-flight, instead of all arriving at once — the cascade that makes a list of features or steps read as a group.

**When to use it:** reach for this when a director says something like:
- "Stagger these in as a list, cascading"
- "Don't pop them all in at once; stagger it"
- "Reveal the words one at a time, staggered"

**How to build it:**
- `vb.spring_at(f - delay, fps, **vb.damped(...))`
- `per-item frame delay (40-80ms list items)`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/staggered-reveals.py` — read it before writing something similar from scratch.

### Pop on the beat

**What it looks like:** A scale accent that lands exactly on the grid. A mark pops — a quick scale accent — exactly on each beat of the grid, the way a logo or a stat should punctuate a cut instead of drifting past it.

**When to use it:** reach for this when a director says something like:
- "Make the logo pop on the beat"
- "Add a scale punch every beat, snapped to the grid"
- "Accent this on beat 2 and beat 4 only"

**How to build it:**
- `vb.Grid.b(beat)`
- `vb.spring_at(f, fps, **vb.damped(...))`
- `GRID.frames_per_beat`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/pop-on-the-beat.py` — read it before writing something similar from scratch.

### Character motion

**What it looks like:** Anticipation, squash and stretch, and follow-through. A hopping shape anticipates before it leaps (a crouch), stretches in the air, squashes on landing, and settles with a little follow-through — the full vocabulary from the animator's handbook, timed in frames.

**When to use it:** reach for this when a director says something like:
- "Give this hop some anticipation and squash and stretch"
- "Make the landing squash, then settle with follow-through"
- "This motion feels flat; add some character to it"

**How to build it:**
- `vb.interpolate`
- `vb.spring_at(f, fps, **vb.damped(0.22, hz=2.2))  # follow-through`
- `frame-level timing in reference/motion.md`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/character-motion.py` — read it before writing something similar from scratch.

### Overlap transitions

**What it looks like:** One segment slides over the outgoing one — no hard cut. Instead of a hard cut, the next segment starts on its own beat while the one before it keeps drawing underneath for a few more frames: a transition, built from `Segment(overlap=k)`, not a crossfade bolted on.

**When to use it:** reach for this when a director says something like:
- "Transition between these, not a hard cut"
- "Slide the end card in over the previous scene (overlap 1 beat)"
- "Keep the outgoing segment visible while the next one arrives"

**How to build it:**
- `vb.Segment(..., overlap=k)`
- `Timeline.live(n) -> Shots back to front`
- `Shot.exit`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/overlap-transitions.py` — read it before writing something similar from scratch.

## Type and data

### Kinetic typography

**What it looks like:** Balanced wrapping, word-by-word reveal, live weight. A headline wraps with balanced line breaks, reveals word by word, and its variable-font weight itself animates in — all real text layout, not an image of text.

**When to use it:** reach for this when a director says something like:
- "Reveal this headline word by word, balanced wrapping"
- "Animate the weight in as it lands (thin to bold)"
- "Make the type itself the motion here"

**How to build it:**
- `text.wrap(copy, font, width, balance=True)`
- `vb.Font(..., weight=interpolated)`
- `text.draw`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/kinetic-typography.py` — read it before writing something similar from scratch.

### Numbers that count up

**What it looks like:** A hero stat counts from zero to its final value. A big number counts up to its final value on a spring, the way a benchmark or a result should land: with weight, not just appearing.

**When to use it:** reach for this when a director says something like:
- "Count this number up to 2.4x"
- "Make the stat count up as it lands, not just appear"
- "Count up to the final value over the first second"

**How to build it:**
- `vb.spring_at / vb.interpolate drives the displayed value`
- `f'{value * min(1, p):.1f}'`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/counting-numbers.py` — read it before writing something similar from scratch.

### Bar charts

**What it looks like:** Bars grow on the beat, each with a direct label. A bar chart grows its bars on their own beats, with the value labelled directly at the end of each bar (not a legend) so it reads correctly even without colour.

**When to use it:** reach for this when a director says something like:
- "Chart these as bars growing on the beat, direct labels"
- "No legend — label each bar directly"
- "Grow the hero bar last so it lands on the verdict"

**How to build it:**
- `cv.rect(..., radius=..., alpha=...)`
- `vb.spring_at for bar growth`
- `text.draw for direct labels`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/bar-charts.py` — read it before writing something similar from scratch.

### Gauges and rings

**What it looks like:** An arc fills to a reading, with a readout in the centre. A ring gauge sweeps from empty to its reading as an arc, with the number centred inside it — the shape for a single score, percentage or level rather than a comparison.

**When to use it:** reach for this when a director says something like:
- "Show this as a ring gauge filling to 72%"
- "Use an arc readout, not a bar, for a single score"
- "Sweep the gauge in on the beat"

**How to build it:**
- `cv.arc(cx, cy, r, a0, a1, colour, width=...)`
- `cv.sector(...)`
- `vb.spring_at drives the sweep angle`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/gauges-and-rings.py` — read it before writing something similar from scratch.

## Imagery and camera

### Camera on a screenshot

**What it looks like:** A window pans and zooms across a captured screen. A camera window pans and zooms across a (generated) screenshot, with a navbar strip pinned to the top of the window while the page itself scrolls underneath it.

**When to use it:** reach for this when a director says something like:
- "Pan and zoom across this screenshot, pin the navbar"
- "Push in on the pricing table, then pan down"
- "Keep the header pinned while the camera scrolls the page"

**How to build it:**
- `cv.view(img, box, center=, scale=, radius=)`
- `vb.log_lerp(a, b, p)  # even zoom`
- `view.pin(src, y=box.y)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/camera-on-a-screenshot.py` — read it before writing something similar from scratch.

### Redrawn product UI

**What it looks like:** A crisp vector screen, redrawn from measured blocks. A product screen redrawn as vector shapes and real text instead of a captured bitmap: crisp at any size, built from measured blocks stacked with `Box.stack`.

**When to use it:** reach for this when a director says something like:
- "Redraw this screen instead of using a screenshot"
- "Rebuild the settings panel as crisp vector UI"
- "Keep this sharp at every size — redraw it, don't capture it"

**How to build it:**
- `Box.stack(heights, gap=..., align="top")`
- `cv.rect / cv.outline / text.draw for each block`
- Read `skill/make-a-video/reference/redrawn-ui.md`.

**Worked example:** `examples/capabilities/redrawn-product-ui.py` — read it before writing something similar from scratch.

### Image treatments

**What it looks like:** Cover and contain crops, rounded clips, soft shadows. The same generated image shown cover-cropped, contain-fitted, clipped to a rounded rect and lifted with a soft shadow — the box-model moves for putting a picture in a layout.

**When to use it:** reach for this when a director says something like:
- "Cover-crop this image into the card"
- "Fit it contain, with rounded corners and a soft shadow"
- "Give this picture a drop shadow, like a card"

**How to build it:**
- `Box.cover(w, h)`
- `Box.contain(w, h)`
- `cv.clip(x, y, w, h, radius=...)`
- `cv.shadow(...)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/image-treatments.py` — read it before writing something similar from scratch.

### Generated art

**What it looks like:** Cairo paths and gradients, seeded so they repeat. A procedural pattern drawn straight from cairo paths and a gradient, from a seeded random source so the same look renders the same way every time — no stock art, no network.

**When to use it:** reach for this when a director says something like:
- "Generate a background pattern, not a stock image"
- "Use a seeded procedural pattern so it renders identically"
- "Draw this as paths and a gradient, not a bitmap"

**How to build it:**
- `cv.ctx  # raw cairo Context`
- `cairo.LinearGradient / RadialGradient`
- `random.Random(seed)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/generated-art.py` — read it before writing something similar from scratch.

### 3D shots

**What it looks like:** A pre-rendered 3D clip, composited like any other image. A ManimGX 3D render (built offline, once) plays back as an ordinary clip inside the film — the same `cv.image` call as any other picture, just fed a frame from a 3D shot instead of a PNG.

**When to use it:** reach for this when a director says something like:
- "Open on a 3D shot of the product, then cut to the UI"
- "Use the orbiting 3D render as the opening shot"
- "Composite the 3D clip behind the headline"

**How to build it:**
- `vb.Clip(path)`
- `clip.frame(local_frame)`
- `cv.image(clip.frame(n), x, y, w, h)`
- Read `skill/make-a-video/reference/3d.md`.

**Worked example:** `examples/capabilities/orbit-3d.py` — read it before writing something similar from scratch.

## Timing, sound and formats

### Cuts locked to the music

**What it looks like:** Hard cuts land exactly on the beat, with a music bed. A music bed drives the cut points directly: every segment starts on a beat of the grid, so the hard cuts land on the music instead of merely sitting near it.

**When to use it:** reach for this when a director says something like:
- "Cut this on the beat, with a music bed under it"
- "Lock the hard cuts to the grid, 120 bpm"
- "Add a placeholder music bed and cut to it"

**How to build it:**
- `vb.Audio(path, gain_db=..., fade_out_frames=...)`
- `skill's make_track.py synth(bpm, beats, ...)`
- `Segment starts are beats, so cuts are on-grid by construction`
- Read `skill/make-a-video/reference/music.md`.

**Worked example:** `examples/capabilities/beat-lock.py` — read it before writing something similar from scratch.

### Every format, recomposed

**What it looks like:** One scene, laid out separately for three shapes. The same scene laid out three separate ways — 9:16, 16:9 and 1:1 — each from its own per-format layout table, not one layout cropped three ways.

**When to use it:** reach for this when a director says something like:
- "Lay this out for 9:16, 16:9 and 1:1, not just one format"
- "Recompose this for square, not just crop it"
- "Give portrait its own layout table, not a cropped landscape one"

**How to build it:**
- `per_format(LAYOUTS, cv)`
- `one LAYOUTS entry per vb.Format, each computed from that format's own geometry`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/every-format.py` — read it before writing something similar from scratch.

### Seamless loops

**What it looks like:** A clip built to play forever with no visible seam. A continuously looping shot — phase driven purely by `n % length`, so the state at the last frame and the state at frame 0 are mathematically the same point in the cycle, not just visually close.

**When to use it:** reach for this when a director says something like:
- "Make this loop seamlessly"
- "This needs to play on repeat with no jump at the seam"
- "Drive the motion from a phase that wraps, so it loops cleanly"

**How to build it:**
- `phase = (n % length) / length`
- `vb.linear for phase/rotation`
- `LOOP = True  # tells check.py to grade the seam`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/seamless-loops.py` — read it before writing something similar from scratch.

