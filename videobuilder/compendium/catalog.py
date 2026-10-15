"""The compendium's registry: every seed component and recipe, the builder
sheet (`index_markdown` / `index_data`), and rendering previews to disk
(`build`), the way `videobuilder/capabilities.py` does for the capabilities
catalog.

    python -m videobuilder compendium index [--json]
    python -m videobuilder compendium build --out DIR [--only ID ...]
"""
import json
import math
import os

import videobuilder as vb

from . import kit
from .components import CATALOG
from .recipes import RECIPES

_BY_ID = {c.id: c for c in CATALOG}
_RECIPES_BY_ID = {r.id: r for r in RECIPES}


def get(id):
    return _BY_ID[id]


def ids():
    return tuple(c.id for c in CATALOG)


def kinds():
    seen = []
    for c in CATALOG:
        if c.kind not in seen:
            seen.append(c.kind)
    return tuple(seen)


def get_recipe(id):
    return _RECIPES_BY_ID[id]


def recipe_ids():
    return tuple(r.id for r in RECIPES)


# ---- building a Film from one component's preview, or a whole recipe ----

def _read_time_frames(grid, values, wps=3.0, lead=1.0):
    """Frames long enough for `skill/make-a-video/scripts/check.py`'s own
    read-time check (`lead` seconds plus `wps` words a second), counting
    words the same way it does: every string slot value, joined."""
    words = sum(len(v.split()) for v in values.values() if isinstance(v, str) and v)
    return math.ceil(grid.fps * (lead + words / wps))


def component_film(component, values=None):
    """A small `Film` previewing `component`: `values` (default: the
    component's own sample) filled in, timed at the compendium's default
    tempo for its own midpoint beat length (or longer, if its sample copy
    needs more than that to read).

    A `transition` component has no neighbouring shot to preview it with, so
    it gets two segments of its own instead of one: `from` holds alone, then
    `to` takes over and overlaps `from` for its own entire length -- a real
    `Segment(overlap=...)`, the same shape `build_recipe_film` gives it
    between two real neighbours, not a one-off for the preview alone. Both
    carry the full sample, so either one read alone still has enough time
    for all of it."""
    values = component.validate(component.sample if values is None else values)
    grid = kit.GRID
    lo, hi = component.beats
    if component.kind == 'transition':
        phase_frames = max(grid.b((lo + hi) / 4), _read_time_frames(grid, values))
        from_until = math.ceil(phase_frames / grid.frames_per_beat * 2) / 2  # the half-beat grid, rounded up
        beats = from_until + phase_frames / grid.frames_per_beat
        segments = [
            vb.Segment('from', 0, from_until, data=values),
            vb.Segment('to', from_until, beats, data=values, overlap=beats - from_until),
        ]
    else:
        frames = max(grid.b((lo + hi) / 2), _read_time_frames(grid, values))
        beats = frames / grid.frames_per_beat
        segments = [vb.Segment(component.id, 0, beats, data=values)]
    timeline = vb.Timeline(grid, segments, end=beats)

    def draw(n, cv):
        shots = timeline.live(n)
        if component.kind == 'transition':
            component.draw(cv, shots)
        else:
            component.draw(cv, shots[-1])

    fmts = tuple(kit.FORMATS[name] for name in component.formats)
    return vb.Film(draw=draw, timeline=timeline, formats=fmts, background=kit.BG)


def build_recipe_film(recipe):
    """Recipe -> an ordinary `videobuilder.Film`: its steps laid out in order
    on `recipe.bpm`'s grid, each a `Segment` whose `data` is that step's
    validated slot values, dispatched to its component's own `draw`. A
    `transition` step overlaps the one before it for its own full length
    (`Segment(overlap=...)`), rather than cutting to it, and is handed every
    shot live during that overlap (outgoing, then itself)."""
    grid = vb.Grid(fps=30, bpm=recipe.bpm)
    segments = []
    comp_map = {}
    at = 0.0
    for i, step in enumerate(recipe.steps):
        comp = get(step.component)
        lo, hi = comp.beats
        if not lo <= step.beats <= hi:
            raise ValueError(f"recipe {recipe.id!r}: step {i} ({step.component}) is {step.beats:g} beats; "
                             f'{step.component} supports {lo:g} to {hi:g}')
        for fmt in recipe.formats:
            if fmt not in comp.formats:
                raise ValueError(f"recipe {recipe.id!r}: format {fmt!r} isn't supported by {step.component}")
        values = comp.validate(step.slots)
        name = f'{i:02d}-{step.component}'
        overlap = step.beats if comp.kind == 'transition' else 0
        segments.append(vb.Segment(name, at, at + step.beats, data=values, overlap=overlap))
        comp_map[name] = comp
        at += step.beats
    timeline = vb.Timeline(grid, segments, end=at)

    def draw(n, cv):
        shots = timeline.live(n)
        comp = comp_map[shots[-1].name]
        if comp.kind == 'transition':
            comp.draw(cv, shots)
        else:
            comp.draw(cv, shots[-1])

    fmts = tuple(kit.FORMATS[name] for name in recipe.formats)
    return vb.Film(draw=draw, timeline=timeline, formats=fmts, background=kit.BG)


