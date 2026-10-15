#!/usr/bin/env python3
"""What a font file says about itself: the family name to use in `Font`, its
weight (or a variable font's axes), and its copyright and licence.

    python fontinfo.py assets/*.ttf assets/*.otf              # each file in detail
    python fontinfo.py --ofl /usr/share/fonts/*/*.[ot]tf      # OFL families on this machine, one line each
    python fontinfo.py --ofl --family Inter /usr/share/fonts/*/*.[ot]tf   # one family's files
    python fontinfo.py --write-ofl assets/Font.otf            # writes assets/<Family>-OFL.txt
    python fontinfo.py --resolve 'Family' 700 assets/*        # the face Pango really draws

Read straight from the file's `name`, `OS/2` and `fvar` tables, so it holds
even where a distro's licence file doesn't match the font. A variable
font's family name often differs from its static siblings' (Source Code
Pro's variable file is `SourceCodeVF`): use the name printed here.
`--resolve` registers the files given, as a film does, and asks Pango which
face it picks for a family and weight, so a silent fallback shows up.
"""
import argparse
import struct
import sys
from pathlib import Path


def _tables(data, offset=0):
    tag = data[offset:offset + 4]
    if tag == b'ttcf':  # a collection: use its first font
        (first,) = struct.unpack('>I', data[12:16])
        return _tables(data, first)
    (num,) = struct.unpack('>H', data[offset + 4:offset + 6])
    out = {}
    for i in range(num):
        rec = data[offset + 12 + 16 * i: offset + 28 + 16 * i]
        tag, _, off, length = struct.unpack('>4sIII', rec)
        out[tag.decode('latin-1')] = data[off:off + length]
    return out


def _names(name):
    fmt, count, base = struct.unpack('>HHH', name[:6])
    found = {}
    for i in range(count):
        pid, eid, lang, nid, length, off = struct.unpack('>HHHHHH', name[6 + 12 * i:18 + 12 * i])
        raw = name[base + off: base + off + length]
        if pid == 3 or pid == 0:
            s, rank = raw.decode('utf-16-be', 'replace'), 0 if lang in (0x409, 0) else 1
        elif pid == 1:
            s, rank = raw.decode('mac_roman', 'replace'), 2
        else:
            continue
        if nid not in found or rank < found[nid][1]:
            found[nid] = (s, rank)
    return {k: v[0] for k, v in found.items()}


def info(path):
    data = Path(path).read_bytes()
    t = _tables(data)
    n = _names(t['name']) if 'name' in t else {}
    weight = struct.unpack('>H', t['OS/2'][4:6])[0] if 'OS/2' in t and len(t['OS/2']) >= 6 else None
    axes = []
    if 'fvar' in t:
        fv = t['fvar']
        axes_off, _, count, size = struct.unpack('>HHHH', fv[4:12])
        for i in range(count):
            tag, lo, default, hi = struct.unpack('>4siii', fv[axes_off + i * size: axes_off + i * size + 16])
            axes.append(f'{tag.decode()} {lo / 65536:g}-{hi / 65536:g}')
    return dict(
        family=n.get(16) or n.get(1, '?'), style=n.get(17) or n.get(2, '?'), weight=weight, axes=axes,
        copyright=n.get(0, ''), licence=n.get(13, ''), licence_url=n.get(14, ''))


def is_ofl(i):
    return 'open font license' in (i['licence'] + i['licence_url']).lower() or 'OFL' in i['licence_url']


# Inter's upstream licence file: a copyright line, then the bare OFL 1.1 text.
# Not Cantarell's, which appends a notice of its own after the licence.
OFL_TEXT = Path(__file__).resolve().parents[3] / 'examples' / 'assets' / 'Inter-OFL.txt'


