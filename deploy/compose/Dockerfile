# The standalone editor: deploy/Dockerfile's image, plus fork-sandbox and the
# Claude Code CLI, so the AI builder runs in this same container, sandboxed by
# bubblewrap. compose.yaml builds deploy/Dockerfile first (its test and
# frame-hash gates included) and hands it to this file as the `base` context.
# Without compose, from the repository root:
#
#   docker build -f deploy/Dockerfile -t videobuilder-base .
#   docker build -f deploy/compose/Dockerfile \
#       --build-context base=docker-image://videobuilder-base -t videobuilder-editor .
FROM base
USER root

# fork-sandbox's local run needs: bwrap (already in the base), pasta (passt)
# for the sandbox's network, ip (iproute2) to find its egress interface,
# tmux for detached runs, jq, socat, and ps/pgrep (procps). less and ripgrep
# are for the agent inside the sandbox, which shares this image's /usr.
# xz-utils unpacks node.
RUN apt-get update && apt-get install -y --no-install-recommends \
        passt iproute2 tmux jq socat procps less ripgrep xz-utils && \
    rm -rf /var/lib/apt/lists/*

# Node 22 for the Claude Code CLI (Debian's nodejs is older), checked against
# the release's published SHA256 list, the way fork-sandbox's own sandbox
# image does it.
ARG NODE_VERSION=v22.16.0
RUN set -eu; \
    case "$(dpkg --print-architecture)" in \
        amd64) node_arch=x64 ;; \
        arm64) node_arch=arm64 ;; \
        *) echo 'node needs an amd64 or arm64 host' >&2; exit 1 ;; \
    esac; \
    node_file="node-${NODE_VERSION}-linux-${node_arch}.tar.xz"; \
    node_url="https://nodejs.org/dist/${NODE_VERSION}"; \
    tmp="$(mktemp -d)"; \
    curl -fsSLo "$tmp/SHASUMS256.txt" "$node_url/SHASUMS256.txt"; \
    curl -fsSLo "$tmp/$node_file" "$node_url/$node_file"; \
    awk -v file="$node_file" '$2 == file' "$tmp/SHASUMS256.txt" > "$tmp/checksum"; \
    [ -s "$tmp/checksum" ]; \
    (cd "$tmp" && sha256sum -c checksum); \
    tar -xJf "$tmp/$node_file" -C /usr/local --strip-components=1 \
        --exclude=CHANGELOG.md --exclude=LICENSE --exclude=README.md; \
    rm -rf "$tmp"

# Installed globally, under /usr/local, never under $HOME: $HOME is a tmpfs
# here, and the sandbox mounts this image's /usr. The default is the version
# fork-sandbox's credential contract was last verified against at the pin
# below.
ARG CLAUDE_CODE_VERSION=2.1.280
RUN npm install -g --no-fund --no-audit "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" && \
    npm cache clean --force && \
    claude --version

# fork-sandbox, pinned by full commit sha. Root-owned, so nothing the editor
# or a builder does can rewrite it.
ARG FORK_SANDBOX_REPO=https://github.com/mgalgs/fork-sandbox
ARG FORK_SANDBOX_REF=b836e130f10b8449fcd956ff85d61da6dfc96507
RUN set -eu; \
    echo "$FORK_SANDBOX_REF" | grep -Eqx '[0-9a-f]{40}' || \
        { echo 'FORK_SANDBOX_REF must be a full 40-hex commit sha' >&2; exit 1; }; \
    git init -q /opt/fork-sandbox; \
    git -C /opt/fork-sandbox fetch -q --depth 1 "$FORK_SANDBOX_REPO" "$FORK_SANDBOX_REF"; \
    git -C /opt/fork-sandbox checkout -q --detach FETCH_HEAD; \
    [ "$(git -C /opt/fork-sandbox rev-parse HEAD)" = "$FORK_SANDBOX_REF" ]; \
    git config --system --add safe.directory /opt/fork-sandbox

# The builder reads the pinned videobuilder's source (skill included). A new
# video pins this image's own version, so serve exactly this source, tagged
# the way the editor's staging expects, from a local repository: staging it
# needs no network and no public mirror. --agent-videobuilder-repo points here.
COPY . /tmp/videobuilder-source
RUN set -eu; \
    version="$(python3 -c 'import videobuilder; print(videobuilder.__version__)')"; \
    cd /tmp/videobuilder-source; \
    git init -q; \
    git add -A; \
    git -c user.name=videobuilder -c user.email=videobuilder@example.com commit -qm "videobuilder $version"; \
    git tag "v$version"; \
    git clone -q --bare /tmp/videobuilder-source /opt/videobuilder-source.git; \
    cd /; \
    rm -rf /tmp/videobuilder-source; \
    git config --system --add safe.directory /opt/videobuilder-source.git

COPY deploy/compose/start.sh /usr/local/bin/vb-compose-start

USER 1000:1000
ENV HOME=/home/editor \
    PATH=/home/editor/.claude/scripts:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    DISABLE_AUTOUPDATER=1
# Fail the build, not the first note, if fork-sandbox is missing a tool.
RUN /opt/fork-sandbox/install.sh --check
CMD ["/usr/local/bin/vb-compose-start"]
