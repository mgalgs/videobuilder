# videobuilder: execution plan

## 0. Charter

**Goal.** A small, dependency-light Python framework for making videos in code: product reels, explainers and benchmark/result videos. A general "make a video" Claude Code skill (in `~/src/claude-config`) will be built on it. It replaces Remotion as the default; Remotion remains an option only where a film is mostly HTML/CSS layout or needs a web player or cloud rendering, and only where its licence covers the user.

**Why this exists.** A sandbox rebuilt a real 32s, 9:16 product reel (screen captures, music, beat-locked cuts, eased motion, real fonts) without Remotion. Every cut landed on the same frame, audio alignment was exact, the springs and eases matched to 1e-9, and text was within 2 px. It rendered in ~14s against Remotion's ~142s. The no-library SVG route (`rsvg-convert`) was rejected: it can't measure text, and it re-decodes large images every frame.

**Principles.**
- **Framework, not style.** It provides mechanisms (timeline, easing, drawing, text, layout, render, preview). It never dictates visual style, palettes, accessibility conventions or brand rules. Those belong to the films and skills that use it, layered on top.
- **Pure frames.** `draw(n, canvas)` renders any frame on its own, deterministically. Parallel chunked rendering, stills and previews all depend on this.
- **Dependencies:** ffmpeg, cairo, Pango (via PyGObject) and Pillow, all ordinary distro packages. Anything heavier (Chromium for HTML panels, whisper for captions) is optional, behind a module that imports it lazily.
- **Beat-aware time.** The timeline is a grid (fps, BPM, head trim), with segments in beats and JS-style round-half-up. Banker's rounding moves cuts.

**Known traps the framework owns** (each found the hard way):
- Remotion's `spring()` treats any damping ratio ≥ 1 as critical. Our springs are real physics; use `critical(k)` to get Remotion's "settle" curve.
- Python's `round()` rounds halves to even. Use `round_half_up` for frame math.
- With ffmpeg's concat demuxer, joins drift unless the chunk length × (1/fps) is exact in µs. The renderer rejects drifting chunk sizes.
- CSS adds letter-spacing after the last letter too; Pango doesn't.

**What each phase is for.** Phase 1 turns the imported code into a project you can actually author in: a preview, layouts and tests. Phase 2 proves it on real films by porting sonlet-videos. Phase 3 builds the skill. The skill must not start before phase 2, because a skill built on an unproven API teaches the wrong API.

## 1. Phases

| # | Phase | State |
|---|---|---|
| 1 | **Project core:** package `videobuilder` (rename from `motion`), `pyproject.toml`, CLI (`render`, `still`, `preview`), **live preview** (frame server, scrubber, hot reload, timeline overlay), **layout** module (row/column/center/anchor/fit) with **per-format layout tables** (9:16 / 16:9 / 1:1 from one film), a generic example film with no Sonlet assets, unit tests (ease, timeline) and golden-still tests, README | done |
| 2 | **Prove it:** port the sonlet-videos party-templates reel onto the package (sonlet-videos depends on videobuilder), then render all three formats from one film; add `media` (video clips, multi-track audio) only if a real film needs it | done |
| 2b | **Close the gaps the port found:** timeline groups and overlaps (`Shot`s from `Timeline.live`), `text.box`/`draw_in`, `Canvas.view` camera with `pin`, and the small edges (short/alpha hex colours, `outline`/`line`, `wrap` forced breaks, `vb.main(__file__)` and `load_module`, one-table-per-format layouts, grid-derived audio trim, per-format sheet tiles, image cache eviction, invisible layers keep their transform). Each proven in the party-templates film with byte-identical frames | done |
| 3 | **Skill:** the "make a video" skill in claude-config: scaffolding a film, the authoring loop (preview → contact sheet → render), music and beat-locking, and the review checks (read times, cuts on grid, ffprobe). Style-neutral | planned |
| 4 | Optional modules as needed: `html` (Chromium screenshot of a static panel → image), `charts`, captions | as needed |

**State (2026-10-06):** phases 1, 2 and 2b are done. The party-templates reel renders 9:16, 16:9 and 1:1 from one film on videobuilder, its timeline grouped and overlapping, with 112 passing tests. Phase 3 (the skill) is next. Phase 1 was done on branch `phase1-core`. The package, CLI (`render`/`still`/`sheet`/`preview`), hot-reloading preview, `layout`, `examples/tour.py` in three formats, and 65 passing tests are in place. Audio in the preview is deferred.

## 2. References
- The comparison report and its evidence: the sonlet-videos repo, branch `video-pt-nolib`, `nolib/REPORT.md`.
