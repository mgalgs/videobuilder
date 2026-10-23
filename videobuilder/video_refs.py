"""Referencing another of the creator's own videos from a note: a pasted
link to this same editor's `/v/<name>` is a library link, resolved locally
-- never fetched over HTTP, unlike an ordinary link (see gather.py) -- and
staged read-only under the note's own /attachments/refs/<name>/ for the
builder to learn from. `extract` splits library links out of a note's links
at note-creation time (editor.add_note/start_video); `stage` does the actual
git reads and the contact sheet render at submission time (NoteStore._submit,
through Editor._stage_video_refs), since both can take a moment and a note
author's access can only be checked once we know who they are.

A reference's tree is a snapshot at the moment the note is sent: the commit
noted alongside it never changes even if the referenced video is edited
later. Access follows the library's own rules (library.Access); a reference
the author cannot open is treated exactly like one that doesn't exist, and
either way the note still runs -- see `stage`.
"""
import io
from pathlib import Path
from urllib.parse import urlsplit

from .gitutil import git
from .library import video_name_in_path

# All of a note's referenced videos' tree copies, combined; the k8s push that mounts a
# note's attachment directory in the builder's pod has its own cap (see notes.ATTACH_DIR_BUDGET),
# so this is just this feature's own, modest share of it.
TREE_BUDGET = 24 * 1048576
# A media/binary file in a referenced video's tree bigger than this is left out of the
# copy entirely (noted in its manifest) rather than spent out of the budget above.
PER_FILE_MEDIA_MAX = 2 * 1048576
MEDIA_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'webm', 'mp3', 'wav', 'm4a', 'aac',
            'ogg', 'pdf', 'zip', 'ttf', 'otf', 'woff', 'woff2'}
# Keyframe-ish frames for the contact sheet: bounded so a long timeline never asks the
# referenced video's sandbox to render an unbounded number of frames.
MAX_SHEET_FRAMES = 48


def extract(links, library):
    """(reference names, remaining links): the `/v/<name>` links among `links` whose
    host this editor's own library serves, in the order first seen and deduplicated,
    and everything else untouched, in its original order, for gather.crawl as before.
    `library` is None outside library mode -- a single project has no other video to
    reference -- where nothing is ever split out."""
    if library is None:
        return [], list(links)
    refs, rest = [], []
    for url in links:
        name = _video_name(url, library)
        if name is None:
            rest.append(url)
        elif name not in refs:
            refs.append(name)
    return refs, rest


def _video_name(url, library):
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in ('http', 'https'):
        return None
    host = (parts.hostname or '').lower().rstrip('.')
    if host not in library.allowed_hosts:
        return None
    return video_name_in_path(parts.path)


def stage(library, author, names, dest_dir):
    """Resolve and stage each of `names` under `dest_dir`/refs/<name>/, for the
    prompt's "## Referenced videos" section (prompt._refs_lines): one descriptor
    per name, in order, either {'name', 'staged': True, 'commit', 'manifest'} (whether
    a manifest.md was written, listing anything left out) or {'name', 'staged': False}
    for one `author` cannot open right now, or that doesn't exist -- the same either
    way, so this never discloses which. A video may not reference itself; the caller
    (editor.add_note/start_video) drops that before it ever reaches here."""
    out, used = [], 0
    for name in names:
        if not _accessible(library, name, author):
            out.append({'name': name, 'staged': False})
            continue
        entry, used = _stage_one(library, name, dest_dir, used)
        out.append(entry)
    return out


def _accessible(library, name, author):
    if not library.has_main(name):
        return False
    if library.accounts is None:
        return True
    return library.access.can_access(name, author, library.accounts)


