"""The capabilities: one entry per thing videobuilder can do, each a one-file
record under `<family>/` read through the registry (`registry.py`; the record
is `schema.Capability`), each with a demo film that proves it. This module is
what reads them for the `/capabilities` page (editor.py) and the
builder-facing sheet (skill/make-a-video/reference/capabilities.md, generated
by `sheet_markdown` below and checked for drift by tests/test_capabilities.py).
Add a capability by adding its one file; nothing else lists capabilities.

    python -m videobuilder capabilities build --out DIR [--only ID]

A capability with a `category` has a card of its own in that section of the
page (in `order`); one that groups others (`members`, e.g. Looks) has the
section to itself, its members after its own card. Every other capability is
counted on its family's card, linking to the family's own page
(/capabilities/<family>).

The full build also renders the showcase (examples/showcase.py), the
product film: every capability counted and on one wall, a beat for each
registry family with its demos playing, and a launch film cut from the
capabilities with cards of their own, all read from this module and the
registry at render time. It is built last, as showcase-16x9.mp4 and
showcase-9x16.mp4 with posters, so its wall is tiled with the posters just
built; it is served beside the clips and shown at the top of the page.

Community-submitted capabilities (community.py) are runtime data, not files:
a separate list shown beside the records, rendered by the same card and
Source-link code (`source_html`), and carrying the same `source` shape.

A capability the editor should let the creator tune carries `settings`
(Choice/Number from settings.py; see capabilities/schema.py and registry.py).
`narration`'s is the worked example, shared with `voiceover` via
speech.narration_settings so the two can't drift. `suggest/catalog`'s
per-capability JSON (video_api.py) carries a `settings` key only for a
capability that declares one.
"""
import json
import os
from functools import lru_cache

from . import registry
from .schema import CATEGORIES, REPO_ROOT, module_name


def _load_all():
    return registry.catalog()


@lru_cache(maxsize=None)
def cards():
    """Every capability with a card of its own on /capabilities, in page
    order: by section (`schema.CATEGORIES`), then `order`, then name, a
    grouping capability's members right after it. What the page and the
    sheet list one by one, and the product film cuts from."""
    top = sorted((t for t in _load_all() if t.category),
                 key=lambda t: (CATEGORIES.index(t.category), t.order, t.name.casefold()))
    out = []
    for t in top:
        out.append(t)
        if t.members:
            out.extend(registry.get(i) for i in t.members.ids)
    return tuple(out)


def with_members():
    """The capabilities that group others (`members`), in page order."""
    return tuple(t for t in cards() if t.members)


@lru_cache(maxsize=None)
def _parents():
    return {i: t for t in _load_all() if t.members for i in t.members.ids}


def parent(t):
    """The capability whose `members` include `t` (a Capability or an id),
    or None."""
    return _parents().get(t if isinstance(t, str) else t.id)


def has_card(t):
    """Whether `t` has a card of its own on /capabilities (a `category`, or
    a member of one that does) rather than only on its family's page."""
    return bool(t.category) or parent(t) is not None


def category(t):
    """The /capabilities section `t`'s card sits in: its own `category`, its
    group's for a member; '' for one shown on its family's page."""
    p = parent(t)
    return t.category or (p.category if p else '')


def members(t):
    """`t`'s member capabilities, in its `members` order ((): none)."""
    return tuple(registry.get(i) for i in t.members.ids) if t.members else ()


def member_paths():
    """{grouping capability id: the file a community member ships} for every
    one that takes them (see schema.MemberBrief): community.MEMBER_PATHS."""
    return {f.id: f.members.brief.file for f in with_members() if f.members.brief}


def member_name(t):
    """The registry name a member answers to (a look's, a type style's), or
    None for one built by hand (paper collage) or a capability that is no
    member."""
    p = parent(t)
    return p.members.name(t.id) if p else None


def kind(t):
    """A member's kind slug ('scene', 'filter'), or None."""
    p = parent(t)
    return p.members.kind(t) if p else None


def kind_groups(family, members_=None):
    """The grouping capability `family`'s members grouped as the page and
    the sheet show them: [(kind, heading, line, members), ...], one group
    with no heading (kind, heading and line None) for one with no kinds."""
    members_ = members(family) if members_ is None else members_
    if not family.members.kinds:
        return [(None, None, None, list(members_))]
    return [(k, heading, line, [c for c in members_ if c.group == heading])
            for k, heading, line in family.members.kinds]


@lru_cache(maxsize=None)
def old_ids():
    """{old id: the id of the capability it was merged into}, from every
    record's `old_ids` (published notes, the showcase and builder prompts
    may name the old one)."""
    return {o: t.id for t in _load_all() for o in t.old_ids}


@lru_cache(maxsize=None)
def _ids():
    return frozenset(registry.ids())


def resolve(id):
    """The id a capability goes by now: `id` itself, or the capability an
    old id was merged into. KeyError for an id that never existed."""
    if id in _ids():
        return id
    if id in old_ids():
        return old_ids()[id]
    raise KeyError(id)


def get(id):
    """The capability `id` names, an old id included. KeyError for none."""
    return registry.get(resolve(id))


def ids():
    """Every capability's id. No new capability may reuse one, nor an old
    id (`old_ids`)."""
    return registry.ids()


def resolve_requested(requested):
    """Of `requested` (candidate capability chips from a note -- each a
    plain id string, or an {id, settings} dict carrying the non-default
    values its settings card picked), the ones that actually exist, each as
    {id, name, definition, api, settings, values}, in the order first seen;
    an unknown or repeated id is silently dropped, so a client's own list
    and its settings are never trusted blind. `definition` is the
    capability's `description` when it has one. `settings` is the
    capability's own declared Choice/Number tuple (empty if it declares
    none); `values` is the requested settings re-validated against it
    (settings.non_default), so it only ever holds entries that actually
    differ from their setting's default. See
    prompt._requested_capabilities_lines, which lists the result for the
    builder, and editor._note_capabilities, which stores it back onto the
    note."""
    from .settings import non_default
    out, seen = [], set()
    for item in requested or ():
        if isinstance(item, str):
            cid, raw_values = item, None
        elif isinstance(item, dict) and isinstance(item.get('id'), str):
            cid, raw_values = item['id'], item.get('settings')
        else:
            continue
        if cid in seen:
            continue
        seen.add(cid)
        try:
            t = get(cid)
        except KeyError:
            continue
        entry = {'id': t.id, 'name': t.name, 'definition': t.description or t.definition, 'api': list(t.api),
                 'settings': t.settings or ()}
        entry['values'] = non_default(entry['settings'], raw_values) if entry['settings'] else {}
        out.append(entry)
    return out


def categories():
    return CATEGORIES


def loose_categories():
    """The categories a capability that isn't a member may take: every one
    but a grouping capability's own section (Looks holds looks only)."""
    own = {f.category for f in with_members()}
    return tuple(c for c in categories() if c not in own)


def source_html(source):
    """A capability's Source link (`schema.Source`, or its `as_json` dict
    for a community capability): the credit as the link text, the upstream
    as a second link when there is one. '' for no source."""
    if not source:
        return ''
    s = source if isinstance(source, dict) else source.as_json()
    out = (f'Source: <a href="{_esc(s["url"])}" target="_blank" rel="noopener noreferrer">'
           f'{_esc(s["credit"])}</a>')
    if s.get('upstream'):
        out += (f', built on <a href="{_esc(s["upstream"])}" target="_blank" rel="noopener noreferrer">'
                f'{_esc(s["upstream_credit"])}</a>')
    return f'<span class="source">{out}</span>'


# ---- the builder-facing sheet (skill/make-a-video/reference/capabilities.md) ----

SHEET_PATH = os.path.join('skill', 'make-a-video', 'reference', 'capabilities.md')
_REGEN_CMD = 'python -m videobuilder capabilities sheet > ' + SHEET_PATH


