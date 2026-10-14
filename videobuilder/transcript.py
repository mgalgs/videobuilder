"""A note's builder transcript, read into a director feed.

A note's `handle` (see notes.py and agents.py) is its fork-sandbox run
directory. The run writes its transcript as JSONL files there, one per leg:

    events.jsonl                     the coding leg ("Building")
    events-review-<n>.jsonl          review leg n ("Review <n>")
    events-fix-<n>.jsonl             fix leg n ("Fix <n>")
    events-s<n>-<stage>-<m>.jsonl    a composed run's stage n, attempt m
                                     ("Plan", "Building"/"Building <m>",
                                     "Review <m>", "Fix <m>", "Maintain <m>",
                                     or the stage name, capitalised)

Files are read from the union of `<handle>/` and `<handle>/evidence/` (a
cluster run lands its transcript in the latter once it finishes); a name
present in both is read from `<handle>/` only. A symlink is never followed
out of the handle directory. The whole read is capped at MAX_BYTES.

Each line is one JSON object. The shape understood here is Claude Code's
stream-json: `type` is "system", "assistant", "user" or "result"; an
"assistant" event's `message.content` is a list of `{type:"text", text}` and
`{type:"tool_use", name, input}` items; a "user" event carries `tool_result`
items (never shown). That shape is not a stable contract -- another harness
(pi, codex, a future Claude Code) may write something else entirely, so a
line that doesn't parse, or doesn't look like that, is skipped silently
rather than raising.

Everything here is pure except `read_feed`, which does the file I/O; the
formatting it delegates to (`format_transcript`) takes already-read lines,
with no I/O of its own. The feed is shown only to people with access to the
project (who can already read the note's text and attachments), so this is
about readability, not secrecy: it never shows a tool's raw output, a
`thinking` block, a system event, the input of a tool it doesn't recognise,
or file contents written by Write/Edit (the path only).
"""
import json
import os
import re
from pathlib import Path

MAX_BYTES = 16 * 1024 * 1024

_FILE_NAME = re.compile(r'events(-[A-Za-z0-9_-]+)?\.jsonl')
_COMPOSED = re.compile(r'events-s(\d+)-([a-z]+)-(\d+)')
_PLAIN_REVIEW = re.compile(r'events-review-(\d+)')
_PLAIN_FIX = re.compile(r'events-fix-(\d+)')

_STAGE_HEADERS = {'plan': 'Plan', 'review': 'Review', 'fix': 'Fix', 'maintain': 'Maintain'}


def _order_key(name):
    stem = name[:-len('.jsonl')]
    if stem == 'events':
        return (0, 0, 0, name)
    m = _COMPOSED.fullmatch(stem)
    if m:
        return (1, int(m.group(1)), int(m.group(3)), name)
    m = _PLAIN_REVIEW.fullmatch(stem)
    if m:
        return (2, int(m.group(1)), 0, name)
    m = _PLAIN_FIX.fullmatch(stem)
    if m:
        return (3, int(m.group(1)), 0, name)
    return (4, 0, 0, name)


def _header(name):
    stem = name[:-len('.jsonl')]
    if stem == 'events':
        return 'Building'
    m = _COMPOSED.fullmatch(stem)
    if m:
        stage, attempt = m.group(2), int(m.group(3))
        if stage == 'plan':
            return 'Plan'
        if stage == 'code':
            return 'Building' if attempt == 1 else f'Building {attempt}'
        label = _STAGE_HEADERS.get(stage)
        return f'{label} {attempt}' if label else stage.capitalize()
    m = _PLAIN_REVIEW.fullmatch(stem)
    if m:
        return f'Review {m.group(1)}'
    m = _PLAIN_FIX.fullmatch(stem)
    if m:
        return f'Fix {m.group(1)}'
    return stem.removeprefix('events-').replace('-', ' ').capitalize()


