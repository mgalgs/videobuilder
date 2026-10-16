<!-- GENERATED from videobuilder/capabilities.py by `sheet_markdown()`. Do not hand-edit;
     regenerate with `python -m videobuilder capabilities sheet > skill/make-a-video/reference/capabilities.md` after changing the catalog. -->
# Capabilities catalog

What videobuilder can already do, with a worked example for each. Reach for one of these before inventing an effect. Adding a capability later means adding one entry to `CATALOG` in `videobuilder/capabilities.py` and one demo film beside the others in `examples/capabilities/`; this file and the `/capabilities` page are both generated from that single catalog.

## Motion

### Eased entrances

**What it looks like:** The named motion tokens, compared side by side. Five named easing curves — videobuilder's motion tokens — each sliding a chip into place on its own row, so their character is easy to tell apart: a fast settle, a restrained glide, a small overshoot.

**When to use it:** reach for this when a director says something like:
- "Ease this in fast, then let it settle gently"
- "Use a restrained entrance, nothing bouncy"
- "Make the exit quicker than the entrance, and a little brisker"

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
- "Use a firm landing, no bounce"
- "Make it bouncier, more cartoonish"

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

### Puppet motion

**What it looks like:** One cut-out picture of a character, alive through movement alone. A cartoon character drawn once, as a single picture with its background cut out, comes alive without a single new drawing: it breathes, sways and bobs, then crouches, hops, stretches in the air, squashes as it lands and settles -- every move pivoting on its feet, so it stays planted on the ground. All it needs is one cut-out picture: upload one, or make one in the editor's Pictures panel with "Cut out the background" on. The video moves the picture you give it; nothing is drawn at render time.

**When to use it:** reach for this when a director says something like:
- "Make the mascot feel alive, breathing and swaying a little"
- "Have the character hop, with a crouch first and a squash when it lands"
- "Animate my fox picture so it doesn't just sit there"

**How to build it:**
- `FOX = vb.Puppet({'idle': 'fox.png'}, height=360)  # at import: downscaled once, feet measured`
- `FOX.draw(cv, pose, x, ground_y, sx=, sy=, lean=, angle=)  # every transform about the feet`
- `FOX.breath(n, period)  # a slow breath; a whole number of periods per loop`
- `vb.spring_at(f, fps, **vb.damped(0.25, hz=2.4))  # the landing settle`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/puppet-motion.py` — read it before writing something similar from scratch.

### Pose swaps

**What it looks like:** A character snaps between drawn poses on the beat, old-cartoon style. The limited-animation trick from old cartoons and anime: a character holds a drawn pose, snaps to the next on a beat with a quick two- or three-frame pop and a few speed lines, and holds again -- talking by flapping between a closed and an open mouth on the syllables, blinking now and then, and breathing under every hold so it never looks frozen. It needs several poses of the same character, each with its background cut out: upload 3-6 poses drawn elsewhere, or make each one from the first picture as a reference (the Pictures panel can't do that by itself yet). Poses that only change the mouth or the eyes swap without a jump; the others are lined up by their feet. The video swaps the pictures you give it; nothing is drawn at render time.

**When to use it:** reach for this when a director says something like:
- "Make the character talk, mouth flapping on the words"
- "Snap to the pointing pose on the beat, with a little pop"
- "Have it blink now and then so it looks alive"
- "Use my fox poses like an old cartoon: hold, snap, hold"

**How to build it:**
- `FOX = vb.Puppet({'idle': ..., 'talk': ..., 'blink': ..., 'point': ...}, height=340)  # poses lined up by their feet`
- `pose, age = FOX.pose_at(n, [(0, 'idle'), (15, 'talk'), (19, 'idle'), (45, 'point')])  # holds`
- `age 0-2: a squash, overshoot, settle pop on the snap`
- `FOX.draw(cv, pose, x, ground_y, sx=, sy=)`
- `FOX.breath(n, period)  # under every hold`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/pose-swaps.py` — read it before writing something similar from scratch.

### Overlap transitions

**What it looks like:** One segment slides over the outgoing one — no hard cut. Instead of a hard cut, the next scene starts on its own beat while the one before it keeps drawing underneath for a few more frames: a transition built into the timeline itself, not a crossfade bolted on.

**When to use it:** reach for this when a director says something like:
- "Transition between these, not a hard cut"
- "Slide the end card in over the previous scene, overlapping for a beat"
- "Keep the previous scene visible while the next one arrives"

**How to build it:**
- `vb.Segment(..., overlap=k)`
- `Timeline.live(n) -> Shots back to front`
- `Shot.exit`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/overlap-transitions.py` — read it before writing something similar from scratch.

### Drawn-on diagram

**What it looks like:** A whiteboard diagram drawn stroke by stroke, pen tracked by camera. A small whiteboard diagram -- boxes, arrows, an icon, handwritten-looking labels -- draws on stroke by stroke with a little hand jitter, the camera tracking the pen across a board bigger than the frame, ending in a pull-back that shows the whole board at once.

