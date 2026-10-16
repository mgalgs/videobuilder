"""Run the test suite's modules across worker subprocesses instead of one process.

    python3 -m tests.run_parallel [--workers N]

Equivalent to `python3 -m unittest discover -s . -t .`, but each worker is its
own subprocess, so module-level state and background threads from one module
can never leak into another. Modules are bin-packed across workers by their
measured time in `tests/timings.json` (longest first, each to the currently
lightest worker), so the busiest modules start immediately instead of landing
on an already-loaded worker near the end.
"""
import argparse
import concurrent.futures
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
TIMINGS = pathlib.Path(__file__).resolve().parent / 'timings.json'

RAN_RE = re.compile(r'Ran (\d+) tests? in')
COUNTS_RE = re.compile(r'(failures|errors|skipped)=(\d+)')


def discover_modules():
    return sorted(p.stem for p in (ROOT / 'tests').glob('test_*.py'))


def load_weights(modules):
    """Seconds per module, from `tests/timings.json`; a module missing there
    (new since the file was last measured) gets the median of the rest, so it
    lands in some worker's bin instead of starving the packing of its weight."""
    try:
        measured = json.loads(TIMINGS.read_text())
    except FileNotFoundError:
        measured = {}
    known = sorted(measured.get(m, 0) for m in modules if m in measured)
    default = known[len(known) // 2] if known else 1.0
    return {m: measured.get(m, default) for m in modules}


def pack(modules, weights, workers):
    """Longest-processing-time bin packing: heaviest modules placed first,
    always into the bin with the least total so far."""
    bins = [[] for _ in range(workers)]
    totals = [0.0] * workers
    for m in sorted(modules, key=lambda m: weights[m], reverse=True):
        i = min(range(workers), key=lambda i: totals[i])
        bins[i].append(m)
        totals[i] += weights[m]
    return [b for b in bins if b]


def run_shard(modules):
    proc = subprocess.run([sys.executable, '-m', 'unittest', *(f'tests.{m}' for m in modules)],
                          cwd=ROOT, capture_output=True, text=True)
    return modules, proc.returncode, proc.stdout, proc.stderr


def summarize(output):
    ran = RAN_RE.search(output)
    counts = {k: int(v) for k, v in COUNTS_RE.findall(output)}
    return (int(ran.group(1)) if ran else None), counts


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workers', type=int, help='default: this machine/container\'s usable CPUs')
    a = p.parse_args(argv)

    from videobuilder.render import default_jobs
    workers = a.workers or default_jobs()

    modules = discover_modules()
    shards = pack(modules, load_weights(modules), min(workers, len(modules)))

    total_ran, totals, crashed = 0, {}, []
    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(shards)) as pool:
        for modules, code, out, err in pool.map(run_shard, shards):
            ran, counts = summarize(out + err)
            ok = code == 0 and ran is not None
            if ran is not None:
                total_ran += ran
            for k, v in counts.items():
                totals[k] = totals.get(k, 0) + v
            label = ', '.join(modules)
            if ok:
                print(f'ok    {label} ({ran} tests)')
            else:
                crashed_note = '' if ran is not None else ' [worker crashed]'
                print(f'FAILED {label}{crashed_note}', file=sys.stderr)
                sys.stderr.write(out)
                sys.stderr.write(err)
                if ran is None:
                    crashed.append(label)
    elapsed = time.monotonic() - start

    print('-' * 70)
    print(f'Ran {total_ran} tests in {elapsed:.3f}s ({workers} workers)')
    print()
    infos = [f'{k}={v}' for k in ('skipped', 'failures', 'errors') if (v := totals.get(k))]
    if crashed:
        infos.append(f'crashed={len(crashed)}')
    failed = bool(crashed) or totals.get('failures') or totals.get('errors')
    if failed:
        print('FAILED (' + ', '.join(infos) + ')')
    elif infos:
        print('OK (' + ', '.join(infos) + ')')
    else:
        print('OK')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
