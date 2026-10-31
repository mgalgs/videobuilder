"""A minimal reader for Fountain (https://fountain.io), the plain-text
screenplay standard pre-production's script uses (see preprod.py,
docs/preproduction.md): just enough to split a script into numbered scenes
and typed elements for the board. Not a full-fidelity renderer -- no dual
dialogue, no notes/boneyard stripping, no page breaks.
"""
import re

ELEMENT_TYPES = ('heading', 'action', 'character', 'dialogue', 'parenthetical', 'transition', 'section', 'synopsis')

_TITLE_FIELD_RE = re.compile(r'^[A-Za-z][A-Za-z ]*:\s?')
_HEADING_RE = re.compile(r'^(?:int|ext|est|i/e|int\./ext)[. /]', re.I)
_SCENE_NUMBER_RE = re.compile(r'#([^#\s]+)#\s*$')
_TRANSITION_RE = re.compile(r'^[A-Z0-9 ]+TO:$')


def _is_upper(text):
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all(c == c.upper() for c in letters)


def parse_title_page(text):
    """(title, draft, body): the title page's Title and Draft (`Draft: N`)
    fields, and the text with the title page removed. A title page is a
    leading run of "Key: value" lines ended by a blank line; without one,
    `body` is `text` unchanged and title/draft are both None."""
    lines = text.split('\n')
    i = 0
    fields = {}
    while i < len(lines) and _TITLE_FIELD_RE.match(lines[i]):
        key, _, value = lines[i].partition(':')
        fields[key.strip().lower()] = value.strip()
        i += 1
    if not fields:
        return None, None, text
    while i < len(lines) and not lines[i].strip():
        i += 1
    draft = None
    if fields.get('draft'):
        m = re.search(r'\d+', fields['draft'])
        draft = int(m.group()) if m else None
    return fields.get('title'), draft, '\n'.join(lines[i:])


def parse(text):
    """{'title', 'draft', 'scenes': [{number, heading, line}],
    'elements': [{type, text, line, scene}]}. `line` is 1-based within the
    whole script text, including any title page. A scene's `number` is its
    heading's `#n#` suffix when it has a digits-only one, else its position
    among headings (1-based)."""
    title, draft, body = parse_title_page(text)
    offset = text.count('\n', 0, len(text) - len(body)) if body is not text else 0
    raw_lines = body.split('\n')
    elements, scenes = [], []
    scene_n = 0
    current_scene = None
    state = None  # 'dialogue' while inside a character's block (dialogue/parenthetical)
    for i, raw in enumerate(raw_lines):
        lineno = offset + i + 1
        stripped = raw.strip()
        if not stripped:
            state = None
            continue
        if stripped.startswith('.') and not stripped.startswith('..'):
            etype, content = 'heading', stripped[1:]
        elif stripped.startswith('>') and not stripped.endswith('<'):
            etype, content = 'transition', stripped[1:].strip()
        elif stripped.startswith('#'):
            etype, content = 'section', stripped.lstrip('#').strip()
        elif stripped.startswith('=') and not stripped.startswith('=='):
            etype, content = 'synopsis', stripped[1:].strip()
        elif stripped.startswith('(') and stripped.endswith(')') and state == 'dialogue':
            etype, content = 'parenthetical', stripped
        elif _HEADING_RE.match(stripped):
            etype, content = 'heading', stripped
        elif _TRANSITION_RE.match(stripped):
            etype, content = 'transition', stripped
        elif state == 'dialogue':
            etype, content = 'dialogue', stripped
        elif _is_upper(stripped) and len(stripped) <= 60:
            etype, content = 'character', stripped
        else:
            etype, content = 'action', stripped
        state = 'dialogue' if etype in ('character', 'dialogue', 'parenthetical') else None
        if etype == 'heading':
            m = _SCENE_NUMBER_RE.search(content)
            content = _SCENE_NUMBER_RE.sub('', content).strip()
            scene_n += 1
            number = int(m.group(1)) if m and m.group(1).isdigit() else scene_n
            current_scene = number
            scenes.append({'number': number, 'heading': content, 'line': lineno})
        elements.append({'type': etype, 'text': content, 'line': lineno, 'scene': current_scene})
    return {'title': title, 'draft': draft, 'scenes': scenes, 'elements': elements}
