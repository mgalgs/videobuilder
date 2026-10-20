# Self-hosting the editor with Docker Compose

This directory runs the videobuilder editor on one Linux machine with Docker:
a video library with accounts, and an AI builder that turns notes into new
versions. Everything runs in one container, built from this checkout. You
don't need Kubernetes, or Python or Pango on the host.

The builder is Claude Code, run by [fork-sandbox](https://github.com/mgalgs/fork-sandbox)
in its local mode: each note gets a throwaway clone of the video, inside a
bubblewrap sandbox in the editor's container. The container gets no Docker
socket and no privileges, and it runs as uid 1000 with every capability
dropped.

## What you need

- A Linux machine (amd64 or arm64) with Docker Engine and Docker Compose v2.24
  or newer (`docker compose version`). Debian 13 and Ubuntu 24.04 are the
  target hosts.
- About 10 GB of disk for the image, plus room for your videos.
- A Claude subscription or account that can run Claude Code, and any machine
  where you can run `claude setup-token`.
- A domain name pointing at the machine, for TLS (see step 5). Without one,
  you can still use the editor over an ssh tunnel.

## Set up

All commands run from this directory:

    git clone <this repository> videobuilder
    cd videobuilder/deploy/compose

**1. Settings.** Copy the example and edit it:

    cp .env.example .env
    chmod 600 .env

- `VB_ADMIN`: the admin's username, for example `admin`.
- `VB_PUBLIC_HOST`: the hostname people will type, for example
  `editor.example.com`. The editor refuses requests for any other host.
- `CLAUDE_CODE_OAUTH_TOKEN`: run `claude setup-token` on any machine with
  Claude Code installed, sign in, and paste the token it prints. It lasts a
  year. When it expires, make a new one, put it here, and run
  `docker compose up -d` again.
- `VB_MODEL`: the builder's model. The default is `claude-opus-5-5`.

**2. The admin password.** Put it on one line in a file called
`admin-password`, here, beside `compose.yaml`:

    printf '%s\n' 'a long password of your own' > admin-password
    chmod 600 admin-password

The container runs as uid 1000. If `id -u` doesn't print `1000` on this
machine, also run `sudo chown 1000 admin-password`, so the container can read
it.

`.env` and `admin-password` are in `.gitignore` and `.dockerignore`, so they
never end up in a commit or an image. The stack refuses to start if `VB_ADMIN`,
the token or the password file is missing, and its message says which one.

**3. Build.** This builds `deploy/Dockerfile` first. That build runs the full
test suite and checks rendered frames against `deploy/frames.sha256`, so it
takes a while the first time:

    docker compose build

**4. Start.**

    docker compose up -d
    docker compose ps          # wait for "healthy"
    docker compose logs -f editor

Check it from the machine itself:

    curl -fsS http://127.0.0.1:8100/healthz

The port is published on `127.0.0.1` only (`VB_PORT` changes the number).
**Never expose it to the internet directly**: put a TLS reverse proxy in front.

**5. TLS.** Any reverse proxy works if it terminates TLS, forwards to
`127.0.0.1:8100`, keeps the `Host` header, and sets `X-Forwarded-Proto: https`
(sign-in cookies are marked `Secure` only when it does). With
[Caddy](https://caddyserver.com) installed on the host, this whole
`/etc/caddy/Caddyfile` gets and renews a certificate by itself:

    editor.example.com {
        reverse_proxy 127.0.0.1:8100
    }

Then run `sudo systemctl reload caddy`. Uploads can be large (source videos
are up to 2 GiB by default), so if you use a proxy other than Caddy, raise its
request size limit.

No domain? From your own computer, run
`ssh -L 8100:127.0.0.1:8100 you@the-machine`, then open http://127.0.0.1:8100.

## First video

1. Open `https://editor.example.com` and sign in as `VB_ADMIN` with the
   password from `admin-password`.
2. Click **+ New video**, give it a name, describe what it's for, and click
   **Create**. That first note goes to the builder.
3. The video page shows the builder working. A build usually takes several
   minutes. When it lands, a new version plays.
4. Use **Chat** to send another note ("make the title bigger at 0:03"). Each
   note becomes a new version.

Anyone who can reach the site can sign up for their own account, and every
account's notes spend your Claude usage. To cap that, pass the editor flags
from the top-level README's editor section, for example
`--account-daily-note-cap`, through a `compose.override.yaml` beside
`compose.yaml` (Compose reads it automatically):

```yaml
services:
  editor:
    command: ["/usr/local/bin/vb-compose-start", "--account-daily-note-cap", "20"]
```

## Where data lives

Everything that persists is in the `videobuilder_data` volume, mounted at
`/var/tmp/claude-scratch` in the container:

| Path in the volume | What |
|---|---|
| `library/` | one bare git repository per video |
| `projects/` | the editor's checkouts (`~/src` in the container links here) |
| `editor-state/` | notes, accounts, render cache, builder sessions |
| `forks/` | fork-sandbox's runs, and the videobuilder source the builder reads |

`$HOME` is a tmpfs: it holds the builder's credential and is rebuilt on every
start. While a build runs, fork-sandbox keeps a copy of the Claude token in a
`forks/claude-sandboxed-state.*` directory in the volume. The build removes it
when it ends, and the container removes any left by a build cut off by a stop,
on its next start. So a copy of the volume can hold the token: delete
`forks/claude-sandboxed-state.*` from any copy you share. `docker compose down` keeps the volume. `docker compose down -v`
deletes it, with every video in it.

## Upgrading

    git pull
    docker compose build
    docker compose up -d

Your videos and accounts are in the volume, so they survive this. Restarting
stops any build that is still running, so upgrade when no notes are building.

A video made here pins the editor's own videobuilder version. The editor runs
every video with the version in the image (`--envs current`), so after an
upgrade, older videos render with the new version.

## Music (optional)

The director's music picker is off by default. To turn it on, write a sources
file (the format is in the top-level README, under "Music sources") as
`music-sources.toml` here, then add this to `compose.override.yaml`:

```yaml
services:
  editor:
    volumes:
      - ./music-sources.toml:/etc/videobuilder/music-sources.toml:ro
    environment:
      VB_MUSIC_SOURCES: /etc/videobuilder/music-sources.toml
```

Then run `docker compose up -d`: the start script passes the file to the
editor's `--music-sources` flag. Only add sources whose licence lets you use
the music the way you intend.

## How the container is locked down

| Setting | Why |
|---|---|
| `user: 1000:1000`, `cap_drop: [ALL]`, `no-new-privileges` | No root, no capabilities, nothing setuid. bubblewrap and pasta need no capability: they build their own user namespace. |
| `seccomp=seccomp-bwrap.json` | Moby's default profile, plus the syscalls a user namespace sandbox needs (`clone`, `unshare`, `mount`, ...). `seccomp-bwrap.NOTICE` says how it was made. |
| `apparmor=unconfined` | Docker's AppArmor profile forbids `mount`, which bwrap needs inside its own namespace. |
| `systempaths=unconfined` | Docker masks parts of `/proc`, and the kernel then refuses the fresh `/proc` each sandbox mounts. As uid 1000 with no capabilities, the container still can't write what this unmasks. |
| `devices: /dev/net/tun` | pasta gives each builder sandbox its network through a tun device in the sandbox's own network namespace. |
| `network_mode: bridge` | fork-sandbox points the sandbox's DNS at a real nameserver. A Compose network offers only Docker's internal stub, which the sandbox can't reach. |

The builder has internet access, the same as the container. It can also reach
your LAN, the same as any container on this machine. It can't see the
container's own loopback, its `$HOME`, the admin password or the video
library: only a clone of the one video it is working on. It does hold a copy
of the Claude token, since that is how it calls the model, so anything a build
runs could read that token. That copy sits in the volume under `forks/` for as
long as the build runs. If you suspect it leaked, make a new one with
`claude setup-token` and revoke the old one from your Claude account settings.

## Troubleshooting

`docker compose logs editor` shows why the editor stopped. Before starting,
it checks bubblewrap and pasta.

**"bubblewrap cannot create a sandbox"**, often with `setting up uid map:
Permission denied` or `loopback: Failed RTM_NEWADDR: Operation not
permitted`: Ubuntu 23.10 and later restrict unprivileged user
namespaces through AppArmor, even in an unconfined container. Allow them:

    sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
    echo 'kernel.apparmor_restrict_unprivileged_userns=0' | \
        sudo tee /etc/sysctl.d/60-videobuilder-userns.conf
    docker compose up -d

That sysctl applies to the whole machine, so any program on it can create
user namespaces again, the way Debian and older Ubuntu releases allow. On
other distributions, check that `sysctl kernel.unprivileged_userns_clone`, if
it exists, is `1`, and that `user.max_user_namespaces` isn't `0`.

**"pasta cannot give the builder's sandbox a network"**, or
`error gathering device information ... /dev/net/tun` from Compose: load the
tun module with `sudo modprobe tun`, and add `tun` to `/etc/modules` to keep it
after a reboot.

**A note fails at once**: the note shows the builder's error. An expired or
mistyped token is the usual cause: fix it in `.env`, then `docker compose up -d`.

**The site refuses every request through the proxy**: `VB_PUBLIC_HOST` must be
exactly the hostname in the browser's address bar, and the proxy must pass the
`Host` header through unchanged.

## Pins

The image pins fork-sandbox by commit, node by version and checksum, and
Claude Code by version (`deploy/compose/Dockerfile`). To try others:

    docker compose build --build-arg FORK_SANDBOX_REF=<full commit sha> \
        --build-arg CLAUDE_CODE_VERSION=<version>
