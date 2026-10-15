"""The compendium's registry: every seed component and recipe, the builder
sheet (`index_markdown` / `index_data`), and rendering previews to disk
(`build`), the way `videobuilder/capabilities.py` does for the capabilities
catalog.

    python -m videobuilder compendium index [--json]
    python -m videobuilder compendium build --out DIR [--only ID ...]
"""
import json
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

def component_film(component, values=None):
    """A small `Film` previewing `component`: one segment, `values` (default:
    the component's own sample) filled in, timed at the compendium's default
    tempo for its own midpoint beat length."""
    values = component.validate(component.sample if values is None else values)
    beats = (component.beats[0] + component.beats[1]) / 2
    grid = kit.GRID
    timeline = vb.Timeline(grid, [vb.Segment(component.id, 0, beats, data=values)], end=beats)

    def draw(n, cv):
        component.draw(cv, timeline.live(n)[-1])

    fmts = tuple(kit.FORMATS[name] for name in component.formats)
    return vb.Film(draw=draw, timeline=timeline, formats=fmts, background=kit.BG)


def build_recipe_film(recipe):
    """Recipe -> an ordinary `videobuilder.Film`: its steps laid out as hard
    cuts on `recipe.bpm`'s grid, each a `Segment` whose `data` is that step's
    validated slot values, dispatched to its component's own `draw`."""
    grid = vb.Grid(fps=30, bpm=recipe.bpm)
    segments = []
    draw_map = {}
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
        segments.append(vb.Segment(name, at, at + step.beats, data=values))
        draw_map[name] = comp.draw
        at += step.beats
    timeline = vb.Timeline(grid, segments, end=at)

    def draw(n, cv):
        shot = timeline.live(n)[-1]
        draw_map[shot.name](cv, shot)

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
            lines.append(f'  - `{s.component}` ({s.beats:g} beats): {s.slots}')
        lines.append('')
    return '\n'.join(lines) + '\n'


# ---- building previews: every component's sample, every recipe ----

def _save_poster(cv, path, quality=82):
    from PIL import Image
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    im = Image.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
    im.convert('RGB').save(path, 'JPEG', quality=quality)


def _render_one(film, out_dir, id, jobs, crf, log):
    import time
    from ..render import render as _render
    results = []
    for fmt in film.formats:
        name = f'{id}-{fmt.name}'
        out_mp4 = os.path.join(out_dir, name + '.mp4')
        t0 = time.time()
        _render(film, out_mp4, fmt, jobs=jobs, crf=crf, log=log)
        _save_poster(film.frame(film.frames // 2, fmt), os.path.join(out_dir, name + '.jpg'))
        results.append({'id': name, 'seconds': time.time() - t0, 'bytes': os.path.getsize(out_mp4)})
    return results


def build(out_dir, only=None, jobs=None, crf=30, log=None):
    """Render every component's sample preview and every recipe (or just the
    ids in `only`) to `<out_dir>/<id>-<format>.mp4` and `.jpg`. Returns a list
    of {id, seconds, bytes} for the clips built."""
    import sys
    log = log or sys.stderr
    if only is not None:
        unknown = set(only) - set(ids()) - set(recipe_ids())
        if unknown:
            raise ValueError(f'unknown id(s): {", ".join(sorted(unknown))}')
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for c in CATALOG:
        if only is not None and c.id not in only:
            continue
        results += _render_one(component_film(c), out_dir, c.id, jobs, crf, log)
    for r in RECIPES:
        if only is not None and r.id not in only:
            continue
        results += _render_one(build_recipe_film(r), out_dir, r.id, jobs, crf, log)
    return results
