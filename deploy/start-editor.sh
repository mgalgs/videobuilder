#!/bin/sh
set -eu
: "${PROJECT_REPO:?set PROJECT_REPO to the project's forge URL}"
: "${PROJECT_DIR:=/home/editor/src/project}"
: "${GIT_AUTHOR_NAME:=Video Editor}"
: "${GIT_AUTHOR_EMAIL:=editor@example.com}"
mkdir -p "$HOME/.ssh" "$(dirname "$PROJECT_DIR")"
chmod 700 "$HOME/.ssh"
cp /run/forge/id_ed25519 "$HOME/.ssh/id_ed25519"
cp /run/forge/known_hosts "$HOME/.ssh/known_hosts"
chmod 600 "$HOME/.ssh/id_ed25519" "$HOME/.ssh/known_hosts"
printf 'Host *\n  IdentityFile %s/.ssh/id_ed25519\n  UserKnownHostsFile %s/.ssh/known_hosts\n  StrictHostKeyChecking yes\n' "$HOME" "$HOME" > "$HOME/.ssh/config"
chmod 600 "$HOME/.ssh/config"
git config --global user.name "$GIT_AUTHOR_NAME"
git config --global user.email "$GIT_AUTHOR_EMAIL"
if [ ! -d "$PROJECT_DIR/.git" ]; then
    git clone "$PROJECT_REPO" "$PROJECT_DIR"
fi
exec python3 -m videobuilder editor "$PROJECT_DIR" "$@"
