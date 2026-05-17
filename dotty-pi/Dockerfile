# Production image for the dotty-pi runtime — the pi coding agent
# running as Dotty's voice-tool brain on Unraid (replacing the RPi
# zeroclaw-bridge per #36).
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
ENV PI_HOME=/root/.pi
ENV PI_OFFLINE=1

# Idle by default — pi is invoked on demand via `docker exec -i` from
# the Unraid-local PiClient (custom-providers/pi_voice/). The container
# stays warm so per-turn spawn cost is just `docker exec`, not a full
# image pull or node bootstrap.
CMD ["sleep", "infinity"]