def sheet_markdown():
    """The builder-facing reference generated from the capabilities with
    cards of their own (`cards`). Regenerate with `_REGEN_CMD`;
    tests/test_capabilities.py fails if the committed file drifts from
    this."""
    lines = [
        '<!-- GENERATED from the capability records by `sheet_markdown()` in videobuilder/capabilities/__init__.py.',
        f'     Do not hand-edit; regenerate with `{_REGEN_CMD}` after changing a capability. -->',
        '# Capabilities catalog',
        '',
        'What videobuilder can already do, with a worked example for each. Reach for one of these '
        'before inventing an effect. Every capability is one file under '
        '`videobuilder/capabilities/<family>/` (see `videobuilder/capabilities/schema.py`); the ones '
        'below have a card of their own on the `/capabilities` page and a worked example film in '
        '`examples/capabilities/`. This file and that page are both generated from those records.',
        '',
    ]
    top = [t for t in cards() if t.category]
    for category_ in categories():
        lines.append(f'## {category_}')
        lines.append('')
        for e in top:
            if e.category != category_:
                continue
            lines.append(f'### {e.name}')
            lines.append('')
            lines.append(f'**What it looks like:** {e.definition} {e.description}')
            lines.append('')
            lines.append('**When to use it:** reach for this when a director says something like:')
            for p in e.phrasings:
                lines.append(f'- "{p}"')
            lines.append('')
            lines.append('**How to build it:**')
            for api in e.api:
                lines.append(f'- `{api}`')
            lines.append(f'- Read `{e.doc}`.')
            lines.append('')
            lines.append(f'**Worked example:** `{e.demo.path}` — read it before writing something similar from scratch.')
            lines.append('')
            if e.members:
                singular, plural = e.members.noun
                kids = members(e)
                lines.append(f'**The {plural}** ({len(kids)}; ask for any {singular} by name):')
                lines.append('')
                for _, heading, line, group in kind_groups(e, kids):
                    if heading:
                        lines.append(f'*{heading}*, {line}:')
                        lines.append('')
                    for child in group:
                        name = member_name(child) or child.id
                        build = '; '.join(f'`{api}`' for api in child.api)
                        lines.append(f"- **{child.name}** (`{name}`): {child.definition} "
                                     f"Ask: \"{child.phrasings[0]}\". Build: {build}. Example: `{child.demo.path}`.")
                    lines.append('')
                merged = [(old, child) for child in kids for old in child.old_ids]
                if merged:
                    lines.append('Old ids, now part of these: ' + '; '.join(
                        f"`{old}` is the **{child.name}**" for old, child in merged) + '.')
                    lines.append('')
    lines.append('## Capability families')
    lines.append('')
    lines.append('Hundreds more capabilities (easing curves, transitions, text reveals and the like), too many '
                 'to list here one by one: each lives in its own file under '
                 '`videobuilder/capabilities/<family>/<id with - as _>.py`, ending in a module-level '
                 '`CAPABILITY = Capability(...)` (see `videobuilder/capabilities/schema.py`), with a short '
                 'demo of its own. List a family\'s with `python -m videobuilder capabilities index --family '
                 '<family>` (drop `--family` for every one; add `--json` for machine-readable output). Call '
                 'what its `api` names to use one in a film -- some are videobuilder\'s own functions, the '
                 'rest live in the module itself and are imported from there; its own `draw` is a worked '
                 'demo of the capability alone, read before using it the first time. Add a new one the same '
                 'way, one new file and nothing else edited, checked by `python3 -m unittest '
                 'tests.test_capabilities_registry.EachCapability.test_<id with - as _>`. The families:')
    lines.append('')
    for fam, (title, description) in REGISTRY_FAMILIES.items():
        lines.append(f'- **{title}** (`{fam}`): {description}')
    lines.append('')
    return '\n'.join(lines) + '\n'


# ---- building the clips and posters ----

def _save_poster(cv, path, quality=82):
    from PIL import Image
    cv.surface.flush()
    w, h = cv.surface.get_width(), cv.surface.get_height()
    im = Image.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
    im.convert('RGB').save(path, 'JPEG', quality=quality)


# ---- the showcase reel: every capability in one film, served beside the clips ----

SHOWCASE = 'examples/showcase.py'
SHOWCASE_ID = 'showcase'
SHOWCASE_FILES = ('showcase-16x9', 'showcase-9x16')   # one per format, each with an .mp4 and a .jpg


def build_showcase(out_dir, jobs=None, crf=30, log=None):
    """Render the showcase in each of its formats (its own 1280x720 and 720x1280)
    to `<out_dir>/showcase-<format>.mp4`, with a poster (the film's `POSTER`
    frame). The film tiles its wall of every capability with the posters
    already in `out_dir` (its `use_clips`), so `build` renders it last; a
    capability with no poster there gets a plain tile. Returns {id, seconds,
    bytes} per format."""
    import sys as _sys
    import time as _time
    from .. import film as _film
    from ..render import render as _render
    log = log or _sys.stderr
    mod = _film.load_module(os.path.join(REPO_ROOT, SHOWCASE))
    film = mod.FILM
    if hasattr(mod, 'use_clips'):
        mod.use_clips(out_dir)
    poster_n = getattr(mod, 'POSTER', None)
    if poster_n is None:
        poster_n = mod.TIMELINE.start('title') + 3 * mod.GRID.frames_per_beat   # the title, landed
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for fmt in film.formats:
        name = f'showcase-{fmt.name}'
        out_mp4 = os.path.join(out_dir, name + '.mp4')
        t0 = _time.time()
        _render(film, out_mp4, fmt, jobs=jobs, crf=crf, log=log)
        _save_poster(film.frame(int(poster_n), fmt), os.path.join(out_dir, name + '.jpg'))
        results.append({'id': name, 'seconds': _time.time() - t0, 'bytes': os.path.getsize(out_mp4)})
    return results


def build(out_dir, only=None, jobs=None, crf=30, log=None):
    """Render every capability's demo (or just the ids in `only`) to
    `<out_dir>/<id>.mp4` (H.264, yuv420p, faststart, audio only where the
    demo has it) and `<out_dir>/<id>.jpg` (a poster: see
    `registry.poster_frame`), via `build_registry`. With no `only`, or with
    'showcase' in it, the showcase reel is built too (`build_showcase`),
    last: its wall is tiled with the posters built before it. Returns a list
    of {id, seconds, bytes} for the ones built, the capabilities with cards
    of their own first (page order), then the rest, then the showcase.
    """
    if only is not None:
        unknown = set(only) - set(ids()) - {SHOWCASE_ID}
        if unknown:
            raise ValueError(f'unknown capability id(s): {", ".join(sorted(unknown))}')
    results = build_registry(out_dir, only=only, jobs=jobs, crf=crf, log=log)
    if only is None or SHOWCASE_ID in only:
        results += build_showcase(out_dir, jobs=jobs, crf=crf, log=log)
    return results


# ---- serving: /capabilities, /capabilities/<id>.mp4, /capabilities/<id>.jpg ----

def clip_file(capabilities_dir, id, kind):
    """The clip ('mp4') or poster ('jpg') path for a capability id or a
    showcase file, or None for an unknown id (checked by membership in the
    registry's ids and SHOWCASE_FILES, never built from the request string
    directly) or a dir that isn't configured. An old id (`old_ids`) gets the
    clip of the capability it was merged into. Every clip lives flat in
    `capabilities_dir`."""
    if capabilities_dir is None:
        return None
    if id in SHOWCASE_FILES:
        return os.path.join(capabilities_dir, f'{id}.{kind}')
    try:
        id = resolve(id)   # an old id serves its new clip
    except KeyError:
        return None
    return os.path.join(capabilities_dir, f'{id}.{kind}')


def available_ids(capabilities_dir):
    if capabilities_dir is None:
        return frozenset()
    return frozenset(i for i in ids() if os.path.exists(clip_file(capabilities_dir, i, 'mp4')))


def showcase_available(capabilities_dir):
    """Whether the 16:9 showcase reel, the one the page shows, is built."""
    return capabilities_dir is not None and os.path.exists(clip_file(capabilities_dir, SHOWCASE_FILES[0], 'mp4'))


# ---- the registry: videobuilder/capabilities/<family>/<id>.py, shown here grouped by family ----
#
# Most capabilities have no card of their own (no `category`): too many (hundreds) to list one by
# one on this page, each family with at least one gets one card, filed into the category section it
# belongs to (FAMILY_CATEGORY below), linking to its own page (/capabilities/<family>). The records
# are read at render and build time, never duplicated into this module -- a capability file
# landing or changing can never make anything here drift. Family titles
# and descriptions, though, are ours to write: one row per videobuilder.capabilities.schema.FAMILIES
# slug (tests/test_capabilities_registry.py checks every slug has one).
REGISTRY_FAMILIES = {
    'principles': ('Animation principles', "The animator's classic toolkit: easing, timing and weight."),
    'typography': ('Typography', 'Type-only moves: reveals, effects and kinetic lettering.'),
    'transitions': ('Transitions', 'Ways from one shot to the next.'),
    'ui': ('UI and interaction', 'Interface moves: buttons, cursors, menus and loading states.'),
    'shapes': ('Shapes and icons', 'Vector shapes and icons that draw on, morph and move.'),
    'particles': ('Particles and generative', 'Particle systems and seeded generative motion.'),
    'camera': ('Camera moves', 'Virtual camera moves: pans, zooms, shakes and racks.'),
    'vfx': ('Visual effects', 'Compositing-style effects: glows, distortions and glitches.'),
    'broadcast': ('Broadcast graphics', 'TV-style graphics: lower thirds, tickers and scoreboards.'),
    'sound': ('Sound', 'Sound-only capabilities: foley, stingers and audio cues.'),
}

# The existing capability-page category each registry family's card files into, after that
# category's own cards (a registry capability IS a capability to a director; there is no section of
# their own). One row per videobuilder.capabilities.schema.FAMILIES slug (tests/test_capabilities_registry.py
# checks every slug maps to a category capabilities.categories() actually has).
FAMILY_CATEGORY = {
    'principles': 'Motion',
    'transitions': 'Motion',
    'ui': 'Motion',
    'shapes': 'Motion',
    'particles': 'Motion',
    'typography': 'Type and data',
    'broadcast': 'Type and data',
    'camera': 'Imagery and camera',
    'vfx': 'Imagery and camera',
    'sound': 'Timing, sound and formats',
}

# The capability whose poster a family's card shows, where its first capability's middle
# frame says little (dip-to-black's is black). A family not named here, or whose pick is absent,
# shows its first capability.
REGISTRY_FAMILY_POSTER = {
    'transitions': 'iris-wipe',
}

# Capabilities on a family's page that are the same move as one with a card of its own: both keep
# their own card, but each links to the other (see _registry_overlap and the modals in
# page_html/family_page_html). Found by reading the records' `api` and `name`. May name only ids
# present in this checkout -- a test checks both sides of every row exist.
REGISTRY_OVERLAP = {
    'ease-out-back': 'eased-entrances',   # both demo vb.ease_out_back
    'shape-morph': 'outline-morph',       # both demo vb.paths.morph; the registry kept the old capability id
}


