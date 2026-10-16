"""Flatten moby's default seccomp profile for an amd64 container with no
capabilities, then allow the syscalls bwrap needs to build a user namespace
sandbox. Prints the OCI profile to stdout.

With --docker, keep moby's per-arch and per-capability conditions instead of
flattening them: Docker evaluates those itself at container start, so one
profile serves every architecture. Only the arg-masked clone entries are
replaced, as in the flattened form.

    python3 mkprofile.py [--docker] default.json > profile.json"""
import json
import sys

ARCH = "amd64"
USERNS = ["clone", "unshare", "setns", "mount", "umount2", "pivot_root",
          "sethostname", "setdomainname"]


def build(src, docker=False):
    out = []
    for s in src["syscalls"]:
        if "clone" in s["names"] and s.get("args"):
            continue  # replaced by an unconditional clone below
        if docker:
            out.append(s)
            continue
        inc, exc = s.get("includes") or {}, s.get("excludes") or {}
        if inc.get("caps"):
            continue  # minKernel entries stay: every target kernel is newer
        if inc.get("arches") and ARCH not in inc["arches"]:
            continue
        if exc.get("arches") and ARCH in exc["arches"]:
            continue
        # excludes.caps: we hold no caps, so the entry applies.
        out.append({k: v for k, v in s.items() if k not in ("includes", "excludes", "comment")})
    out.append({"names": USERNS, "action": "SCMP_ACT_ALLOW"})
    prof = {k: v for k, v in src.items() if k != "syscalls"}
    if not docker:
        prof["archMap"] = [a for a in prof["archMap"] if a["architecture"] == "SCMP_ARCH_X86_64"]
    prof["syscalls"] = out
    return prof


if __name__ == "__main__":
    args = sys.argv[1:]
    docker = "--docker" in args
    paths = [a for a in args if a != "--docker"]
    if len(paths) != 1:
        sys.exit(__doc__)
    print(json.dumps(build(json.load(open(paths[0])), docker), indent=1))
