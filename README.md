# DarkeVox

Hold a key anywhere in Windows, talk, release. Your words land at the cursor as clean text, in your tone, without leaving your machine.

DarkeVox is a local-first dictation tool: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) transcribes on your CPU, a small local LLM through [Ollama](https://ollama.com) fixes grammar and fillers, and a clipboard swap drops the result into whatever app has focus. No accounts, no telemetry, no cloud storage. The roadmap (see `PLAN.md`) adds a document knowledge base that grounds dictation so names and numbers come out right; the seam for it is already in place.

**Status: phases 0-2 of the build plan.** Dictation with polish works; the context engine is next.

## Setup

Windows 10/11 x64. DarkeVox is not on PyPI, so `pip install darkevox` doesn't exist: it runs from a git clone, which is also what the built-in updater pulls from. In PowerShell:

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Git.Git
winget install -e --id Ollama.Ollama
```

Close and reopen the terminal so PATH picks up the new tools, then:

```powershell
git clone https://github.com/darkelights-del/DarkeVox.git
cd DarkeVox
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
ollama pull qwen2.5:3b
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m darkevox.app
```

The venv's python is called by full path so PowerShell's script-execution policy never gets a say. The pytest line is optional and should end `142 passed`. First launch downloads the speech model (`small.en`, about 484 MB) to `%LOCALAPPDATA%\DarkeVox\models\` and sits in the tray. If Ollama isn't running, dictation still works; you get the raw transcript instead of the polished one, and the status pill says so. If a winget ID doesn't resolve on your machine, the same installers live at python.org, git-scm.com, and ollama.com/download.

## Use

| Keys | What happens |
|---|---|
| Hold `Ctrl+Alt+Space` | Listen while held; release to transcribe, polish, and inject |
| `Ctrl+Alt+D` | Toggle long dictation on/off; segments transcribe while you talk |

Pick a tone from the tray menu: **email** (leads with the point), **message** (short, casual), **notes** (terse lines), **verbatim** (raw transcript, no LLM, no network). The polish step never invents content; it cleans what you said and obeys spoken commands like "new paragraph" and "scratch that".

There's also a mouse-first way in: the **panel**, a draggable mic pill floating above your windows (tray > Open panel, or double-click the pill to expand). Click the mic to start and stop, or press-and-hold it to talk. Your words stream into an editable "Heard" field at each pause, the tone buttons polish them (edit either field by hand whenever you like), Copy puts the result on the clipboard, and Insert hands focus back to the app you were in and pastes it there. The panel remembers where you left it.

## Configuration

Config lives at `%APPDATA%\DarkeVox\config.toml`; the Settings dialog covers the common cases. API keys go to Windows Credential Manager, never into the file. Models, database, and logs live under `%LOCALAPPDATA%\DarkeVox\`.

The default polish model is `qwen2.5:3b` because it's fast enough to feel instant on CPU. `qwen2.5:7b` is reserved in config for the future summarize path, where quality beats speed. Any tag your Ollama can pull works in either slot (`llama3.2:3b`, `glm4:9b`, whatever comes next): change it in Settings or `config.toml`, then `ollama pull` that tag. On a CPU-only machine, a bigger polish model mostly buys latency rather than better grammar fixes; keep polish small and spend parameters on summarize. To use OpenRouter instead of Ollama, switch the backend in Settings and pick a model from [openrouter.ai/models](https://openrouter.ai/models) (filter: free). The free list rotates without warning, which is exactly why no free model name ships as a default.

Dictionary terms (names, project words) go in the `[dictionary]` section of the config; they seed the speech recognizer and the polish prompt so "DarkeVox" never comes out "dark vox".

## Running without a terminal

```powershell
.\.venv\Scripts\pythonw.exe -m darkevox.app
```

`pythonw.exe` has no console: the command returns immediately, the app lives in the tray, and closing the terminal doesn't kill it (console logging switches off by itself; the file log keeps everything). To start it with Windows, press Win+R, run `shell:startup`, and drop in a shortcut whose target is that full `pythonw.exe` path plus `-m darkevox.app`. A proper installer with a Start Menu entry comes with phase 7.

## Updates

DarkeVox checks its git upstream once per launch (`[update] auto_check` in the config turns this off) and tells you from the tray when new commits exist; tray > Update now applies a fast-forward pull, then you restart the app. If dependencies changed in the update, rerun `pip install -e ".[dev]"` in the venv. Installer-based release updates arrive with phase 7 packaging.

## API keys

You don't need any. The default stack is fully local: faster-whisper for speech and Ollama for polish, both on your machine. A key only enters the picture if you switch the polish backend to OpenRouter: paste it into Settings > OpenRouter key, which stores it in Windows Credential Manager. No key ever goes into a file in this project, and don't put one in `config.toml`; the app won't read it from there.

## Known limitations

- CTranslate2 accelerates on NVIDIA CUDA only. Intel iGPUs don't count; CPU int8 is the real default and `small.en` is tuned for it.
- Non-text clipboard contents (images, files) are not restored after injection in v1. Text is.
- Some apps block synthetic Ctrl+V; switch the injection method to `type` in Settings for those.
- The typing fallback is never attempted automatically, so a blocked paste into a password field does nothing rather than typing your words somewhere you can't see.

Developing? Read `.claude/skills/darkevox-guidelines/` first; `TESTPLAN.md` lists the manual Windows checks the unit suite can't cover.
