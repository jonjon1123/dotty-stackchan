# Production image for the dotty-pi runtime — the pi coding agent
# running as Dotty's voice-tool brain (replacing the RPi-hosted
# zeroclaw-bridge per #36).
#
# Build context is the repo root (set by docker-compose.yml build.context).
# Extension source and native deps are baked in; models.json and runtime
# state (brain.db, persona, auth) are provided by host volume mounts.
#
# Pins are intentional:
# - node:25.9-alpine3.23 — matches the spike build (audits/pi-rpc-spike-report.md).
# - @earendil-works/pi-coding-agent@0.74.0 — the version the spike was
#   measured against (3.2–3.7 s warm-turn latency).
# Bump these deliberately, not via floating tags.
FROM node:25.9-alpine3.23

RUN npm install -g @earendil-works/pi-coding-agent@0.74.0 \
    && pi --version

WORKDIR /root

# --- Extension (baked into image) ---

# Extension source → voice tools (memory_lookup, remember, recall_person,
# remember_person, think_hard, take_photo, play_song).
COPY dotty-pi-ext/ .pi/extensions/dotty-pi-ext/

# Install extension deps (better-sqlite3 is a native Alpine module).
# node-gyp needs python3, make, and g++ to compile the native addon.
# The host state mount can overlay these at runtime if node_modules exist
# on the host, but the baked copy makes the image self-contained.
WORKDIR /root/.pi/extensions/dotty-pi-ext
RUN apk add --no-cache python3 make g++ \
    && npm ci --ignore-scripts \
    && npx node-gyp rebuild \
       --directory=node_modules/better-sqlite3 \
       --build-from-source \
    && apk del make g++
WORKDIR /root

ENV PI_HOME=/root/.pi
ENV PI_OFFLINE=1

# Idle by default — pi is invoked on demand via `docker exec -i` from
# the PiClient (custom-providers/pi_voice/). The container stays warm
# so per-turn spawn cost is just `docker exec`, not a full image pull
# or node bootstrap.
CMD ["sleep", "infinity"]