def discover(handle):
    """Ordered list of (header, Path) transcript files for a run directory
    `handle`: the union of `handle` and `handle/evidence`, a name in both
    taken from `handle`, never crossing a symlink out of `handle`."""
    base = Path(handle)
    try:
        base_real = base.resolve(strict=True)
    except OSError:
        return []
    found = {}
    for directory in (base / 'evidence', base):  # `base` second, so it wins ties
        if not directory.is_dir():
            continue
        try:
            names = [p.name for p in directory.iterdir() if _FILE_NAME.fullmatch(p.name)]
        except OSError:
            continue
        for name in names:
            path = directory / name
            try:
                real = path.resolve(strict=True)
            except OSError:
                continue
            if real != base_real and base_real not in real.parents:
                continue
            found[name] = path
    return [(_header(name), found[name]) for name in sorted(found, key=_order_key)]


def _read_lines(files):
    """[(header, [raw line, ...]), ...], the whole read capped at MAX_BYTES."""
    legs = []
    remaining = MAX_BYTES
    for header, path in files:
        if remaining <= 0:
            break
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if len(raw) > remaining:
            raw = raw[:remaining].rsplit(b'\n', 1)[0]
        remaining -= len(raw)
        text = raw.decode('utf-8', errors='replace')
        legs.append((header, [line for line in text.split('\n') if line.strip()]))
    return legs


def read_feed(handle, project_root=None, show_cost=True):
    """The feed for a note's run directory `handle`: [] for a falsy or
    missing handle, or one with no transcript yet."""
    if not handle:
        return []
    return format_transcript(_read_lines(discover(handle)), project_root, show_cost)


def _relative(path, root):
    if not path or not root:
        return path
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return path
    return path if rel.startswith('..') else rel


def _truncate(text, limit):
    return text if len(text) <= limit else text[:limit].rstrip() + '…'


def _collapse(text):
    return _truncate(re.sub(r'\s+', ' ', text).strip(), 400)


def _tool_line(name, input, project_root):
    input = input if isinstance(input, dict) else {}
    if name in ('Read', 'Edit', 'Write'):
        path = _relative(input.get('file_path'), project_root)
        return f'{name} {path}' if path else name
    if name == 'Bash':
        command = input.get('command')
        first = str(command).splitlines()[0] if command else ''
        return f'Bash: {_truncate(first, 160)}'
    if name in ('Grep', 'Glob'):
        pattern = input.get('pattern')
        return f'{name} {pattern}' if pattern else name
    return name or 'tool'


def _duration(ms):
    seconds = round(ms / 1000)
    minutes, seconds = divmod(seconds, 60)
    return f'{minutes}m {seconds}s' if minutes else f'{seconds}s'


def _result_line(result, show_cost):
    parts = []
    turns = result.get('num_turns')
    if isinstance(turns, int) and not isinstance(turns, bool):
        parts.append(f"{turns} turn{'s' if turns != 1 else ''}")
    duration = result.get('duration_ms')
    if isinstance(duration, (int, float)) and not isinstance(duration, bool):
        parts.append(_duration(duration))
    cost = result.get('total_cost_usd')
    if show_cost and isinstance(cost, (int, float)) and not isinstance(cost, bool):
        parts.append(f'${cost:.2f}')
    return ' · '.join(parts) if parts else None


def _assistant_entries(message, project_root):
    content = message.get('content') if isinstance(message, dict) else None
    if not isinstance(content, list):
        return []
    entries = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get('type') == 'text' and isinstance(item.get('text'), str):
            text = _collapse(item['text'])
            if text:
                entries.append({'kind': 'text', 'text': text})
        elif item.get('type') == 'tool_use':
            entries.append({'kind': 'tool', 'text': _tool_line(item.get('name'), item.get('input'), project_root)})
        # tool_result, thinking, and anything else a line might carry: never shown.
    return entries


def format_transcript(legs, project_root=None, show_cost=True):
    """`legs`, an ordered `[(header, [raw line, ...]), ...]` of already-read
    transcript lines, to a flat list of feed entries `{kind, text}`. Pure:
    no file access, no network."""
    entries = []
    for header, lines in legs:
        if not lines:
            continue
        entries.append({'kind': 'leg', 'text': header})
        for line in lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get('type')
            if kind == 'assistant':
                entries.extend(_assistant_entries(event.get('message'), project_root))
            elif kind == 'result':
                text = _result_line(event, show_cost)
                if text:
                    entries.append({'kind': 'result', 'text': text})
            # system, user (tool_result), and any other event type: never shown.
    return entries
