#!/usr/bin/env python3
"""What a font file says about itself: the family name to use in `Font`, its
weight (or a variable font's axes), and its copyright and licence.

    python fontinfo.py assets/*.ttf assets/*.otf
    python fontinfo.py /usr/share/fonts/**/*.otf --ofl     # only OFL-licensed files

Read straight from the file's `name`, `OS/2` and `fvar` tables, so it holds
even where a distro's licence file doesn't match the font. Pure Python.
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


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('fonts', nargs='+')
    p.add_argument('--ofl', action='store_true', help='only list fonts whose licence names the SIL OFL')
    a = p.parse_args(argv)
    for f in a.fonts:
        try:
            i = info(f)
        except Exception as e:  # noqa: BLE001
            print(f'{f}: unreadable ({e})', file=sys.stderr)
            continue
        ofl = 'open font license' in (i['licence'] + i['licence_url']).lower() or 'OFL' in i['licence_url']
        if a.ofl and not ofl:
            continue
        print(f'{f}')
        print(f"  Font('{i['family']}', ...)  style {i['style']}, weight {i['weight']}"
              + (f", variable: {', '.join(i['axes'])}" if i['axes'] else ''))
        if i['copyright']:
            print(f"  {i['copyright'][:200]}")
        print(f"  licence: {(i['licence'] or 'not stated')[:200]}" + (f" <{i['licence_url']}>" if i['licence_url'] else ''))


if __name__ == '__main__':
    main()
