#!/usr/bin/env python3
"""Build the sound-effects pack, vb-sfx-1.tar, from a rendered earshot bank.

    python3 scripts/build_sfx_pack.py BANK --license LICENSE --out vb-sfx-1.tar [--dir unpacked/]
    python3 scripts/build_sfx_pack.py BANK --license LICENSE --dir tests/fixtures/sfx-pack --fixture

BANK is earshot's bank rendered once to files, outside videobuilder:
`BANK/index.json` ({"source", "commit", "files": [...]}: one row per file,
with earshot's id, category, kinds, notes, source and its audit,
`checks_ok`) and `BANK/wav/*.wav`. earshot is not a dependency: this reads
its files, nothing else.

Each take that passed earshot's audit (a category with none that did keeps
its takes) is cut 0.15 s past its end (where it is 50 dB under its peak),
faded over that, and encoded to Opus at `--bitrate` in Ogg; then the Opus
file is decoded and measured again (`videobuilder.sfx.measure`: onset, peak,
end), so the index describes the files as shipped. The encode must not
shift a take (its envelope is matched against the WAV's), and every peak
lands within 2 ms of the WAV's (see `settle` for broad sounds, whose loudest
stretch is flat). The pack is an uncompressed tar of index.json
(schema `videobuilder.sfx.SCHEMA`), audio/*.ogg, LICENSE-earshot, CREDITS.md
and README.md, its members sorted and dated 0, so the same bank makes the
same tar.
"""
import argparse
import concurrent.futures
import io
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from videobuilder import sfx  # noqa: E402

TAIL_S = 0.15          # kept past a take's measured end, faded out
PEAK_TOLERANCE_S = 0.002
PLATEAU_DB = 1.5       # see `settle`: about how much a noisy sound's 5 ms loudness wanders
MAX_LAG_MS = 20
BITRATE = '128k'
EARSHOT_URL = 'https://github.com/Leonxlnx/earshot'
# The tests' fixture pack (`--fixture`): a few takes, each cut to `FIXTURE_MAX_S`. ding_2045 Fs5 fails
# earshot's audit and is left out; hover_tick/detent fails it too, but is its category's only take here.
FIXTURE = ('whoosh_fast/tight--0.25s', 'whoosh_fast/tight--0.5s', 'fit/click/floss_lid', 'pro_impact/short',
           'pro_notify/ding_2045', 'pro_notify/ding_2045--G5', 'pro_notify/ding_2045--A5',
           'pro_notify/ding_2045--Fs5', 'hover_tick/detent')
FIXTURE_MAX_S = 0.6

# Each earshot category: our plain-words role for it, and what it is for.
ROLES = {
    'click': ('click', 'a cursor press or a button: a short tick with a little body'),
    'pro_click': ('click', 'a bright designed UI click'),
    'hover_tick': ('tick', 'a tiny tick: hover, rows going by, a counter'),
    'pro_hover_tick': ('tick', 'a tiny designed tick: hover, a cursor blink, a counter'),
    'tap': ('tap', 'a finger on a surface: a soft knock'),
    'pro_tap': ('tap', 'a designed tap: the soft thump of a touch'),
    'toggle': ('toggle', 'a switch: a press and a latch'),
    'pop': ('pop', 'a bubble pop'),
    'pro_pop': ('pop', 'a tonal pop'),
    'pro_pop_in': ('pop', 'an element popping in: a round low thump'),
    'notify': ('ding', 'a struck bell chime'),
    'pro_notify': ('ding', 'a short clean notification ding; a run steps up a semitone a ding'),
    'shimmer': ('shimmer', 'chimes ringing out'),
    'pro_shimmer': ('shimmer', 'a granular sparkle'),
    'whoosh_fast': ('whoosh', 'a fast pass: a whip pan, a fly-in, an element moving'),
    'whoosh_big': ('whoosh', 'a big airy pass for a large transition'),
    'pro_whoosh_big': ('whoosh', 'a designed low swell into a cut'),
    'swish': ('swish', 'a thin flick: text sliding in'),
    'swipe': ('swish', 'a cloth or paper swipe'),
    'riser': ('riser', 'a build that stops on its loudest moment'),
    'pro_riser': ('riser', 'a designed build into a reveal, ending on it'),
    'downlifter': ('downlifter', 'energy falling away out of a moment'),
    'pro_zip': ('zip', 'a tonal sweep across a cut'),
    'impact': ('hit', 'a cinematic hit with a long tail: a reveal, a title slam'),
    'pro_impact': ('hit', 'a designed sub hit with a gated tail'),
    'sub_drop': ('sub drop', 'low weight under a hit'),
    'pro_sub_drop': ('sub drop', 'a designed drop that blooms just after the cut'),
    'logo_sting': ('logo sting', 'a logo reveal in one gesture'),
    'pro_logo_sting': ('logo sting', 'a launch gesture landing on a tone'),
    'glitch': ('glitch', 'a glitch transition'),
    'pro_glitch': ('glitch', 'a designed stutter that ends on the cut'),
    'typing_key': ('key', 'one mechanical key press'),
    'pro_typing_key': ('key', 'a designed key tick, high and short'),
    'pro_typing_run': ('typing', 'a run of typing'),
    'pluck': ('pluck', 'a kalimba tine, tuned'),
}
# A fitted sound's role, from the role in its id (fit/<role>/<name>).
FIT_ROLES = {'bell': 'ding', 'click': 'click', 'hit': 'knock', 'key': 'key', 'key.space': 'key',
             'land.light': 'tap', 'pop': 'pop', 'snap': 'toggle', 'tick': 'tick', 'whoosh.short': 'whoosh'}