# ---- the index: a builder-facing sheet, markdown or JSON ----

def _slot_data(slot):
    return {'name': slot.name, 'type': slot.type, 'required': slot.required, 'hint': slot.hint,
           'max_length': slot.max_length, 'min_count': slot.min_count, 'max_count': slot.max_count}


def _component_data(c):
    return {'id': c.id, 'kind': c.kind, 'description': c.description, 'tags': list(c.tags),
           'formats': list(c.formats), 'beats': list(c.beats), 'slots': [_slot_data(s) for s in c.slots]}


def _jsonify(v):
    """`v` with every tuple turned into a list, recursively, so a round trip
    through JSON reproduces it exactly, and a slot value with no JSON form
    (an `Image`) turned into a short description instead."""
    if isinstance(v, vb.Image):
        return f'<image {v.w}x{v.h}>'
    if isinstance(v, (list, tuple)):
        return [_jsonify(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonify(x) for k, x in v.items()}
    return v


def _step_data(s):
    return {'component': s.component, 'beats': s.beats, 'slots': _jsonify(s.slots)}


def _recipe_data(r):
    return {'id': r.id, 'title': r.title, 'description': r.description, 'bpm': r.bpm,
           'formats': list(r.formats), 'steps': [_step_data(s) for s in r.steps]}


def index_data():
    """The whole index as plain JSON-safe lists and dicts (no tuples), so
    `json.loads(index_json()) == index_data()`."""
    return {'components': [_component_data(c) for c in CATALOG], 'recipes': [_recipe_data(r) for r in RECIPES]}


def index_json():
    return json.dumps(index_data(), indent=2) + '\n'


def _slot_line(s):
    bounds = ''
    if s.type == 'text':
        bounds = f', max {s.max_length} characters'
    elif s.type == 'images':
        bounds = f', {s.min_count} to {s.max_count} images'
    need = 'required' if s.required else 'optional'
    return f"- `{s.name}` ({s.type}{bounds}, {need}): {s.hint}"


def index_markdown():
    """The builder-facing index: every component's id, kind, description,
    tags, formats, beats and slots, plus every recipe. Grouped by kind."""
    lines = ['# Compendium', '',
             'Pre-built, good-looking components. Pick one by its description and tags, fill its slots from '
             "their types and hints, and drop it into a film -- there is no need to read a component's code.",
             '']
    for kind in kinds():
        lines.append(f'## {kind}')
        lines.append('')
        for c in CATALOG:
            if c.kind != kind:
                continue
            lines.append(f'### `{c.id}`')
            lines.append('')
            lines.append(c.description)
            lines.append('')
            lines.append(f"- tags: {', '.join(c.tags)}")
            lines.append(f"- formats: {', '.join(c.formats)}")
            lines.append(f'- beats: {c.beats[0]:g} to {c.beats[1]:g}')
            lines.append('- slots:')
            for s in c.slots:
                lines.append('  ' + _slot_line(s))
            lines.append('')
    lines.append('## Recipes')
    lines.append('')
    for r in RECIPES:
        lines.append(f'### `{r.id}`: {r.title}')
        lines.append('')
        lines.append(r.description)
        lines.append('')
        lines.append(f'- bpm: {r.bpm:g}')
        lines.append(f"- formats: {', '.join(r.formats)}")
        lines.append('- steps:')
        for s in r.steps:
            lines.append(f'  - `{s.component}` ({s.beats:g} beats): {_jsonify(s.slots)}')
        lines.append('')
    return '\n'.join(lines) + '\n'


# ---- building previews: every component's sample, every recipe ----

def _save_poster(cv, path, quality=82):
    from PIL import Image
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    im = Image.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
    im.convert('RGB').save(path, 'JPEG', quality=quality)


def _poster_frame(film):
    """70% into the shot live at the middle frame: a recipe's middle often lands
    on a step's first frame, before anything in it has entered."""
    mid = film.frames // 2
    if film.timeline is None:
        return mid
    shot = film.timeline.live(mid)[-1]
    return min(film.frames - 1, mid - shot.f + int(shot.length * 0.7))


def _loop_window(film, pad_seconds=0.5, still_threshold=1.0, scale=0.08):
    """A transition's preview `film`'s own move, found by rendering the `to`
    segment frame by frame and watching where consecutive frames stop
    differing. The `to` segment (see `component_film`) overlaps `from` for
    its *entire* length, which for most transitions is far longer than the
    move itself: once the incoming card settles, holding it for the rest of
    the overlap is static. The move always starts at the first frame of `to`
    in this preview (`_transition_util.start_frame` returns 0 when both
    phases carry the same sample data), so the search only needs to find
    where it ends. Padded by `pad_seconds` on each side and clamped to the
    film, in seconds: `[start, end)` for the feed to loop instead of the
    whole clip."""
    grid = film.timeline.grid
    lo_f, span_hi_f = film.timeline.span('to')
    search_hi_f = min(span_hi_f, film.frames - 1)
    fmt = film.format()

    def pixels(n):
        cv = film.frame(n, fmt, scale=scale)
        cv.surface.flush()
        return bytes(cv.surface.get_data())

    move_end_f = lo_f
    prev = pixels(lo_f)
    for n in range(lo_f, search_hi_f):
        cur = pixels(n + 1)
        diff = sum(abs(a - b) for a, b in zip(prev, cur)) / len(prev)
        if diff > still_threshold:
            move_end_f = n + 1
        prev = cur

    pad_f = round(pad_seconds * grid.fps)
    lo_f, hi_f = max(0, lo_f - pad_f), min(film.frames, move_end_f + pad_f)
    return [grid.seconds(lo_f), grid.seconds(hi_f)]


def _render_one(film, out_dir, id, kind, jobs, crf, log):
    import time
    from ..render import render as _render
    loop = _loop_window(film) if kind == 'transition' else None
    results = []
    clips = []
    for fmt in film.formats:
        name = f'{id}-{fmt.name}'
        out_mp4 = os.path.join(out_dir, name + '.mp4')
        t0 = time.time()
        _render(film, out_mp4, fmt, jobs=jobs, crf=crf, log=log)
        _save_poster(film.frame(_poster_frame(film), fmt), os.path.join(out_dir, name + '.jpg'))
        results.append({'id': name, 'seconds': time.time() - t0, 'bytes': os.path.getsize(out_mp4)})
        clips.append({'id': id, 'kind': kind, 'format': fmt.name, 'loop': loop})
    return results, clips


def build(out_dir, only=None, jobs=None, crf=30, log=None):
    """Render every component's sample preview and every recipe (or just the
    ids in `only`) to `<out_dir>/<id>-<format>.mp4` and `.jpg`, and write
    `<out_dir>/index.json`: `{"clips": [...]}`, one entry per clip built, each
    `{id, kind, format, loop}` -- `kind` is the component's own kind, or
    `'recipe'`; `loop` is a transition's `[start, end]` in seconds (see
    `_loop_window`), else null. Returns a list of {id, seconds, bytes} for the
    clips built."""
    import sys
    from ..atomic import write_json_atomic
    log = log or sys.stderr
    if only is not None:
        unknown = set(only) - set(ids()) - set(recipe_ids())
        if unknown:
            raise ValueError(f'unknown id(s): {", ".join(sorted(unknown))}')
    os.makedirs(out_dir, exist_ok=True)
    results, clips = [], []
    for c in CATALOG:
        if only is not None and c.id not in only:
            continue
        r, cl = _render_one(component_film(c), out_dir, c.id, c.kind, jobs, crf, log)
        results += r
        clips += cl
    for r_ in RECIPES:
        if only is not None and r_.id not in only:
            continue
        r, cl = _render_one(build_recipe_film(r_), out_dir, r_.id, 'recipe', jobs, crf, log)
        results += r
        clips += cl
    write_json_atomic(os.path.join(out_dir, 'index.json'), {'clips': clips}, indent=2, newline=True)
    return results
