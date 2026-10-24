"""The `Capability` record every registry module defines as `CAPABILITY`, and
the families a capability belongs to (one subpackage each). Every capability
is one of these records, the ones with cards of their own on /capabilities
too; the parts a record may carry beyond the core fields are here as well:
`Example` (a worked example film as the demo, the one exemption from the
short-demo rule), `Members` and `MemberBrief` (a capability grouping
others, and what a community member of it ships) and `Source` (the post a
capability came from).

The record is checked when it is built, so a malformed capability fails at
import with a message naming it. `api` is only format-checked here; whether
each name resolves to a real object is checked by `registry.load`, after the
module defining it has finished importing.
"""
import importlib
import os
import re
from dataclasses import dataclass

from .settings import check as check_settings

FAMILIES = ('principles', 'typography', 'transitions', 'ui', 'shapes', 'particles', 'camera', 'vfx',
            'broadcast', 'sound')

# The /capabilities page's sections, in page order: a capability with a `category` has its own card in
# that section (see `Capability.category`); every other one is counted on its family's card.
CATEGORIES = ('Motion', 'Type and data', 'Imagery and camera', 'Looks', 'Type', 'Timing, sound and formats')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ID_RE = re.compile(r'\A[a-z][a-z0-9]*(-[a-z0-9]+)*\Z')
DOTTED_RE = re.compile(r'\A[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)+\Z')
MAX_DEFINITION = 240


def module_name(id):
    """A capability's module name: its id with `-` as `_`."""
    return id.replace('-', '_')


def resolve(dotted):
    """The object a dotted name such as `videobuilder.ease_out_back` names:
    the longest importable module prefix, then attributes from there. Raises
    `LookupError` saying which part is missing."""
    parts = dotted.split('.')
    for i in range(len(parts), 0, -1):
        name = '.'.join(parts[:i])
        try:
            obj = importlib.import_module(name)
        except ModuleNotFoundError as e:
            if e.name and not (name + '.').startswith(e.name + '.'):
                raise  # the module exists but one of its own imports is missing
            continue
        for attr in parts[i:]:
            if not hasattr(obj, attr):
                raise LookupError(f'{dotted}: {".".join(parts[:i])} has no {attr!r}')
            obj = getattr(obj, attr)
        return obj
    raise LookupError(f'{dotted}: no module {parts[0]!r}')


def _strings(owner, field, value, at_least=0):
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValueError(f'{owner}: {field} must be a tuple of strings, not {type(value).__name__}')
    for v in value:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f'{owner}: {field} has an empty or non-string entry {v!r}')
    if len(value) < at_least:
        raise ValueError(f'{owner}: {field} needs at least {at_least} entries, has {len(value)}')
    if len(set(value)) != len(value):
        raise ValueError(f'{owner}: {field} has duplicate entries')
    return tuple(value)


def _text(owner, field, value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f'{owner}: {field} must be non-empty text without surrounding spaces')
    return value


def _link(owner, field, value):
    if not isinstance(value, str) or not re.match(r'\Ahttps?://[^\s/]+\S*\Z', value):
        raise ValueError(f'{owner}: {field} must be an http(s) URL, not {value!r}')
    return value


@dataclass(frozen=True)
class Example:
    """A demo that is a worked example film, `path` (relative to the repo
    root, e.g. `examples/capabilities/eased-entrances.py`, defining `FILM`):
    `demo=Example(path)` instead of a `_demo.py` film. It is the one
    exemption from the registry's short-demo rule (16:9, about 2 to 5 s),
    made in the record itself: such a demo runs as long as the example needs,
    in its own format, and the gallery and the product film show it as it is.
    A capability with one may also give `api` as the usage lines that
    example writes (`vb.spring_at(f, fps, ...)`), shown as written rather than
    resolved."""
    path: str

    def __post_init__(self):
        if not isinstance(self.path, str) or not self.path.endswith('.py') or self.path.startswith('/'):
            raise ValueError(f'Example path {self.path!r} must be a repo-relative .py file')

    def __call__(self):
        from ..film import load
        return load(os.path.join(REPO_ROOT, self.path))


@dataclass(frozen=True)
class Source:
    """Where a capability came from: the post or page it was seen in (`url`)
    and who to credit for it (`credit`, the link's text), plus, when that post
    built on someone else's repo, the repo (`upstream`) and its credit
    (`upstream_credit`). Shown as a Source link on the capability's card and
    carried in the index JSON (`registry.index_data`)."""
    url: str
    credit: str
    upstream: str = ''
    upstream_credit: str = ''

    def __post_init__(self):
        _link('source', 'url', self.url)
        _text('source', 'credit', self.credit)
        if bool(self.upstream) != bool(self.upstream_credit):
            raise ValueError('source: give upstream and upstream_credit together, or neither')
        if self.upstream:
            _link('source', 'upstream', self.upstream)
            _text('source', 'upstream_credit', self.upstream_credit)

    def as_json(self):
        d = {'url': self.url, 'credit': self.credit}
        if self.upstream:
            d.update(upstream=self.upstream, upstream_credit=self.upstream_credit)
        return d