def _registry_overlap(capability_id):
    """The registry id REGISTRY_OVERLAP maps to `capability_id`, or None."""
    for registry_id, mapped in REGISTRY_OVERLAP.items():
        if mapped == capability_id:
            return registry_id
    return None


def _family_members(family):
    """The capabilities on `family`'s own page, registry order: every one of
    the family's but those with cards of their own (`has_card`)."""
    return tuple(t for t in registry.catalog(family) if not has_card(t))


def _registry_groups(members):
    """`members` (one family's registry capabilities, registry/catalog order) grouped by
    their `group` field, each group's first-seen order kept: [(group,
    [capability, ...]), ...]. Unlike registry.grouped(), never re-sorts."""
    order, by_group = [], {}
    for t in members:
        if t.group not in by_group:
            by_group[t.group] = []
            order.append(t.group)
        by_group[t.group].append(t)
    return [(g, by_group[g]) for g in order]


def build_registry(out_dir, only=None, jobs=None, crf=30, log=None):
    """Render every capability's demo (or just `only`'s ids) to the flat
    `<out_dir>/<id>.mp4` and `<out_dir>/<id>.jpg` (its poster frame:
    `registry.poster_frame`, the record's own `poster` when it gives one,
    else the demo's middle frame). Returns [{id, seconds, bytes}, ...], the
    capabilities with cards of their own first (page order), then the rest
    in registry order."""
    import sys as _sys
    import time as _time
    from ..render import render as _render
    log = log or _sys.stderr
    first = cards()
    chosen = first + tuple(t for t in registry.catalog() if t not in first)
    if only is not None:
        chosen = tuple(t for t in chosen if t.id in only)
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for t in chosen:
        film = t.demo()
        fmt = film.formats[0]
        out_mp4 = os.path.join(out_dir, t.id + '.mp4')
        t0 = _time.time()
        _render(film, out_mp4, fmt, jobs=jobs, crf=crf, log=log)
        poster_n = registry.poster_frame(t, film, film.frames // 2)
        _save_poster(film.frame(poster_n, fmt), os.path.join(out_dir, t.id + '.jpg'))
        results.append({'id': t.id, 'seconds': _time.time() - t0, 'bytes': os.path.getsize(out_mp4)})
    return results


def family_page_html(family, capabilities_dir, version, header='', header_style=''):
    """The /capabilities/<family> page: that family's capabilities, grouped
    under their own `group` heading, in registry order. Clicking a card opens
    the same kind of modal /capabilities uses, with the clip, the definition,
    the phrasings as example prompts, the aliases and the api names, plus a
    link back to the overlapping capability (REGISTRY_OVERLAP), if there is
    one. Raises KeyError for a family that isn't one of registry.FAMILIES
    (the route checks this, never builds a path from the request string)."""
    from . import registry
    if family not in registry.FAMILIES:
        raise KeyError(family)
    members = _family_members(family)
    title, description = REGISTRY_FAMILIES[family]
    search_label = title[0].lower() + title[1:]
    built = available_ids(capabilities_dir)
    body = []
    for group, group_members in _registry_groups(members):
        body.append(f'<h3 class="kind">{_esc(group)}</h3><div class="grid">')
        for t in group_members:
            body.append(_card_html(t.id, t.name, t.definition, _thumb_html(t.id, built)))
        body.append('</div>')
    data = []
    for t in members:
        item = {'id': t.id, 'title': t.name, 'family': t.family, 'familyTitle': title,
                'group': t.group,
                'description': t.definition, 'prompts': list(t.phrasings), 'aliases': list(t.aliases),
                'api': list(t.api), 'available': t.id in built}
        overlap = REGISTRY_OVERLAP.get(t.id)
        if overlap:
            cap = get(overlap)
            item['overlap'] = {'id': cap.id, 'title': cap.name}
        data.append(item)
    style = _PAGE_STYLE + header_style + _REGISTRY_MODAL_STYLE
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>{_esc(title)} · videobuilder</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<style>{style}</style></head><body>{header}'
        f'<main><div class="cap-head"><h1>{_esc(title)}</h1>'
        f'<span class="version">videobuilder v{_esc(version)}</span>'
        f'<input type="search" id="reg-search" class="cap-search" placeholder="Search {_esc(search_label)}…" '
        f'aria-label="Search {_esc(search_label)}" autocomplete="off" spellcheck="false"></div>'
        f'<p class="section-lead">{_esc(description)} <a href="/capabilities">Back to Capabilities</a></p>'
        f'{"".join(body)}<p class="search-none search-hide" id="search-none" role="status"></p></main>' +
        _REGISTRY_MODAL_HTML +
        f'<script id="registry-data" type="application/json">{json.dumps(data).replace("<", "\\u003c")}</script>'
        f'<script>{_REGISTRY_PAGE_SCRIPT}</script><script>{_REGISTRY_SEARCH_SCRIPT}</script>'
        '</body></html>'
    )
    return html.encode()


def _esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


_PAGE_STYLE = """
:root{color-scheme:dark}
body{font:16px/1.5 system-ui,sans-serif;background:#0d0d10;color:#eee;margin:0;overflow-x:hidden}
a{color:#ef5b4c}
.cap-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 14px;padding:28px 0 0}
.cap-head h1{font-size:clamp(26px,3vw,34px);letter-spacing:-.02em;margin:0;font-weight:800}
.cap-head .version{color:#a9a9b2;font-size:13px}
.cap-search{margin-left:auto;flex:0 1 320px;min-width:0;align-self:center;box-sizing:border-box;min-height:44px;
  padding:8px 14px;border-radius:10px;border:1px solid #2c2c33;background:#141417;color:#f4f4f2;font:inherit;
  font-size:16px}
.cap-search:focus{outline:none;border-color:#6b6b75;box-shadow:0 0 0 3px rgba(244,244,242,.08)}
.cap-search + #add-capability{margin-left:0}
@media (max-width:720px){.cap-search{order:5;flex:1 1 100%;margin:6px 0 0}}
.search-hide{display:none!important}
.search-none{color:#a9a9b2;margin:28px 2px}
main{max-width:1180px;margin:0 auto;padding:8px 32px 48px;box-sizing:border-box}
.reel{margin:24px 0 8px}
.reel .player{position:relative;border-radius:14px;overflow:hidden;background:#000;aspect-ratio:16/9}
.reel.portrait .player{aspect-ratio:9/16;width:min(100%,calc(80vh * 9 / 16));margin:0 auto}
.reel video{width:100%;height:100%;display:block;cursor:pointer}
.reel .unmute{position:absolute;bottom:12px;right:12px;min-height:36px;padding:6px 12px;border-radius:8px;
  border:1px solid #fff5;background:#000a;color:#fff;cursor:pointer}
.reel .fullscreen{position:absolute;top:12px;right:12px;min-height:36px;padding:6px 12px;border-radius:8px;
  border:1px solid #fff5;background:#000a;color:#fff;cursor:pointer}
.reel p{color:#a9a9b2;margin:10px 2px 0;font-size:14px}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:#a9a9b2;margin:36px 0 14px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
@media (max-width:1000px){.grid{grid-template-columns:repeat(3,1fr)}}
@media (max-width:720px){main{padding:8px 16px 48px}.cap-head{padding-top:20px}}
@media (max-width:700px){.grid{grid-template-columns:repeat(2,1fr)}}
.card{display:block;width:100%;text-align:left;background:#141417;border:1px solid #26262c;border-radius:12px;
  padding:0;overflow:hidden;cursor:pointer;color:inherit;font:inherit;min-height:44px;text-decoration:none}
.card:hover,.card:focus-visible{border-color:#e5483b;outline:none}
.card .thumb{width:100%;aspect-ratio:1/1;background:#0d0d10;display:flex;align-items:center;justify-content:center;
  color:#5a5d66;font-size:13px;text-align:center;overflow:hidden}
.card .thumb img{width:100%;height:100%;object-fit:cover;display:block}
.card .meta{display:block;padding:10px 12px 14px}
.card .meta strong{display:block;font-size:14px;margin-bottom:4px}
.card .meta span{display:block;font-size:12.5px;color:#a9a9b2}
.sourced-card{display:flex;flex-direction:column;gap:6px}
.sourced-card .source,.community-card .source{font-size:12px;color:#a9a9b2;padding:0 4px}
#modal{position:fixed;inset:0;background:#000c;display:flex;align-items:center;justify-content:center;
  padding:24px;z-index:30}
#modal[hidden]{display:none}
#modal .box{background:#141417;border-radius:16px;max-width:560px;width:100%;max-height:92vh;overflow:auto;
  position:relative}
#modal video{width:100%;aspect-ratio:1/1;background:#000;display:block}
#modal video[hidden]{display:none}
#modal .placeholder{width:100%;aspect-ratio:1/1;background:#0d0d10;display:flex;align-items:center;
  justify-content:center;color:#5a5d66}
#modal .placeholder[hidden]{display:none}
#modal .body{padding:20px 22px 26px}
#modal h3{margin:0 0 6px;font-size:20px}
#modal .cat{color:#a9a9b2;font-size:13px;margin:0 0 14px}
#modal .cap-id{display:flex;align-items:center;gap:8px;margin:-8px 0 14px}
#modal .cap-id code{color:#e5483b;font-family:monospace;font-size:13px}
#modal .copy-id{min-height:28px;padding:2px 10px;border-radius:7px;border:1px solid #34343c;background:#1d1d22;
  color:#dcdcdc;font:inherit;font-size:12px;cursor:pointer}
#modal .copy-id:hover{border-color:#e5483b;color:#fff}
#modal .desc{margin:0 0 18px;color:#dcdcdc}
#modal .prompts{background:#1b1e24;border-radius:10px;padding:14px 16px;margin:0}
#modal .prompts p{margin:0 0 8px;font-weight:600;font-size:13px;color:#a9a9b2;text-transform:uppercase;
  letter-spacing:.03em}
#modal .prompts ul{margin:0;padding-left:20px}
#modal .prompts li{margin:4px 0;color:#eee}
#modal .close{position:absolute;top:10px;right:10px;width:44px;height:44px;border-radius:50%;border:0;
  background:#0006;color:#fff;font-size:18px;cursor:pointer;z-index:1}
#modal .unmute{position:absolute;bottom:10px;right:10px;min-height:36px;padding:6px 12px;border-radius:8px;
  border:1px solid #fff5;background:#000a;color:#fff;cursor:pointer}
.section-lead{color:#a9a9b2;margin:-4px 0 14px;font-size:14px}
.section-lead .count{display:inline-block;margin-left:6px;padding:2px 9px;border-radius:999px;background:#1f1f25;
  color:#dcdcdc;font-size:12px;font-weight:700}
h3.kind{font-size:14px;margin:22px 0 10px;color:#eee}
h3.kind span{display:block;font-weight:400;font-size:13px;color:#8b8b94;margin-top:2px}
.reg-overlap{margin:0 0 14px;font-size:13px;color:#a9a9b2}
.reg-overlap a{color:#ef5b4c}
#reg-hits{list-style:none;margin:8px 2px 0;padding:0}
#reg-hits li{margin:4px 0}
#reg-hits a{color:#eee;text-decoration:none;display:block;padding:8px 10px;border-radius:8px;background:#141417;
  border:1px solid #26262c}
#reg-hits a:hover{border-color:#e5483b}
#reg-hits a span{color:#8b8b94;font-size:12.5px;margin-left:6px}
@media (max-width:700px){
  #modal{padding:0}
  #modal .box{max-width:none;width:100%;height:100%;max-height:none;border-radius:0}
  #modal video,#modal .placeholder{aspect-ratio:auto;height:50vh}
  .looks-grid{grid-template-columns:repeat(3,1fr);gap:10px}
  .looks-grid .card .meta{padding:7px 8px 9px}
  .looks-grid .card .meta strong{font-size:12.5px;margin:0;line-height:1.3}
  .looks-grid .card .meta span{display:none}
}
"""

