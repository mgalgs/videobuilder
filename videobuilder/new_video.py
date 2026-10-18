"""What New video's Start building writes into a video beyond the blank film
`Library.create_blank` commits, and what it adds to the first note.

The page sends it on the first note (`POST /api/videos/first-note`), next to
the description, attachments and links:

    {"look": "woodblock", "length": "2:30",
     "film": {"acts": ["The river"],
              "clips": [{"source": "boat", "act": 0}, {"title": "Credits", "line": "...", "act": 0}],
              "lanes": [{"sound": "theme", "act": null}],
              "world": "...",
              "characters": [{"name": "Mara", "description": "...", "pictures": [attachment id...]}]}}

`look` is a `vb.looks` name, or "as-shot" (footage keeps its own look);
`length` is free text ("2:30"). In `film`, a clip with a `source` is footage
the page already uploaded to the video's sources; one with a `title` and a
`line` is a sketch of a clip for the builder to make. `act` is an index into
`acts`; a lane's `sound` is a source too, played over the whole video or one
act.

Footage makes the video a film of clips (see films.md): `start_files` writes
a small root title film, a `timeline.json` with one footage clip per source
in order (the whole file), each lane's sound as one item, and `.vb-cache/` in
`.gitignore`. Sketches, characters or a world make a planned film: a bible
(`bible/bible.md`, `bible/characters/<name>.md` with their pictures beside
them) for the builder to make the clips from. Neither: nothing is written,
and the first note is the same as it always was.
"""
from dataclasses import dataclass, field
import json
import re

from . import timeline_file

FPS = 30
FORMATS = ('16x9',)
AS_SHOT = 'as-shot'
MAX_TEXT = 4000
MAX_ITEMS = 200
PICTURE_EXTS = ('png', 'jpg', 'jpeg', 'webp', 'gif')


@dataclass
class Start:
    look: str | None = None
    length: str | None = None
    acts: list = field(default_factory=list)
    clips: list = field(default_factory=list)       # {'source'} or {'title', 'line'}, each with 'act'
    lanes: list = field(default_factory=list)       # {'sound', 'act'}
    world: str = ''
    characters: list = field(default_factory=list)  # {'name', 'description', 'pictures'}

    @property
    def footage(self):
        return [c for c in self.clips if 'source' in c]

    @property
    def sketches(self):
        return [c for c in self.clips if 'source' not in c]

    @property
    def planned(self):
        return bool(self.sketches or self.characters or self.world)

    def picture_ids(self):
        return [p for c in self.characters for p in c['pictures']]


def _text(value, what, limit=MAX_TEXT):
    if value is None:
        return ''
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f'{what} must be text of at most {limit} characters')
    return value.strip()


def _list(value, what):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ValueError(f'{what} must be a list of at most {MAX_ITEMS}')
    return value


def _act(raw, acts, what):
    act = raw.get('act')
    if act is None:
        return None
    if isinstance(act, bool) or not isinstance(act, int) or not 0 <= act < len(acts):
        raise ValueError(f'{what}.act must be the index of one of the acts')
    return act