@dataclass(frozen=True)
class MemberBrief:
    """What a creator's new member of a grouping capability ships, and how
    its builder is briefed (community.brief): `file`, the member's own
    reusable code beside its demo (a look's look.py); `registry`, the module
    whose `get(name)` finds the built-in members (KeyError for none), so a
    new one can't take a built-in name, and whose `names()` the brief lists;
    `intro` (two paragraphs: its first line, then the contract to read),
    `code`, `film` and `doc`, the brief's lines for the member's file, its
    demo film.py and its capability.md. `{source}` in `code` becomes "post"
    or "page"."""
    file: str
    registry: str
    intro: tuple
    code: str
    film: str
    doc: str

    def __post_init__(self):
        object.__setattr__(self, 'intro', _strings('brief', 'intro', self.intro, at_least=2))
        for field in ('file', 'registry', 'code', 'film', 'doc'):
            _text('brief', field, getattr(self, field))


@dataclass(frozen=True)
class Members:
    """The capabilities one capability groups (Looks groups the named looks):
    the one way to group capabilities. `ids`, the members in the order the
    page and the sheet list them (each its own record, anywhere in the
    registry); `noun`, (singular, plural) for a member ("look", "looks";
    default "capability"); `lead`, the title of the grouping capability's
    own card when it has its section to itself, first there (its demo shows
    the members together), and `lead_line` its line ('': its `name` and
    `definition`).
    `kinds`, ((kind, heading, who it is for), ...), splits the members into
    groups under those headings, a member's `group` naming its kind's
    heading; empty keeps them in one. `names`, {member id: the name it
    answers to in the members' own registry module} (a look's name in
    videobuilder.looks), for those that have one. `brief` (MemberBrief), what
    a community member must ship for the page's add flow; None takes none."""
    ids: tuple
    noun: tuple = ('capability', 'capabilities')
    lead: str = ''
    lead_line: str = ''
    kinds: tuple = ()
    names: object = ()
    brief: object = None

    def __post_init__(self):
        set_ = lambda k, v: object.__setattr__(self, k, v)  # noqa: E731
        set_('ids', _strings('members', 'ids', self.ids, at_least=1))
        for i in self.ids:
            if not ID_RE.match(i):
                raise ValueError(f'members: id {i!r} is not kebab-case')
        set_('noun', _strings('members', 'noun', self.noun, at_least=2))
        if len(self.noun) != 2:
            raise ValueError('members: noun must be (singular, plural)')
        for field in ('lead', 'lead_line'):
            if getattr(self, field):
                _text('members', field, getattr(self, field))
        kinds = tuple(tuple(k) for k in self.kinds)
        if any(len(k) != 3 for k in kinds):
            raise ValueError('members: each kind must be (kind, heading, line)')
        set_('kinds', kinds)
        names = tuple(dict(self.names).items())
        if not {i for i, _ in names} <= set(self.ids):
            raise ValueError('members: names may only name members')
        set_('names', names)
        if self.brief is not None and not isinstance(self.brief, MemberBrief):
            raise ValueError('members: brief must be a MemberBrief')

    def name(self, id):
        """The name member `id` answers to in its registry module, or None
        (a member built by hand: paper collage)."""
        return dict(self.names).get(id)

    def kind(self, member):
        """The kind slug of `member` (a Capability): the kind whose heading
        is its `group`, or None for members with no kinds."""
        return next((k for k, heading, _ in self.kinds if heading == member.group), None)


