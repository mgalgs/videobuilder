"""The admin-only compendium vote feed: `/compendium`, its clips and its
vote store. The owner scrolls every component and recipe preview on his
phone and votes up or down; the votes are kept (in full, as data for
steering future components) in an append-only JSONL file, one line per vote
event, the current state being the last event per (user, id).

    GET  /compendium                     the feed page
    GET  /api/compendium                 {items, votes}
    POST /api/compendium/vote {id, vote: "up"|"down"|null, reason?}
    GET  /compendium/<id>-<format>.mp4|.jpg  a built clip or poster

Serving follows capabilities.py's pattern: a clip id is only ever looked up
by membership (here, in the built `index.json`), never built from the
request string directly.
"""
import datetime
import json
import os
import threading

VOTES = ('up', 'down', None)
MAX_REASON = 300


class CompendiumVotes:
    """`path`'s append-only JSONL: one line per vote event (`at`, `by`, `id`,
    `vote`, `reason`, `version`). The current state is the last event per
    (by, id); nothing is ever rewritten or compacted, so the full history is
    kept as data."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()

    def _events(self):
        """Every event line parsed, skipping one that fails: a process killed
        or a disk filling mid-append can leave a torn last line, and that
        must not cost every vote recorded before it."""
        try:
            with open(self.path, encoding='utf-8') as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            return []
        events = []
        for line in lines:
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        return events

    def for_user(self, user):
        """{id: {"vote", "reason"}}, `user`'s current votes: the last event
        per id, among events attributed to `user`."""
        current = {}
        for event in self._events():
            if event.get('by') == user:
                current[event['id']] = event
        return {id: {'vote': e['vote'], 'reason': e.get('reason')} for id, e in current.items()}

    def record(self, user, id, vote, reason):
        from . import __version__
        event = {'at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                 'by': user, 'id': id, 'vote': vote, 'reason': reason, 'version': __version__}
        with self.lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + '\n')
        return event


def known_ids():
    from . import compendium
    return set(compendium.ids()) | set(compendium.recipe_ids())


def validate_vote(body):
    """`(id, vote, reason)` from a vote POST body, or raises `ValueError`
    with a plain message naming what's wrong. `body` is already known to be
    a JSON object (the request body parser enforces that)."""
    id = body.get('id')
    if not isinstance(id, str) or id not in known_ids():
        raise ValueError('id must be a known component or recipe id')
    vote = body.get('vote')
    if vote not in VOTES:
        raise ValueError('vote must be "up", "down" or null')
    reason = body.get('reason')
    if reason is not None and (not isinstance(reason, str) or len(reason) > MAX_REASON):
        raise ValueError(f'reason must be a string of at most {MAX_REASON} characters')
    return id, vote, reason


def _load_index(compendium_dir):
    if compendium_dir is None:
        return None
    try:
        with open(os.path.join(compendium_dir, 'index.json'), encoding='utf-8') as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return None


def clip_file(compendium_dir, clip_id, kind):
    """The clip ('mp4') or poster ('jpg') path for `<component-or-recipe-id>
    -<format>`, or None for an id not in the built index (never built from
    the request string directly) or a dir that isn't configured."""
    index = _load_index(compendium_dir)
    if index is None:
        return None
    known = {f"{c['id']}-{c['format']}" for c in index['clips']}
    if clip_id not in known:
        return None
    return os.path.join(compendium_dir, f'{clip_id}.{kind}')


