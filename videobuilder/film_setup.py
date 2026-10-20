"""How a video is set up as a film beyond its code: what the editor's Film
details sheet writes, and how a blank video becomes a film of clips.

Film details -- the look, the length, the world and the characters -- live in
the video's bible (films.md, "The bible"), which every builder reads first:
`bible/bible.md` holds a `## Look`, `## Length`, `## World` and
`## Characters` section, and each character is `bible/characters/<slug>.md`
with its pictures beside it (`<slug>-<n>.<ext>`). A save rewrites only the
sections and characters that changed, so anything else in the bible (an
outline or a tone a builder wrote) stays as it is.

A blank video becomes a film of clips (films.md) with its first clip:
`start_files` writes a small root title film, a `timeline.json` holding that
one clip, and `.vb-cache/` in `.gitignore`. A clip is footage (a source, the
whole file) or planned: a clip directory whose film is a placeholder card with
the clip's title, and whose docstring is its line -- what the clip is for, as
every builder is shown it (film_brief) -- for the builder to make.
"""
from dataclasses import dataclass, field
import json
import re

from . import timeline_file

FPS = 30
FORMATS = ('16x9',)
AS_SHOT = 'as-shot'
MAX_TEXT = 4000
MAX_CHARACTERS = 50
MAX_PICTURES = 12
PICTURE_EXTS = ('png', 'jpg', 'jpeg', 'webp', 'gif')
BIBLE = 'bible/bible.md'
CHARACTERS = 'bible/characters'
# The sections the sheet owns, in the order a new bible lists them (after a Logline, if any).
ORDER = ('Logline', 'Look', 'Length', 'World', 'Characters')
PICTURES_LINE = 'Pictures, beside this file:'
PLAN_SECONDS = 3


@dataclass
class Details:
    look: str | None = None
    length: str | None = None
    world: str = ''
    characters: list = field(default_factory=list)  # {'name', 'slug', 'description', 'pictures': [file names]}


def _text(value, what, limit=MAX_TEXT):
    if value is None:
        return ''
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f'{what} must be text of at most {limit} characters')
    return value.strip()


def _list(value, what, limit):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f'{what} must be a list of at most {limit}')
    return value


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:60]


def look_name(look):
    """`look` as a `vb.looks` name, or AS_SHOT; None for none. ValueError for
    a look there is no such thing as."""
    from . import looks
    if look in (None, ''):
        return None
    if not isinstance(look, str):
        raise ValueError('look must be a look name')
    if look == AS_SHOT:
        return look
    try:
        return looks.get(look).name
    except (KeyError, ValueError):
        raise ValueError(f'no look called {look!r}') from None


def parse_details(body, current):
    """The Details a save asks for, from its body; `current` is what the bible
    says now. Each character is {'slug'?, 'name', 'description', 'keep':
    [its picture file names to keep], 'add': [attachment ids]}: a character
    with the slug of a current one is that character (renamed, perhaps), one
    without is new. Returns (details, added): `added` is [(slug, attachment
    id)...], the pictures still to read, in order. ValueError (a 400) for a
    malformed one."""
    details = Details(look=look_name(body.get('look')),
                      length=_text(body.get('length'), 'length', 80) or None,
                      # A `## ` line in it would start a section of its own in bible.md (see _split).
                      world=re.sub(r'(?m)^## ', '### ', _text(body.get('world'), 'world')))
    known = {c['slug']: c for c in current.characters}
    names, slugs, added = set(), set(), []
    raws = _list(body.get('characters'), 'characters', MAX_CHARACTERS)
    # A current character keeps its file: its slug is taken before any new one picks one.
    taken = {r.get('slug') for r in raws if isinstance(r, dict) and r.get('slug') in known}
    for i, raw in enumerate(raws):
        what = f'characters[{i}]'
        if not isinstance(raw, dict):
            raise ValueError(f'{what} must be an object')
        name = _text(raw.get('name'), f'{what}.name', 80)
        if not name or name.casefold() in names:
            raise ValueError(f'{what} needs a name of its own')
        names.add(name.casefold())
        slug = raw.get('slug')
        if slug is not None and slug not in known:
            raise ValueError(f'{what}: no character {slug!r} in this film; reload to see it')
        if slug is None:
            # The slug is only a file name: a name with no ASCII letters ("Анна")
            # or one that differs only by punctuation still gets a file of its own.
            base = _slug(name) or f'character-{i + 1}'
            slug, n = base, 2
            while slug in slugs or slug in taken:
                slug, n = f'{base}-{n}', n + 1
        slugs.add(slug)
        keep = _list(raw.get('keep'), f'{what}.keep', MAX_PICTURES)
        have = known[slug]['pictures'] if slug in known else []
        if not all(isinstance(p, str) and p in have for p in keep):
            raise ValueError(f'{what}.keep must name its own pictures')
        add = _list(raw.get('add'), f'{what}.add', MAX_PICTURES)
        if not all(isinstance(p, str) for p in add):
            raise ValueError(f'{what}.add must be attachment ids')
        if len(keep) + len(add) > MAX_PICTURES:
            raise ValueError(f'{what} can have at most {MAX_PICTURES} pictures')
        added += [(slug, p) for p in add]
        details.characters.append({'name': name, 'slug': slug, 'pictures': list(keep),
                                   'description': _text(raw.get('description'), f'{what}.description')})
    return details, added


