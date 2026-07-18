# DarkeVox Test Plan

The pytest suite (98 tests) covers every piece of pure logic and runs on any platform: config round-trips, the ring buffer, pause segmentation, the hotkey state machine, injection with fakes, prompt assembly, the polish pipeline with a fake LLM, and an offscreen end-to-end controller flow. `ruff check .` must be clean.

What the suite cannot cover is the OS integration this app exists for. Those checks live here, run by hand on the real Windows machine. Status boxes stay unchecked until someone actually did the thing.

## Phase 0

- [ ] `darkevox` launches to the tray on Windows 10/11; the mic icon appears and the menu opens.
- [ ] Launching a second instance exits immediately (named mutex); the first instance is unaffected.
- [x] Log file appears under `%LOCALAPPDATA%\DarkeVox\logs\` (path logic verified in tests; file creation verified in the dev container).
- [x] Config round-trip: verified by the unit suite.

## Phase 1

- [ ] First run shows the download dialog with a moving MB counter, then dictation works without a restart. (HuggingFace was blocked in the dev container, so the download path has never run end to end.)
- [ ] Hold Ctrl+Alt+Space, say two sentences, release: text lands in Notepad, the Chrome address bar, and the VS Code editor.
- [ ] Clipboard text from before the dictation is restored after injection.
- [ ] With text copied, dictate; with an image copied, dictate: the image is not restored (v1 limitation) and the log shows the non-text warning, no crash.
- [ ] Latency: a 15-second utterance with `small.en` on CPU lands in under ~2 s. Check the log line `dictation stt=…ms inject=…ms total=…ms`.
- [ ] Rapid double-press and mashing of the hold key: no deadlock, no stuck "listening" pill; worst case a dropped recording.
- [ ] Unplug or disable the microphone, press the hotkey: tray notification "No microphone found.", app keeps running.
- [ ] Toggle mode (Ctrl+Alt+D): talk for 3+ minutes with pauses; the log shows multiple segment transcriptions during recording, and the full text injects once on the second press.

## Phase 2

- [ ] With Ollama running and `qwen2.5:3b` pulled: dictate "uh so basically tell jake that um the meeting moved to thursday no wait friday" in message tone; the injected text is a clean message saying the meeting moved to Friday, nothing invented.
- [ ] Each tone behaves: email leads with the point, message stays short, notes renders terse lines, verbatim injects the raw transcript with no network call (verify with Ollama stopped: verbatim still injects instantly).
- [ ] Timeout path: point `ollama_url` at a dead port in `%APPDATA%\DarkeVox\config.toml`, dictate in email tone: raw transcript injects after the timeout and the HUD says "Ollama isn't running. Raw transcript injected."
- [ ] Missing model path: with Ollama running but the model absent, the HUD names the fix: "Ollama doesn't have qwen2.5:3b. Run: ollama pull qwen2.5:3b".
- [ ] OpenRouter path: save a key and a current free model in Settings, switch backend, dictate; polished text arrives. (The free list rotates; pick from openrouter.ai/models first.)
- [ ] Settings: change the hold hotkey, save, and the new combo works immediately; the old one is dead.
- [ ] Tray tone menu switches the active tone for the next dictation without touching config defaults.

## Cross-cutting

- [ ] Every dictation writes a timing line to the log; polish adds a `polish=…ms` stage.
- [ ] Injection into a password box: paste either works or nothing happens; the app never falls back to typing on its own. (Typing is only used when Settings selects it.)
- [ ] Quit from the tray exits cleanly; no orphaned process, hotkeys released.

## Deferred (not built yet, do not test)

Cloud STT toggle (config keys exist, no code path), the grounded-dictation badge with a real knowledge base (phase 6), Compose tab (phase 3), packaging (phase 7).
