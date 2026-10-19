#!/usr/bin/env python3
"""One self-contained page to listen to a sound-effects pack: a card per role,
a button per sound and take, each with its measured length and peak.

    python3 scripts/sfx_bank_page.py PACK_DIR --out sfx-bank.html [--bitrate 96k]

The audio is embedded (Opus in WebM, which phones play more widely than
Ogg), re-encoded from the pack's own files at `--bitrate` to keep the page
small enough to open on a phone; the page says so. No external links.
"""
import argparse
import base64
import concurrent.futures
import html
import json
import os
import subprocess
import tempfile
from pathlib import Path

STYLE = """
:root{color-scheme:dark;--bg:#14151a;--card:#1d1f26;--ink:#f4f4f2;--muted:#9397a1;--accent:#ef5b4c;--teal:#4fc3b0;--line:#2a2c33}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,-apple-system,sans-serif}
header{padding:20px 16px 8px}h1{font-size:22px;margin:0 0 6px}header p{color:var(--muted);margin:4px 0}
nav{display:flex;flex-wrap:wrap;gap:6px;padding:8px 16px 4px;position:sticky;top:0;background:var(--bg);z-index:2;
border-bottom:1px solid var(--line)}nav a{color:var(--ink);text-decoration:none;background:var(--card);padding:6px 10px;
border-radius:16px;font-size:13px}main{padding:8px 12px 40px;display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(330px,1fr))}
section.role{grid-column:1/-1}h2{font-size:18px;margin:18px 4px 2px;text-transform:capitalize}
.card{background:var(--card);border-radius:14px;padding:12px 12px 8px}.card h3{font-size:15px;margin:0;font-family:ui-monospace,monospace}
.meta{color:var(--muted);font-size:13px;margin:2px 0 8px}.fam{font-size:11px;padding:1px 7px;border-radius:9px;
background:var(--line);color:var(--muted);margin-left:6px;font-family:system-ui}.takes{display:flex;flex-direction:column;gap:4px}
button.take{display:grid;grid-template-columns:64px 1fr 92px;align-items:center;gap:8px;width:100%;min-height:44px;
background:#252832;border:0;border-radius:10px;color:var(--ink);font:inherit;text-align:left;padding:6px 10px;cursor:pointer}
button.take.on{outline:2px solid var(--accent)}.v{font-weight:600}.bar{position:relative;height:8px;background:var(--line);border-radius:4px}
.bar i{position:absolute;top:0;bottom:0;left:0;background:#3d4250;border-radius:4px}.bar b{position:absolute;top:-4px;width:3px;
height:16px;background:var(--accent);border-radius:2px}.t{font-size:12px;color:var(--muted);text-align:right;font-variant-numeric:tabular-nums}
.credit{font-size:12px;color:var(--muted);margin-top:6px}.left{color:var(--muted);font-size:13px;grid-column:1/-1}
.left li{margin:2px 0}
"""

SCRIPT = """
const A=JSON.parse(document.getElementById('audio').textContent),player=new Audio();let on=null;
document.addEventListener('click',e=>{const b=e.target.closest('button.take');if(!b)return;
if(on===b&&!player.paused){player.pause();b.classList.remove('on');on=null;return}
if(on)on.classList.remove('on');on=b;b.classList.add('on');player.src='data:audio/webm;base64,'+A[b.dataset.k];
player.currentTime=0;player.play()});player.addEventListener('ended',()=>{if(on)on.classList.remove('on');on=null});
"""


def encode(job):
    src, out, bitrate = job
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-c:a', 'libopus', '-b:a', bitrate, '-vn',
                    str(out)], check=True)
    return base64.b64encode(Path(out).read_bytes()).decode()


def page(pack, bitrate='96k'):
    pack = Path(pack)
    doc = json.loads((pack / 'index.json').read_text(encoding='utf-8'))
    takes = [(s, v) for s in doc['sounds'] for v in s['variants']]
    with tempfile.TemporaryDirectory() as tmp:
        jobs = [(pack / v['file'], Path(tmp) / f'{k}.webm', bitrate) for k, (_, v) in enumerate(takes)]
        with concurrent.futures.ThreadPoolExecutor(os.cpu_count()) as pool:
            audio = list(pool.map(encode, jobs))
    key = {(s['id'], v['variant']): str(k) for k, (s, v) in enumerate(takes)}
    by_role = {}
    for s in doc['sounds']:
        by_role.setdefault(s['role'], []).append(s)
    e = html.escape
    out = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
           f'content="width=device-width,initial-scale=1"><title>{e(doc["pack"])}: the sound-effects bank</title>'
           f'<style>{STYLE}</style></head><body><header><h1>{e(doc["pack"])}: the sound-effects bank</h1>'
           f'<p>{len(doc["sounds"])} sounds, {len(takes)} takes, by role. Tap a take to play it; tap again to stop. '
           f'The bar is the take\'s length (to scale within a sound) and the red tick its measured peak, the point '
           f'<code>vb.sfx</code> puts on a frame by default.</p><p>earshot\'s bank (MIT, Leon Lin); the fitted sounds '
           f'are recipes measured from CC0 recordings. This page plays {e(bitrate)}/s copies; the pack ships '
           f'{e(doc["audio"]["bitrate"])}/s Opus.</p></header><nav>']
    out += [f'<a href="#{e(r.replace(" ", "-"))}">{e(r)} ({len(by_role[r])})</a>' for r in sorted(by_role)]
    out.append('</nav><main>')
    for role in sorted(by_role):
        out.append(f'<section class="role" id="{e(role.replace(" ", "-"))}"><h2>{e(role)}</h2></section>')
        for s in by_role[role]:
            longest = max(v['dur_s'] for v in s['variants'])
            out.append(f'<div class="card"><h3>{e(s["id"])}<span class="fam">{e(s["family"])}</span></h3>'
                       f'<div class="meta">{e(s["about"])}</div><div class="takes">')
            for v in s['variants']:
                label = v['variant'] or 'base'
                w = 100 * v['dur_s'] / longest
                pk = 100 * v['peak_s'] / longest
                out.append(f'<button class="take" data-k="{key[(s["id"], v["variant"])]}"><span class="v">{e(label)}'
                           f'</span><span class="bar"><i style="width:{w:.1f}%"></i><b style="left:{pk:.1f}%"></b>'
                           f'</span><span class="t">{v["dur_s"]:.2f} s<br>peak {v["peak_s"]:.3f} s</span></button>')
            out.append('</div>')
            c = s.get('credit')
            if c:
                out.append(f'<div class="credit">fitted from "{e(c["title"])}" by {e(c["author"])} '
                           f'({e(c["license"])})</div>')
            out.append('</div>')
    if doc.get('left_out'):
        out.append('<div class="left"><h2>Left out</h2><p>Takes that failed earshot\'s own audit:</p><ul>')
        out += [f'<li><code>{e(x["id"])}{"--" + e(x["variant"]) if x["variant"] else ""}</code>: {e(x["why"])}</li>'
                for x in doc['left_out']]
        out.append('</ul></div>')
    out.append('</main><script type="application/json" id="audio">')
    out.append(json.dumps(dict(enumerate(audio)), separators=(',', ':')))
    out.append(f'</script><script>{SCRIPT}</script></body></html>')
    return ''.join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('pack', help='an unpacked pack: index.json and audio/')
    p.add_argument('--out', required=True)
    p.add_argument('--bitrate', default='96k')
    a = p.parse_args(argv)
    Path(a.out).write_text(page(a.pack, a.bitrate), encoding='utf-8')
    print(f'{a.out}: {Path(a.out).stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
