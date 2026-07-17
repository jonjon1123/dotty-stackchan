# Dotty — Self-Hosted StackChan Robot Assistant

A fully self-hosted voice stack for the M5Stack **StackChan** desktop robot.
Voice I/O routes through a self-hosted xiaozhi-esp32-server; the brain is a
**pi** coding agent running in the `dotty-pi` container. No cloud AI services
required — fully self-hosted except for the LLM call (replaceable with local
Ollama).

## Prerequisites

- Docker with Compose v2
- NVIDIA GPU with CUDA runtime (required for llama-swap + WhisperLocal ASR)
- Python 3.10+ (for `hf` model downloads)
- ~15 GB disk for models

## Setup

### 1. Clone and create your `.env`

```bash
git clone https://github.com/BrettKinny/dotty-stackchan.git
cd dotty-stackchan
cp .env.example .env
```

Edit `.env` — the only **required** values are:

| Variable | What to set |
|---|---|
| `TZ` | Your timezone (e.g. `Australia/Brisbane`) |
| `DOTTY_ADMIN_TOKEN` | A random secret string (same value shared across all services) |

Everything else has sensible defaults. See `.env.example` for the full list.

### 2. Create the state directory

All runtime state lives under `state/` (gitignored). Create the skeleton:

```bash
mkdir -p state/shared state/logs state/secrets state/behaviour state/pi/agent
```

### 3. Download models

Models are not shipped with the repo. Install the HuggingFace CLI and
download everything into `models/`:

```bash
pip install huggingface-hub
```

#### ASR — pick one

**WhisperLocal** (default — CUDA, best accuracy):

```bash
mkdir -p models/whisper-small.en-ct2
hf download Systran/faster-whisper-small.en \
  --local-dir models/whisper-small.en-ct2 \
  --include "config.json model.bin tokenizer.json vocabulary.txt"
```

**SenseVoiceSmall** (CPU fallback):

```bash
mkdir -p models/SenseVoiceSmall
hf download FunAudioLLM/SenseVoiceSmall \
  --local-dir models/SenseVoiceSmall
```

**SenseVoiceOnnx** (int8, no PyTorch):

```bash
mkdir -p models/SenseVoiceSmall-onnx
hf download csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 \
  --local-dir models/SenseVoiceSmall-onnx \
  --include "model.int8.onnx tokens.txt"
```

After downloading, set `selected_module.ASR` in `data/.config.yaml` to match:
`WhisperLocal` (default), `FunASR`, or `SenseVoiceOnnx`.

#### TTS — Piper (default, offline)

```bash
mkdir -p models/piper
hf download rhasspy/piper-voices \
  --local-dir models/piper \
  --include "en/en_GB/cori/medium/en_GB-cori-medium.onnx en/en_GB/cori/medium/en_GB-cori-medium.onnx.json"
mv models/piper/en/en_GB/cori/medium/en_GB-cori-medium.* models/piper/
rm -rf models/piper/en
```

To use a different Piper voice, download its `.onnx` + `.onnx.json` pair
into `models/piper/` and update `TTS.LocalPiper` paths in
`data/.config.yaml`.

#### VAD — SileroVAD

```bash
mkdir -p models/snakers4_silero-vad
hf download snakers4/silero-vad \
  --local-dir models/snakers4_silero-vad \
  --include "files/silero_vad.onnx"
mv models/snakers4_silero-vad/files/silero_vad.onnx models/snakers4_silero-vad/
rm -rf models/snakers4_silero-vad/files models/snakers4_silero-vad/src
```

#### LLM — GGUF models for llama-swap

llama-swap mounts `models/` at `/models` inside its container.

```bash
mkdir -p models/Qwen3.5-4B
hf download Qwen/Qwen3.5-4B-GGUF \
  --local-dir models/Qwen3.5-4B \
  --include "Qwen3.5-4B-Q5_K_M.gguf"

mkdir -p models/Qwen3.5-27B
hf download Qwen/Qwen3.5-27B-GGUF \
  --local-dir models/Qwen3.5-27B \
  --include "Qwen3.5-27B-UD-IQ2_M.gguf"
```

