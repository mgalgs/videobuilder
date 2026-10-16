#!/bin/bash
# Container start for the standalone editor (deploy/compose). Checks the
# settings it cannot run without, provisions $HOME (a tmpfs) and the data
# volume, then hands off to deploy/start-editor.sh in library mode with
# accounts on and the builder running through fork-sandbox's local bwrap mode.
set -euo pipefail

DATA=/var/tmp/claude-scratch
PASSWORD_FILE=/run/secrets/admin_password
SETUP="see deploy/compose/README.md"

fail() {
    printf 'videobuilder: %s\n' "$@" >&2
    exit 1
}

[ -n "${VB_ADMIN:-}" ] || fail "VB_ADMIN is not set." "Name the admin account in deploy/compose/.env ($SETUP)."
[ -f "$PASSWORD_FILE" ] || fail "no admin password: $PASSWORD_FILE is missing ($SETUP)."
[ -r "$PASSWORD_FILE" ] || fail "the admin password file is not readable by uid 1000." \
    "On the host, run: sudo chown 1000 admin-password ($SETUP)."
[ -n "$(tr -d '[:space:]' < "$PASSWORD_FILE")" ] || fail "the admin password file is empty ($SETUP)."
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || fail "CLAUDE_CODE_OAUTH_TOKEN is not set." \
    "Run 'claude setup-token' and put the token in deploy/compose/.env ($SETUP)."
[ -w "$DATA" ] || fail "$DATA (the data volume) is not writable by uid 1000."

# bwrap runs every preview, render and builder session. Check it now, the way
# fork-sandbox will use it, rather than fail on the first note.
if ! bwrap --ro-bind / / --dev /dev --proc /proc --unshare-all --die-with-parent true 2>/tmp/bwrap-check; then
    cat /tmp/bwrap-check >&2
    fail "bubblewrap cannot create a sandbox in this container." \
        "Check the seccomp, apparmor and systempaths settings in compose.yaml, and" \
        "on Ubuntu 23.10 or later the user namespace sysctl ($SETUP, Troubleshooting)."
fi
if ! pasta --quiet --config-net -- /bin/true 2>/tmp/pasta-check; then
    cat /tmp/pasta-check >&2
    fail "pasta cannot give the builder's sandbox a network." \
        "Check that /dev/net/tun exists on the host and is passed in compose.yaml ($SETUP, Troubleshooting)."
fi

# fork-sandbox's own install: symlinks into ~/.claude/scripts. $HOME is a
# fresh tmpfs on every start, so this runs every time; it is quick.
/opt/fork-sandbox/install.sh >/dev/null

# The credential the claude harness reads, in the shape `claude setup-token`
# tokens take on fork-sandbox's cluster path. It lives in $HOME (tmpfs), not
# on the data volume, and the variable is dropped before the editor starts.
# (A running build holds its own copy on the volume; see below.)
mkdir -p "$HOME/.claude"
(
    umask 077
    jq -n --arg token "$CLAUDE_CODE_OAUTH_TOKEN" \
        --argjson expires "$(( ($(date +%s) + 365 * 24 * 3600) * 1000 ))" \
        '{claudeAiOauth: {accessToken: $token, expiresAt: $expires}}' > "$HOME/.claude/.credentials.json"
)
unset CLAUDE_CODE_OAUTH_TOKEN

# fork-sandbox only takes projects under ~/src. Link it onto the volume, as
# the cluster pod does, so checkouts persist.
mkdir -p "$DATA/projects" "$DATA/forks"
ln -sfn "$DATA/projects" "$HOME/src"

# Each build's claude-sandboxed copies the token into a state directory under
# forks/ (on the volume) and removes it on exit. A build killed with the
# container never gets to, and fork-sandbox's sweep skips these. No build can
# be live yet, so remove any left behind.
rm -rf "$DATA"/forks/claude-sandboxed-state.*

# --envs current: a video made here pins this image's own videobuilder, which
# is already installed; building per-pin environments would need PyPI or a
# private forge. --agent-videobuilder-repo serves the builder that same source
# from the image (see the Dockerfile).
args=(
    --host 0.0.0.0 --port 8100
    --state-dir "$DATA/editor-state"
    --envs current
    --admin "$VB_ADMIN" --admin-password-file "$PASSWORD_FILE"
    --agent fork-sandbox
    --agent-extra-arg=--harness --agent-extra-arg=claude
    --agent-extra-arg=--model "--agent-extra-arg=${VB_MODEL:-claude-opus-5-5}"
    --agent-context-root "$DATA/forks/videobuilder-context"
    --agent-videobuilder-repo "${VB_VIDEOBUILDER_REPO:-file:///opt/videobuilder-source.git}"
)
[ -z "${VB_PUBLIC_HOST:-}" ] || args+=(--allow-host "$VB_PUBLIC_HOST")
[ -z "${VB_MUSIC_SOURCES:-}" ] || args+=(--music-sources "$VB_MUSIC_SOURCES")

exec /opt/videobuilder/deploy/start-editor.sh "${args[@]}" "$@"