_COMMUNITY_STYLE = """
.community-badge{display:inline-block;margin-left:6px;padding:2px 7px;border-radius:6px;font-size:10.5px;
  font-weight:700;letter-spacing:.03em;text-transform:uppercase;background:#2a2320;color:#e9a23b;
  vertical-align:middle}
.card .meta strong .community-badge{margin-left:4px}
.draft-section{margin:36px 0 14px}
.draft-section h2{margin-bottom:6px}
.draft-section .hint{color:#8b8b94;font-size:13px;margin:0 0 14px}
.draft-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.draft-card{background:#141417;border:1px solid #26262c;border-radius:12px;padding:14px 16px;
  display:flex;flex-direction:column;gap:6px}
.draft-card strong{font-size:14px}
.draft-slug{font-size:11.5px;color:#6f6f78;font-family:monospace}
.draft-status{font-size:12.5px;color:#a9a9b2}
.draft-status.problem{color:#ff8a80}
.draft-submitter{font-size:12.5px;color:#8b8b94}
.draft-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px}
.draft-actions a,.draft-actions button{min-height:34px;padding:0 12px;border-radius:8px;font:inherit;
  font-size:13px;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center}
.draft-actions a{border:1px solid #2c2c33;background:#0d0d10;color:#eee}
.draft-actions button{border:0;color:#fff;background:#3a3a42}
.draft-actions button[data-cap-action=publish]{background:#2a7a4f}
.draft-actions button[data-cap-action=reject]{background:#8a2f2f}
.draft-actions button[data-cap-action=send]{background:#e5483b}
.draft-actions button:disabled{opacity:.6;cursor:default}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:0 1.1rem;
  border-radius:10px;border:1px solid #2c2c33;background:#141417;color:#f4f4f2;font:inherit;font-weight:600;
  cursor:pointer}
.btn-primary{background:#e5483b;border-color:#e5483b;color:#fff;font-weight:700}
.btn-primary:hover{background:#ef5b4c;border-color:#ef5b4c}
.draft-error{color:#ff8a80;font-size:12.5px;margin:0}.draft-error:empty{display:none}
.community-card{display:flex;flex-direction:column;gap:6px}
.community-card .draft-actions{padding:0}
"""

_PAGE_SCRIPT = """
(function(){
  var data = JSON.parse(document.getElementById('capabilities-data').textContent);
  var communityEl = document.getElementById('community-data');
  var community = communityEl ? JSON.parse(communityEl.textContent) : [];
  var byId = {};
  data.forEach(function(e){byId[e.id] = e});
  community.forEach(function(e){byId[e.id] = e});
  var modal = document.getElementById('modal');
  var video = document.getElementById('modal-video');
  var placeholder = document.getElementById('modal-placeholder');
  var unmuteBtn = document.getElementById('modal-unmute');
  var regOverlapEl = document.getElementById('modal-reg-overlap');
  var idEl = document.getElementById('modal-id');
  var idCode = document.getElementById('modal-id-code');
  var copyBtn = document.getElementById('modal-copy');
  var copyId = null;
  var opener = null;
  var box = modal.querySelector('.box');
  function openCard(id){
    var e = byId[id];
    if(!e) return;
    opener = document.querySelector('[data-card="' + id + '"]');
    document.getElementById('modal-title').textContent = e.title;
    document.getElementById('modal-cat').textContent = e.members ?
      e.category + ' \u00b7 ' + e.members + ' ' + e.plural : (e.family ? e.category + ' \u00b7 ' + e.kindTitle : e.category);
    // A family's own lead card (e.members set) is a navigation card, and a community
    // card's id (the registry doesn't know "community:<slug>") isn't one #id chips
    // can name either: no slug to copy there, only on an actual registry capability's card.
    copyId = (e.members || id.indexOf('community:') === 0) ? null : id;
    idEl.hidden = !copyId;
    if(copyId){ idCode.textContent = '#' + copyId; copyBtn.textContent = 'Copy' }
    document.getElementById('modal-desc').textContent = e.description;
    var ul = document.getElementById('modal-prompts');
    ul.innerHTML = '';
    e.prompts.forEach(function(p){
      var li = document.createElement('li');
      li.textContent = p;
      ul.appendChild(li);
    });
    if(e.regOverlap){
      regOverlapEl.innerHTML = '';
      regOverlapEl.appendChild(document.createTextNode('See also: '));
      var a = document.createElement('a');
      a.href = '/capabilities/' + e.regOverlap.family + '#' + e.regOverlap.id;
      a.textContent = e.regOverlap.title;
      regOverlapEl.appendChild(a);
      regOverlapEl.appendChild(document.createTextNode('.'));
      regOverlapEl.hidden = false;
    } else regOverlapEl.hidden = true;
    if(e.available){
      video.src = e.clip || ('/capabilities/' + id + '.mp4');
      video.poster = e.poster || ('/capabilities/' + id + '.jpg');
      video.muted = true;
      video.hidden = false;
      placeholder.hidden = true;
      unmuteBtn.hidden = !e.unmute;
      unmuteBtn.textContent = 'Unmute';
      video.play().catch(function(){});
    } else {
      video.hidden = true;
      video.removeAttribute('src');
      placeholder.hidden = false;
      unmuteBtn.hidden = true;
    }
    modal.hidden = false;
    box.scrollTop = 0;
    document.getElementById('modal-close').focus();
  }
  function closeModal(){
    if(modal.hidden) return;
    modal.hidden = true;
    video.pause();
    video.removeAttribute('src');
    video.load();
    if(opener) opener.focus();
  }
  document.querySelectorAll('[data-card]').forEach(function(btn){
    btn.addEventListener('click', function(){openCard(btn.getAttribute('data-card'))});
  });
  document.getElementById('modal-close').addEventListener('click', closeModal);
  modal.addEventListener('click', function(e){if(e.target === modal) closeModal()});
  copyBtn.addEventListener('click', function(){
    if(!copyId) return;
    var text = '#' + copyId;
    var done = function(){ copyBtn.textContent = 'Copied!'; setTimeout(function(){ copyBtn.textContent = 'Copy' }, 1200) };
    if(navigator.clipboard) navigator.clipboard.writeText(text).then(done, done);
    else {
      var ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy') } catch(e){}
      document.body.removeChild(ta);
      done();
    }
  });
  unmuteBtn.addEventListener('click', function(){
    video.muted = !video.muted;
    unmuteBtn.textContent = video.muted ? 'Unmute' : 'Mute';
  });
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape') closeModal();
  });
  // The showcase reel: muted until asked, paused while a card's clip plays,
  // and still (on its poster) for anyone who prefers reduced motion.
  var reel = document.getElementById('reel');
  if(reel){
    // The 9:16 cut for portrait screens is picked here, not with <source media>,
    // which older Safari and Firefox ignore.
    var section = reel.closest('.reel');
    var tall = section.dataset.portrait;
    if(tall && window.matchMedia && window.matchMedia('(orientation: portrait)').matches){
      section.classList.add('portrait');
      reel.poster = '/capabilities/' + tall + '.jpg';
      reel.src = '/capabilities/' + tall + '.mp4';
    }
    var reelUnmute = document.getElementById('reel-unmute');
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(!still) reel.play().catch(function(){});
    reel.addEventListener('click', function(){ if(reel.paused) reel.play(); else reel.pause(); });
    reelUnmute.addEventListener('click', function(){
      reel.muted = !reel.muted;
      reelUnmute.textContent = reel.muted ? 'Unmute' : 'Mute';
      if(!reel.muted && reel.paused) reel.play().catch(function(){});
    });
    document.getElementById('reel-fullscreen').addEventListener('click', function(){
      // iPhone Safari has no element fullscreen, only the video's own player.
      if(document.fullscreenEnabled && reel.requestFullscreen) reel.requestFullscreen().catch(function(){});
      else if(reel.webkitEnterFullscreen) reel.webkitEnterFullscreen();
      reel.play().catch(function(){});
    });
    document.querySelectorAll('[data-card]').forEach(function(btn){
      btn.addEventListener('click', function(){ reel.pause(); });
    });
  }
  if(location.hash) openCard(location.hash.slice(1));
})();
"""


