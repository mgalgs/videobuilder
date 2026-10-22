# Techniques

A registry of named motion-design techniques -- easing curves, transitions,
text reveals, looks, camera moves and more -- each with its own short demo.
When a brief asks for a named move ("bounce it in", "dip to black", "make the
title decode"), look here before writing it yourself.

## Finding one

```sh
python -m videobuilder techniques index                    # the full sheet, grouped by family then group
python -m videobuilder techniques index --family transitions
python -m videobuilder techniques index --json
```

Each entry gives the id, the name, a one-line definition, everyday phrasings
people use for it, and `api`: the dotted names a film calls. To see the demos,
`python -m videobuilder techniques build --out DIR [--only ID]...` renders
each to `DIR/<id>.mp4` (repeat `--only` for several ids) and writes a gallery,
`DIR/index.html`.

## Using one in a film

Call what `api` names. Some are videobuilder's own functions
(`vb.ease_out_back`); the rest live in the technique's module,
`videobuilder/techniques/<family>/<id with - as _>.py`, and are imported from
there:

```python
import videobuilder as vb
from videobuilder.techniques.principles.bounce_ease_out import bounce_ease_out
from videobuilder.techniques.transitions.dip_to_black import dip_to_black

y = vb.interpolate(shot.f, [0, 24], [-200, 400], ease=bounce_ease_out)

# A transition is `transition(cv, a, b, p)`: a and b draw the outgoing and
# incoming scenes, p runs 0 -> 1. Call it while two shots are live in an overlap:
old, new = TIMELINE.live(n)
dip_to_black(cv, lambda c: scene_a(c, old), lambda c: scene_b(c, new), new.f / OVERLAP_FRAMES)
```

The module's own `draw` is a worked demo of the technique alone: read it
before using the technique for the first time.

## Adding one

One technique is one new file, `videobuilder/techniques/<family>/<id with - as _>.py`,
ending in `TECHNIQUE = Technique(...)` (see `videobuilder/techniques/schema.py`);
nothing else is edited. Copy one of the four worked examples:
`principles/ease_out_back.py` (names an existing API), `principles/bounce_ease_out.py`
(new code), `transitions/dip_to_black.py` (a transition),
`typography/scramble_decode.py` (a text reveal). Demos use the shared kit,
`videobuilder/techniques/_demo.py`. Definitions and phrasings are written in
our own words. It is done when this passes:

```sh
python3 -m unittest tests.test_techniques.EachTechnique.test_<id with - as _>
```