def parse(body):
    """The `Start` in a first note's body; raises ValueError (a 400) on a
    malformed one. A body without any of these keys is an empty Start."""
    from . import looks
    look = body.get('look')
    if look is not None:
        if not isinstance(look, str):
            raise ValueError('look must be a look name')
        if look != AS_SHOT:
            try:
                look = looks.get(look).name
            except (KeyError, ValueError):
                raise ValueError(f'no look called {look!r}') from None
    start = Start(look=look, length=_text(body.get('length'), 'length', 16) or None)
    film = body.get('film')
    if film is None:
        return start
    if not isinstance(film, dict):
        raise ValueError('film must be an object')
    start.acts = [_text(a, 'an act title', 200) for a in _list(film.get('acts'), 'acts')]
    if not all(start.acts):
        raise ValueError('every act needs a title')
    for i, raw in enumerate(_list(film.get('clips'), 'clips')):
        what = f'clips[{i}]'
        if not isinstance(raw, dict):
            raise ValueError(f'{what} must be an object')
        if raw.get('source') is not None:
            if not isinstance(raw['source'], str):
                raise ValueError(f'{what}.source must be a source name')
            clip = {'source': raw['source']}
        else:
            clip = {'title': _text(raw.get('title'), f'{what}.title', 200),
                    'line': _text(raw.get('line'), f'{what}.line')}
            if not clip['title'] and not clip['line']:
                raise ValueError(f'{what} needs a source, or a title or a line')
        clip['act'] = _act(raw, start.acts, what)
        start.clips.append(clip)
    for i, raw in enumerate(_list(film.get('lanes'), 'lanes')):
        what = f'lanes[{i}]'
        if not isinstance(raw, dict) or not isinstance(raw.get('sound'), str):
            raise ValueError(f'{what} needs a sound: a source name')
        start.lanes.append({'sound': raw['sound'], 'act': _act(raw, start.acts, what)})
    start.world = _text(film.get('world'), 'world')
    names, slugs = set(), set()
    for i, raw in enumerate(_list(film.get('characters'), 'characters')):
        what = f'characters[{i}]'
        if not isinstance(raw, dict):
            raise ValueError(f'{what} must be an object')
        name = _text(raw.get('name'), f'{what}.name', 80)
        if not name.strip() or name.strip().casefold() in names:
            raise ValueError(f'{what} needs a name of its own')
        names.add(name.strip().casefold())
        # The slug is only a file name: a name with no ASCII letters ("Анна")
        # or one that differs only by punctuation still gets a file of its own.
        base = _slug(name) or f'character-{i + 1}'
        slug, n = base, 2
        while slug in slugs:
            slug, n = f'{base}-{n}', n + 1
        slugs.add(slug)
        pictures = _list(raw.get('pictures'), f'{what}.pictures')
        if not all(isinstance(p, str) for p in pictures):
            raise ValueError(f'{what}.pictures must be attachment ids')
        start.characters.append({'name': name, 'slug': slug,
                                 'description': _text(raw.get('description'), f'{what}.description'),
                                 'pictures': pictures})
    return start


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:60]


def _frames(seconds):
    return int((seconds or 0) * FPS)


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


def timeline(start, sources):
    """The timeline file (a dict) for `start`'s footage, with `sources`
    {name: source meta} holding every source it names. Raises ValueError
    for a source that is missing or too short to show."""
    def meta(name):
        try:
            return sources[name]
        except KeyError:
            raise ValueError(f'no source called {name!r}; upload it first') from None

    clips, ids, spans = [], set(), {}
    at = 0
    for c in start.footage:
        m = meta(c['source'])
        if m.get('width') is None:
            raise ValueError(f'{c["source"]} is a sound, not footage: drop it on Audio')
        # Rounded as `assembly.assemble` rounds a footage file's length.
        frames = round((m.get('duration') or 0) * FPS)
        if frames < 1:
            raise ValueError(f'{c["source"]} is too short to use as a clip')
        cid, n = m['name'], 2
        while cid in ids:
            cid, n = f'{m["name"]}-{n}', n + 1
        ids.add(cid)
        clips.append({'id': cid, 'footage': f'sources/{m["name"]}.{m["ext"]}', 'in': 0, 'out': frames})
        if c['act'] is not None:
            first, last = spans.get(c['act'], (at, at))
            spans[c['act']] = (first, at + frames)
        at += frames
    total = at
    data = {'version': timeline_file.VERSION, 'fps': FPS, 'formats': list(FORMATS), 'clips': clips}
    acts = [{'title': title, 'clips': [clips[i]['id'] for i, c in enumerate(start.footage) if c['act'] == n]}
            for n, title in enumerate(start.acts)]
    # With planned clips still to make, the acts are the bible's, and the
    # builder puts them in the timeline along with those clips.
    if not start.sketches and any(a['clips'] for a in acts):
        data['acts'] = [a for a in acts if a['clips']]
    lanes = []
    for lane in start.lanes:
        m = meta(lane['sound'])
        begin, end = (0, total) if lane['act'] is None else spans.get(lane['act'], (0, total))
        frames = min(_frames(m.get('duration')), end - begin)
        if frames < 1:
            raise ValueError(f'{lane["sound"]} is too short to play')
        lanes.append({'items': [{'sound': f'sources/{m["name"]}.{m["ext"]}', 'at': begin, 'offset': 0,
                                 'frames': frames}]})
    if lanes:
        data['lanes'] = lanes
    try:
        timeline_file.parse(data)
    except timeline_file.TimelineError as exc:
        raise ValueError(str(exc)) from None
    return data


def _look_line(look):
    from . import looks
    if look == AS_SHOT:
        return 'as shot. The footage keeps its own look; don\'t restyle it.'
    return f'{looks.get(look).title} (`vb.looks` name `{look}`), for every clip.'


def _over(lane, start):
    return 'the whole film' if lane['act'] is None else f'Act {lane["act"] + 1} ({start.acts[lane["act"]]})'