LENGTH = re.compile(r'^\d+(\.\d+)?s$')


def describe(row):
    """(role, family, about) of an earshot index row."""
    cat = row['category']
    if cat == 'fit':
        kind = row['id'].split('/')[1]
        about = re.split(r', fitted from ', row['notes'] or '', maxsplit=1)[0]
        return FIT_ROLES.get(kind, kind.split('.')[0]), 'fitted', about
    role, about = ROLES[cat]
    return role, 'designed' if cat.startswith('pro_') else 'classic', about


def momentary_max(path):
    """The loudest momentary (400 ms) loudness of a file, in LUFS (ffmpeg's
    ebur128, with 0.4 s of silence after it so a short sound fills a window)."""
    result = subprocess.run(['ffmpeg', '-v', 'verbose', '-hide_banner', '-nostats', '-i', str(path), '-af',
                             'apad=pad_dur=0.4,ebur128=framelog=verbose', '-f', 'null', '-'],
                            capture_output=True, text=True, check=True)
    values = [float(v) for v in re.findall(r' M:\s*(-?[\d.]+)', result.stderr)]
    return round(max(values), 2) if values else None


def encode(job):
    """Encode one take; (row, measured, problem or None)."""
    row, wav, out, bitrate, max_s = job
    src = sfx.decode(wav)
    m_wav = sfx.measure(src)
    cut = min(m_wav['dur_s'], m_wav['end_s'] + TAIL_S)
    fade_at = m_wav['end_s']
    if max_s and cut > max_s:
        cut, fade_at = max_s, max(m_wav['peak_s'] + 0.01, max_s - TAIL_S)
    af = []
    if cut < m_wav['dur_s']:
        af = ['-af', f'atrim=end={cut:.4f},afade=t=out:st={fade_at:.4f}:d={cut - fade_at:.4f}']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav), *af, '-ac', str(row['channels']),
                    '-c:a', 'libopus', '-b:a', bitrate, '-map_metadata', '-1', '-fflags', '+bitexact',
                    '-flags:a', '+bitexact', str(out)], check=True)
    shipped = sfx.decode(out)
    m = sfx.measure(shipped)
    m['lufs_m_max'] = momentary_max(out)
    return row, m, m_wav, settle(row['file'], m, m_wav, src, shipped)


