# DarkeVox Test Plan

The pytest suite (146 tests) covers every piece of pure logic and runs on any platform: config round-trips, the ring buffer, pause segmentation, the hotkey state machine, injection with fakes, prompt assembly, the polish pipeline with a fake LLM, the append-mode draft joining, settings validation, and an offscreen end-to-end controller flow. `ruff check .` must be clean.

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

Cloud STT toggle (config keys exist, no code path), the grounded-dictation badge with a real knowledge base (phase 6), packaging (phase 7). The Compose tab was built as phase 3 and then removed on 2026-07-21: the app is voice-only, and the panel is the one surface — it is not coming back.

## Redesign checks (owner, on Windows, after the 2026-07-21 v3 redesign)

- [ ] The panel card and the HUD have genuinely rounded corners over any wallpaper — no cream square behind them — and both cast a soft visible shadow.
- [ ] Tray left-click: the card fades in (fast); "hide" or Esc fades it out to the tray. No teleporting, no mini pill anywhere.
- [ ] While recording, the wave bars ride your voice level (mic AND the HUD mark), a ring pulses, and every surface reads the same "Listening — 0:07" with a live count — panel, HUD, and tray row never disagree.
- [ ] Speak, pause, speak again in one panel session, then start a second session: the new take APPENDS to the draft. A stray tap on the mic wipes nothing; "undo take" removes the last take.
- [ ] Copy says "Copied — N words" and reverts; Insert ends in "Inserted — N words" or a clay error that stays. Nothing sticks on "inserting".
- [ ] Tray: left-click opens/hides the panel; right-click ALWAYS opens the menu (use the app for a while, then check again — Settings and Quit must stay reachable), with a status dot row and an update item that reads "Check for updates" until an update exists.
- [ ] Right-click the panel: close-to-tray works, and the panel is gone until you bring it back from the tray.
- [ ] Settings fits on screen (tabs), the Microphone picker lists your devices, Polish shows only the active backend's fields, and switching injection method applies without a restart.
- [ ] Esc closes the card to the tray; Ctrl+Enter inserts; Ctrl+Shift+C copies.
- [ ] Launch a second DarkeVox: a message box says it's already running (no silent nothing).
