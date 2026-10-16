"""Command line: render, still, sheet, preview, edit, editor.

    python -m videobuilder render  film.py [--format 9x16|16x9|1x1|all] [--jobs N] [--out FILE]
    python -m videobuilder still   film.py FRAME [FRAME ...] [--format F] [--out PATH] [--overlay]
    python -m videobuilder sheet   film.py [--format F] [--every N | --frames 0,30,60] [--out FILE] [--width W] [--cols C]
    python -m videobuilder preview film.py [--port 8000] [--host 127.0.0.1]
    python -m videobuilder edit roll film.py SEGMENT UNTIL
    python -m videobuilder edit copy film.py SEGMENT KEY VALUE
    python -m videobuilder editor PROJECT-DIR [--port 8100] [--host 127.0.0.1] [--state-dir DIR]
"""
import argparse
import os
import sys

from .film import load


def _stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def _formats(film, arg):
    if arg == 'all':
        return list(film.formats)
    return [film.format(arg)]


def cmd_render(a):
    from .render import render
    film = load(a.film)
    fmts = _formats(film, a.format)
    frames = tuple(int(x) for x in a.frames.split(':')) if a.frames else None
    for fmt in fmts:
        out = a.out or f'{_stem(a.film)}-{fmt.name}.mp4'
        if len(fmts) > 1 and a.out:
            root, ext = os.path.splitext(a.out)
            out = f'{root}-{fmt.name}{ext or ".mp4"}'
        render(film, out, fmt, jobs=a.jobs, chunk=a.chunk, crf=a.crf, frames=frames, stall=a.stall)


def _still(film, n, fmt, overlay=False, scale=1.0):
    if not 0 <= n < film.frames:
        raise SystemExit(f'frame {n} outside 0..{film.frames - 1}')
    cv = film.frame(n, fmt, scale=scale)
    if overlay:
        from . import overlay as ov
        ov.draw(cv, film, n)
    return cv


def cmd_still(a):
    film = load(a.film)
    for fmt in _formats(film, a.format):
        many = len(a.frames) > 1 or a.format == 'all'
        for n in a.frames:
            name = f'{_stem(a.film)}-{fmt.name}-f{n:05d}.png'
            if a.out and many:
                os.makedirs(a.out, exist_ok=True)
                path = os.path.join(a.out, name)
            else:
                path = a.out or name
            _still(film, n, fmt, a.overlay, a.scale).save_png(path)
            print(path)


def sheet_tiles(fmt):
    """Default (thumbnail width, columns) of a sheet in `fmt`: 360 px x 6 for a
    portrait format, 480 px x 4 otherwise, so each format's sheet reads well."""
    return (360, 6) if fmt.portrait else (480, 4)