**When to use it:** reach for this when a director says something like:
- "Draw this diagram on stroke by stroke, like a whiteboard"
- "Track the camera on the pen as it draws, then pull back"
- "Give the lines a bit of hand-drawn wobble, not perfectly straight"

**How to build it:**
- `videobuilder.paths.reveal(points, fraction)`
- `videobuilder.paths.jitter(points, seed)`
- `cv.layer(dx=.., dy=.., scale=..)  # the tracking camera`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/drawn-on-diagram.py` — read it before writing something similar from scratch.

### Shape morph

**What it looks like:** One outline smoothly becomes the next, not a cut. A circle turns into a document icon and back, its outline resampled to match point for point and interpolated with a smooth ease while its colour travels along -- one idea turning into the next instead of a hard cut between two shapes.

**When to use it:** reach for this when a director says something like:
- "Don't cut between these icons, morph one into the other"
- "Turn the circle into the document shape smoothly"
- "Let the colour shift as the shape changes, not just the outline"

**How to build it:**
- `videobuilder.paths.morph(a, b, t, closed=True)`
- `videobuilder.paths.draw(cv, points, colour, fill=True)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/shape-morph.py` — read it before writing something similar from scratch.

## Type and data

### Kinetic typography

**What it looks like:** Balanced wrapping, word-by-word reveal, live weight. A headline wraps with balanced line breaks, reveals word by word, and its variable-font weight itself animates in — all real text layout, not an image of text.

**When to use it:** reach for this when a director says something like:
- "Reveal this headline word by word, with neatly balanced line breaks"
- "Animate the weight in as it lands, thin to bold"
- "Make the type itself the motion here"

**How to build it:**
- `text.wrap(copy, font, width, balance=True)`
- `vb.Font(..., weight=interpolated)`
- `text.draw`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/kinetic-typography.py` — read it before writing something similar from scratch.

### Word-timed captions

**What it looks like:** Captions that follow the words as they are spoken. A speaker's words run along the bottom of the clip one short line at a time, each line measured to fit the frame: the word being spoken lights up in yellow as it is said, and a chosen keyword stays green, so the captions keep pace with the voice instead of sitting there as a block of text.

**When to use it:** reach for this when a director says something like:
- "Add captions that follow along word by word"
- "Highlight each word in yellow as it is said"
- "Make the word "mornings" stand out in green in the captions"

**How to build it:**
- `vb.captions.parse(text) / vb.captions.load(path)  # .vtt or .srt, word times kept`
- `track.slice(a, b).shift(at - a)  # a clip cut from a longer source`
- `vb.captions.draw(cv, track, t, keywords={...}, font=..., safe=...)`
- Read `skill/make-a-video/reference/captions.md`.

**Worked example:** `examples/capabilities/word-timed-captions.py` — read it before writing something similar from scratch.

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

### Self-drawing line chart with a callout

**What it looks like:** Axes first, the line draws itself on, then one point is called out. Honest axes appear first, then every series draws itself on along its own path -- the background series in grey, only the hero series in colour -- and once it lands, one callout (a dot, a leader line and a short label) points at the single point that matters.

**When to use it:** reach for this when a director says something like:
- "Draw the axes first, then let the line draw itself on"
- "Keep the other lines grey, only highlight the hero line"
- "Call out the final point with a dot and a short label"

**How to build it:**
- `videobuilder.paths.reveal(points, fraction)`
- `videobuilder.paths.draw(cv, points, colour, width=...)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/line-chart-callout.py` — read it before writing something similar from scratch.

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

**What it looks like:** A crisp vector screen, redrawn from measured blocks. A product screen redrawn as vector shapes and real text instead of a captured bitmap: crisp at any size, built from measured blocks stacked edge to edge.

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
- "Use a generated pattern that renders exactly the same every time"
- "Draw this as paths and a gradient, not a bitmap"

**How to build it:**
- `cv.ctx  # raw cairo Context`
- `cairo.LinearGradient / RadialGradient`
- `random.Random(seed)`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/generated-art.py` — read it before writing something similar from scratch.

### 3D shots

**What it looks like:** A pre-rendered 3D clip, composited like any other image. A pre-rendered 3D render (built offline, once) plays back as an ordinary clip inside the film, composited exactly like any other picture, just fed a frame from a 3D shot instead of a still image.

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

### Hard-light sweep

**What it looks like:** A hard-edged band of light sweeps across the shot. A dim, shadowed version of the scene sits underneath a warm, lit version clipped to a hard-edged band -- a slanted shaft of light with window-mullion bars cut out of it -- that sweeps across the frame.

**When to use it:** reach for this when a director says something like:
- "Sweep a hard beam of sunlight across this shot"
- "Add a dramatic light sweep, like light through a window"
- "Make part of the scene glow as a band of light passes over it"

**How to build it:**
- `cv.ctx path + even-odd fill_rule for the clip`
- `cv.image(img, *box) for the dim and lit layers`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/hard-light-sweep.py` — read it before writing something similar from scratch.

