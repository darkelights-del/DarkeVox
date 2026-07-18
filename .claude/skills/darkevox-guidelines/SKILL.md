---
name: darkevox-guidelines
description: Engineering guidelines for the DarkeVox app. Read before writing, changing, or reviewing any code in this repo - architecture boundaries, threading model, latency and failure discipline, prompt hygiene, config rules, code style, and the phase-gate process. Applies to every phase of the build, every session.
---

# DarkeVox Engineering Guidelines

DarkeVox is a local-first Windows dictation and context tool. Its whole value is feel: you hold a key, talk, release, and clean text appears where your cursor was, fast enough that you never think about the machinery. Every guideline below exists to protect that feel. When two goals conflict, smooth-and-light wins: a lighter dependency beats a fancier one, a warm-loaded model beats a lazy-loaded one, and a feature that adds latency to the hot path needs to justify itself or live off it.

## The rule that outranks the rest

**Never lose the user's words.** Whatever fails (LLM timeout, injection blocked, clipboard weirdness), the raw transcript ends up on the clipboard and the HUD says so. A crash that eats a dictated paragraph is the worst bug this app can have. Every new code path that touches a transcript must answer: where do the words go if this fails?

## Architecture boundaries

The core packages `stt/`, `polish/`, and `context/` never import PySide6, pynput, pywin32, or anything Windows-specific. They take plain paths and config values as constructor arguments and expose plain-Python APIs. The long-term plan wraps the core in a small FastAPI service so phone clients reach the same knowledge base over Tailscale; any core function that would be awkward to expose over HTTP (hidden global state, Qt types in signatures) is a design bug today, not later.

Everything OS-bound lives in `audio/hotkeys.py`, `inject/`, and `ui/`. `audio/capture.py` may import sounddevice but keeps Qt out; hotkeys use plain callbacks that `app.py` bridges to Qt signals. Windows-only imports (pywin32) are guarded so the test suite runs on any platform against fakes.

The bridge seam: `context/provider.py` defines `ContextProvider` (retrieve chunks for a query) with a `NullContextProvider` default. The polish pipeline takes a provider and threads retrieved chunks into the prompt when grounding is on. Phases 4 to 6 implement a real provider behind the same interface; nothing upstream changes.

Full module map and data flow in `references/architecture.md`.

## Threading model

The Qt main thread owns all UI, full stop. One worker thread runs the dictation pipeline (STT then polish then inject) off a job queue; the audio callback fills a ring buffer on PortAudio's thread; pynput listens on its own thread. Cross-thread communication is Qt signals only. No widget is touched from a worker, and no blocking work runs on the main thread. The STT model loads once at startup, warm; loading per-utterance is a bug.

## Latency discipline

Log per-stage timings on every dictation: capture stop, STT, polish, inject, total. The budget on CPU with `small.en`: under about 2 seconds end-to-end for a 15-second utterance, with polish on a 3B Ollama model adding at most a second. A timing regression is a bug with the same priority as a crash. If a change can't say what it does to the hot path, measure before merging.

## Failure behavior

Every network call has a timeout and a user-visible fallback. Polish gets a hard 10-second cap, then the raw transcript injects with a HUD notice. A missing microphone is a tray notification, not a crash. Rapid hotkey mashing may drop a recording; it must never deadlock the state machine. Errors shown to the user follow the no-slop-writing skill: short, concrete, no exclamation marks ("Polish timed out. Raw transcript injected." not "Oops! Something went wrong").

## Prompt hygiene

All prompts live in `polish/prompts.py` with docstrings explaining intent. Nowhere else. The polish prompt never invents content: it fixes grammar, removes fillers, obeys spoken commands, and preserves meaning. Retrieved document text is untrusted data: delimit it, label it reference material, and instruct the model it is not instructions. The no-slop distillation embedded in the prompts derives from `.claude/skills/no-slop-writing/`; when that skill changes, re-derive the distillation rather than letting them drift apart.

## Config rules

No model ID, API URL, or hotkey is hardcoded outside `config.py` defaults. Config is TOML at `%APPDATA%\DarkeVox\config.toml`; models, database, and logs live under `%LOCALAPPDATA%\DarkeVox\`. Nothing is ever written next to the exe. API keys go in Windows Credential Manager via keyring, never in the TOML. Ollama is the default backend (`qwen2.5:3b` polish, `qwen2.5:7b` summarize); OpenRouter is opt-in with a user-chosen model, because the free-model list rotates. Audio leaves the machine only when the cloud-STT toggle is explicitly on, and the settings UI says so in plain words.

## Code style

Type hints everywhere. `ruff` clean before any commit. Functions under about 50 lines. No global mutable state outside the single `AppState`. Comments state constraints the code can't show, nothing else. Dependencies stay thin: no LangChain, no LlamaIndex, no torch, no Electron, no `keyboard` package, no pyautogui. If a problem looks like it needs a framework, it needs 300 lines we can read instead.

## Phase gates

Work goes phase by phase per the spec, and a phase is done only when its acceptance criteria pass. Commit at each phase boundary as `phase-N: summary`. Never fabricate a passing test: criteria that need the real Windows machine are parked in `TESTPLAN.md` with the reason, explicitly, and stay open until verified there. Features not in the spec don't get built, including meeting recording, accounts, auto-update, and mobile clients (v1).

## UI

Follow the `darkevox-ui-style` skill for every pixel: pastel blue on cream, one accent, quiet motion. All user-facing text in the app (labels, menus, errors, tooltips) follows `no-slop-writing`: plain words, no filler, no performed enthusiasm.