def picture_name(slug, n, original):
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else 'png'
    return f'{slug}-{n}.{ext if ext in PICTURE_EXTS else "png"}'


def look_line(look):
    from . import looks
    if look == AS_SHOT:
        return 'as shot. The footage keeps its own look; don\'t restyle it.'
    return f'{looks.get(look).title} (`vb.looks` name `{look}`), for every clip.'


# ---- the bible, read and written ----

def _split(md):
    """(head, [[title, body]...]) of a bible.md, split at its `## ` headings."""
    head, sections = [], []
    for line in md.splitlines():
        if line.startswith('## '):
            sections.append([line[3:].strip(), []])
        elif sections:
            sections[-1][1].append(line)
        else:
            head.append(line)
    return '\n'.join(head).strip(), [[t, '\n'.join(b).strip()] for t, b in sections]


def _join(head, sections):
    parts = [head] + [f'## {t}\n\n{b}' if b else f'## {t}' for t, b in sections]
    return '\n\n'.join(p for p in parts if p) + '\n'


def _character_file(c):
    body = [f'# {c["name"]}', '']
    if c['description']:
        body += [c['description'], '']
    if c['pictures']:
        body += [PICTURES_LINE, ''] + [f'- {name}' for name in c['pictures']] + ['']
    return '\n'.join(body).encode()


def _read_character(directory, slug, name):
    path = directory / CHARACTERS / f'{slug}.md'
    try:
        lines = path.read_text(errors='replace').splitlines()
    except OSError:
        return None
    if lines and lines[0].startswith('# '):
        name, lines = lines[0][2:].strip() or name, lines[1:]
    pictures, rest, listing = [], [], False
    for line in lines:
        if line.strip() == PICTURES_LINE:
            listing = True
        elif listing and line.startswith('- '):
            pictures.append(line[2:].strip())
        elif listing and not line.strip():
            continue
        else:
            listing = False
            rest.append(line)
    pictures = [p for p in pictures if '/' not in p and (directory / CHARACTERS / p).is_file()]
    return {'name': name, 'slug': slug, 'description': '\n'.join(rest).strip(), 'pictures': pictures}


def read_details(directory):
    """The Details of the video in `directory` (a Path), from its bible; an
    empty one without a bible."""
    try:
        md = (directory / BIBLE).read_text(errors='replace')
    except OSError:
        md = ''
    _, sections = _split(md)
    text = {t: b for t, b in sections}
    details = Details(world=text.get('World', ''))
    look = text.get('Look', '')
    m = re.search(r'`vb\.looks` name `([^`]+)`', look)
    if m:
        details.look = m.group(1)
    elif look.lower().startswith('as shot'):
        details.look = AS_SHOT
    m = re.fullmatch(r'about (.+?)\.?', text.get('Length', ''), re.I | re.S)
    details.length = (m.group(1) if m else text.get('Length')) or None
    listed = [(s, n) for n, s in re.findall(r'^- (.+?): characters/([^/\s]+)\.md\s*$',
                                            text.get('Characters', ''), re.M)]
    folder = directory / CHARACTERS
    loose = sorted(p.stem for p in folder.glob('*.md')) if folder.is_dir() else []
    seen = set()
    for slug, name in listed + [(s, s) for s in loose]:
        if slug in seen:
            continue
        seen.add(slug)
        c = _read_character(directory, slug, name)
        if c:
            details.characters.append(c)
    return details