def _stage_one(library, name, dest_dir, used):
    repo = library.path(name)
    sha = git(None, 'rev-parse', 'refs/heads/main', git_dir=repo, hooks=False)
    root = Path(dest_dir) / 'refs' / name
    tree_dir = root / 'tree'
    tree_dir.mkdir(parents=True, exist_ok=True)
    left_out = []
    listing = git(None, 'ls-tree', '-r', '-l', '-z', sha, git_dir=repo, hooks=False)
    for entry in filter(None, listing.split('\0')):
        meta, path = entry.split('\t', 1)
        _mode, kind, blob_id, size_text = meta.split()
        if kind != 'blob':
            continue
        size = int(size_text)
        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else ''
        if ext in MEDIA_EXT and size > PER_FILE_MEDIA_MAX:
            left_out.append((path, size, 'a media file over the per-file size cap'))
            continue
        if used + size > TREE_BUDGET:
            left_out.append((path, size, 'the reference size cap was reached'))
            continue
        # check=False, raw .stdout: git()'s own check=True strips leading/trailing
        # whitespace off stdout (fine for a rev-parse sha, not for a file's exact bytes --
        # see community.load's `read` for the same pattern).
        result = git(None, 'cat-file', 'blob', blob_id, git_dir=repo, hooks=False, check=False, binary=True)
        if result.returncode:
            continue
        data = result.stdout
        target = tree_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        used += size
    sheet_problem = _build_sheet(library, name, root / 'sheet.png')
    if left_out or sheet_problem:
        lines = ['# Left out of this reference', '']
        if sheet_problem:
            lines.append(f'- contact sheet: {sheet_problem}')
        lines += [f'- {path} ({size} bytes): {reason}' for path, size, reason in left_out]
        (root / 'manifest.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'name': name, 'staged': True, 'commit': sha, 'manifest': bool(left_out or sheet_problem)}, used


class _Fmt:
    """Just enough of a film.Format for cli.sheet_tiles, built from the plain dict
    Session.info() reports -- no loaded Film is ever needed here."""
    def __init__(self, width, height):
        self.width, self.height, self.portrait = width, height, height > width


def _frame_list(info):
    """Keyframe-ish frames for a contact sheet, reading only Session.info()'s plain
    dict -- the in, middle and last frame of each timeline segment (cli.
    default_sheet_frames' fallback for a film with no timeline keyframes of its own,
    which info() doesn't report), or, with no timeline, one frame a second."""
    frames, fps = info['frames'], info['fps']
    timeline = info.get('timeline')
    if not timeline:
        step = max(1, round(fps))
        return list(range(0, frames, step)) or [0]
    picks = set()
    for segment in timeline['segments']:
        a, z = segment['start'], segment['end']
        picks.update((a, (a + z) // 2, max(a, z - 1)))
    return sorted(p for p in picks if 0 <= p < frames) or [0]


def _label(info, n, fmt):
    timeline = info.get('timeline')
    name = ''
    if timeline:
        segment = next((s for s in timeline['segments'] if s['start'] <= n < s['end']), None)
        if segment:
            name = f"{segment['group']} / {segment['name']}" if segment['group'] else segment['name']
    text = f"f {n}  {n / info['fps']:.2f}s"
    return f'{text}  {name}' if name else text


def _build_sheet(library, name, out_path):
    """A contact sheet PNG of `name`'s current render at `out_path`, built from
    frames rendered one at a time through its own editor's sandboxed worker (the
    same op a preview uses -- see workers.Pool), never by loading its film code
    in this process. The problem, as a short plain sentence, if it couldn't be
    built at all -- the video doesn't load, or its worker couldn't be reached --
    so the caller can carry on and just note it; None once `out_path` exists."""
    from .cli import sheet_tiles
    try:
        ref_editor = library.editor(name)
        vid = ref_editor.project.videos()[0].id
        session = ref_editor.session(vid)
        info = session.request('info')
    except Exception:
        return 'this video could not be opened; no contact sheet'
    if 'frames' not in info:
        return 'the video does not load; no contact sheet'
    try:
        fmt = info['formats'][0]
        width, cols = sheet_tiles(_Fmt(fmt['width'], fmt['height']))
        scale = width / fmt['width']
        tile_height = round(fmt['height'] * scale)
        frames = _frame_list(info)[:MAX_SHEET_FRAMES]
        from PIL import Image, ImageDraw
        label_h, gap = 22, 8
        rows = (len(frames) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * (width + gap) + gap, rows * (tile_height + label_h + gap) + gap),
                          (24, 24, 24))
        draw = ImageDraw.Draw(sheet)
        for i, n in enumerate(frames):
            png = session.request('frame', frame=n, format=fmt['name'], scale=scale)
            tile = Image.open(io.BytesIO(png)).convert('RGB')
            x = gap + (i % cols) * (width + gap)
            y = gap + (i // cols) * (tile_height + label_h + gap)
            sheet.paste(tile, (x, y))
            draw.text((x + 2, y + tile_height + 4), _label(info, n, fmt), fill=(220, 220, 220))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out_path)
        return None
    except Exception:
        return 'the video does not load; no contact sheet'