def bible(title, description, start, sources, pictures):
    """The planned film's bible: {path: bytes}. `pictures` is [(character
    slug, file name, bytes)...], already read from their attachments."""
    out = {}
    lines = [f'# {title}', '']
    if description:
        lines += ['## Logline', '', description, '']
    if start.look:
        line = _look_line(start.look)
        lines += ['## Look', '', line[:1].upper() + line[1:], '']
    if start.world:
        lines += ['## World', '', start.world, '']
    if start.characters:
        lines += ['## Characters', '']
        for c in start.characters:
            lines.append(f'- {c["name"]}: characters/{c["slug"]}.md')
            mine = [name for slug, name, _ in pictures if slug == c['slug']]
            body = [f'# {c["name"]}', '']
            if c['description']:
                body += [c['description'], '']
            if mine:
                body += ['Pictures, beside this file:', ''] + [f'- {name}' for name in mine] + ['']
            out[f'bible/characters/{c["slug"]}.md'] = '\n'.join(body).encode()
        lines.append('')
    if start.clips:
        lines += ['## Outline', '']

        def clip_line(n, c):
            if 'source' in c:
                m = sources.get(c['source']) or {}
                return f'{n}. Footage: sources/{m.get("name", c["source"])}.{m.get("ext", "mp4")}'
            head = f'**{c["title"]}.** ' if c['title'] else ''
            return f'{n}. {head}{c["line"]}'.rstrip()

        number = 1
        if start.acts:
            loose = [c for c in start.clips if c['act'] is None]
            if loose:
                for c in loose:
                    lines.append(clip_line(number, c))
                    number += 1
                lines.append('')
            for a, act in enumerate(start.acts):
                lines += [f'### Act {a + 1}: {act}', '']
                for c in start.clips:
                    if c['act'] == a:
                        lines.append(clip_line(number, c))
                        number += 1
                lines.append('')
        else:
            for c in start.clips:
                lines.append(clip_line(number, c))
                number += 1
            lines.append('')
    if start.lanes:
        lines += ['## Audio', '']
        for i, lane in enumerate(start.lanes):
            m = sources.get(lane['sound']) or {}
            lines.append(f'- {timeline_file.lane_name(i)}: sources/{m.get("name", lane["sound"])}.'
                         f'{m.get("ext", "mp3")}, over {_over(lane, start)}')
        lines.append('')
    out['bible/bible.md'] = '\n'.join(lines).encode()
    for slug, name, data in pictures:
        out[f'bible/characters/{name}'] = data
    return out


def picture_name(slug, n, original):
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else 'png'
    return f'{slug}-{n}.{ext if ext in PICTURE_EXTS else "png"}'


def note_lines(start, sources):
    """The lines `start` adds to the first note, after the description."""
    lines = []
    if start.length:
        lines.append(f'Length: about {start.length}.')
    if start.look:
        lines.append('Look: ' + _look_line(start.look))
    footage = start.footage
    if footage:
        lines.append(f'This video is a film made of clips (timeline.json; see films.md): {len(footage)} footage '
                     f'clip{"" if len(footage) == 1 else "s"} from sources/, in the order the director put them, '
                     'each the whole file for now.')
        songs = [f'{timeline_file.lane_name(i)} (sources/{sources[l["sound"]]["name"]}.'
                 f'{sources[l["sound"]]["ext"]})' for i, l in enumerate(start.lanes) if l['sound'] in sources]
        if songs:
            lines.append(f'Cut these clips to the song on {songs[0]}.' if len(songs) == 1 else
                         'Cut these clips to the sound on ' + ', '.join(songs) + '.')
    if start.planned:
        lines.append('Make the clips of this film as planned in bible/bible.md: a clip directory for each clip '
                     'in its outline, put in order (and in its acts) by a timeline.json, as films.md says. '
                     'Every clip follows the bible\'s look, world and characters (bible/characters/).')
    elif start.lanes and not footage:
        lines.append('Audio: ' + '; '.join(f'{timeline_file.lane_name(i)} is sources/{sources[l["sound"]]["name"]}.'
                                          f'{sources[l["sound"]]["ext"]}, over {_over(l, start)}'
                                          for i, l in enumerate(start.lanes) if l['sound'] in sources) + '.')
    return lines


def start_files(title, description, start, sources, pictures):
    """Every file Start building writes for `start` ({path: bytes}, relative
    to the video's directory); {} for a plain short video."""
    out = {}
    if start.footage:
        out['film.py'] = title_film(title).encode()
        out['timeline.json'] = (json.dumps(timeline(start, sources), indent=2) + '\n').encode()
        out['.gitignore'] = b'.vb-cache/\n'
    if start.planned:
        out.update(bible(title, description, start, sources, pictures))
    return out