# Extra modal fields only a registry capability has (aliases, api names): layered on top of
# _PAGE_STYLE on the family page, which otherwise matches /capabilities exactly.
_REGISTRY_MODAL_STYLE = """
#modal .reg-aliases{margin:0 0 14px;color:#a9a9b2;font-size:13px}
#modal .reg-api{background:#1b1e24;border-radius:10px;padding:14px 16px;margin:0 0 14px}
#modal .reg-api p{margin:0 0 8px;font-weight:600;font-size:13px;color:#a9a9b2;text-transform:uppercase;
  letter-spacing:.03em}
#modal .reg-api ul{margin:0;padding-left:20px}
#modal .reg-api li{margin:4px 0;color:#eee;font-family:monospace;font-size:13px}
"""

# The registry family page's modal: like /capabilities' own (clip, title, category line,
# description, phrasings as "What to tell the builder"), plus aliases, api names and -- only when
# REGISTRY_OVERLAP names this id -- a link back to the capability it overlaps.
_REGISTRY_MODAL_HTML = (
    '<div id="modal" hidden role="dialog" aria-modal="true" aria-labelledby="modal-title">'
    '<div class="box">'
    '<button class="close" id="modal-close" aria-label="Close">&times;</button>'
    '<video id="modal-video" autoplay loop muted playsinline hidden></video>'
    '<div class="placeholder" id="modal-placeholder"><span>clip not built</span></div>'
    '<button class="unmute" id="modal-unmute" hidden>Unmute</button>'
    '<div class="body">'
    '<h3 id="modal-title"></h3><p class="cat" id="modal-cat"></p>'
    '<p class="cap-id" id="modal-id" hidden><code id="modal-id-code"></code>'
    '<button type="button" class="copy-id" id="modal-copy">Copy</button></p>'
    '<p class="desc" id="modal-desc"></p>'
    '<div class="prompts"><p>What to tell the builder</p><ul id="modal-prompts"></ul></div>'
    '<p class="reg-aliases" id="modal-aliases" hidden></p>'
    '<div class="reg-api" id="modal-api-wrap" hidden><p>Build it</p><ul id="modal-api"></ul></div>'
    '<p class="reg-overlap" id="modal-overlap" hidden></p>'
    '</div></div></div>'
)

_REGISTRY_PAGE_SCRIPT = """
(function(){
  var data = JSON.parse(document.getElementById('registry-data').textContent);
  var byId = {};
  data.forEach(function(t){byId[t.id] = t});
  var modal = document.getElementById('modal');
  var video = document.getElementById('modal-video');
  var placeholder = document.getElementById('modal-placeholder');
  var unmuteBtn = document.getElementById('modal-unmute');
  var aliasesEl = document.getElementById('modal-aliases');
  var apiWrap = document.getElementById('modal-api-wrap');
  var apiList = document.getElementById('modal-api');
  var overlapEl = document.getElementById('modal-overlap');
  var idEl = document.getElementById('modal-id');
  var idCode = document.getElementById('modal-id-code');
  var copyBtn = document.getElementById('modal-copy');
  var copyId = null;
  var opener = null;
  var box = modal.querySelector('.box');
  function openCard(id){
    var t = byId[id];
    if(!t) return;
    opener = document.querySelector('[data-card="' + id + '"]');
    document.getElementById('modal-title').textContent = t.title;
    document.getElementById('modal-cat').textContent = t.familyTitle + ' \\u00b7 ' + t.group;
    copyId = id;
    idCode.textContent = '#' + id;
    idEl.hidden = false;
    copyBtn.textContent = 'Copy';
    document.getElementById('modal-desc').textContent = t.description;
    var ul = document.getElementById('modal-prompts');
    ul.innerHTML = '';
    t.prompts.forEach(function(p){
      var li = document.createElement('li');
      li.textContent = p;
      ul.appendChild(li);
    });
    if(t.aliases && t.aliases.length){
      aliasesEl.textContent = 'Also called: ' + t.aliases.join(', ');
      aliasesEl.hidden = false;
    } else aliasesEl.hidden = true;
    apiList.innerHTML = '';
    t.api.forEach(function(a){
      var li = document.createElement('li');
      li.textContent = a;
      apiList.appendChild(li);
    });
    apiWrap.hidden = false;
    if(t.overlap){
      overlapEl.innerHTML = '';
      overlapEl.appendChild(document.createTextNode('Also on the Capabilities page as '));
      var a = document.createElement('a');
      a.href = '/capabilities#' + t.overlap.id;
      a.textContent = t.overlap.title;
      overlapEl.appendChild(a);
      overlapEl.appendChild(document.createTextNode('.'));
      overlapEl.hidden = false;
    } else overlapEl.hidden = true;
    if(t.available){
      video.src = '/capabilities/' + id + '.mp4';
      video.poster = '/capabilities/' + id + '.jpg';
      video.muted = true;
      video.hidden = false;
      placeholder.hidden = true;
      unmuteBtn.hidden = true;
      video.play().catch(function(){});
    } else {
      video.hidden = true;
      video.removeAttribute('src');
      placeholder.hidden = false;
      unmuteBtn.hidden = true;
    }
    modal.hidden = false;
    box.scrollTop = 0;
    document.getElementById('modal-close').focus();
  }
  function closeModal(){
    if(modal.hidden) return;
    modal.hidden = true;
    video.pause();
    video.removeAttribute('src');
    video.load();
    if(opener) opener.focus();
  }
  document.querySelectorAll('[data-card]').forEach(function(btn){
    btn.addEventListener('click', function(){
      history.replaceState(null, '', '#' + btn.getAttribute('data-card'));
      openCard(btn.getAttribute('data-card'));
    });
  });
  document.getElementById('modal-close').addEventListener('click', closeModal);
  modal.addEventListener('click', function(e){if(e.target === modal) closeModal()});
  copyBtn.addEventListener('click', function(){
    if(!copyId) return;
    var text = '#' + copyId;
    var done = function(){ copyBtn.textContent = 'Copied!'; setTimeout(function(){ copyBtn.textContent = 'Copy' }, 1200) };
    if(navigator.clipboard) navigator.clipboard.writeText(text).then(done, done);
    else {
      var ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy') } catch(e){}
      document.body.removeChild(ta);
      done();
    }
  });
  unmuteBtn.addEventListener('click', function(){
    video.muted = !video.muted;
    unmuteBtn.textContent = video.muted ? 'Unmute' : 'Mute';
  });
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape') closeModal();
  });
  if(location.hash) openCard(location.hash.slice(1));
})();
"""

# The family page's search box: filters its own cards by name, alias and phrasing (no hit list --
# every capability in the family already has a card right there).
_REGISTRY_SEARCH_SCRIPT = """
(function(){
  var input = document.getElementById('reg-search');
  if(!input) return;
  var main = document.querySelector('main');
  var none = document.getElementById('search-none');
  var data = JSON.parse(document.getElementById('registry-data').textContent);
  var text = {};
  data.forEach(function(t){
    text[t.id] = [t.title, t.group].concat(t.aliases || [], t.prompts || []).join(' ').toLowerCase();
  });
  var cards = Array.prototype.slice.call(main.querySelectorAll('[data-card]'));
  function hide(el, yes){ el.classList.toggle('search-hide', yes) }
  function apply(){
    var words = input.value.toLowerCase().split(/\\s+/).filter(Boolean);
    var searching = words.length > 0, shown = 0;
    cards.forEach(function(card){
      var hay = (text[card.getAttribute('data-card')] || '') + ' ' + card.textContent.toLowerCase();
      var match = words.every(function(w){ return hay.indexOf(w) >= 0 });
      hide(card.closest('.sourced-card') || card, searching && !match);
      if(match) shown++;
    });
    main.querySelectorAll('.grid').forEach(function(grid){
      hide(grid, !Array.prototype.some.call(grid.children, function(c){
        return !c.classList.contains('search-hide') }));
    });
    main.querySelectorAll('h3.kind').forEach(function(h){
      var next = h.nextElementSibling;
      hide(h, !!next && next.classList.contains('grid') && next.classList.contains('search-hide'));
    });
    none.textContent = searching && !shown ? 'No capabilities match \\u201c' + input.value.trim() + '\\u201d.' : '';
    hide(none, !searching || shown > 0);
  }
  input.addEventListener('input', apply);
  input.addEventListener('keydown', function(e){
    if(e.key === 'Escape' && input.value){ e.preventDefault(); input.value = ''; apply() }
  });
  if(input.value) apply();
})();
"""


