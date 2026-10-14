# Style for the capabilities catalog's demo films

One palette and one type system across every demo in this directory, so the
capabilities page reads as one set rather than twenty unrelated samples.
Shared constants and helpers live in `_kit.py`; every demo imports from it
instead of inventing its own numbers.

## Palette

| role | colour | notes |
|---|---|---|
| background | `#14151a` | near-black, close to the editor's own `#0d0d10`/`#181b20` |
| ink (primary text) | `#f4f4f2` | off-white; ~17:1 on the background |
| muted (secondary text) | `#9397a1` | ~6.3:1 on the background |
| accent | `#ef5b4c` | warm red-orange, close to the director's own `--accent` |
| teal | `#4fc3b0` | second series/marker colour, chosen for contrast with the
  accent even for red-green colour blindness (hue separation, not just
  lightness) |
| line | `#2a2c33` | gridlines, dividers, faint strokes |

Small text never sits directly on a saturated fill (accent or teal): a
chip's label sits beside or below the colour, not inside it, so contrast
stays >= 4.5:1 everywhere. Direct chart/series labels are plain `ink` or
`muted` text next to the mark they describe, never colour-only.

## Type

- **Inter** (`examples/assets/Inter-Variable.ttf`) for every heading, label
  and body line.
- **SourceCodeVF** (`examples/assets/SourceCodeVF-Upright.otf`) for numerals
  that are the hero of a shot (counting numbers, chart values, gauge
  readouts) and for anything meant to read as data rather than copy.
- Sizes: ~40px/700 for a shot's title, ~22px/600 for a caption or chart
  label, ~96-140px for a hero number. `_kit.font(size, weight)` wraps
  `vb.Font('Inter', ...)`.

## Format and timing

- `_kit.FORMAT`: a custom 720x720 `vb.Format`, 30 fps. Every demo uses only
  this format.
- `_kit.GRID`: 120 bpm by default (15 frames/beat), so a 6-beat film is a
  clean 3.0 s loop. A demo that needs more room can pass its own `bpm` to
  `_kit.grid()`, but stays inside 2-4 s (60-120 frames).

## One hero move, and a loop that doesn't jump

Pick one move per demo (the thing the card's "what to tell the builder"
block asks for) and let everything else hold still while it reads.

Looping is designed in, not patched on afterwards: either the motion is a
true period (a rotation, a pulse, a camera drift) where frame 0 and the
last frame are the same point in the cycle by construction, or the demo
rests at an identical, quiet state at both ends (something enters, holds,
then leaves exactly as it came in, so the last few frames and the first
few frames read the same).

## Marks

Every visible block of copy, every chart/diagram element and every image
gets a `cv.mark(name, *box)` (`_kit.text_marked` and `_kit.rect_marked` do
both steps together) so `skill/make-a-video/scripts/check.py` can check it
against the safe area and against the other marks on screen.

## Colour-blind safety

Any chart or diagram with more than one series carries a direct label on
each bar/sector/line (not colour alone) and, where two series could be
confused by hue, a distinct shape or stroke style as well (filled vs.
outlined, circle vs. triangle).