def bible_files(title, md, current, new, pictures):
    """What a save writes: {path: bytes, or None to remove it}, relative to
    the video's directory. `md` is the bible.md there now ('' for none),
    `current` and `new` the Details before and after, and `pictures`
    {slug: [(original file name, bytes)...]}, the pictures added to each
    character, in order (their names are picked here, into `new`)."""
    out = {}
    before = {c['slug']: c for c in current.characters}
    for c in new.characters:
        names = set(before.get(c['slug'], {}).get('pictures', ())) | set(c['pictures'])
        n = 1
        for original, data in pictures.get(c['slug'], ()):
            while picture_name(c['slug'], n, original) in names:
                n += 1
            name = picture_name(c['slug'], n, original)
            names.add(name)
            c['pictures'].append(name)
            out[f'{CHARACTERS}/{name}'] = data
        old = before.get(c['slug'])
        if old is None or any(old[k] != c[k] for k in ('name', 'description', 'pictures')):
            out[f'{CHARACTERS}/{c["slug"]}.md'] = _character_file(c)
        for gone in set(old['pictures'] if old else ()) - set(c['pictures']):
            out[f'{CHARACTERS}/{gone}'] = None
    kept = {c['slug'] for c in new.characters}
    for slug, old in before.items():
        if slug not in kept:
            out[f'{CHARACTERS}/{slug}.md'] = None
            for name in old['pictures']:
                out[f'{CHARACTERS}/{name}'] = None
    head, sections = _split(md)
    wanted = {}
    if new.look != current.look:
        wanted['Look'] = '' if new.look is None else (lambda s: s[:1].upper() + s[1:])(look_line(new.look))
    if new.length != current.length:
        wanted['Length'] = f'About {new.length}.' if new.length else ''
    if new.world != current.world:
        wanted['World'] = new.world
    if [(c['slug'], c['name']) for c in new.characters] != [(c['slug'], c['name']) for c in current.characters]:
        wanted['Characters'] = '\n'.join(f'- {c["name"]}: characters/{c["slug"]}.md' for c in new.characters)
    if not wanted and not out:
        return {}
    for t, body in wanted.items():
        at = next((i for i, s in enumerate(sections) if s[0] == t), None)
        if at is not None:
            if body:
                sections[at][1] = body
            else:
                del sections[at]
        elif body:
            earlier = ORDER[:ORDER.index(t)]
            after = [i for i, s in enumerate(sections) if s[0] in earlier]
            sections.insert(after[-1] + 1 if after else 0, [t, body])
    if wanted:
        text = _join(head or f'# {title}', sections)
        if text != md:
            out[BIBLE] = text.encode()
    return out


def note_lines(details):
    """What a video's first note adds about the film details already set:
    the look and the length, and where the world and characters are."""
    lines = []
    if details.length:
        lines.append(f'Length: about {details.length}.')
    if details.look:
        lines.append('Look: ' + look_line(details.look))
    if details.world or details.characters:
        lines.append('This film has a bible: read bible/bible.md first, with its world and characters '
                     '(bible/characters/, each with any pictures beside it), and keep every clip true to it.')
    return lines


# ---- a film of clips, from its first clip ----

def title_film(title):
    """The root film of a film of clips: a title card at the timeline's fps and
    formats, so the editor finds the video (films.md)."""
    return (
        "import videobuilder as vb\n"
        "from videobuilder import text\n\n"
        "TITLE = " + json.dumps(title) + "\n\n"
        f"T = vb.Timeline(vb.Grid(fps={FPS}, bpm=120), [\n"
        "    vb.Segment('title', 0, 4, dict(title=TITLE)),\n"
        "], end=4)\n\n\n"
        "def draw(n, cv):\n"
        "    cv.rect(0, 0, cv.width, cv.height, '#101418')\n"
        "    font = vb.Font('Sans', cv.height / 12, weight=700)\n"
        "    lines = text.wrap(TITLE, font, cv.width * 0.8)\n"
        "    w, h = text.block_size(lines, font)\n"
        "    text.draw(cv, lines, font, (cv.width - w) / 2, (cv.height - h) / 2, '#f4f4f2', align='center')\n\n\n"
        f"FILM = vb.Film(draw=draw, timeline=T, formats={FORMATS!r})\n"
    )