def write_ofl(path):
    """<Family>-OFL.txt beside the font: its copyright line, then the OFL 1.1
    text. The font's own copyright field can be shorter than its upstream
    notice (Adobe's omits its trademark sentence), so prefer the upstream
    licence file whenever one ships with the font."""
    i = info(path)
    if not is_ofl(i):
        raise SystemExit(f'{path}: its licence is not the SIL OFL: {i["licence"][:120]!r}')
    body = OFL_TEXT.read_text().split('\n', 1)[1]  # drop Inter's own copyright line
    out = Path(path).parent / f"{i['family'].replace(' ', '')}-OFL.txt"
    out.write_text((i['copyright'] or f"Copyright: the authors of {i['family']}") + '\n' + body)
    return out


def resolve(family, weight, files):
    import gi
    gi.require_version('Pango', '1.0')
    gi.require_version('PangoCairo', '1.0')
    from gi.repository import Pango, PangoCairo
    fm = PangoCairo.FontMap.get_default()
    for f in files:
        fm.add_font_file(str(f))
    d = Pango.FontDescription.from_string(f'{family} @wght={weight}')
    d.set_weight(Pango.Weight(min((int(w) for w in Pango.Weight.__enum_values__.values()),
                                  key=lambda k: abs(k - weight))))
    d.set_absolute_size(40 * Pango.SCALE)
    font = fm.load_font(fm.create_context(), d)
    got = font.describe()
    # Not font.get_face(): Pango 1.56 aborts the process there for a font added
    # with add_font_file. describe() carries the weight and style the face has.
    weight = int(got.get_weight())
    try:
        face = Pango.Weight(weight).value_nick.replace('-', ' ').title()
    except ValueError:
        face = f'wght {weight}'
    if got.get_style() != Pango.Style.NORMAL:
        face += ' ' + got.get_style().value_nick.title()
    return got.get_family(), face, weight


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('fonts', nargs='*')
    p.add_argument('--ofl', action='store_true', help='only fonts whose licence names the SIL OFL')
    p.add_argument('--family', help='only this family (case-insensitive substring)')
    p.add_argument('--files', action='store_true', help='every file in detail, even for many files')
    p.add_argument('--write-ofl', metavar='FONT', help="write FONT's <Family>-OFL.txt beside it")
    p.add_argument('--resolve', nargs=2, metavar=('FAMILY', 'WEIGHT'),
                   help='register the fonts given, then print the face Pango picks')
    a = p.parse_args(argv)
    if a.write_ofl:
        print(write_ofl(a.write_ofl))
        return
    if a.resolve:
        fam, face, w = resolve(a.resolve[0], int(a.resolve[1]), a.fonts)
        note = '' if fam.lower() == a.resolve[0].lower() else '   <- NOT the family asked for: a fallback'
        print(f'{a.resolve[0]} @ {a.resolve[1]} -> {fam} {face} (weight {w}){note}')
        return
    infos = []
    for f in a.fonts:
        try:
            i = info(f)
        except Exception as e:  # noqa: BLE001
            print(f'{f}: unreadable ({e})', file=sys.stderr)
            continue
        if a.ofl and not is_ofl(i):
            continue
        if a.family and a.family.lower() not in i['family'].lower():
            continue
        infos.append((f, i))
    if len(infos) > 8 and not a.files:  # many: one line per family
        fams = {}
        for f, i in infos:
            fams.setdefault(i['family'], []).append((f, i))
        for fam, items in sorted(fams.items()):
            weights = sorted({i['weight'] for _, i in items if i['weight']})
            axes = sorted({ax for _, i in items for ax in i['axes']})
            print(f"{fam:32} {len(items):3} files  " + (f"variable {', '.join(axes)}" if axes else
                                                       f"weights {', '.join(map(str, weights))}")
                  + f"  e.g. {items[0][0]}")
        print(f'{len(fams)} families; --family NAME lists one family\'s files')
        return
    for f, i in infos:
        print(f'{f}')
        print(f"  Font('{i['family']}', ...)  style {i['style']}, weight {i['weight']}"
              + (f", variable: {', '.join(i['axes'])}" if i['axes'] else ''))
        if i['copyright']:
            print(f"  {i['copyright'][:200]}")
        print(f"  licence: {(i['licence'] or 'not stated')[:200]}" + (f" <{i['licence_url']}>" if i['licence_url'] else ''))


if __name__ == '__main__':
    main()