**These files must exist at exactly these paths** — both
`data/llama-swap.config.yaml` and `dotty-pi/models.json` reference them
by name. If you use different files or paths, update both config files
(they must stay in sync).

After download, your `models/` directory should look like:

```
models/
├── Qwen3.5-4B/
│   └── Qwen3.5-4B-Q5_K_M.gguf          # voice chitchat (default)
├── Qwen3.5-27B/
│   └── Qwen3.5-27B-UD-IQ2_M.gguf        # think-big / think-small
├── piper/
│   ├── en_GB-cori-medium.onnx            # TTS voice
│   └── en_GB-cori-medium.onnx.json
├── whisper-small.en-ct2/                 # ASR (if WhisperLocal)
│   ├── config.json
│   ├── model.bin
│   ├── tokenizer.json
│   └── vocabulary.txt
└── snakers4_silero-vad/
    └── silero_vad.onnx                   # VAD
```

### 4. Edit config files

**`data/.config.yaml`** — the xiaozhi-server config. Key things to set:

| Section | Field | What to change |
|---|---|---|
| `server.websocket` | URL | Your Docker host's LAN IP (e.g. `ws://192.168.1.6:8000/xiaozhi/v1/`) |
| `selected_module` | ASR | Match the ASR backend you downloaded (default: `WhisperLocal`) |
| `prompt` | text | The system prompt — must start each reply with an emoji |
| `ASR.WhisperLocal` | `model_dir` | Must match your download path (`models/whisper-small.en-ct2`) |
| `TTS.LocalPiper` | `model_path` / `config_path` | Must match your Piper download paths |

**`data/llama-swap.config.yaml`** — llama-swap model registry. Edit the
`cmd:` paths if your GGUF files are in different locations. The model
aliases (`default`, `think-small`, `think-big`) must match the model IDs
in `dotty-pi/models.json`.

**`dotty-pi/models.json`** — pi's model registry. Model IDs (`default`,
`think-big`, `think-small`) must match the aliases in
`data/llama-swap.config.yaml`. Only edit this file if you're adding
removing models.

### 5. Build and start

```bash
docker compose up --build -d
```

That's it. Five containers, one network, one command.

### 6. Verify

```bash
# Check all containers are running
docker compose ps

# Dashboard should return {"status":"healthy"}
curl http://localhost:8081/health

# View logs
docker compose logs -f
```

Connect your StackChan to the WebSocket URL you set in
`data/.config.yaml` (`ws://<YOUR_DOCKER_HOST_IP>:8000/xiaozhi/v1/`).
The StackChan must be on the same LAN as the Docker host.

## Architecture

```
                 StackChan hardware → configured persona
                   │  ESP32-S3, xiaozhi firmware
                   │  WiFi / WebSocket (Xiaozhi protocol)
                   ▼
                 xiaozhi-esp32-server (:8000 ws, :8003 http)
                   ├─ ASR: WhisperLocal / FunASR / SenseVoiceOnnx (local)
                   ├─ TTS: LocalPiper / EdgeTTS (local or cloud)
                   └─ LLM: PiVoiceLLM
                        │  PiClient → docker exec -i dotty-pi pi --mode rpc …
                        ▼
                 dotty-pi (the brain)
                   ├─ outer loop: default model on llama-swap
                   └─ dotty-pi-ext → 7 voice tools:
                        memory_lookup · remember · recall_person ·
                        remember_person · think_hard (→ think-big) ·
                        take_photo · play_song

  Perception:       firmware event frames → xiaozhi relay → dotty-behaviour (:8090)
  LLM inference:    llama-swap (:8080 internal) — CUDA GPU, model matrix
  Admin dashboard:  dotty-bridge (:8081, /ui)
```

All five services run as Docker containers on a single host, connected by a
single bridge network (`dotty-net`). Inter-service traffic uses container
names — no IPs, no host networking.

## Firmware