def feed_items(compendium_dir):
    """Every component, then every recipe, in catalog order: `id`, `kind`
    ('recipe' for a recipe), `tags`, `description`, the formats actually
    built (`[]` with no `compendium_dir`, or a clip not yet built) and, for a
    built transition, its `loop` window in seconds (else null)."""
    from . import compendium
    index = _load_index(compendium_dir)
    by_id = {}
    if index:
        for c in index['clips']:
            entry = by_id.setdefault(c['id'], {'formats': [], 'loop': c.get('loop')})
            entry['formats'].append(c['format'])
    items = []
    for c in compendium.CATALOG:
        entry = by_id.get(c.id, {'formats': [], 'loop': None})
        items.append({'id': c.id, 'is_recipe': False, 'kind': c.kind, 'tags': list(c.tags),
                     'description': c.description, 'formats': sorted(entry['formats']), 'loop': entry['loop']})
    for r in compendium.RECIPES:
        entry = by_id.get(r.id, {'formats': [], 'loop': None})
        items.append({'id': r.id, 'is_recipe': True, 'kind': 'recipe', 'tags': [],
                     'description': r.description, 'formats': sorted(entry['formats']), 'loop': None})
    return items


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


_PAGE_STYLE = """
body{font:16px/1.5 system-ui,sans-serif;background:#0d0d10;color:#eee;margin:0;
  display:flex;flex-direction:column;height:100vh;height:100dvh}
.signed-out-banner{flex:none;padding:10px 24px;border-bottom:1px solid #1f1f25;background:#2a1a18;color:#ffb4ad}
.signed-out-banner a{color:#e5483b;font-weight:600}
header{flex:none;background:#141417;border-bottom:1px solid #26262c;
  padding:10px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
header a.back{color:#a9a9b2;text-decoration:none;font-weight:600;margin-right:4px}
header h1{font-size:16px;margin:0;margin-right:auto}
#filters{display:flex;gap:6px;flex-wrap:wrap}
#filters button{min-height:36px;padding:6px 12px;border-radius:8px;border:1px solid #26262c;
  background:#1b1e24;color:#eee;font-size:13px;cursor:pointer}
#filters button[aria-pressed="true"]{background:#e5483b;border-color:#e5483b}
#count{font-size:12.5px;color:#a9a9b2;width:100%}
#feed{flex:1;min-height:0;overflow-y:auto;scroll-snap-type:y mandatory}
.item{height:100%;scroll-snap-align:start;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:16px;box-sizing:border-box;border-bottom:1px solid #141417}
.item .player{position:relative;max-height:62%;max-width:92%;background:#000;border-radius:14px;overflow:hidden}
.item video{display:block;max-height:62vh;max-width:92vw}
.item .placeholder{width:280px;height:498px;background:#141417;display:flex;align-items:center;
  justify-content:center;color:#5a5d66;border-radius:14px}
.item .meta{max-width:92vw;margin-top:14px;text-align:center}
.item .meta .id{font-size:16px;font-weight:700}
.item .meta .kind{color:#a9a9b2;font-size:12.5px;text-transform:uppercase;letter-spacing:.03em;margin-left:8px}
.item .meta .tags{color:#a9a9b2;font-size:12.5px;margin-top:4px}
.item .meta .desc{color:#dcdcdc;font-size:13.5px;margin-top:6px}
.votes{display:flex;gap:14px;margin-top:14px;align-items:center;justify-content:center}
.votes button{min-height:48px;min-width:64px;font-size:22px;border-radius:12px;border:1px solid #26262c;
  background:#141417;color:#eee;cursor:pointer}
.votes button[aria-pressed="true"].up{background:#1f6b3a;border-color:#1f6b3a}
.votes button[aria-pressed="true"].down{background:#8a2a2a;border-color:#8a2a2a}
.reason{display:none;margin-top:10px;width:92vw;max-width:420px}
.reason.open{display:block}
.reason textarea{width:100%;box-sizing:border-box;border-radius:8px;border:1px solid #26262c;
  background:#1b1e24;color:#eee;font:inherit;padding:8px;resize:vertical;min-height:44px}
.reason .err{color:#ff8a80;font-size:12.5px;margin-top:4px;display:none}
"""