def contact_sheet(film, frames, fmt, width=None, cols=None, overlay=False, decorate=None):
    """A PIL image: the given frames as thumbnails `width` px wide, labelled.
    `width` and `cols` default to `sheet_tiles(fmt)`.

    `frames` holds frame numbers or (frame, label) pairs; a frame without a
    label is named by its segment. `decorate(canvas, n)`, if given, is called
    on each drawn frame and may draw over it in film px (a check's overlay,
    using `canvas.marks`, say); a string it returns is added to the label.
    """
    from PIL import Image, ImageDraw
    fmt = film.format(fmt)
    dw, dc = sheet_tiles(fmt)
    width, cols = width or dw, cols or dc
    scale = width / fmt.width
    th = round(fmt.height * scale)
    label = 22
    gap = 8
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (width + gap) + gap, rows * (th + label + gap) + gap), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for i, item in enumerate(frames):
        n, name = (item, '') if isinstance(item, int) else item
        cv = _still(film, n, fmt, overlay, scale)
        note = decorate(cv, n) if decorate else None
        cv.surface.flush()
        w, h = cv.surface.get_width(), cv.surface.get_height()
        im = Image.frombuffer('RGBA', (w, h), bytes(cv.surface.get_data()), 'raw', 'BGRA', cv.surface.get_stride(), 1)
        x = gap + (i % cols) * (width + gap)
        y = gap + (i // cols) * (th + label + gap)
        sheet.paste(im.convert('RGB'), (x, y))
        text = f'f {n}  {n / film.fps:.2f}s'
        if not name and film.timeline is not None:
            try:
                name = film.timeline.label(n)
            except IndexError:
                pass
        if name:
            text += f'  {name}'
        if isinstance(note, str):
            text += f'  {note}'
        d.text((x + 2, y + th + 4), text, fill=(220, 220, 220))
    return sheet


def default_sheet_frames(film, every=None):
    """`every` N frames if asked; else the film's keyframes; else the first,
    middle and last frame of each segment, groups' children included (or one a
    second, with no timeline)."""
    if every:
        return list(range(0, film.frames, every))
    if film.keyframes:
        return list(film.keyframes)
    tl = film.timeline
    if tl is None:
        return list(range(0, film.frames, film.fps))
    b = tl.grid.b
    picks = set()
    for s in tl.leaves():
        a, z = b(s.at), b(s.until)
        picks.update((a, (a + z) // 2, z - 1))  # in, middle, last frame of each segment
    return sorted(p for p in picks if 0 <= p < film.frames)


def cut_sheet_frames(film, count=3):
    """First `count` frames at each hard cut, including frame zero."""
    if count < 1:
        raise ValueError('cut frame count must be positive')
    if film.timeline is None:
        raise ValueError('--cuts requires a timeline')
    return sorted({n for c in film.timeline.cut_frames()
                   for n in range(c, min(c + count, film.frames))})


def cmd_sheet(a):
    film = load(a.film)
    try:
        frames = (cut_sheet_frames(film, a.cuts) if a.cuts is not None else
                  [int(x) for x in a.frames.split(',')] if a.frames else default_sheet_frames(film, a.every))
    except ValueError as e:
        raise SystemExit(str(e)) from None
    for fmt in _formats(film, a.format):
        out = a.out or f'{_stem(a.film)}-{fmt.name}-sheet.png'
        if a.format == 'all' and a.out:
            root, ext = os.path.splitext(a.out)
            out = f'{root}-{fmt.name}{ext or ".png"}'
        contact_sheet(film, frames, fmt, a.width, a.cols, a.overlay).save(out)
        print(out)


def cmd_motion(a):
    from .motion_plot import render
    film = load(a.film)
    fmt = film.format(a.format)
    def frame(value, end=False):
        if value is None:
            return film.frames - 1 if end else 0
        try:
            return int(value)
        except ValueError:
            if film.timeline is None:
                raise SystemExit('segment names require a timeline')
            try:
                lo, hi = film.timeline.span(value)
            except KeyError:
                raise SystemExit(f'unknown segment {value!r}') from None
            return hi - 1 if end else lo
    try:
        _, _, summary = render(film, fmt, frame(a.start), frame(a.end, True), a.mark, a.onion, a.out)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(a.out)
    for name, peak, peak_frame, settled in summary:
        print(f'{name}: peak {peak:.2f} px/frame at f{peak_frame}; settled ' +
              (f'by f{settled}' if settled is not None else 'not in range'))


def cmd_preview(a):
    from .preview import serve
    serve(a.film, host=a.host, port=a.port, open_browser=a.open)


def cmd_editor(a):
    from .editor import serve, serve_library, _optional_positive, _resolved_positive
    try:
        agent = {k: v for k, v in dict(backend=a.agent, executable=a.agent_executable,
                    submit_command=a.agent_submit_command, poll_command=a.agent_poll_command,
                    submit_args=a.agent_submit_args, poll_args=a.agent_poll_args,
                    extra_args=a.agent_extra_arg, context_root=a.agent_context_root,
                    context_mount=a.agent_context_mount,
                    videobuilder_repo=a.agent_videobuilder_repo).items() if v is not None}
        if a.library:
            if a.project:
                raise ValueError('PROJECT and --library cannot be used together')
            if a.sync_remote:
                raise ValueError('--sync-remote is only for single-project mode')
            if len(a.admin) != len(a.admin_password_file):
                raise ValueError('--admin and --admin-password-file must be given the same number of '
                                 'times, paired in order')
            note_cap = _optional_positive(a.account_daily_note_cap, 'account_daily_note_cap', int)
            cost_cap = _optional_positive(a.account_daily_cost_cap_usd, 'account_daily_cost_cap_usd', (int, float))
            _resolved_positive(a.source_max_mb, {}, 'source_max_mb', 2048)
            _resolved_positive(a.source_max_total_mb, {}, 'source_max_total_mb', 8192)
            serve_library(a.library, host=a.host, port=a.port, checkouts=a.checkouts,
                          state_dir=a.state_dir, open_browser=a.open, agent=agent,
                          allowed_hosts=a.allow_host, unsandboxed_previews=a.unsandboxed_previews, envs=a.envs,
                          admins=list(zip(a.admin, a.admin_password_file)), capabilities_dir=a.capabilities_dir,
                          compendium_dir=a.compendium_dir, music_sources=a.music_sources,
                          compendium_for_builder=a.compendium_for_builder,
                          account_daily_note_cap=note_cap, account_daily_cost_cap_usd=cost_cap,
                          source_max_mb=a.source_max_mb, source_max_total_mb=a.source_max_total_mb,
                          capability_agent_extra_args=a.capability_agent_extra_arg)
        else:
            if not a.project:
                raise ValueError('provide PROJECT or --library DIR')
            if a.admin or a.admin_password_file:
                raise ValueError('--admin is only for --library mode')
            if a.compendium_for_builder is not None:
                raise ValueError('--compendium-for-builder is only for --library mode; set '
                                 '[editor] compendium_for_builder in the project config instead')
            if a.account_daily_note_cap is not None or a.account_daily_cost_cap_usd is not None:
                raise ValueError('--account-daily-note-cap and --account-daily-cost-cap-usd are only for '
                                 '--library mode; set [editor] account_daily_note_cap / '
                                 'account_daily_cost_cap_usd in the project config instead')
            if a.source_max_mb is not None or a.source_max_total_mb is not None:
                raise ValueError('--source-max-mb and --source-max-total-mb are only for --library mode; '
                                 'set [editor] source_max_mb / source_max_total_mb in the project config instead')
            if a.capability_agent_extra_arg is not None:
                raise ValueError('--capability-agent-extra-arg … only for --library mode')
            serve(a.project, host=a.host, port=a.port, state_dir=a.state_dir, open_browser=a.open,
                  agent=agent, allowed_hosts=a.allow_host, unsandboxed_previews=a.unsandboxed_previews,
                  envs=a.envs, sync_remote=a.sync_remote, capabilities_dir=a.capabilities_dir,
                  compendium_dir=a.compendium_dir, music_sources=a.music_sources)
    except ValueError as e:
        raise SystemExit(f'editor: {e}') from None


def cmd_frames(a):
    from .frames import check, manifest
    try:
        print(check(a.films, a.check) if a.check else manifest(a.films), end="")
    except ValueError as e:
        raise SystemExit(str(e)) from None


def cmd_capabilities(a):
    from . import capabilities
    if a.capabilities_cmd == 'sheet':
        sys.stdout.write(capabilities.sheet_markdown())
        return
    try:
        results = capabilities.build(a.out, only=set(a.only) if a.only else None, jobs=a.jobs, crf=a.crf)
    except ValueError as e:
        raise SystemExit(str(e)) from None
    total = 0.0
    largest = 0
    for r in results:
        total += r['seconds']
        largest = max(largest, r['bytes'])
        print(f"{r['id']}: {r['seconds']:.1f}s, {r['bytes'] / 1024:.0f} KiB")
    print(f"{len(results)} clip(s) built in {total:.1f}s total; largest clip {largest / 1024:.0f} KiB")


def cmd_compendium(a):
    from . import compendium
    if a.compendium_cmd == 'index':
        sys.stdout.write(compendium.index_json() if a.json else compendium.index_markdown())
        return
    try:
        results = compendium.build(a.out, only=set(a.only) if a.only else None, jobs=a.jobs, crf=a.crf)
    except (ValueError, KeyError) as e:
        raise SystemExit(str(e)) from None
    total = 0.0
    largest = 0
    for r in results:
        total += r['seconds']
        largest = max(largest, r['bytes'])
        print(f"{r['id']}: {r['seconds']:.1f}s, {r['bytes'] / 1024:.0f} KiB")
    print(f"{len(results)} clip(s) built in {total:.1f}s total; largest clip {largest / 1024:.0f} KiB")


def cmd_edit(a):
    from . import edits
    try:
        if a.edit == 'roll':
            edits.roll(a.film, a.segment, a.until)
        else:
            edits.set_copy(a.film, a.segment, a.key, a.value)
    except ValueError as e:
        raise SystemExit(f'not edited: {e}') from None
    print(edits.path_for(a.film))


def main(argv=None):
    p = argparse.ArgumentParser(prog='videobuilder', description='Make videos in code.')
    sub = p.add_subparsers(dest='cmd', required=True)

    r = sub.add_parser('render', help='render a film to MP4')
    r.add_argument('film')
    r.add_argument('--format', help="a format name, or 'all' (default: the film's first)")
    r.add_argument('--jobs', type=int, help='worker processes (default: CPU count)')
    r.add_argument('--out', help='output file (default: <film>-<format>.mp4)')
    r.add_argument('--frames', help='a:b, half-open, to render part of the film')
    r.add_argument('--chunk', type=int, default=15, help='frames per encoded chunk')
    r.add_argument('--crf', type=int, default=18, help='x264 quality (lower is better)')
    r.add_argument('--stall', type=float, default=600,
                   help='give up when no chunk finishes for this many seconds (default 600)')
    r.set_defaults(fn=cmd_render)

    s = sub.add_parser('still', help='render frames to PNG')
    s.add_argument('film')
    s.add_argument('frames', type=int, nargs='+', metavar='frame')
    s.add_argument('--format')
    s.add_argument('--out', help='PNG path, or a directory when there are several stills')
    s.add_argument('--overlay', action='store_true', help='draw the timeline overlay')
    s.add_argument('--scale', type=float, default=1.0)
    s.set_defaults(fn=cmd_still)

    c = sub.add_parser('sheet', help="a contact sheet of frames (default: the film's keyframes, or in/middle/out of each segment)")
    c.add_argument('film')
    c.add_argument('--format')
    picks = c.add_mutually_exclusive_group()
    picks.add_argument('--cuts', nargs='?', const=3, type=int, metavar='N',
                       help='first N frames at each hard cut, including frame zero (default 3)')
    picks.add_argument('--frames', help='comma-separated frame numbers')
    picks.add_argument('--every', type=int, help='every N frames')
    c.add_argument('--cols', type=int, help='default: 6 for portrait formats, else 4')
    c.add_argument('--width', type=int, help='thumbnail width, px (default: 360 for portrait formats, else 480)')
    c.add_argument('--overlay', action='store_true')
    c.add_argument('--out')
    c.set_defaults(fn=cmd_sheet)

    m = sub.add_parser('motion', help='render mark speed graph and optional onion skin to PNG')
    m.add_argument('film')
    m.add_argument('--format', help='format name (default: first)')
    m.add_argument('--mark', action='append', help='mark to graph (repeatable; default: all)')
    m.add_argument('--from', dest='start', help='first frame or segment name')
    m.add_argument('--to', dest='end', help='last frame or segment name')
    m.add_argument('--onion', type=int, metavar='N', help='composite every Nth frame')
    m.add_argument('-o', '--out', default='motion.png')
    m.set_defaults(fn=cmd_motion)

    v = sub.add_parser('preview', help='serve a live preview with hot reload')
    v.add_argument('film')
    v.add_argument('--host', default='127.0.0.1')
    v.add_argument('--port', type=int, default=8000)
    v.add_argument('--open', action='store_true', help='open a browser')
    v.set_defaults(fn=cmd_preview)

    e = sub.add_parser('edit', help="write a direct edit to the film's <film>.edits.toml")
    esub = e.add_subparsers(dest='edit', required=True)
    er = esub.add_parser('roll', help='move the cut at the end of a segment (the next one starts there)')
    er.add_argument('film')
    er.add_argument('segment')
    er.add_argument('until', type=float, help='the new end, in beats, on the half-beat grid')
    er.set_defaults(fn=cmd_edit)
    ec = esub.add_parser('copy', help="replace a string in a segment's data")
    ec.add_argument('film')
    ec.add_argument('segment')
    ec.add_argument('key')
    ec.add_argument('value')
    ec.set_defaults(fn=cmd_edit)

    d = sub.add_parser('editor', help="a web editor for a project's videos: timeline, direct edits that commit, notes")
    d.add_argument('project', nargs='?', help='the project directory: its videos are found under it')
    d.add_argument('--library', help='host one git repository per video under DIR')
    d.add_argument('--checkouts', help='library checkout directory (default: DIR/checkouts)')
    d.add_argument('--host', default='127.0.0.1')
    d.add_argument('--port', type=int, default=8100)
    d.add_argument('--sync-remote', help='fetch and push main through this git remote')
    d.add_argument('--state-dir', help='where notes are kept (default: <project>/.vb-editor)')
    d.add_argument('--open', action='store_true', help='open a browser')
    d.add_argument('--allow-host', action='append', default=[])
    d.add_argument('--unsandboxed-previews', action='store_true',
                   help='render drafts without bwrap: draft code can read whatever the editor can')
    d.add_argument('--envs', choices=['pinned', 'current'], help='use video pins or the editor interpreter')
    d.add_argument('--admin', action='append', default=[],
                   help='an admin username (repeatable); library mode only, turns on accounts')
    d.add_argument('--admin-password-file', action='append', default=[],
                   help="that admin's password, one line, plaintext (repeatable, paired with --admin in order)")
    d.add_argument('--agent', choices=['null', 'fake', 'command', 'fork-sandbox'])
    d.add_argument('--agent-executable')
    for name in ('submit-command', 'poll-command', 'submit-args', 'poll-args'):
        d.add_argument('--agent-' + name, type=__import__('json').loads, help='JSON argv array')
    d.add_argument('--agent-extra-arg', action='append', help='repeatable; use = for leading dashes')
    d.add_argument('--agent-context-root', help="stage each video's pinned videobuilder here")
    d.add_argument('--agent-context-mount', help='where the agent sees --agent-context-root')
    d.add_argument('--agent-videobuilder-repo', help='videobuilder git URL, for == pins')
    d.add_argument('--capabilities-dir', help='a directory of pre-built capability clips/posters '
                   '(from `videobuilder capabilities build`), served at /capabilities')
    d.add_argument('--compendium-dir', help='a directory of pre-built compendium clips/posters '
                   '(from `videobuilder compendium build`), served at /compendium (admin only)')
    d.add_argument('--music-sources', help='a TOML file of pluggable music sources for the director '
                   "(see README); with none given, the director shows no music picker")
    d.add_argument('--compendium-for-builder', action=argparse.BooleanOptionalAction, default=None,
                   help='--library mode only: tell the builder about the compendium (default: on). A '
                        'library-hosted repo cannot set this itself, since [editor] compendium_for_builder '
                        "isn't among the config keys it's trusted for; use this flag instead, e.g. for a "
                        'bake-off arm that should build from scratch')
    d.add_argument('--account-daily-note-cap', type=int, metavar='N',
                   help='--library mode only: library-wide cap on new notes per account per rolling 24h '
                        '(default: no cap); an admin may override it per account from /account. For '
                        'single-project mode, set [editor] account_daily_note_cap in the project config instead')
    d.add_argument('--account-daily-cost-cap-usd', type=float, metavar='X',
                   help='--library mode only: library-wide cap on recorded cost per account per rolling 24h '
                        '(default: no cap); an admin may override it per account from /account. For '
                        'single-project mode, set [editor] account_daily_cost_cap_usd in the project config instead')
    d.add_argument('--source-max-mb', type=int, metavar='N',
                   help='--library mode only: per-file size limit for an uploaded source video, in MiB '
                        '(default 2048). For single-project mode, set [editor] source_max_mb instead')
    d.add_argument('--source-max-total-mb', type=int, metavar='N',
                   help="--library mode only: cap on one video's total source-video storage, in MiB "
                        '(default 8192). For single-project mode, set [editor] source_max_total_mb instead')
    d.add_argument('--capability-agent-extra-arg', action='append',
                   help='--library mode only: repeatable; use = for leading dashes. Appended after '
                        '--agent-extra-arg, but only for notes on a community-capability project '
                        '(capabilities/<slug>); with none given, those notes instead get the note args '
                        'plus a heavier default (--review-loop 2 --maintainer-loop 1 --review-model M '
                        '--maintainer-model M when --agent-extra-arg names a --model M, else just '
                        '--review-loop 2)')
    d.set_defaults(fn=cmd_editor)

    cap = sub.add_parser('capabilities', help="the capabilities catalog's clips and builder sheet")
    capsub = cap.add_subparsers(dest='capabilities_cmd', required=True)
    capb = capsub.add_parser('build', help='render every demo to <out>/<id>.mp4 and <id>.jpg (or just --only ids)')
    capb.add_argument('--out', required=True, help='output directory')
    capb.add_argument('--only', action='append', help='build only this capability id (repeatable)')
    capb.add_argument('--jobs', type=int, help='worker processes (default: CPU count)')
    capb.add_argument('--crf', type=int, default=30, help='x264 quality (default 30: small clips over sharpness)')
    capb.set_defaults(fn=cmd_capabilities)
    caps = capsub.add_parser('sheet', help='print the generated builder sheet (redirect it to the committed file)')
    caps.set_defaults(fn=cmd_capabilities)

    comp = sub.add_parser('compendium', help='the compendium: pre-built components and reference recipes')
    compsub = comp.add_subparsers(dest='compendium_cmd', required=True)
    compi = compsub.add_parser('index', help='list every component and recipe, markdown or --json')
    compi.add_argument('--json', action='store_true')
    compi.set_defaults(fn=cmd_compendium)
    compb = compsub.add_parser('build', help='render every component sample and recipe to <out>/<id>-<format>.mp4/.jpg')
    compb.add_argument('--out', required=True, help='output directory')
    compb.add_argument('--only', action='append', help='build only this component or recipe id (repeatable)')
    compb.add_argument('--jobs', type=int, help='worker processes (default: CPU count)')
    compb.add_argument('--crf', type=int, default=30, help='x264 quality (default 30: small clips over sharpness)')
    compb.set_defaults(fn=cmd_compendium)

    f = sub.add_parser('frames', help='hash fixed example keyframes in every format')
    f.add_argument('--hash', action='store_true', required=True)
    f.add_argument('--check', help='compare against a frame manifest')
    f.add_argument('films', nargs='+')
    f.set_defaults(fn=cmd_frames)

    w = sub.add_parser('worker', help='serve the versioned film worker protocol on standard streams')
    w.set_defaults(fn=lambda a: __import__('videobuilder.worker', fromlist=['serve']).serve())

    a = p.parse_args(argv)
    a.fn(a)


def film_main(path, argv=None):
    """Run the CLI on the film file `path`, so a film is runnable on its own:
    end it with `if __name__ == '__main__': videobuilder.main(__file__)`, and
    `python film.py render --format all` is `python -m videobuilder render
    film.py --format all`. `argv` defaults to the command line."""
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv or argv[0].startswith('-'):
        return main(argv or ['--help'])
    return main([argv[0], os.path.abspath(path), *argv[1:]])
