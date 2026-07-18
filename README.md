# DarkeVox

Hold a key anywhere in Windows, talk, release. Your words land at the cursor as clean text, in your tone, without leaving your machine.

DarkeVox is a local-first dictation tool: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) transcribes on your CPU, a small local LLM through [Ollama](https://ollama.com) fixes grammar and fillers, and a clipboard swap drops the result into whatever app has focus. No accounts, no telemetry, no cloud storage. The roadmap (see `PLAN.md`) adds a document knowledge base that grounds dictation so names and numbers come out right; the seam for it is already in place.

**Status: phases 0-2 of the build plan.** Dictation with polish works; the context engine is next.

## Setup

You need Windows 10/11 x64, Python 3.12, and (for polish) Ollama.

```
pip install -e .
ollama pull qwen2.5:3b
darkevox
```

First launch downloads the speech model (`small.en`, about 484 MB) to `%LOCALAPPDATA%\DarkeVox\models\` and sits in the tray. If Ollama isn't running, dictation still works; you get the raw transcript instead of the polished one, and the status pill says so.

## Use

| Keys | What happens |
|---|---|
| Hold `Ctrl+Alt+Space` | Listen while held; release to transcribe, polish, and inject |
| `Ctrl+Alt+D` | Toggle long dictation on/off; segments transcribe while you talk |

Pick a tone from the tray menu: **email** (leads with the point), **message** (short, casual), **notes** (terse lines), **verbatim** (raw transcript, no LLM, no network). The polish step never invents content; it cleans what you said and obeys spoken commands like "new paragraph" and "scratch that".

## Configuration

Config lives at `%APPDATA%\DarkeVox\config.toml`; the Settings dialog covers the common cases. API keys go to Windows Credential Manager, never into the file. Models, database, and logs live under `%LOCALAPPDATA%\DarkeVox\`.

The default polish model is `qwen2.5:3b` because it's fast enough to feel instant on CPU. `qwen2.5:7b` is reserved in config for the future summarize path, where quality beats speed. To use OpenRouter instead of Ollama, switch the backend in Settings and pick a model from [openrouter.ai/models](https://openrouter.ai/models) (filter: free). The free list rotates without warning, which is exactly why no free model name ships as a default.

Dictionary terms (names, project words) go in the `[dictionary]` section of the config; they seed the speech recognizer and the polish prompt so "DarkeVox" never comes out "dark vox".

## Known limitations

- CTranslate2 accelerates on NVIDIA CUDA only. Intel iGPUs don't count; CPU int8 is the real default and `small.en` is tuned for it.
- Non-text clipboard contents (images, files) are not restored after injection in v1. Text is.
- Some apps block synthetic Ctrl+V; switch the injection method to `type` in Settings for those.
- The typing fallback is never attempted automatically, so a blocked paste into a password field does nothing rather than typing your words somewhere you can't see.

Developing? Read `.claude/skills/darkevox-guidelines/` first; `TESTPLAN.md` lists the manual Windows checks the unit suite can't cover.