_PAGE_SCRIPT = """
(function(){
  var feedEl = document.getElementById('feed');
  var countEl = document.getElementById('count');
  var banner = document.getElementById('signed-out-banner');
  var filterBtns = Array.prototype.slice.call(document.querySelectorAll('#filters button'));
  var state = {items: [], votes: {}, filter: 'unvoted'};
  var observer = new IntersectionObserver(function(entries){
    entries.forEach(function(e){
      var v = e.target.querySelector('video');
      if(!v) return;
      if(e.isIntersecting && e.intersectionRatio > 0.6){
        var loop = v.getAttribute('data-loop');
        if(loop){
          var bounds = loop.split(',').map(Number);
          if(v.currentTime < bounds[0] || v.currentTime >= bounds[1]) v.currentTime = bounds[0];
        }
        v.play().catch(function(){});
      } else {
        v.pause();
      }
    });
  }, {threshold: [0, 0.6]});
  function wide(){ return window.innerWidth > window.innerHeight; }
  function pickFormat(item){
    if(wide() && item.formats.indexOf('16x9') !== -1) return '16x9';
    if(item.formats.indexOf('9x16') !== -1) return '9x16';
    return item.formats[0];
  }
  function voteCount(){
    return state.items.filter(function(i){ return state.votes[i.id] && state.votes[i.id].vote; }).length;
  }
  function visible(item){
    var v = state.votes[item.id] && state.votes[item.id].vote;
    if(state.filter === 'all') return true;
    if(state.filter === 'unvoted') return !v;
    return v === state.filter;
  }
  function itemEl(item){
    var sec = document.createElement('section');
    sec.className = 'item';
    sec.dataset.id = item.id;
    var fmt = pickFormat(item);
    var player = document.createElement('div');
    player.className = 'player';
    if(fmt){
      var v = document.createElement('video');
      v.muted = true; v.playsInline = true; v.preload = 'metadata';
      v.poster = '/compendium/' + item.id + '-' + fmt + '.jpg';
      v.src = '/compendium/' + item.id + '-' + fmt + '.mp4';
      if(item.loop){
        v.setAttribute('data-loop', item.loop[0] + ',' + item.loop[1]);
        v.addEventListener('timeupdate', function(){
          if(v.currentTime >= item.loop[1]) v.currentTime = item.loop[0];
        });
      } else {
        v.loop = true;
      }
      player.appendChild(v);
    } else {
      var ph = document.createElement('div');
      ph.className = 'placeholder';
      ph.textContent = 'preview not built';
      player.appendChild(ph);
    }
    sec.appendChild(player);
    var meta = document.createElement('div');
    meta.className = 'meta';
    meta.innerHTML = '<span class="id"></span><span class="kind"></span>' +
      '<div class="tags"></div><div class="desc"></div>';
    meta.querySelector('.id').textContent = item.id;
    meta.querySelector('.kind').textContent = item.is_recipe ? 'recipe' : item.kind;
    meta.querySelector('.tags').textContent = item.tags.join(', ');
    meta.querySelector('.desc').textContent = item.description;
    sec.appendChild(meta);
    var votes = document.createElement('div');
    votes.className = 'votes';
    var up = document.createElement('button');
    up.className = 'up'; up.type = 'button'; up.textContent = '\\uD83D\\uDC4D';
    up.setAttribute('aria-label', 'Keep');
    var down = document.createElement('button');
    down.className = 'down'; down.type = 'button'; down.textContent = '\\uD83D\\uDC4E';
    down.setAttribute('aria-label', 'Prune');
    votes.appendChild(up); votes.appendChild(down);
    sec.appendChild(votes);
    var reason = document.createElement('div');
    reason.className = 'reason';
    reason.innerHTML = '<textarea maxlength="300" placeholder="Why? (optional)"></textarea>' +
      '<div class="err"></div>';
    sec.appendChild(reason);
    function paint(){
      var current = state.votes[item.id] && state.votes[item.id].vote;
      up.setAttribute('aria-pressed', current === 'up' ? 'true' : 'false');
      down.setAttribute('aria-pressed', current === 'down' ? 'true' : 'false');
      reason.classList.toggle('open', current === 'down');
      if(current === 'down'){
        reason.querySelector('textarea').value = (state.votes[item.id] && state.votes[item.id].reason) || '';
      }
    }
    function setVote(vote, reasonText){
      var before = state.votes[item.id];
      state.votes[item.id] = {vote: vote, reason: reasonText || null};
      paint();
      renderCount();
      fetch('/api/compendium/vote', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: item.id, vote: vote, reason: reasonText || null})
      }).then(function(r){
        if(r.status === 401){ banner.hidden = false; throw new Error('signed out'); }
        if(!r.ok) throw new Error('save failed');
        return r.json();
      }).catch(function(){
        state.votes[item.id] = before;
        paint();
        renderCount();
        reason.querySelector('.err').style.display = 'block';
        reason.querySelector('.err').textContent = "Couldn't save -- try again.";
      });
    }
    up.addEventListener('click', function(){
      var current = state.votes[item.id] && state.votes[item.id].vote;
      setVote(current === 'up' ? null : 'up');
    });
    down.addEventListener('click', function(){
      var current = state.votes[item.id] && state.votes[item.id].vote;
      if(current === 'down'){ setVote(null); return; }
      setVote('down', reason.querySelector('textarea').value);
      reason.classList.add('open');
    });
    reason.querySelector('textarea').addEventListener('blur', function(){
      if((state.votes[item.id] || {}).vote === 'down'){
        setVote('down', reason.querySelector('textarea').value);
      }
    });
    paint();
    return sec;
  }
  function renderCount(){
    countEl.textContent = voteCount() + ' of ' + state.items.length + ' voted';
  }
  function render(){
    feedEl.querySelectorAll('.item').forEach(function(el){ observer.unobserve(el); });
    feedEl.innerHTML = '';
    state.items.filter(visible).forEach(function(item){
      var el = itemEl(item);
      feedEl.appendChild(el);
      observer.observe(el);
    });
    renderCount();
  }
  filterBtns.forEach(function(btn){
    btn.addEventListener('click', function(){
      state.filter = btn.getAttribute('data-filter');
      filterBtns.forEach(function(b){ b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
      render();
    });
  });
  fetch('/api/compendium').then(function(r){
    if(r.status === 401){ banner.hidden = false; return {items: [], votes: {}}; }
    if(!r.ok) throw new Error('load failed');
    return r.json();
  }).then(function(data){
    state.items = data.items || [];
    state.votes = data.votes || {};
    render();
  }).catch(function(){
    countEl.textContent = 'Could not load the compendium.';
  });
})();
"""