This project includes a fork of the [StackChan firmware](https://github.com/m5stack/StackChan/tree/main/firmware) at `firmware/firmware/`
(a git submodule pinned to `BrettKinny/StackChan @ dotty`). The StackChan
device must be flashed with this firmware — it includes Dotty-specific
additions that the server stack depends on: the six-state StateManager,
perception event emission, MCP tool handlers, and the emotion protocol.

## Ports

Only four ports are published to the host (and thus to your LAN):

| Service | Host port | Protocol | Purpose |
|---|---|---|---|
| xiaozhi-esp32-server | **8000** | ws:// | WebSocket — device connects here |
| xiaozhi-esp32-server | **8003** | http | OTA firmware updates, HTTP admin |
| llama-swap | **8080** | http | LLM inference API + dashboard at `/ui` |
| dotty-bridge | **8081** | http | Admin dashboard at `/ui` |

Internal-only (not published, reachable only between containers on `dotty-net`):

| Service | Container port | Purpose |
|---|---|---|
| dotty-behaviour | 8090 | Perception bus, vision/audio explain, greeter |

## Network

All containers live on the `dotty-net` Docker bridge network. Services
reference each other by **container name**:

- `dotty-xiaozhi-esp32-server` — the voice pipeline
- `llama-swap` — LLM inference
- `dotty-bridge` — admin dashboard
- `dotty-pi` — the brain (pi coding agent)
- `dotty-behaviour` — perception, greeter, vision/audio explain

No `network_mode: host`. No hardcoded IPs. The compose file wires everything.

## Configuration Reference

### `.env`

Required: `TZ`, `DOTTY_ADMIN_TOKEN`. All other variables have defaults.
See `.env.example` for the full list with documentation.

### `data/.config.yaml`

xiaozhi-server config — mounted read-only into the xiaozhi container.
See Setup step 4 for the key fields to edit.

- `selected_module.LLM` — `PiVoiceLLM` (default, routes through dotty-pi)
  or `OpenAICompat` (direct endpoint).
- `server.vision_explain` — must point to `http://dotty-behaviour:8090/api/vision/explain`.

### `data/llama-swap.config.yaml` + `dotty-pi/models.json`

LLM model aliases — **these two files must stay in sync**. Model aliases
in `llama-swap.config.yaml` must match model IDs in `models.json`.

`dotty-pi/models.json` must define a provider and model named `default` —
this is the fallback model pi uses for voice chitchat. If you only need one
model, `default` is the only entry you need to define.

Current aliases:

| Alias | Role | Model |
|---|---|---|
| `default` | Voice chitchat (outer agent loop) | Qwen3.5-4B Q5_K_M |
| `think-big` | `think_hard` escalation (8K context), Coding agent | Qwen3.5-27B UD-IQ2_M |
| `think-small` | Voice escalation: big model at small context | Qwen3.5-4B Q5_K_M |

**Never** request `think-small` from the voice path — it evicts the voice
model pair and takes 30–50s to cold-reload.

### `personas/` and `songs/`

Optional. Persona prompt files and audio assets for the `play_song` voice
tool. Both mounted read-only into the xiaozhi container. Active persona is
set by `PERSONA` in `.env`.

## LLM Providers

By default, this stack runs **llama-swap** as the LLM backend — it manages
local GGUF models on your NVIDIA GPU and exposes an OpenAI-compatible API on
port 8080 (`/ui` for the dashboard). The pi agent connects to it via
`dotty-pi/models.json`.

pi supports other providers too (OpenAI, Anthropic, Google, Ollama, OpenRouter,
Mistral, Bedrock, and more). To switch, edit `dotty-pi/models.json` — change
the `api` field and `baseUrl`. If you no longer need llama-swap locally, remove
it from `docker-compose.yml`.

**Example** — switching to OpenRouter:

```json
{
  "providers": {
    "default": {
      "baseUrl": "https://openrouter.ai/api/v1",
      "api": "openai-completions",
      "apiKey": "YOUR_KEY",
      "models": [
        { "id": "default", "name": "qwen/qwen3-4b", "reasoning": false,
          "input": ["text"], "contextWindow": 4096, "maxTokens": 2048,
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 } }
      ]
    }
  }
}
```

Full provider docs:
https://github.com/earendil-works/pi/blob/HEAD/packages/coding-agent/docs/providers.md

## State Directory

All runtime state lives under `./state/` (gitignored). This is where Docker
containers read and write persistent data.

```
state/
├── shared/                    # Shared across services
│   ├── kid-mode               # Kid-mode toggle file (bridge writes, xiaozhi + behaviour read)
│   ├── smart-mode             # Smart-mode toggle file (bridge writes, xiaozhi + behaviour read)
│   └── household.yaml         # Household roster (bridge writes, behaviour reads)
├── logs/                      # Conversation logs (NDJSON)
│   └── *.ndjson               # Daily log files — bridge + behaviour both write here
├── secrets/                   # Credentials (never commit)
│   └── google-calendar-sa.json
├── behaviour/                 # dotty-behaviour-specific state
│   └── greeter_state.json     # Proactive greeter persistence
└── pi/                        # dotty-pi runtime state
    ├── memory/
    │   └── brain.db           # FTS5 memory store
    ├── persona/               # Persona files (live, not from repo)
    ├── agent/
    │   └── auth.json          # pi auth state
    ├── sessions/              # pi session state
    └── extensions/
        └── dotty-pi-ext/
            └── node_modules/  # Host-compiled better-sqlite3 (mounted into container)
```

### Shared State

Three files are shared between services via the `state/shared/` directory:

| File | Writer | Readers | Purpose |
|---|---|---|---|
| `kid-mode` | dotty-bridge | xiaozhi-server, dotty-behaviour | Kid-mode toggle (LED pips on reconnect) |
| `smart-mode` | dotty-bridge | xiaozhi-server, dotty-behaviour | Smart-mode toggle |
| `household.yaml` | dotty-bridge | dotty-behaviour | Household roster for face-name greeting |

The bridge mounts `state/shared/` read-write. xiaozhi-server and
dotty-behaviour mount it **read-only**. This keeps the firmware LED pips in
sync with the dashboard across reconnects.

### Shared Logs

Both dotty-bridge and dotty-behaviour write conversation logs to
`state/logs/`. They mount the same directory, so log files from both services
coexist in one place.

## Volume Mounts

### xiaozhi-esp32-server

The heaviest volume setup — mounts custom providers, patches, models, and
shared state:

- `data/.config.yaml` → server config (read-only)
- `models/` → ASR/TTS model weights (SenseVoiceSmall, Piper, Whisper)
- `custom-providers/` → LLM, TTS, ASR provider overrides
- `custom-providers/xiaozhi-patches/` → drop-in overrides for admin routes,
  WebSocket server, OTA handler
- `personas/` → persona prompt files (read-only)
- `songs/` → audio assets (read-only)
- `state/shared/` → kid/smart-mode toggle state (read-only)
- `/var/run/docker.sock` → Docker socket (required for `docker exec` into
  dotty-pi from PiVoiceLLM)

### dotty-bridge

- `state/shared/` → kid/smart-mode toggle state (read-write)
- `state/logs/` → conversation logs (read-write)
- `state/secrets/` → credentials (read-only)

### dotty-pi

- `dotty-pi/models.json` → model registry (read-only, stays in sync with
  `data/llama-swap.config.yaml`)
- `state/pi/memory/` → brain.db FTS5 store
- `state/pi/persona/` → persona files
- `state/pi/agent/auth.json` → auth state
- `state/pi/sessions/` → session state
- `state/pi/extensions/dotty-pi-ext/node_modules/` → host-compiled native
  modules (better-sqlite3)

The extension source and npm dependencies are **baked into the dotty-pi image**
at build time. The host `node_modules` mount overlays the baked copy so native
modules survive image rebuilds without recompilation.

### dotty-behaviour

- `state/shared/` → household.yaml (read-only)
- `state/behaviour/` → greeter state (read-write)
- `state/logs/` → conversation logs (read-write)
- `state/secrets/` → credentials (read-only)

### llama-swap

- `data/llama-swap.config.yaml` → model registry
- `models/` → GGUF model files

## Building

```bash
# Build everything
docker compose build

# Build a specific service
docker compose build dotty-pi

# Build and start
docker compose up --build -d
```

Three services are built from Dockerfiles in this repo:

- **xiaozhi-esp32-server** — `Dockerfile` at repo root (builds from the
  pinned upstream image, adds Piper TTS, faster-whisper, fluidsynth, Docker
  CLI)
- **dotty-pi** — `dotty-pi/Dockerfile` (build context is repo root so it
  can access both `dotty-pi/` and `dotty-pi-ext/`; bakes in the extension
  source and native deps)
- **dotty-bridge** — `bridge/Dockerfile` (build context is repo root; copies
  `bridge.py`, `bridge/`, and `custom-providers/`)
- **dotty-behaviour** — `dotty-behaviour/Dockerfile` (build context is
  `dotty-behaviour/`; perception bus, greeter, vision/audio explain)

One service uses a pre-built image:

- **llama-swap** — `ghcr.io/mostlygeek/llama-swap:unified-cuda`

## Running

```bash
# Start everything
docker compose up -d

# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f dotty-xiaozhi-esp32-server

# Stop everything
docker compose down

# Restart everything
docker compose restart

# Check status
docker compose ps
```

## Health Checks

```bash
# Dashboard
curl http://<DOCKER_HOST_LAN_IP>:8081/health

# dotty-behaviour (internal — use docker exec)
docker exec dotty-behaviour curl -fsS http://localhost:8090/health

# pi agent
docker exec dotty-pi pi --version
```

## Emotion Protocol

The LLM response MUST start with an emoji. The xiaozhi firmware parses it
into a face animation on the StackChan display:

| Emoji | Expression |
|---|---|
| 😊 | smile |
| 😆 | laugh |
| 😢 | sad |
| 😮 | surprise |
| 🤔 | thinking |
| 😠 | angry |
| 😐 | neutral |
| 😍 | love |
| 😴 | sleepy |

Enforced by the persona prompt (primary) and the `data/.config.yaml`
top-level `prompt:` block (system message injection).

## Key Files Reference

| File | Purpose |
|---|---|
| `docker-compose.yml` | Unified stack — all 5 services, one network |
| `.env` | Centralized environment variables |
| `.env.example` | Documented env var reference |
| `Dockerfile` | xiaozhi-esp32-server image build |
| `dotty-pi/Dockerfile` | dotty-pi image build (extension + deps baked in) |
| `dotty-pi/models.json` | pi model registry (must match llama-swap config) |
| `data/.config.yaml` | xiaozhi-server config (modules, prompt, server URLs) |
| `data/llama-swap.config.yaml` | llama-swap model registry (must match models.json) |
| `personas/default.md` | Default robot persona prompt |
| `bridge/` | Dashboard service source (FastAPI, /ui) |
| `dotty-pi-ext/` | Voice tool extension (7 tools for pi agent) |
| `dotty-behaviour/` | Perception bus, greeter, vision/audio explain |
| `custom-providers/` | LLM, TTS, ASR provider overrides |
| `custom-providers/xiaozhi-patches/` | Drop-in overrides for xiaozhi-server |
| `state/` | Runtime state (gitignored) |
| `models/` | Downloaded model weights (gitignored) |

## Maintenance

| Task | How |
|---|---|
| Change TTS voice | Edit `data/.config.yaml` → `TTS` section. Download new `.onnx` into `models/piper/`. Restart. |
| Change system prompt | Edit `data/.config.yaml` → `prompt:` block. Restart. |
| Add LLM model | Add entry to both `data/llama-swap.config.yaml` AND `dotty-pi/models.json`. Restart. |
| Change persona | Edit `personas/<name>.md`, set `PERSONA=<name>` in `.env`. Restart. |
| View conversation logs | `cat state/logs/*.ndjson` |
| Check container logs | `docker compose logs -f <service>` |
| Update model weights | Re-run the relevant `hf download` commands in Setup step 3. Restart. |

## GPU

Both `xiaozhi-esp32-server` (WhisperLocal ASR) and `llama-swap` (LLM
inference) require NVIDIA GPU access. The compose file includes CUDA runtime
configuration — comment out the `runtime: nvidia` and `deploy: resources`
blocks if running without a GPU (CPU-only fallbacks are available for ASR
but not for llama-swap's GGUF models).