def settle(name, m, m_wav, src, shipped):
    """Check the encoded take against its WAV, and settle its peak: None,
    or what is wrong. The encode must not move the sound (its 1 ms envelope
    matches the WAV's with no lag: no pre-skip left in). Its peak must be
    within `PEAK_TOLERANCE_S` of the WAV's; where it isn't, the sound's
    loudest stretch is flat to a fraction of a dB (a sub drop's bloom, a
    swell, two near-equal hits) and the encode moved its loudest 5 ms along
    it, so the WAV's peak is kept, as long as the encoded take is within
    `PLATEAU_DB` of its loudest there too."""
    env_w, env_o = sfx.envelope(src, 2), sfx.envelope(shipped, 2)
    n = min(len(env_w), len(env_o))
    lag, r = sfx._correlate(env_w[:n], [0.0] * MAX_LAG_MS + env_o[:n] + [0.0] * MAX_LAG_MS, MAX_LAG_MS)
    if lag:
        return f'{name}: the encoded take is {lag:+d} ms off the WAV (envelope r {r:.3f})'
    if abs(m['peak_s'] - m_wav['peak_s']) <= PEAK_TOLERANCE_S + 1e-9:
        return None
    p5 = [sum(env_o[i:i + 5]) / 5 for i in range(max(1, len(env_o) - 4))]
    at = min(len(p5) - 1, max(0, round(m_wav['peak_s'] * 1000 - 2.5)))
    below = 10 * math.log10(max(p5) / max(p5[at], 1e-30))
    if below > PLATEAU_DB:
        return (f'{name}: peak at {m["peak_s"]:.4f} s after encoding, {m_wav["peak_s"]:.4f} s in the WAV, '
                f'where the encoded take is {below:.2f} dB under its loudest')
    m['peak_s'] = m_wav['peak_s']
    return None


def select(rows, only=None):
    """(kept rows, left out [{id, variant, why}]): a take whose audit failed
    is left out, unless its category would have no take at all without it."""
    if only:
        names = set(only)
        rows = [r for r in rows if r['id'] + (f'--{r["variant"]}' if r['variant'] else '') in names]
    passing = {r['category'] for r in rows if r['checks_ok']}
    kept, left = [], []
    for r in rows:
        if r['checks_ok'] or r['category'] not in passing:
            kept.append(r)
        else:
            why = r['checks'].split(': ', 1)[-1]
            left.append({'id': r['id'], 'variant': r['variant'], 'why': f'earshot audit: {why}'})
    return kept, left


def index(results, left, source):
    """The pack's index.json, as a dict."""
    sounds = {}
    for row, m, m_wav, _ in results:
        role, family, about = describe(row)
        s = sounds.setdefault(row['id'], {
            'id': row['id'], 'category': row['category'], 'role': role, 'family': family, 'about': about,
            'kinds': row.get('kinds') or [], 'centroid_hz': row.get('centroid_hz'),
            'attack_ms': row.get('attack_ms'),
            'credit': ({k: row['source'][k] for k in ('title', 'author', 'license', 'url')}
                       if row.get('source') else None),
            'variants': []})
        v = row['variant']
        s['variants'].append({
            'variant': v, 'file': f'audio/{Path(row["file"]).stem}.ogg',
            'length_s': (float(v[:-1]) if v and LENGTH.match(v) else None if v else m_wav['dur_s']),
            'note': sfx.note_name(v) if v and not LENGTH.match(v) else None,
            'channels': row['channels'], **m})
    for s in sounds.values():
        s['variants'].sort(key=lambda v: (v['variant'] is not None, v['length_s'] or 0,
                                          sfx._note_midi(v['note']) if v['note'] else 0))
    return {'pack': sfx.PACK, 'schema': sfx.SCHEMA,
            'audio': {'codec': 'opus', 'container': 'ogg', 'bitrate': BITRATE, 'rate': sfx.RATE},
            'made_from': {'bank': 'earshot', 'url': EARSHOT_URL, 'commit': source.get('commit'),
                          'license': 'MIT', 'author': 'Leon Lin'},
            'measured': ('on each file as shipped, decoded: onset_s is the start of the first 1 ms within 30 dB '
                         'of its loudest 1 ms; peak_s the middle of its loudest 5 ms (1 ms steps), or, where that '
                         'loudness holds (within 1 dB) over a stretch, the stretch\'s middle weighted by loudness, '
                         'so a ding or a shimmer peaks in its swell, which can be far from earshot\'s own peak; '
                         'where the encode moved that along a flat top, the WAV\'s; end_s the end '
                         'of its last 5 ms within 50 dB of the loudest; peak_db its sample peak; lufs_m_max its '
                         'loudest 400 ms (EBU R128 momentary)'),
            'sounds': sorted(sounds.values(), key=lambda s: s['id']),
            'left_out': left}


