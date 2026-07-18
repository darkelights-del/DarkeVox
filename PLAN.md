# DarkeVox Build Plan

## What we're building

DarkeVox is a Windows 10/11 desktop app for one person, running on their machine. It does three things. First, system-wide dictation: hold a hotkey in any app, talk, release; local Whisper turns the speech into text, a small LLM cleans it into the chosen tone, and the result lands at the cursor through a clipboard swap. Second (later), a context engine: drop in documents, get a three-tier summary with citations, ask questions over a local knowledge base. Third, the bridge: dictation grounded in that knowledge base, so names and numbers come out right. Python 3.12, PySide6 Widgets, faster-whisper on CPU int8, SQLite when the context engine arrives. No telemetry, no accounts, no cloud storage, no LangChain/LlamaIndex/Electron/torch.

This branch delivers phases 0-2: skeleton, raw dictation, polish layer. The context engine (phases 3-6) is deliberately not started, but the seam it plugs into exists now: the polish pipeline accepts a `ContextProvider` and ships with a null implementation. Adding grounding later means writing one provider class against an interface that already runs on every dictation.

## Ambiguities found and how they were resolved

1. **App name.** Spec says "VoxDesk (rename freely)"; the repo is DarkeVox. User confirmed **DarkeVox**. Data dirs are `%APPDATA%\DarkeVox` and `%LOCALAPPDATA%\DarkeVox`.
2. **LLM defaults.** The spec leaned OpenRouter-first. User directive reversed it: **Ollama is the default backend**, with `qwen2.5:3b` for polish (has to feel instant) and `qwen2.5:7b` reserved in config for summarize (background work, quality over speed). OpenRouter free tier is a manual toggle whose model ID ships blank; the free-model list rotates, so the README points at the live list instead of trusting a name. The Claude API is not in the default build.
3. **Skills wiring.** User confirmed the separated design: `.claude/skills/` holds the canonical guidelines (engineering, UI style, no-slop writing); the app embeds a compact distillation of the no-slop rules in `polish/prompts.py`. No file I/O on the dictation hot path.
4. **Ollama transport.** The OpenAI-compatible endpoint would let one client cover both backends, but the spec names native `/api/chat`. Kept native (better errors, no dummy key), with OpenRouter on the `openai` SDK behind the same `LlmClient` interface.
5. **Long dictation.** Toggle mode cuts segments at energy-detected pauses while recording and transcribes them eagerly; text is joined and injected once at stop. A five-minute ramble never processes as one blob, and polish still sees the full transcript.
6. **Dev environment vs target.** Built and unit-tested on Linux/Python 3.11 in this session; the target is Windows/Python 3.12. Every Windows-bound dependency (pywin32, pynput runtime, sounddevice device I/O, Qt) sits behind an interface with a fake, so pytest runs green here. OS-integration behavior is enumerated in `TESTPLAN.md` for manual verification on the real machine; until someone runs those steps there, they count as open items.
7. **Dependency pinning.** Exact-pinning wheels this container cannot resolve would be guesswork. Deps carry conservative lower bounds now; Phase 7's Windows CI build resolves and exact-pins them for real.

## Open decisions taken (spec §6)

- **Styling:** pastel blue on cream, light-first; the full token set lives in `.claude/skills/darkevox-ui-style/`. Dark variant deferred.
- **Icon:** drawn at runtime with QPainter (mic glyph on a pastel roundrect), so the repo carries no binary assets.
- **HUD:** frameless pill, bottom-center, fades in/out, pulses while listening, shows the polishing state and a "grounded" badge.
- **Settings:** one dialog covering hotkeys, STT model, LLM backend, default tone, and injection method. Tray menu carries tone and mode toggles.
- **Chunk-size tuning and the second reduce pass:** deferred to phases 4–5, as the spec allows.

## Phase gates

A phase commit lands only when pytest is green, ruff is clean, and the phase's acceptance criteria are either verified here or explicitly parked in `TESTPLAN.md` with the reason. Commit messages follow `phase-N: summary`.
