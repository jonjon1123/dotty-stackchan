# pi_voice

xiaozhi-server custom LLM provider that routes voice turns through the
[`dotty-pi`](../../dotty-pi/) container instead of bridge.py. The
RPi-replacement path per [#36](https://github.com/BrettKinny/dotty-stackchan/issues/36).

**Status: skeleton.** Not yet wired into xiaozhi-server's
`selected_module:` config. The legacy provider (`zeroclaw`) and the
Tier1Slim provider (`tier1_slim`) remain the production paths until
this is built out and soaked.

## Architecture

```
xiaozhi-server (Docker)                     dotty-pi (Docker, same host)
┌────────────────────────────┐              ┌──────────────────────────────┐
│  selected_module.LLM:      │              │  pi (idling via sleep ∞)     │
│    PiVoiceLLM              │              │                              │
│       │                    │              │  on `docker exec -i` from    │
│       ↓ async call         │              │  PiClient:                   │
│  custom-providers/         │  docker exec │    pi --provider ollama      │
│    pi_voice/               │  ───────────→│      --model qwen3.6:27b     │
│      pi_voice.py           │              │      --extensions dotty-pi-ext│
│      pi_client.py          │  ←─────────  │      --thinking minimal      │
│                            │  stdout RPC  │      <prompt>                │
└────────────────────────────┘              └──────────────────────────────┘
                                                          ↓
                                                ┌──────────────────────┐
                                                │ dotty-pi-ext         │
                                                │   5 voice tools      │
                                                │   (memory_lookup,    │
                                                │    think_hard, …)    │
                                                └──────────────────────┘
                                                          ↓
                                            llama-swap (qwen3.6:27b-think)
                                            xiaozhi-admin (songs, MCP)
                                            brain.db (FTS5)
```

## Components

### `pi_voice.py` — xiaozhi LLMProviderBase subclass

Translates xiaozhi's chat-completion interface to a pi RPC turn. Async
`chat_stream` shape so xiaozhi can pipe text deltas straight to TTS
without buffering the full reply.

### `pi_client.py` — Unraid-local RPC client

Owns the long-lived pi process. Per #36's Step-5 constraints:

- **Single persistent pi process** spawned once per xiaozhi-server boot
  (don't respawn per turn — that recovers the 1.2–1.8 s spike-measured
  startup tax).
- **Auto-cancel `extension_ui_request`** with `{cancelled: true}` to
  prevent pi from blocking on UI prompts no one will answer.
- **Filter `assistantMessageEvent.type == "thinking_delta"`** out of the
  event stream the provider yields back to xiaozhi (per spike: 19
  thinking deltas vs 3 text deltas per turn; only text reaches TTS).

### `__init__.py` — package marker

So xiaozhi-server's `core.providers.llm.pi_voice` import path resolves.

## Wiring into xiaozhi-server (planned)

Mount this directory as a volume into the xiaozhi container at
`core/providers/llm/pi_voice/`, then in `data/.config.yaml`:

```yaml
selected_module:
  LLM: PiVoiceLLM

LLM:
  PiVoiceLLM:
    type: pi_voice
    container_name: dotty-pi
    model: qwen3.6:27b
    extension: dotty-pi-ext
```

Existing `DOTTY_VOICE_PROVIDER=pi` env-var contract on the bridge will
become the soak-toggle: when the xiaozhi-server side is on `PiVoiceLLM`
and the bridge is still up, the bridge becomes a no-op pass-through;
once soaked, bridge.py goes away entirely.

## Open questions for the implementation pass

1. **Stream shape.** xiaozhi's `chat_stream` expects `{type: "content",
   content: <chunk>}` dicts. Pi's `assistantMessageEvent` shape needs
   adapting; figure out the exact mapping before committing.
2. **Tool-call surfacing.** Tool results currently come back as part of
   the assistant's final message in pi's flow. xiaozhi's TTS gate may
   need `tool_call` vs `content` distinction — verify against tier1_slim
   to see how it handles the same case.
3. **Sandwich enforcement.** Tier1Slim wraps every turn with
   `build_turn_suffix(KID_MODE)` from `core.utils.textUtils`. PiVoiceLLM
   needs the same — either inject server-side here, or move the
   sandwich into the pi extension's system prompt.
4. **Failure paths.** Bridge.py has a long-tail of fallback / timeout /
   exception handling. Each path needs an equivalent: container missing,
   pi crash, llama-swap unreachable, extension exception.

## See also

- [`../../dotty-pi/README.md`](../../dotty-pi/README.md) — the runtime image.
- [`../../dotty-pi-ext/README.md`](../../dotty-pi-ext/README.md) — voice-tool extension.
- [`../tier1_slim/tier1_slim.py`](../tier1_slim/tier1_slim.py) — reference for the
  chat_stream contract + sandwich wiring + tool dispatch pattern.
- [#36](https://github.com/BrettKinny/dotty-stackchan/issues/36) — cutover plan + soak rule.
