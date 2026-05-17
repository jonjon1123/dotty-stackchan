# dotty-pi

Production Docker image for the **pi coding agent** running as Dotty's
voice-tool brain on Unraid. Replaces the RPi-hosted `zeroclaw-bridge`
per [#36](https://github.com/BrettKinny/dotty-stackchan/issues/36).

## What this is

A pinned `node:25.9-alpine3.23` image with `@earendil-works/pi-coding-agent`
installed globally. Idles via `sleep infinity`; voice turns invoke pi on
demand via `docker exec -i` from the Unraid-local `PiClient` (lives in
[`../custom-providers/pi_voice/`](../custom-providers/pi_voice/)).

The runtime contract is:

- **xiaozhi-server** routes voice-LLM calls to the `PiVoiceLLM` provider.
- **PiVoiceLLM / PiClient** translates each turn into a pi RPC request.
- **pi** (this container) runs the prompt against llama-swap on the same
  host (`http://localhost:8080/v1`, model `qwen3.6:27b` by default), with
  the [`dotty-pi-ext`](../dotty-pi-ext/) extension loaded for the five
  voice tools (`memory_lookup`, `think_hard`, `take_photo`, `play_song`,
  `set_led`).

## Build + run on Unraid

```bash
ssh root@<UNRAID_HOST> '
  mkdir -p /mnt/user/appdata/dotty-pi-src &&
  cd /mnt/user/appdata/dotty-pi-src &&
  # copy Dockerfile + docker-compose.yml here, plus models.json into agent/
  docker build -t dotty-pi:0.1.0 . &&
  docker compose up -d
'
```

First-time appdata layout:

```
/mnt/user/appdata/dotty-pi/
├── agent/
│   └── models.json          # provider config (this directory)
├── sessions/                # pi session state (unused for now)
├── persona/                 # Dotty persona — migrated from RPi
├── memory/
│   └── brain.db             # FTS5 store — migrated from RPi
└── extensions/
    └── dotty-pi-ext/        # voice-tool extension (../dotty-pi-ext/)
```

## Versioning

| Tag | Pi version | Notes |
|---|---|---|
| `dotty-pi:0.1.0` | `0.74.0` | Production-grade promotion of the 2026-05-15 spike. |
| `dotty-pi:spike` | `0.74.0` | The original day-0 spike (`audits/pi-rpc-spike-report.md`). Keep until production is soaked. |

Bump the image tag deliberately when pi or node moves; do not use floating
tags. Cutover testing depends on a known-good image.

## See also

- [`../dotty-pi-ext/README.md`](../dotty-pi-ext/README.md) — voice-tool extension contract.
- [`../custom-providers/pi_voice/README.md`](../custom-providers/pi_voice/README.md) — xiaozhi-side glue.
- [#36](https://github.com/BrettKinny/dotty-stackchan/issues/36) — the cutover plan + soak rule.