### Comic-book halftone

**What it looks like:** Dot-fill shading, thick ink outlines, a jittering burst callout. A flat-colour shape shaded with a halftone dot fill, a thick ink outline, and a jittering starburst callout with a short word -- the dot plate sits a couple of pixels off from the ink, the way an old four-colour print misregisters its plates.

**When to use it:** reach for this when a director says something like:
- "Give this a comic-book look, dot shading and thick outlines"
- "Add a jittering burst callout with a short word"
- "Let the colour plate sit slightly off from the linework, like an old print"

**How to build it:**
- `videobuilder.halftone_pattern(pitch, radius, angle=.., color=..)`
- `cv.arc(..., width=..)  # the thick outline`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/comic-halftone.py` — read it before writing something similar from scratch.

### Pixel-art layer

**What it looks like:** A scene rendered blocky, 8-bit style, with stepped motion. A small scene -- sky, ground, a walking character, a HUD label -- is drawn at a fraction of the frame's resolution and scaled back up with blocky nearest-neighbour filtering, its motion held two frames at a time for an 8-bit, stop-motion feel; any text drawn into the layer pixelates with it.

**When to use it:** reach for this when a director says something like:
- "Render this as retro 8-bit pixel art"
- "Make the motion choppier, like an old game, not smooth 30fps"
- "Keep the on-screen text blocky and pixelated too, not crisp"

**How to build it:**
- `cv.pixelated(factor)`
- `stepped_n = (n // 2) * 2  # 15fps motion on a 30fps film`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/pixel-art-layer.py` — read it before writing something similar from scratch.

### Paper collage

**What it looks like:** Torn-paper headlines, cut-paper objects, a stamp, and a rip-open transition. The editorial paper-cutout explainer look: a grey-beige paper wall under still window light, a headline printed on a torn scrap, a cut-paper object whose soft shadow follows its outline, hand-drawn marks and a red rubber stamp, all moving in stop-motion steps -- then the wall rips open from the middle, its flaps curling back to reveal one accent colour with the next scene pasted on it. Objects are drawn shapes or images you supply, never generated.

**When to use it:** reach for this when a director says something like:
- "Make this look like a paper collage explainer, all torn paper and cut-outs"
- "Put each headline on a torn strip of paper"
- "Rip the paper open to get to the next scene"
- "Stamp NO PROOF across it in red"
- "Make the paper pieces move like stop-motion, a bit choppy"

**How to build it:**
- `paths.torn(outline, seed, amount=5)  # a torn edge, baked once at import`
- `cv.shape_shadow(points, dx=.., dy=.., blur=..)  # a lift shadow that follows the shape`
- `vb.paper_grain(w, h, seed)  # with cairo.OPERATOR_SOFT_LIGHT`
- `stepped_n = n - n % 2  # paper held on twos`
- Read `skill/make-a-video/reference/api.md`.

**Worked example:** `examples/capabilities/paper-collage.py` — read it before writing something similar from scratch.

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

### Footage with its own sound

**What it looks like:** A clip plays with its sound while the music dips under it. A speaker clip cuts in and plays with its own sound, mixed with the music bed: the music dips under the speech while the clip plays and comes back up when it ends, and the whole mix is evened out to one loudness, so the voice is easy to hear without the music ever cutting out.

**When to use it:** reach for this when a director says something like:
- "Use this clip with its sound, and bring the music down under the speech"
- "Let us hear the speaker, then bring the music back up after"
- "Cut between the interview clips and the graphics, with the music underneath"

**How to build it:**
- `vb.Sound(path, at=, start=, frames=, fade_in_frames=, fade_out_frames=)`
- `ft = vb.footage(TIMELINE, 'segment', start=seconds)  # picture and sound in sync`
- `clip.frame(clip.frame_at(ft.seconds_at(n)))`
- `ft.sound(path) -> Film(sounds=(...))`
- `vb.Audio(music, duck_db=-12)  # the music ducks while a sound plays`
- Read `skill/make-a-video/reference/footage.md`.

**Worked example:** `examples/capabilities/footage-with-sound.py` — read it before writing something similar from scratch.

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

**What it looks like:** A clip built to play forever with no visible seam. A continuously looping shot, its motion driven by a repeating cycle, so the state at the last frame and the state at frame 0 are mathematically the same point in the cycle, not just visually close.

**When to use it:** reach for this when a director says something like:
- "Make this loop seamlessly"
- "This needs to play on repeat with no jump at the seam"
- "Drive the motion in a cycle that wraps around cleanly, with no jump at the seam"

**How to build it:**
- `phase = (n % length) / length`
- `vb.linear for phase/rotation`
- `LOOP = True  # tells check.py to grade the seam`
- Read `skill/make-a-video/reference/motion.md`.

**Worked example:** `examples/capabilities/seamless-loops.py` — read it before writing something similar from scratch.

