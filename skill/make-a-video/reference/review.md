# Review checklist

Run before calling a film done. Every box gets checked on every format.

## Automatic: `check.py`

    PYTHONPATH=$VB python $SKILL/scripts/check.py film.py --video

- [ ] **0 failed.** It FAILs on:
  - read time: a segment shorter than 1 s + its words at 3 words/s;
  - a `cv.mark` box outside the format's `safe` box, or two marks
    overlapping (on the held frames: middle and three-quarter of each
    segment, plus `FILM.keyframes`; `--every N` checks every Nth frame);
  - ffprobe: not H.264 / yuv420p, wrong size or fps, frame count not
    exactly `FILM.frames`, duration off by half a frame, audio missing,
    not AAC, or not as long as the picture.
- [ ] **WARNs judged.** A picture jump off the cut grid (a flash, a
  segment drawing a frame early or late): look at `still c-1 c c+1`. Music
  off the beat: apply the suggested `head_trim`, or justify it.
- [ ] Every block of copy, chart and image is marked; with no marks, the
  safe-area check checks nothing (it warns).

## By eye: contact sheets and stills

    PYTHONPATH=$VB python film.py sheet --format all

Read each sheet PNG (and `sheet --every 10` for motion):

- [ ] Every segment shows what the storyboard says, in every format.
- [ ] No text clipped by the frame or a box, no line too long or too short
  for its width, no widow word on a line of its own when it could balance.
- [ ] Nothing overlaps that shouldn't, including during transitions.
- [ ] No empty frame that isn't meant to be (a segment's first frame before
  its entrance is fine for a beat, not for a second).
- [ ] Each format is laid out for its shape, not a scaled copy.
- [ ] The intended font is drawn (not a fallback), at a size that reads
  at the delivery size (look at a `still` at `--scale 0.5` for a phone).
- [ ] Colours and type are the brief's, or flagged to the user as your
  placeholders.

## The deliverable

- [ ] `<film>-<format>.mp4` per format asked for.
- [ ] `assets/README.md` lists every asset, its source and licence; fonts
  are vendored with their licence files.
- [ ] Report to the user: paths, duration, formats, the storyboard, choices
  and placeholders, and the check output.