def page_html(compendium_dir, version):
    """The /compendium feed page: a phone-first vertical scroll-snap feed,
    fetched and rendered client-side from `/api/compendium` (so the server
    page itself carries no per-item data, unlike capabilities.page_html)."""
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>Compendium · videobuilder</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<style>{_PAGE_STYLE}</style></head><body>'
        '<div id="signed-out-banner" class="signed-out-banner" role="alert" hidden>'
        '<span>You’ve been signed out. <a href="/login" target="_blank" rel="noopener">Sign in again</a> '
        'to keep going; your votes are kept.</span></div>'
        '<header><a class="back" href="/" aria-label="Back">&larr;</a>'
        '<h1>Compendium</h1>'
        f'<span class="version" style="color:#a9a9b2;font-size:12px">v{_esc(version)}</span>'
        '<div id="filters">'
        '<button type="button" data-filter="unvoted" aria-pressed="true">Not voted yet</button>'
        '<button type="button" data-filter="all" aria-pressed="false">All</button>'
        '<button type="button" data-filter="up" aria-pressed="false">\U0001F44D</button>'
        '<button type="button" data-filter="down" aria-pressed="false">\U0001F44E</button>'
        '</div>'
        '<span id="count">0 of 0 voted</span>'
        '</header>'
        '<div id="feed"></div>'
        f'<script>{_PAGE_SCRIPT}</script>'
        '</body></html>'
    )
    return html.encode()
