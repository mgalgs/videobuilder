# The builder agent's base: the editor image plus ManimGX for 3D shots.
# fork-sandbox's build-sandbox-image.sh --base layers the agent tooling on
# top of this, and needs the image to end as root.
#
#   docker build --build-arg BASE=<editor base image> -f deploy/agent/Dockerfile deploy/agent
#
# ManimGX's wheels are GPL-3 (they bundle x264), so it stays out of the
# editor image: only authors render shots; films read the committed MP4.
ARG BASE
FROM ${BASE}
USER root
# rsvg-convert renders gathered or uploaded SVGs to PNG at any size.
RUN apt-get update && apt-get install -y --no-install-recommends librsvg2-bin \
    && rm -rf /var/lib/apt/lists/* && rsvg-convert --version
RUN python3 -m venv --system-site-packages /opt/manimgx \
    && /opt/manimgx/bin/pip install --no-cache-dir manimgx==0.1.1 \
    && /opt/manimgx/bin/python -c 'import manimgx'