@dataclass(frozen=True)
class Capability:
    """One named motion-design capability.

    `id`: kebab-case starting with a letter, the module's filename with `_` as `-`. `family`: the
    subpackage it lives in (one of `FAMILIES`); `group`: a free-text
    sub-heading within the family ("Easing", "Wipes"). `definition`: one
    plain sentence saying what it looks like. `phrasings`: at least two
    everyday ways someone might ask for it. `related`: ids of related
    capabilities, which need not exist yet. `api`: dotted names of what a film
    calls to use it. `demo`: a no-argument callable returning a short 16:9
    `videobuilder.Film` showing the capability alone (see `_demo.py`).
    `settings`: optional `Choice`/`Number` entries (settings.py) the editor
    shows as a card beside this capability's chip, e.g. voiceover's voice.

    The rest are optional, defaulting so most records never name them:
    `description`, a longer text for its modal on the /capabilities page;
    `doc`, the skill reference doc (`skill/make-a-video/reference/...md`) to
    read before using it; `poster`, the demo frame its poster is taken from
    (None: the default, see `registry.poster_frame`); `category`, one of
    `CATEGORIES`: the /capabilities page section where it has a card of its
    own, at position `order` (lowest first) -- empty (the default) shows it
    on its family's page instead, counted on that family's card; `members`
    (Members), the capabilities it groups, shown in its section after its
    own card; `old_ids`, ids it used to have before another capability was
    merged into it, still answered for it; `source` (Source), the post or
    page it came from. `demo` may be an `Example`: a worked example film,
    exempt from the short-demo rule (see Example).
    """
    id: str
    name: str
    family: str
    group: str
    definition: str
    phrasings: tuple
    api: tuple
    demo: object  # demo() -> videobuilder.Film
    aliases: tuple = ()
    related: tuple = ()
    settings: tuple = ()  # Choice/Number the editor shows as a card beside this capability's chip (see settings.py)
    description: str = ''
    doc: str = ''
    poster: object = None  # int frame, or None
    category: str = ''
    order: int = 0
    members: object = None  # Members, or None
    old_ids: tuple = ()
    source: object = None  # Source, or None

    def __post_init__(self):
        if not isinstance(self.id, str) or not ID_RE.match(self.id):
            raise ValueError(f'capability id {self.id!r} must be kebab-case starting with a letter: lowercase '
                             'letters and digits, joined by - (spell a leading number out: three-d-flip)')
        who = self.id
        for field in ('name', 'group', 'definition'):
            v = getattr(self, field)
            if not isinstance(v, str) or not v.strip() or v != v.strip():
                raise ValueError(f'{who}: {field} must be non-empty text without surrounding spaces')
        if self.family not in FAMILIES:
            raise ValueError(f'{who}: unknown family {self.family!r}; families are {", ".join(FAMILIES)}')
        if not self.definition.endswith('.') or len(self.definition) > MAX_DEFINITION:
            raise ValueError(f'{who}: definition must be one sentence ending in a full stop, '
                             f'at most {MAX_DEFINITION} characters')
        set_ = lambda k, v: object.__setattr__(self, k, v)  # noqa: E731 -- frozen: normalise lists to tuples
        set_('aliases', _strings(who, 'aliases', self.aliases))
        set_('phrasings', _strings(who, 'phrasings', self.phrasings, at_least=2))
        set_('related', _strings(who, 'related', self.related))
        set_('api', _strings(who, 'api', self.api, at_least=1))
        set_('settings', check_settings(who, self.settings))
        set_('old_ids', _strings(who, 'old_ids', self.old_ids))
        for field in ('description', 'doc', 'category'):
            v = getattr(self, field)
            if v != '':
                _text(who, field, v)
        if self.category and self.category not in CATEGORIES:
            raise ValueError(f'{who}: unknown category {self.category!r}; categories are {", ".join(CATEGORIES)}')
        if self.doc and (not self.doc.endswith('.md') or self.doc.startswith('/')):
            raise ValueError(f'{who}: doc must be a repo-relative .md path')
        if self.poster is not None and (not isinstance(self.poster, int) or self.poster < 0):
            raise ValueError(f'{who}: poster must be a frame number')
        if not isinstance(self.order, int):
            raise ValueError(f'{who}: order must be a whole number')
        if self.members is not None and not isinstance(self.members, Members):
            raise ValueError(f'{who}: members must be a Members(...)')
        if self.members is not None and self.id in self.members.ids:
            raise ValueError(f'{who}: lists itself as a member')
        if self.source is not None and not isinstance(self.source, Source):
            raise ValueError(f'{who}: source must be a Source(url, credit)')
        for o in self.old_ids:
            if not ID_RE.match(o) or o == self.id:
                raise ValueError(f'{who}: old id {o!r} must be kebab-case and not its own id')
        for r in self.related:
            if not ID_RE.match(r):
                raise ValueError(f'{who}: related id {r!r} is not kebab-case')
            if r == self.id:
                raise ValueError(f'{who}: lists itself as related')
        for a in self.api:
            if not DOTTED_RE.match(a) and not self.is_example:
                raise ValueError(f'{who}: api entry {a!r} must be a dotted name, e.g. videobuilder.ease_out_back')
        if not callable(self.demo):
            raise ValueError(f'{who}: demo must be a callable returning a videobuilder.Film')

    @property
    def is_example(self):
        """Whether the demo is a worked example film (see Example)."""
        return isinstance(self.demo, Example)

    def resolve_api(self):
        """Every `api` name resolved to its object, in order. Raises
        `LookupError` naming the first that doesn't resolve. An Example
        capability's api lines are usage as its film writes it, so none of
        them are resolved: ()."""
        if self.is_example:
            return ()
        out = []
        for a in self.api:
            try:
                out.append(resolve(a))
            except LookupError as e:
                raise LookupError(f'{self.id}: api {e}') from None
        return tuple(out)
