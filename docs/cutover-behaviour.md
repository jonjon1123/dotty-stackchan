---
title: dotty-behaviour cutover runbook
last_reviewed: 2026-05-19
status: executed
---

# dotty-behaviour cutover runbook

**Status:** executed 2026-05-19. RPi powered off, zeroclaw-bridge
archived to `/mnt/user/appdata/dotty-behaviour/archives/zeroclaw-archive-20260519T115841Z.tgz`.
This file is preserved as a reference for the cutover shape (and as
the procedure to restore from archive if the RPi ever comes back).
See the "Lessons learned" section at the bottom for the diffs between
this runbook as written and what was actually needed.

Steps to flip xiaozhi-server from the RPi-hosted `zeroclaw-bridge` to
the new Unraid-resident `dotty-behaviour` container, then decommission
the RPi.

Prerequisites:

- `feat/dotty-behaviour` branch merged (or being deployed from)
- SSH access to the Unraid host
- xiaozhi-server's `docker-compose.yml` and `data/.config.yaml` in
  this repo (they get edited in step 4)

## 1. Build + ship dotty-behaviour

```bash
BEHAVIOUR_HOST=root@<UNRAID_HOST> bash scripts/deploy-behaviour.sh
```

The script does: tracked-files tar → SSH → `docker build` →
`docker compose up -d --force-recreate` → poll `/health` → md5
round-trip verification.

Verify on Unraid:

```bash
ssh root@<UNRAID_HOST> 'curl -s http://localhost:8090/health'
# → {"status":"ok","service":"dotty-behaviour","version":"0.1.0"}
```

## 2. Migrate state files from the RPi

```bash
# household.yaml — used by greeter + face_recognized handler
scp <ZEROCLAW_USER>@<ZEROCLAW_HOST>:/root/.zeroclaw/household.yaml \
    /tmp/household.yaml
scp /tmp/household.yaml \
    root@<UNRAID_HOST>:/mnt/user/appdata/dotty-behaviour/state/household.yaml

# greeter_state.json — preserves greet log + per-day cap counters
scp <ZEROCLAW_USER>@<ZEROCLAW_HOST>:/root/.zeroclaw/greeter_state.json \
    /tmp/greeter_state.json || true  # may not exist if greeter never fired
scp /tmp/greeter_state.json \
    root@<UNRAID_HOST>:/mnt/user/appdata/dotty-behaviour/state/greeter_state.json \
    || true

# Google Calendar service-account JSON
scp <ZEROCLAW_USER>@<ZEROCLAW_HOST>:/root/.zeroclaw/secrets/google-calendar-sa.json \
    /tmp/cal-sa.json
scp /tmp/cal-sa.json \
    root@<UNRAID_HOST>:/mnt/user/appdata/dotty-behaviour/secrets/google-calendar-sa.json
rm /tmp/cal-sa.json
```

The state dir is bind-mounted into the container; no restart needed
after copying (household.yaml hot-reloads on mtime, greeter_state.json
is read on next greet).

## 3. Migrate daily NDJSON logs (optional)

These are append-only ring files; older days can stay on the RPi as
historical archive if you don't need them on Unraid:

```bash
ssh <ZEROCLAW_USER>@<ZEROCLAW_HOST> \
    'sudo tar -czf /tmp/zb-logs.tgz -C /root/zeroclaw-bridge logs/'
scp <ZEROCLAW_USER>@<ZEROCLAW_HOST>:/tmp/zb-logs.tgz /tmp/
scp /tmp/zb-logs.tgz root@<UNRAID_HOST>:/tmp/
ssh root@<UNRAID_HOST> \
    'tar -xzf /tmp/zb-logs.tgz -C /mnt/user/appdata/dotty-behaviour/'
```

## 4. Retarget xiaozhi-server at the new URL

Edit `docker-compose.yml` in this repo:

```yaml
environment:
  - VISION_BRIDGE_URL=http://<XIAOZHI_HOST>:8090  # was: http://<ZEROCLAW_HOST>:8080
  # NOTE: 127.0.0.1 only works if xiaozhi-server uses host networking.
  # It doesn't (bridge net), so use the Unraid LAN IP, not loopback.
```

Edit `data/.config.yaml`:

```yaml
plugins:
  vision_explain: http://<XIAOZHI_HOST>:8090/api/vision/explain
```

Drop the obsolete LLM config block in `.config.yaml` that points at
`http://<ZEROCLAW_HOST>:8080/api/message/stream` — PiVoiceLLM doesn't
use it, and the bridge that served it is about to be powered off.

Deploy the xiaozhi-server config change:

```bash
bash scripts/deploy-xiaozhi.sh  # or whichever script you use
```

Then recreate the container so the new env takes effect (a plain
`docker compose restart` will NOT pick up env-var changes from
`docker-compose.yml` — it only re-runs the existing container's
entrypoint with the existing environment):

```bash
ssh root@<UNRAID_HOST> \
    'cd /mnt/user/appdata/xiaozhi-server && docker compose up -d xiaozhi-esp32-server'
```