_ADD_CAPABILITY_STYLE = """
#add-capability{margin-left:auto}
.cap-dialog{position:fixed;border:1px solid #26262c;border-radius:16px;background:#141417;color:#f4f4f2;
  padding:1.5rem 1.25rem 1.25rem;max-width:480px;width:calc(100vw - 32px);box-sizing:border-box;
  box-shadow:0 30px 80px rgba(0,0,0,.6)}
.cap-dialog::backdrop{background:rgba(0,0,0,.65)}
.cap-dialog h2{margin:0 2.5rem .9rem 0;font-size:1.25rem;letter-spacing:-.01em;text-transform:none;color:#f4f4f2}
.cap-dialog-close{position:absolute;top:.75rem;right:.75rem;min-height:36px;min-width:36px;
  border-radius:8px;border:1px solid #26262c;background:#0d0d10;color:#f4f4f2;font-size:1.1rem;
  line-height:1;cursor:pointer}
#capability-form{display:flex;flex-direction:column;gap:1rem}
#capability-form label{display:flex;flex-direction:column;gap:.35rem;font-size:.85rem;color:#a9a9b2}
#capability-form input:not([type=file]),#capability-form textarea{font:inherit;color:#f4f4f2;
  min-height:46px;padding:.6rem .8rem;border-radius:10px;border:1px solid #2c2c33;background:#0d0d10;
  outline:none;box-sizing:border-box;width:100%}
#capability-form .drop{position:relative;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:.25rem;min-height:100px;padding:1rem;border:1.5px dashed #3a3a42;
  border-radius:12px;background:#0d0d10;text-align:center;cursor:pointer}
#capability-form .drop.over{border-color:#ef5b4c;background:#1a1211}
#capability-form .drop input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}
.drop-title{color:#f4f4f2;font-weight:600;font-size:.95rem}
.drop-title u{color:#ef5b4c;text-decoration:none}
.drop-hint{color:#8b8b94;font-size:.82rem}
.drop-files{color:#c9c9cf;font-size:.85rem;overflow-wrap:anywhere}
.drop-files:empty{display:none}
#capability-form .kind{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;border:0;margin:0;padding:0;min-width:0}
#capability-form .kind legend{padding:0;margin:0 0 .45rem;font-size:.85rem;color:#a9a9b2}
#capability-form .kind label{position:relative;display:flex;flex-direction:column;gap:.2rem;min-height:72px;
  padding:.7rem .8rem;border:1.5px solid #2c2c33;border-radius:12px;background:#0d0d10;cursor:pointer;color:#a9a9b2}
#capability-form .kind input{position:absolute;opacity:0;pointer-events:none}
#capability-form .kind strong{color:#f4f4f2;font-size:.95rem}
#capability-form .kind small{font-size:.8rem;line-height:1.35}
#capability-form .kind label:has(input:checked){border-color:#ef5b4c;background:#1a1211}
#capability-form .kind label:has(input:focus-visible){outline:2px solid #ef5b4c;outline-offset:2px}
#capability-submit{min-height:48px;border-radius:12px;border:0;background:#e5483b;color:#fff;font:inherit;
  font-weight:700;cursor:pointer}
#capability-submit:hover{background:#ef5b4c}
#capability-submit:disabled{opacity:.6;cursor:default}
#capability-error{color:#ff8a80;margin:0;font-size:.9rem}#capability-error:empty{display:none}
"""

# The search field: every word typed must appear in a card's title, line, category, description or
# example phrasings. Grids, kind headings and sections left empty hide with it, as do the reel and
# the drafts while a search is on.
_SEARCH_SCRIPT = """
(function(){
  var input = document.getElementById('cap-search');
  if(!input) return;
  var main = document.querySelector('main');
  var none = document.getElementById('search-none');
  var text = {};
  ['capabilities-data', 'community-data'].forEach(function(id){
    var el = document.getElementById(id);
    if(!el) return;
    JSON.parse(el.textContent).forEach(function(e){
      text[e.id] = [e.title, e.category, e.description, e.kindTitle || ''].concat(e.prompts || [])
        .join(' ').toLowerCase();
    });
  });
  var cards = Array.prototype.slice.call(main.querySelectorAll('[data-card]'));
  var registryEl = document.getElementById('registry-search-data');
  var registryCapabilities = registryEl ? JSON.parse(registryEl.textContent) : [];
  var hits = document.getElementById('reg-hits');
  function hide(el, yes){ el.classList.toggle('search-hide', yes) }
  function apply(){
    var words = input.value.toLowerCase().split(/\\s+/).filter(Boolean);
    var searching = words.length > 0, shown = 0;
    cards.forEach(function(card){
      var hay = (text[card.getAttribute('data-card')] || '') + ' ' + card.textContent.toLowerCase();
      var match = words.every(function(w){ return hay.indexOf(w) >= 0 });
      hide(card.closest('.community-card, .sourced-card') || card, searching && !match);
      if(match) shown++;
    });
    main.querySelectorAll('.reel, .draft-section').forEach(function(el){ hide(el, searching) });
    main.querySelectorAll('.grid').forEach(function(grid){
      hide(grid, !Array.prototype.some.call(grid.children, function(c){
        return !c.classList.contains('search-hide') }));
    });
    main.querySelectorAll('h3.kind').forEach(function(h){
      var next = h.nextElementSibling;
      hide(h, !!next && next.classList.contains('grid') && next.classList.contains('search-hide'));
    });
    main.querySelectorAll('h2').forEach(function(h){
      var run = [], el = h.nextElementSibling;
      while(el && el.tagName !== 'H2' && el !== none){ run.push(el); el = el.nextElementSibling }
      var any = run.some(function(r){ return r.classList.contains('grid') && !r.classList.contains('search-hide') });
      hide(h, searching && !any);
      run.forEach(function(r){ if(r.classList.contains('section-lead')) hide(r, searching && !any) });
    });
    // Registry capabilities don't have their own cards here (hundreds of them): a match links
    // straight to its family page instead of filtering a card in place.
    var regHits = 0;
    if(hits){
      hits.innerHTML = '';
      if(searching){
        registryCapabilities.forEach(function(t){
          var hay = [t.id, t.title, t.family].concat(t.aliases || []).join(' ').toLowerCase();
          if(!words.every(function(w){ return hay.indexOf(w) >= 0 })) return;
          regHits++;
          var li = document.createElement('li');
          var a = document.createElement('a');
          a.href = '/capabilities/' + t.family + '#' + t.id;
          a.textContent = t.title;
          var span = document.createElement('span');
          span.textContent = t.family;
          a.appendChild(span);
          li.appendChild(a);
          hits.appendChild(li);
        });
      }
      hide(hits, !searching || regHits === 0);
    }
    none.textContent = searching && !shown && !regHits ?
      'No capabilities match \\u201c' + input.value.trim() + '\\u201d.' : '';
    hide(none, !searching || shown > 0 || regHits > 0);
  }
  input.addEventListener('input', apply);
  input.addEventListener('keydown', function(e){
    if(e.key === 'Escape' && input.value){ e.preventDefault(); input.value = ''; apply() }
  });
  if(input.value) apply();
})();
"""


_ADD_CAPABILITY_SCRIPT = """
(function(){
  var openBtn = document.getElementById('add-capability');
  if(!openBtn) return;
  var dialog = document.getElementById('add-capability-dialog');
  var form = document.getElementById('capability-form');
  var error = document.getElementById('capability-error');
  var submit = document.getElementById('capability-submit');
  var fileInput = form.querySelector('input[type=file]');
  var heading = dialog.querySelector('h2');
  var capture = form.querySelector('input[name=capture]');
  // "A new capability" or a new member of a family ("A new look"): the
  // heading and the capture hint follow the choice.
  function syncKind(){
    var picked = form.querySelector('input[name=family]:checked');
    var label = picked ? picked.closest('label') : null;
    heading.textContent = label ? label.getAttribute('data-heading') : 'Add a capability';
    if(label) capture.placeholder = label.getAttribute('data-placeholder');
  }
  form.querySelectorAll('input[name=family]').forEach(function(r){ r.addEventListener('change', syncKind); });
  openBtn.addEventListener('click', function(){
    error.textContent = '';
    form.reset();
    syncKind();
    var list = form.querySelector('.drop-files');
    if(list) list.textContent = '';
    submit.disabled = false;
    dialog.showModal();
  });
  dialog.querySelector('.cap-dialog-close').addEventListener('click', function(){ dialog.close(); });
  dialog.addEventListener('click', function(e){
    var r = dialog.getBoundingClientRect();
    if(e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dialog.close();
  });
  function pathOf(name){ return name.split('/').map(encodeURIComponent).join('/'); }
  form.addEventListener('submit', async function(e){
    e.preventDefault();
    error.textContent = '';
    submit.disabled = true;
    var data = new FormData(form);
    var url = (data.get('url') || '').trim();
    var capture = (data.get('capture') || '').trim();
    var files = fileInput ? fileInput.files : [];
    var created = null;
    try{
      var body = {files: files.length};
      var family = data.get('family');
      if(family) body.family = family;
      if(url) body.url = url;
      if(capture) body.capture = capture;
      var r = await fetch('/api/capabilities/new', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      created = await r.json();
      if(!r.ok) throw new Error(created.error || "Couldn't start the submission.");
      if(created.read && created.read.error){
        if(!window.confirm(created.read.error + ' Continue with just the dropped files?')){
          submit.disabled = false;
          return;
        }
      }
      var ids = (created.attachments || []).slice();
      for(var i = 0; i < files.length; i++){
        var file = files[i];
        var ur = await fetch('/v/' + pathOf(created.name) + '/api/attachments?' +
          new URLSearchParams({video: created.video, name: file.name}),
          {method: 'POST', headers: {'Content-Type': file.type || 'application/octet-stream'}, body: file});
        var uploaded = await ur.json();
        if(!ur.ok) throw new Error(uploaded.error || ('could not upload ' + file.name));
        ids.push(uploaded.id);
      }
      var sr = await fetch('/api/capabilities/' + created.slug + '/send', {method: 'POST',
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({attachments: ids})});
      var sent = await sr.json();
      if(!sr.ok) throw new Error(sent.error || "Couldn't send it to the builder.");
      location.href = '/v/' + pathOf(created.name) + '/';
    }catch(err){
      error.textContent = err.message;
      submit.disabled = false;
    }
  });
})();
"""


