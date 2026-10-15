#!/bin/sh
set -eu
: "${LIBRARY_DIR:=/var/tmp/claude-scratch/library}"
: "${CHECKOUTS_DIR:=/home/editor/src}"
: "${CAPABILITIES_DIR:=/opt/videobuilder-capabilities}"
: "${COMPENDIUM_DIR:=/opt/videobuilder-compendium}"
: "${GIT_AUTHOR_NAME:=Video Editor}"
: "${GIT_AUTHOR_EMAIL:=editor@example.com}"
mkdir -p "$LIBRARY_DIR" "$CHECKOUTS_DIR"
if [ -f /run/forge/id_ed25519 ] && [ -f /run/forge/known_hosts ]; then
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    cp /run/forge/id_ed25519 "$HOME/.ssh/id_ed25519"
    cp /run/forge/known_hosts "$HOME/.ssh/known_hosts"
    chmod 600 "$HOME/.ssh/id_ed25519" "$HOME/.ssh/known_hosts"
    printf 'Host *\n  IdentityFile %s/.ssh/id_ed25519\n  UserKnownHostsFile %s/.ssh/known_hosts\n  StrictHostKeyChecking yes\n' "$HOME" "$HOME" > "$HOME/.ssh/config"
    chmod 600 "$HOME/.ssh/config"
fi
git config --global user.name "$GIT_AUTHOR_NAME"
git config --global user.email "$GIT_AUTHOR_EMAIL"
if [ -d "$CAPABILITIES_DIR" ] && [ -d "$COMPENDIUM_DIR" ]; then
    exec python3 -m videobuilder editor --library "$LIBRARY_DIR" --checkouts "$CHECKOUTS_DIR" \
        --capabilities-dir "$CAPABILITIES_DIR" --compendium-dir "$COMPENDIUM_DIR" "$@"
elif [ -d "$CAPABILITIES_DIR" ]; then
    exec python3 -m videobuilder editor --library "$LIBRARY_DIR" --checkouts "$CHECKOUTS_DIR" \
        --capabilities-dir "$CAPABILITIES_DIR" "$@"
elif [ -d "$COMPENDIUM_DIR" ]; then
    exec python3 -m videobuilder editor --library "$LIBRARY_DIR" --checkouts "$CHECKOUTS_DIR" \
        --compendium-dir "$COMPENDIUM_DIR" "$@"
fi
exec python3 -m videobuilder editor --library "$LIBRARY_DIR" --checkouts "$CHECKOUTS_DIR" "$@"