def _new_id(name, taken):
    base = _slug(name) or 'clip'
    cid, n = base, 2
    while cid in taken:
        cid, n = f'{base}-{n}', n + 1
    return cid


def footage_clip(meta, seconds, taken=()):
    """The timeline entry for a whole footage source: `meta` its source
    record, `seconds` its picture's length (as `assembly.probe` measures it:
    the container's can run longer with a trailing audio tail)."""
    if meta.get('width') is None:
        raise ValueError(f'{meta["name"]} is a sound, not footage: add it to Audio')
    frames = round((seconds or 0) * FPS)
    if frames < 1:
        raise ValueError(f'{meta["name"]} is too short to use as a clip')
    return {'id': _new_id(meta['name'], taken), 'footage': f'sources/{meta["name"]}.{meta["ext"]}',
            'in': 0, 'out': frames}


def plan_text(title, line):
    """A planned clip's title and line, checked: (title, line)."""
    title, line = _text(title, 'title', 200), _text(line, 'line')
    if not title and not line:
        raise ValueError('a planned clip needs a title or a line')
    return title, line


def planned_film(title, line, formats):
    """A planned clip's film file: a card with its title and line until a
    builder makes the clip. The docstring's first paragraph is what the clip
    is for (film_brief shows builders that line)."""
    about = ' '.join((line or title).split()).replace('\\', '/').replace('"""', "''")
    return (
        f'"""{about}\n\n'
        'Planned in the editor and not made yet: a builder makes this clip from the line above (and the\n'
        'bible, if the film has one), replacing this placeholder card."""\n'
        "import videobuilder as vb\n"
        "from videobuilder import text\n\n"
        f"TITLE = {json.dumps(title)}\n"
        f"LINE = {json.dumps(line)}\n\n"
        f"T = vb.Timeline(vb.Grid(fps={FPS}, bpm=120), [\n"
        "    vb.Segment('plan', 0, " + str(PLAN_SECONDS) + ", dict(title=TITLE)),\n"
        f"], end={PLAN_SECONDS})\n\n\n"
        "def draw(n, cv):\n"
        "    cv.rect(0, 0, cv.width, cv.height, '#16161b')\n"
        "    big = vb.Font('Sans', cv.height / 14, weight=700)\n"
        "    small = vb.Font('Sans', cv.height / 26)\n"
        "    head = text.wrap(TITLE, big, cv.width * 0.8) if TITLE else []\n"
        "    body = text.wrap(LINE, small, cv.width * 0.7) if LINE else []\n"
        "    hw, hh = text.block_size(head, big) if head else (0, 0)\n"
        "    bw, bh = text.block_size(body, small) if body else (0, 0)\n"
        "    gap = cv.height / 30 if head and body else 0\n"
        "    y = (cv.height - hh - gap - bh) / 2\n"
        "    if head:\n"
        "        text.draw(cv, head, big, (cv.width - hw) / 2, y, '#f4f4f2', align='center')\n"
        "    if body:\n"
        "        text.draw(cv, body, small, (cv.width - bw) / 2, y + hh + gap, '#a9a9b2', align='center')\n\n\n"
        f"FILM = vb.Film(draw=draw, timeline=T, formats={tuple(formats)!r})\n"
    )


def planned_clip(title, line, taken=(), formats=FORMATS):
    """(timeline entry, {path: bytes}) for a planned clip: its own clip
    directory, `clips/<id>`, holding `planned_film`."""
    title, line = plan_text(title, line)
    cid = _new_id(title or ' '.join(line.split()[:6]), taken)
    directory = f'clips/{cid}'
    return {'id': cid, 'dir': directory}, {f'{directory}/film.py': planned_film(title, line, formats).encode()}


def start_files(title, clip, clip_files=None):
    """Every file that makes a blank video a film of clips with `clip` (a
    timeline entry) as its first: {path: bytes}, relative to the video's
    directory. `clip_files` are the clip's own (a planned clip's directory)."""
    data = {'version': timeline_file.VERSION, 'fps': FPS, 'formats': list(FORMATS), 'clips': [clip]}
    timeline_file.parse(data)
    return {'film.py': title_film(title).encode(),
            'timeline.json': (json.dumps(data, indent=2) + '\n').encode(),
            '.gitignore': b'.vb-cache/\n', **(clip_files or {})}