def _add_capability_html(fetch):
    url_field = ('<label>Link (an X post, a blog post, a demo page)<input type="url" name="url" '
                'placeholder="https://&hellip;"></label>' if fetch else '')
    kinds = [('', 'A new capability', 'Something videobuilder can\'t do yet', 'Add a capability',
              'A one-line description of the effect')]
    for f in with_members():
        if f.members.brief:
            singular, plural = f.members.noun
            kinds.append((f.id, f'A new {singular}', f'Added to {f.name}, for any video to ask for',
                          f'Add a {singular}', f'A one-line description of the {singular}'))
    options = ''.join(
        f'<label data-heading="{_esc(heading)}" data-placeholder="{_esc(hint)}">'
        f'<input type="radio" name="family" value="{_esc(value)}"{" checked" if not value else ""}>'
        f'<strong>{_esc(title)}</strong><small>{_esc(sub)}</small></label>'
        for value, title, sub, heading, hint in kinds)
    kind_field = (f'<fieldset class="kind"><legend>What are you adding?</legend>{options}</fieldset>'
                  if len(kinds) > 1 else '')
    return (
        '<dialog id="add-capability-dialog" class="cap-dialog">'
        '<button type="button" class="cap-dialog-close" aria-label="Close">&times;</button>'
        '<h2>Add a capability</h2>'
        '<form id="capability-form">' + kind_field + url_field +
        '<label id="files-field" class="drop"><input type="file" name="files" multiple accept="image/*,video/*">'
        '<span class="drop-title">Drop a clip or screenshot or <u>browse</u></span>'
        '<span class="drop-hint">Optional</span><span class="drop-files" aria-live="polite"></span></label>'
        '<label>What should it capture? (optional)<input type="text" name="capture" maxlength="200" '
        'placeholder="A one-line description of the effect"></label>'
        '<button id="capability-submit" type="submit">Submit</button>'
        '<p id="capability-error" role="alert"></p>'
        '</form></dialog>'
    )


_COMMUNITY_SCRIPT = """
(function(){
  document.querySelectorAll('[data-cap-action]').forEach(function(btn){
    btn.addEventListener('click', async function(){
      var slug = btn.getAttribute('data-cap-slug');
      var action = btn.getAttribute('data-cap-action');
      var card = btn.closest('.draft-card') || btn.closest('.community-card') || btn.closest('.card');
      var errEl = card ? card.querySelector('.draft-error') : null;
      btn.disabled = true;
      try{
        var body = action === 'send' ? {attachments: []} : btn.hasAttribute('data-cap-update') ? {update: true} : {};
        var r = await fetch('/api/capabilities/' + slug + '/' + action, {method: 'POST',
          headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
        var data = await r.json();
        if(!r.ok) throw new Error(data.error || ("could not " + action + " this capability"));
        location.reload();
      }catch(err){
        if(errEl) errEl.textContent = err.message;
        btn.disabled = false;
      }
    });
  });
})();
"""


def _draft_status_line(draft):
    if draft['status'] == 'published':
        return 'problem', 'Published, but needs review: ' + (draft['problem'] or '')
    if not draft['sent']:
        return '', 'Draft — not sent to the builder yet'
    return '', 'Draft — waiting on the builder'


def _draft_card_html(draft, is_admin):
    css, status = _draft_status_line(draft)
    actions = []
    if not draft['sent']:
        actions.append(f'<button type="button" data-cap-action="send" data-cap-slug="{_esc(draft["slug"])}">'
                       'Send to the builder</button>')
    actions.append(f'<a href="/v/capabilities/{_esc(draft["slug"])}/">Open project</a>')
    if is_admin:
        actions.append(f'<button type="button" data-cap-action="publish" data-cap-slug="{_esc(draft["slug"])}">'
                       'Publish</button>')
        actions.append(f'<button type="button" data-cap-action="reject" data-cap-slug="{_esc(draft["slug"])}">'
                       'Reject</button>')
    title = draft.get('title') or 'Untitled draft'
    return (
        f'<div class="draft-card" data-slug="{_esc(draft["slug"])}">'
        f'<strong>{_esc(title)}</strong>'
        f'<span class="draft-slug">{_esc(draft["slug"])}</span>'
        f'<span class="draft-status {css}">{_esc(status)}</span>'
        f'<span class="draft-submitter">Submitted by {_esc(draft["submitter"])}</span>'
        f'<div class="draft-actions">{"".join(actions)}</div>'
        '<p class="draft-error" role="alert"></p>'
        '</div>'
    )


def _community_actions_html(entry, is_admin):
    """A published community card's status line and admin buttons (Publish
    update / Discard update / Take down), or '' when there are none."""
    slug = entry['slug']
    pending = entry.get('pending_update')
    status = '<span class="draft-status problem">Update awaiting approval</span>' if pending else ''
    actions = []
    if is_admin:
        if pending:
            actions.append(f'<button type="button" data-cap-action="publish" data-cap-slug="{_esc(slug)}">'
                           'Publish update</button>')
            actions.append(f'<button type="button" data-cap-action="reject" data-cap-update="1" '
                           f'data-cap-slug="{_esc(slug)}">Discard update</button>')
        actions.append(f'<button type="button" data-cap-action="reject" data-cap-slug="{_esc(slug)}">'
                       'Take down</button>')
    extra = status
    if actions:
        extra += f'<div class="draft-actions">{"".join(actions)}</div><p class="draft-error" role="alert"></p>'
    return extra


def _community_card_html(entry, is_admin):
    slug = entry['slug']
    thumb = (f'<img src="/capabilities/community/{_esc(slug)}.jpg" alt="" loading="lazy">' if entry.get('available')
            else '<span>clip not built</span>')
    return (
        '<div class="community-card">'
        f'<button class="card" type="button" data-card="{_esc("community:" + slug)}">'
        f'<span class="thumb">{thumb}</span>'
        f'<span class="meta"><strong>{_esc(entry["title"])}'
        '<span class="community-badge">Community</span></strong>'
        f'<span>{_esc(entry["card"])}</span></span>'
        '</button>' + source_html(entry.get('source')) + _community_actions_html(entry, is_admin) +
        '</div>'
    )



def _card_html(card_id, title, card, thumb, source=None):
    """A capability's card; one with a `source` (schema.Source) gets its
    Source link under it (`source_html`)."""
    html = (
        f'<button class="card" type="button" data-card="{_esc(card_id)}">'
        f'<span class="thumb">{thumb}</span>'
        f'<span class="meta"><strong>{_esc(title)}</strong><span>{_esc(card)}</span></span>'
        '</button>')
    if source:
        html = f'<div class="sourced-card">{html}{source_html(source)}</div>'
    return html


def _thumb_html(id_, built):
    return (f'<img src="/capabilities/{id_}.jpg" alt="" loading="lazy">' if id_ in built
            else '<span>clip not built</span>')


def _kind_title(entry):
    """What a member is, for its modal: its kind's heading made singular
    ('Scene look', 'Filter look'), or its group's noun ('Type style') for
    one with no kinds. `entry` is a member Capability, or a community
    member's dict (its `family` the grouping capability's id; a community
    member is always of the first kind)."""
    if isinstance(entry, dict):
        family, kind_ = get(entry['family']), None
    else:
        family, kind_ = parent(entry), kind(entry)
    kinds = family.members.kinds
    if not kinds:
        return family.members.noun[0].capitalize()
    return next(heading for k, heading, _ in kinds if k == (kind_ or kinds[0][0]))[:-1]