## 5. Smoke-test

```bash
# Perception event ingest hits the new container
ssh root@<UNRAID_HOST> 'curl -s http://localhost:8090/api/perception/state'

# Trigger a take_photo via the firmware (talk to Dotty and ask "what
# do you see?") — verify the description comes from dotty-behaviour's
# vision_cache, not the bridge:
ssh root@<UNRAID_HOST> 'docker logs --tail 20 dotty-behaviour | grep vision'
```

Optional: tail the bridge journal — there should be zero new
perception events, vision requests, or admin POSTs:

```bash
ssh <ZEROCLAW_USER>@<ZEROCLAW_HOST> 'sudo journalctl -u zeroclaw-bridge -f'
```

## 6. Decommission the RPi

Once smoke-test passes:

```bash
# Stop and disable the service
ssh <ZEROCLAW_USER>@<ZEROCLAW_HOST> '
    sudo systemctl stop zeroclaw-bridge
    sudo systemctl disable zeroclaw-bridge
'

# Archive the RPi state to Unraid for posterity
ssh <ZEROCLAW_USER>@<ZEROCLAW_HOST> '
    sudo tar -czf /tmp/zeroclaw-archive.tgz \
        /root/.zeroclaw /root/zeroclaw-bridge /etc/systemd/system/zeroclaw-bridge.service
'
scp <ZEROCLAW_USER>@<ZEROCLAW_HOST>:/tmp/zeroclaw-archive.tgz /tmp/
scp /tmp/zeroclaw-archive.tgz \
    root@<UNRAID_HOST>:/mnt/user/appdata/dotty-behaviour/archives/
ssh <ZEROCLAW_USER>@<ZEROCLAW_HOST> 'rm /tmp/zeroclaw-archive.tgz'

# Power off
ssh <ZEROCLAW_USER>@<ZEROCLAW_HOST> 'sudo poweroff'
```

The RPi can now be physically removed. Update CLAUDE.md /
README.md / docker-compose.yml comments to drop the `<ZEROCLAW_HOST>`
references in a follow-up commit.

## Rollback

If anything goes wrong before step 6, revert in this order:

1. Revert the `VISION_BRIDGE_URL` and `vision_explain` config edits.
2. Restart xiaozhi-server.
3. Bridge.py is still running on the RPi (disabled only in step 6),
   so it'll start receiving events again immediately.

After step 6, rollback requires restoring `/root/.zeroclaw/` and
`/root/zeroclaw-bridge/` from the archive tgz and re-enabling the
systemd unit.

## Lessons learned (2026-05-19 execution)

The runbook above is preserved as written for archaeology. These are
the deltas between it and what actually worked:

1. **`VISION_BRIDGE_URL` must be the Unraid LAN IP, not `127.0.0.1`.**
   Loopback inside xiaozhi-server resolves to the container itself,
   not the host, because xiaozhi-server runs on a bridge net rather
   than `network_mode: host`. dotty-behaviour is on host net (so its
   loopback reaches the host), but xiaozhi-server isn't, so the URL
   xiaozhi uses must be host-routable. The fix is the host's LAN IP.
   Verified by `docker exec xiaozhi-esp32-server python3 -c
   'urllib.request.urlopen("http://<host>/health")'` against both.

2. **Step 4 needs `docker compose up -d`, not `docker compose restart`.**
   `restart` re-runs the existing container with the existing env;
   compose env-var changes only apply on container recreate. `up -d`
   is idempotent and recreates if and only if the spec changed.

3. **scp from the RPi failed — use tar-over-ssh instead.** DietPi
   ships without the OpenSSH server's sftp subsystem, so every
   `scp <ZEROCLAW_USER>@<ZEROCLAW_HOST>:...` line above is broken.
   The working pattern is `ssh ... 'sudo cat <path>' | ssh
   <unraid> 'cat > <dest>'` for single files, and `ssh ... 'sudo
   tar -czf - <paths>' | ssh <unraid> 'cat > /...archive.tgz'` for
   trees. This is captured in `[[reference_dietpi_file_transfer]]`
   in user memory and is the canonical RPi→Unraid transfer for this
   project.

4. **The `dotty-behaviour/Dockerfile` had six missing `COPY` entries**
   — `consumers/`, `dispatch/`, `greeter/`, `household/`, `logs/`,
   `calendar_/`. The post-scaffold slice commits added each
   subpackage but never updated the COPY list, so the first build
   produced an image that crashed on import. Fixed in `ba5224f`
   before the deploy could land. Caught only because the deploy
   script polls `/health` and `docker logs` for 30 s — without that
   the build would have looked successful.

5. **`purr.opus` asset wasn't shipped with the original scaffold.**
   `dotty-behaviour/consumers/purr_player.py` was lifted from
   `bridge/purr_player.py` but the asset at `bridge/assets/purr.opus`
   wasn't copied across. First head-pet event after cutover would
   have logged a missing-asset warning. Fixed in the same
   tidy-up commit as these doc updates.
