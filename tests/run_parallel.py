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
SUMMARY_RE = re.compile(r'^(OK|FAILED)(?: \(([^)]*)\))?\s*$', re.MULTILINE)


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
    """Totals come only from unittest's own last `OK`/`FAILED (...)` line, so a
    traceback or test body that happens to print e.g. `failures=1` can't be
    mistaken for the summary."""
    ran = RAN_RE.search(output)
    counts = {}
    matches = SUMMARY_RE.findall(output)
    if matches:
        _, detail = matches[-1]
        for part in filter(None, (p.strip() for p in detail.split(','))):
            key, _, value = part.partition('=')
            counts[key.strip()] = int(value)
    return (int(ran.group(1)) if ran else None), counts


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workers', type=int, help='default: this machine/container\'s usable CPUs')
    a = p.parse_args(argv)

    from videobuilder.render import default_jobs
    workers = a.workers or default_jobs()

    modules = discover_modules()
    shards = pack(modules, load_weights(modules), min(workers, len(modules)))

    total_ran, totals, crashed, failed_shards = 0, {}, [], []
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
                else:
                    failed_shards.append(label)
    elapsed = time.monotonic() - start

    print('-' * 70)
    print(f'Ran {total_ran} tests in {elapsed:.3f}s ({workers} workers)')
    print()
    infos = [f'{k}={v}' for k in
             ('failures', 'errors', 'skipped', 'expected failures', 'unexpected successes')
             if (v := totals.get(k))]
    if crashed:
        infos.append(f'crashed={len(crashed)}')
    if failed_shards:
        infos.append(f'nonzero exit={len(failed_shards)}')
    # The exit code, not the parsed counts, decides pass/fail: a shard can print
    # a clean summary and still exit nonzero (e.g. a crash during interpreter
    # shutdown, or unittest's own exit(1) on an unexpected success).
    failed = bool(crashed) or bool(failed_shards)
    if failed:
        print('FAILED (' + ', '.join(infos) + ')')
    elif infos:
        print('OK (' + ', '.join(infos) + ')')
    else:
        print('OK')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