def credits(doc):
    lines = ['# Credits', '',
             f'The sounds in {sfx.PACK} are the sound bank of earshot ({EARSHOT_URL}), by Leon Lin, under the MIT',
             'licence (LICENSE-earshot), rendered once to files'
             + (f' at earshot commit {doc["made_from"]["commit"]}' if doc['made_from'].get('commit') else '') + '.',
             'earshot makes its sounds in code; the "fitted" ones are recipes measured from these recordings, all',
             'released under CC0 1.0 (public domain, which asks for no credit; the recordists are thanked here',
             'anyway). No recording is in the pack: a fitted sound is rendered from its recipe.', '',
             '| sound | recording | recordist | licence | source |', '|---|---|---|---|---|']
    for s in doc['sounds']:
        c = s.get('credit')
        if c:
            lines.append(f'| `{s["id"]}` | {c["title"]} | {c["author"]} | {c["license"]} | {c["url"]} |')
    return '\n'.join(lines) + '\n'


README = """# {pack}

Sound effects for videobuilder films: `vb.sfx` reads this directory
($VIDEOBUILDER_SFX_DIR). index.json lists every sound, its role and its takes
(audio/*.ogg, Opus) with their measured onset, peak and end. The sounds are
earshot's bank (MIT): see CREDITS.md and LICENSE-earshot.
"""


def write_tar(path, files):
    """An uncompressed tar of {name: bytes}, sorted, dated 0, owned by root."""
    with tarfile.open(path, 'w', format=tarfile.USTAR_FORMAT) as tf:
        for name in sorted(files):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(files[name]), 0, 0o644
            tf.addfile(info, io.BytesIO(files[name]))


def build(bank, license, out=None, unpacked=None, only=None, max_s=None, bitrate=BITRATE, jobs=None,
          work=None, log=sys.stderr):
    """Build the pack from `bank`; returns (index dict, peak problems)."""
    bank = Path(bank)
    src = json.loads((bank / 'index.json').read_text(encoding='utf-8'))
    kept, left = select(src['files'], only)
    if only and not kept:
        raise SystemExit(f'--only matched nothing in {bank}/index.json')
    with tempfile.TemporaryDirectory(dir=work) as tmp:
        audio = Path(tmp) / 'audio'
        audio.mkdir()
        tasks = [(r, bank / 'wav' / r['file'], audio / f'{Path(r["file"]).stem}.ogg', bitrate, max_s) for r in kept]
        if jobs == 1:
            results = [encode(t) for t in tasks]
        else:
            with concurrent.futures.ProcessPoolExecutor(jobs) as pool:
                results = []
                for k, res in enumerate(pool.map(encode, tasks, chunksize=4), 1):
                    results.append(res)
                    if k % 100 == 0:
                        print(f'{k}/{len(tasks)} encoded', file=log)
        problems = [p for *_, p in results if p]
        doc = index(results, left, src)
        files = {f'audio/{p.name}': p.read_bytes() for p in audio.iterdir()}
    files['index.json'] = (json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode()
    files['LICENSE-earshot'] = Path(license).read_bytes()
    files['CREDITS.md'] = credits(doc).encode()
    files['README.md'] = README.format(pack=sfx.PACK).encode()
    if out:
        write_tar(out, files)
    if unpacked:
        d = Path(unpacked)
        (d / 'audio').mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (d / name).write_bytes(data)
    return doc, problems


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('bank', help='the rendered bank: index.json and wav/')
    p.add_argument('--license', required=True, help="earshot's LICENSE (MIT), copied in as LICENSE-earshot")
    p.add_argument('--out', help='the tar to write')
    p.add_argument('--dir', help='write the pack unpacked here too')
    p.add_argument('--only', help='comma-separated takes, ID (its base take) or ID--VARIANT (a fixture)')
    p.add_argument('--max-s', type=float, help='cut every take to at most this long (a fixture)')
    p.add_argument('--fixture', action='store_true', help='the tests\' fixture pack: --only FIXTURE --max-s 0.6')
    p.add_argument('--bitrate', default=BITRATE)
    p.add_argument('--jobs', type=int)
    a = p.parse_args(argv)
    if not a.out and not a.dir:
        p.error('give --out, --dir or both')
    if a.fixture:
        a.only, a.max_s = ','.join(FIXTURE), FIXTURE_MAX_S
    doc, problems = build(a.bank, a.license, a.out, a.dir, a.only.split(',') if a.only else None, a.max_s,
                          a.bitrate, a.jobs)
    takes = sum(len(s['variants']) for s in doc['sounds'])
    print(f'{len(doc["sounds"])} sounds, {takes} takes; left out {len(doc["left_out"])} takes')
    if a.out:
        print(f'{a.out}: {Path(a.out).stat().st_size / 1e6:.1f} MB')
    for problem in problems:
        print(f'peak moved: {problem}', file=sys.stderr)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
