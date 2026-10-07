"""Flatten moby's default seccomp profile for an amd64 container with no
capabilities, then allow the syscalls bwrap needs to build a user namespace
sandbox. Prints the OCI profile to stdout."""
import json
import sys

ARCH = "amd64"
USERNS = ["clone", "unshare", "setns", "mount", "umount2", "pivot_root",
          "sethostname", "setdomainname"]

src = json.load(open(sys.argv[1]))
out = []
for s in src["syscalls"]:
    inc, exc = s.get("includes") or {}, s.get("excludes") or {}
    if inc.get("caps"):
        continue  # minKernel entries stay: every target kernel is newer
    if inc.get("arches") and ARCH not in inc["arches"]:
        continue
    if exc.get("arches") and ARCH in exc["arches"]:
        continue
    # excludes.caps: we hold no caps, so the entry applies.
    if "clone" in s["names"] and s.get("args"):
        continue  # replaced by an unconditional clone below
    e = {k: v for k, v in s.items() if k not in ("includes", "excludes", "comment")}
    out.append(e)
out.append({"names": USERNS, "action": "SCMP_ACT_ALLOW"})
prof = {k: v for k, v in src.items() if k != "syscalls"}
prof["archMap"] = [a for a in prof["archMap"] if a["architecture"] == "SCMP_ARCH_X86_64"]
prof["syscalls"] = out
print(json.dumps(prof, indent=1))
