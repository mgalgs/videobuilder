"""Rendering every registry capability's demo for review by eye: `<id>.mp4` and a
`<id>.jpg` poster each, and `index.html`, a self-contained gallery page (one
looping tile per capability, grouped by family and group, a filter box, light
and dark themes).

    python -m videobuilder capabilities gallery --out DIR [--only ID]... [--family F]
"""
import html
import os
import sys
import time
import traceback

from .registry import catalog, grouped, ids

POSTER_AT = 0.7  # how far into a demo its poster is taken: most demos have done their move by then


def _save_poster(film, path):
    from PIL import Image
    cv = film.frame(min(film.frames - 1, int(film.frames * POSTER_AT)))
    s = cv.surface
    s.flush()
    im = Image.frombuffer('RGBA', (s.get_width(), s.get_height()), bytes(s.get_data()), 'raw', 'BGRA',
                          s.get_stride(), 1)
    im.convert('RGB').save(path, 'JPEG', quality=82)


def build(out_dir, only=None, family=None, jobs=None, crf=30, log=None):
    """Render each capability (all, one `family`'s, or the ids in `only`) to
    `out_dir`, then write `index.html` for those that built. A capability that
    fails to build is reported, not fatal: the rest still build. Returns
    `(results, failures)`: `[{id, seconds, bytes}]` and `[(id, message)]`."""
    from ..render import render
    log = log or sys.stderr
    chosen = catalog(family)
    if only:
        unknown = set(only) - set(ids())
        if unknown:
            raise ValueError(f'unknown capability id(s): {", ".join(sorted(unknown))}')
        chosen = tuple(t for t in chosen if t.id in only)
    os.makedirs(out_dir, exist_ok=True)
    results, failures, built = [], [], []
    for t in chosen:
        t0 = time.time()
        mp4 = os.path.join(out_dir, f'{t.id}.mp4')
        try:
            film = t.demo()
            render(film, mp4, jobs=jobs, crf=crf, log=log)
            _save_poster(film, os.path.join(out_dir, f'{t.id}.jpg'))
        except Exception as e:  # noqa: BLE001 -- one bad demo must not stop a run over hundreds
            traceback.print_exc(file=log)
            failures.append((t.id, f'{type(e).__name__}: {e}'))
            continue
        built.append(t)
        results.append({'id': t.id, 'seconds': time.time() - t0, 'bytes': os.path.getsize(mp4)})
    with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as fh:
        fh.write(gallery_html(built))
    return results, failures


_CSS = """
:root { color-scheme: light dark; --bg: #f6f5f2; --panel: #ffffff; --ink: #1b1c20; --muted: #6b6f78;
  --line: #e2e0da; --accent: #d94a3b; --chip: #efede8; }
@media (prefers-color-scheme: dark) { :root { --bg: #111216; --panel: #1b1c22; --ink: #f1f1ee;
  --muted: #9a9ea8; --line: #2c2e36; --accent: #ef6b5c; --chip: #25272f; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { position: sticky; top: 0; z-index: 2; background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(8px); border-bottom: 1px solid var(--line); padding: 14px 28px;
  display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; }
header h1 { font-size: 18px; margin: 0; }
header .count { color: var(--muted); font-size: 13px; }
header input { flex: 1 1 240px; max-width: 380px; padding: 7px 12px; border-radius: 8px;
  border: 1px solid var(--line); background: var(--panel); color: var(--ink); font: inherit; }
nav { display: flex; flex-wrap: wrap; gap: 6px; }
nav a { font-size: 13px; text-decoration: none; color: var(--ink); background: var(--chip);
  padding: 3px 10px; border-radius: 99px; }
nav a:hover { background: var(--accent); color: #fff; }
main { padding: 8px 28px 60px; }
section > h2 { font-size: 22px; margin: 34px 0 4px; text-transform: capitalize; }
h3 { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
  margin: 18px 0 10px; font-weight: 600; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }
.tile { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.tile video { display: block; width: 100%; aspect-ratio: 16 / 9; background: #14151a; }
.tile .text { padding: 10px 14px 14px; }
.tile .name { font-weight: 650; font-size: 16px; }
.tile .meta { color: var(--muted); font-size: 12.5px; margin: 1px 0 6px; }
.tile code { font: 12px ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--accent); }
.tile p { margin: 0; font-size: 14px; }
.hidden { display: none !important; }
"""

_JS = """
const tiles = [...document.querySelectorAll('.tile')];
const io = new IntersectionObserver(entries => {
  for (const e of entries) { const v = e.target; if (e.isIntersecting) { v.play().catch(() => {}); } else { v.pause(); } }
}, {rootMargin: '200px'});
document.querySelectorAll('video').forEach(v => io.observe(v));
const q = document.getElementById('q'), count = document.getElementById('count');
function filter() {
  const words = q.value.toLowerCase().split(/\\s+/).filter(Boolean);
  let shown = 0;
  for (const t of tiles) {
    const hit = words.every(w => t.dataset.search.includes(w));
    t.classList.toggle('hidden', !hit); shown += hit;
  }
  for (const el of document.querySelectorAll('.group, section')) {
    el.classList.toggle('hidden', !el.querySelector('.tile:not(.hidden)'));
  }
  count.textContent = shown + ' of ' + tiles.length;
}
q.addEventListener('input', filter);
filter();
"""


def _family_title(slug):
    from . import REGISTRY_FAMILIES
    return REGISTRY_FAMILIES.get(slug, (slug,))[0]


def _tile(t):
    e = html.escape
    search = ' '.join((t.id, t.name, t.family, t.group, t.definition, *t.aliases, *t.phrasings)).lower()
    # A sound capability is the one tile worth hearing: controls, not muted.
    media = 'controls preload="none"' if t.family == 'sound' else 'muted loop playsinline preload="none"'
    return (f'<article class="tile" id="{e(t.id)}" data-search="{e(search)}">'
            f'<video src="{e(t.id)}.mp4" poster="{e(t.id)}.jpg" {media}></video>'
            f'<div class="text"><div class="name">{e(t.name)}</div>'
            f'<div class="meta">{e(_family_title(t.family))} / {e(t.group)} &middot; '
            f'<code>{e(t.id)}</code></div>'
            f'<p>{e(t.definition)}</p></div></article>')


def gallery_html(capabilities):
    """The gallery page for `capabilities`, whose clips and posters sit beside it."""
    groups = grouped(capabilities)
    nav = ''.join(f'<a href="#family-{fam}">{html.escape(_family_title(fam))}</a>' for fam, _ in groups)
    body = []
    for fam, gs in groups:
        body.append(f'<section id="family-{fam}"><h2>{html.escape(_family_title(fam))}</h2>')
        for g, ts in gs:
            body.append(f'<div class="group"><h3>{html.escape(g)}</h3><div class="grid">'
                        + ''.join(_tile(t) for t in ts) + '</div></div>')
        body.append('</section>')
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>videobuilder capabilities</title><style>{_CSS}</style></head><body>'
            '<header><h1>videobuilder capabilities</h1>'
            f'<span class="count" id="count">{len(capabilities)}</span>'
            '<input id="q" type="search" placeholder="Filter by name, family, words..." autocomplete="off">'
            f'<nav>{nav}</nav></header><main>{"".join(body)}</main><script>{_JS}</script></body></html>\n')
