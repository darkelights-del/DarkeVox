# DarkeVox Architecture

## Module map

```
darkevox/
  app.py                # entry: single-instance lock, first-run download, wiring, Qt loop
  controller.py         # DictationController: hotkeys -> capture -> STT [-> polish] -> inject
  state.py              # AppState: the only mutable shared state, guarded by design
  config.py             # TOML load/save, defaults, data-dir paths, keyring access
  logging_setup.py      # rotating file log in %LOCALAPPDATA%\DarkeVox\logs + stage timers
  audio/
    capture.py          # sounddevice stream -> ring buffer, 16 kHz mono f32 (no Qt)
    segmenter.py        # energy-based pause detection for long-dictation chunking
    hotkeys.py          # pynput listener: hold-to-talk + toggle, plain callbacks
  stt/                  # CORE - no Qt, no Windows imports
    engine.py           # faster-whisper wrapper, warm load, vad_filter always on
    models.py           # first-run download w/ progress callback, CUDA detection
  polish/               # CORE - no Qt, no Windows imports
    pipeline.py         # transcript -> polished text (tones, grounding, fallback)
    prompts.py          # ALL prompt templates, incl. the no-slop distillation
    llm.py              # Ollama native /api/chat + OpenRouter via openai SDK
  update.py             # dev-mode self-update: git upstream check + ff pull
  inject/
    injector.py         # clipboard swap + Ctrl+V, typing fallback, restore
    clipboard.py        # ClipboardBackend protocol; pywin32 impl + in-memory fake
    focus.py            # ForegroundTracker: hand focus back before panel Insert
  context/              # CORE - no Qt, no Windows imports
    provider.py         # ContextProvider protocol, GroundingChunk, NullContextProvider
  ui/
    theme.py            # design tokens + QSS builder (pure strings, testable)
    tray.py             # QSystemTrayIcon: status, tone menu, mode toggles, quit
    hud.py              # frameless always-on-top status pill
    panel.py            # floating dictation card <-> mic pill (mouse PTT, live text)
    interaction.py      # pure click/hold/drag interpreter for the mic (no Qt)
    settings.py         # hotkeys, models, tones, backend config dialog
    firstrun.py         # model download progress dialog
    icons.py            # QPainter-drawn icons (no binary assets)
tests/                  # pytest, pure logic only, runs on any platform
```

## Data flow (dictation)

```
hotkey down ──> capture.start() ──> HUD "listening"
hotkey up ────> capture.stop() ──> job queue ──> worker thread:
                  stt.engine.transcribe(audio, initial_prompt=dictionary)
                  polish.pipeline.polish(transcript, tone, provider)   [skipped for verbatim]
                  inject.injector.inject(text)
                └─> signals: state changes, errors ──> HUD / tray (main thread)
```

Toggle mode: `segmenter` cuts the stream at energy pauses (>1s silence after >5s
speech); each segment transcribes eagerly on the worker while recording continues;
stop joins the segment transcripts, then polish and inject run once on the whole text.

## Threading

| Thread | Owns | Talks to others via |
|---|---|---|
| Qt main | all widgets, tray, HUD | receives Qt signals |
| PortAudio callback | ring buffer writes | lock-free buffer handoff |
| pynput listener | key state machine | plain callbacks -> Qt signal bridge |
| Worker (one) | STT model, polish, injection | Qt signals out, queue in |

Rules: the STT model is created once on the worker at startup (warm load). The job
queue depth is 1 with replacement: a new dictation while one is processing queues
behind it; hotkey events during processing never block the listener thread.

## The grounding seam (bridge to phases 4-6)

`polish.pipeline.polish()` accepts `provider: ContextProvider`. When
`polish.grounding_enabled` is true, the pipeline calls
`provider.retrieve(transcript, k=3)` and passes any chunks above the similarity
floor into the prompt as delimited, untrusted reference material with the
instruction: use only to correct names, numbers, and facts the speaker clearly
intended; never inject new claims. `NullContextProvider` returns nothing, so
phases 0-2 behave exactly as if the feature doesn't exist. Phase 4-6 adds a
`StoreContextProvider` over SQLite + fastembed behind the same method signature,
plus the HUD "grounded" badge lights up when chunks were actually used.

Anything that would make this seam awkward over HTTP (Qt types in the signature,
hidden globals, filesystem side effects in retrieve()) is a design bug: the
long-term plan exposes the core over FastAPI for phone clients via Tailscale.

## Portability rule, restated

`stt/`, `polish/`, `context/`: importable on a bare Linux CI box with only
numpy and their own pinned deps. `audio/capture.py` and `segmenter.py`: numpy +
sounddevice, no Qt. `inject/clipboard.py` guards pywin32 behind a runtime check
so importing the module never fails off-Windows. Tests exercise all pure logic
with fakes; only `TESTPLAN.md` items need real Windows.