def _family_section_html(e, built, community_members, is_admin):
    """A grouping capability's section of the page, under its category's
    heading: one line on it, its own card (`lead`, its demo showing the
    members together), then its members grouped by kind (`kinds`), each
    group under a heading that says who it is for, or in one grid for one
    with none. Published community members close the first group, with the
    actions their cards have elsewhere. On a phone the cards drop their line
    and sit three across, so the whole section scans in a few screens."""
    singular, plural = e.members.noun
    n = len(e.members.ids) + len(community_members)
    out = [f'<p class="section-lead">{_esc(e.definition)} <span class="count">{n} {plural}</span></p>',
           '<div class="grid looks-grid">',
           _card_html(e.id, e.members.lead, e.members.lead_line, _thumb_html(e.id, built), e.source),
           '</div>']
    for i, (kind_, heading, line, group) in enumerate(kind_groups(e)):
        cards_ = [_card_html(c.id, c.name, c.definition, _thumb_html(c.id, built), c.source) for c in group]
        if i == 0:
            cards_ += [_community_card_html(entry, is_admin) for entry in community_members]
        if heading:
            out.append(f'<h3 class="kind" data-kind="{kind_}">{_esc(heading)} <span>{_esc(line)}</span></h3>')
        out.append(f'<div class="grid looks-grid" data-family="{_esc(e.id)}">{"".join(cards_)}</div>')
    return ''.join(out)


def _drafts_section_html(drafts, is_admin):
    if not drafts:
        return ''
    cards = ''.join(_draft_card_html(d, is_admin) for d in drafts)
    return (
        '<section class="draft-section">'
        '<h2>Drafts</h2>'
        '<p class="hint">Only you and admins can see these.</p>'
        f'<div class="draft-grid">{cards}</div>'
        '</section>'
    )


def page_html(capabilities_dir, version, header='', header_style='', community=None):
    """The /capabilities page: a card grid grouped by category, generated from
    the capability records (`cards`, then a card per family), plus a modal that plays the clip and shows the longer text. Cards
    for a capability with no built clip (`capabilities_dir` unset, or missing
    that id's mp4) show a quiet "clip not built" placeholder instead of a
    player; the page still lists every capability's text either way.
    `header`/`header_style`: the library's shared page header and its CSS
    (pages.app_header), or nothing, for a single-project editor with no
    library to go back to. `community`: library.Library.community_view(user)
    (published/drafts/can_submit/is_admin/fetch), or None to leave the page
    byte-identical to one with no community feature at all (single-project
    mode, or a library with no accounts)."""
    has_community = community is not None
    is_admin = bool(community and community.get('is_admin'))
    published_by_category, published_by_family = {}, {}
    groupers = with_members()
    family_ids = {f.id for f in groupers}
    for entry in (community.get('published') if community else None) or []:
        if entry.get('family') in family_ids:
            published_by_family.setdefault(entry['family'], []).append(entry)
        else:
            published_by_category.setdefault(entry['category'], []).append(entry)
    built = available_ids(capabilities_dir)
    carded = cards()
    family_cards_by_category = {}
    for fam in registry.FAMILIES:
        members = _family_members(fam)
        if not members:
            continue
        title, description = REGISTRY_FAMILIES[fam]
        n = len(members)
        line = f"{description} ({n} capabilit{'ies' if n != 1 else 'y'})"
        ids_ = {t.id for t in members}
        poster = REGISTRY_FAMILY_POSTER.get(fam)
        thumb = _thumb_html(poster if poster in ids_ else members[0].id, built)
        card = (f'<a class="card" href="/capabilities/{fam}">'
                f'<span class="thumb">{thumb}</span>'
                f'<span class="meta"><strong>{_esc(title)}</strong><span>{_esc(line)}</span></span></a>')
        family_cards_by_category.setdefault(FAMILY_CATEGORY[fam], []).append(card)
    parts = []
    if showcase_available(capabilities_dir):
        name = SHOWCASE_FILES[0]
        tall = SHOWCASE_FILES[1]
        portrait = (f' data-portrait="{tall}"'
                    if os.path.exists(clip_file(capabilities_dir, tall, 'mp4')) else '')
        parts.append(
            f'<section class="reel" aria-label="Showcase"{portrait}>'
            '<div class="player">'
            f'<video id="reel" src="/capabilities/{name}.mp4" poster="/capabilities/{name}.jpg" loop muted playsinline '
            'preload="metadata" aria-label="Showcase: every capability in one film"></video>'
            '<button class="unmute" id="reel-unmute" type="button">Unmute</button>'
            '<button class="fullscreen" id="reel-fullscreen" type="button">Full screen</button>'
            '</div>'
            '<p>Every shot in this reel is one of the capabilities below; its tag is the card\'s title.</p>'
            '</section>')
    for section in categories():
        family = next((f for f in groupers if f.category == section), None)
        if family is not None:          # a grouping capability is a section of its own
            parts.append(f'<h2>{_esc(section)}</h2>')
            parts.append(_family_section_html(family, built, published_by_family.get(family.id, []), is_admin))
            continue
        parts.append(f'<h2>{_esc(section)}</h2><div class="grid">')
        for e in carded:
            if e.category != section:
                continue
            parts.append(_card_html(e.id, e.name, e.definition, _thumb_html(e.id, built), e.source))
        for entry in published_by_category.get(section, []):
            parts.append(_community_card_html(entry, is_admin))
        parts.extend(family_cards_by_category.get(section, []))
        parts.append('</div>')
    data = []
    for e in carded:
        item = {'id': e.id, 'title': e.name, 'category': category(e), 'description': e.description,
                'prompts': list(e.phrasings), 'available': e.id in built, 'unmute': e.id == 'beat-lock'}
        if e.members:
            item.update(members=len(e.members.ids) + len(published_by_family.get(e.id, [])),
                        plural=e.members.noun[1])
        p = parent(e)
        if p:
            item.update(family=p.id, kindTitle=_kind_title(e))
        registry_id = _registry_overlap(e.id)
        if registry_id:
            t = registry.get(registry_id)
            item['regOverlap'] = {'id': t.id, 'family': t.family, 'title': t.name}
        data.append(item)
    registry_search_data = [{'id': t.id, 'title': t.name, 'family': t.family, 'aliases': list(t.aliases)}
                           for t in registry.catalog() if not has_card(t)]
    registry_search_json = json.dumps(registry_search_data).replace('<', '\\u003c')
    registry_search_script = (f'<script id="registry-search-data" type="application/json">'
                             f'{registry_search_json}</script>')
    body = ''.join(parts)
    can_submit = bool(community and community.get('can_submit'))
    add_button = ('<button type="button" id="add-capability" class="btn btn-primary">Add capability</button>'
                  if can_submit else '')
    dialog_html = dialog_script = community_style = community_data_script = community_script = drafts_html = ''
    style = _PAGE_STYLE + header_style
    if can_submit:
        from ..pages import DROP_SCRIPT
        style += _ADD_CAPABILITY_STYLE
        dialog_html = _add_capability_html(bool(community.get('fetch')))
        dialog_script = f'<script>{_ADD_CAPABILITY_SCRIPT}</script>' + DROP_SCRIPT
    if has_community:
        style += _COMMUNITY_STYLE
        community_script = f'<script>{_COMMUNITY_SCRIPT}</script>'
        drafts_html = _drafts_section_html(community.get('drafts') or [], is_admin)
        community_data = []
        for e in community.get('published') or []:
            item = {'id': 'community:' + e['slug'], 'title': e['title'], 'category': e['category'],
                    'description': e['description'], 'prompts': list(e['prompts']),
                    'available': bool(e.get('available')),
                    'unmute': False, 'clip': f'/capabilities/community/{e["slug"]}.mp4',
                    'poster': f'/capabilities/community/{e["slug"]}.jpg'}
            if e.get('family') in family_ids:
                item.update(family=e['family'], kindTitle=_kind_title(e))
            community_data.append(item)
        community_json = json.dumps(community_data).replace('<', '\\u003c')
        community_data_script = f'<script id="community-data" type="application/json">{community_json}</script>'
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>Capabilities · videobuilder</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<style>{style}</style></head><body>{header}'
        f'<main><div class="cap-head"><h1>Capabilities</h1>'
        f'<span class="version">videobuilder v{_esc(version)}</span>'
        '<input type="search" id="cap-search" class="cap-search" placeholder="Search capabilities…" '
        f'aria-label="Search capabilities" autocomplete="off" spellcheck="false">{add_button}</div>'
        f'{drafts_html}'
        f'{body}<ul class="search-hide" id="reg-hits" aria-label="Matching capabilities"></ul>'
        '<p class="search-none search-hide" id="search-none" role="status"></p></main>'
        '<div id="modal" hidden role="dialog" aria-modal="true" aria-labelledby="modal-title">'
        '<div class="box">'
        '<button class="close" id="modal-close" aria-label="Close">&times;</button>'
        '<video id="modal-video" autoplay loop muted playsinline hidden></video>'
        '<div class="placeholder" id="modal-placeholder"><span>clip not built</span></div>'
        '<button class="unmute" id="modal-unmute" hidden>Unmute</button>'
        '<div class="body">'
        '<h3 id="modal-title"></h3><p class="cat" id="modal-cat"></p>'
        '<p class="cap-id" id="modal-id" hidden><code id="modal-id-code"></code>'
        '<button type="button" class="copy-id" id="modal-copy">Copy</button></p>'
        '<p class="desc" id="modal-desc"></p>'
        '<div class="prompts"><p>What to tell the builder</p><ul id="modal-prompts"></ul></div>'
        '<p class="reg-overlap" id="modal-reg-overlap" hidden></p>'
        '</div></div></div>' + dialog_html +
        f'<script id="capabilities-data" type="application/json">{json.dumps(data)}</script>' +
        community_data_script + registry_search_script +
        f'<script>{_PAGE_SCRIPT}</script><script>{_SEARCH_SCRIPT}</script>' + dialog_script + community_script +
        '</body></html>'
    )
    return html.encode()
