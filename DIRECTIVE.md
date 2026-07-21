# DarkeVox Operating Directive

The owner's standing instructions, engineered into an executable order. Read together with `PLAN.md` (vision and phases) and `.claude/skills/refinement-loop/` (the process contract). Any session, human or watchdog-fired, starts here.

## Mission

Ship DarkeVox to release grade: dictation that hears correctly, polish that never rewrites the speaker, a UI a design-conscious user is happy to look at, then the full PLAN.md roadmap (context engine, grounded dictation, installer). The app is voice-only by owner decision (2026-07-21): the panel is the primary surface, the composer is gone. The bar is a product the owner can hand to someone else without apologizing for anything.

## Standing priorities, in order

1. **Field reports.** What the owner hit on the real machine outranks everything. Open reports: words misrecognized (mitigated: beam search 5, mic selection, dictionary; awaiting re-test), polisher rewriting content (mitigated: fidelity rule, temperature 0, email tone defanged; awaiting re-test), UI "looks terrible" on the real machine (needs a screenshot to target; offscreen renders look right, so suspect fonts/DPI).
2. Red tests or a broken main. Fix before any feature.
3. The refinement loop on the active segment until two sweeps run dry (voice pipeline first).
4. PLAN.md phases in order: 4 (ingest/store), 5 (tiered summary + Q&A), 6 (bridge + dictionary UI), 7 (packaging, installer, real release automation). Phase 3 (Compose) is retired: built, then removed with the voice-only decision.

## Operating rules

- Every iteration ships: ruff clean, pytest green, visual changes rendered and looked at, commit, push branch and `main` (direct PAT push; the session's credential proxy is read-only).
- Reviewers are independent parallel agents with skeptic verification; unverified findings never drive fixes (see refinement-loop).
- The task ledger (TaskList) is the memory that survives resets and compaction. Update it before every ship.
- The hourly watchdog runs ONE bounded iteration per firing against this file and the ledger, and parks anything that needs the owner instead of guessing.
- Honesty is load-bearing: what needs the owner's Windows machine goes to TESTPLAN.md unchecked; blocked platform actions (e.g. the proxy refuses Release creation) get reported with the one-step workaround, not worked around silently.
- Before every prompt, scan the installed skills (project `.claude/skills` and `~/.claude/skills`, incl. impeccable, frontend-design, ui-animation, mobile-app-ui-design) and load anything remotely related to the request. Owner's standing order, 2026-07-21.

## Current state (update on every ship)

Voice-only redesign shipped 2026-07-21 (design system v3, after a 5-agent audit informed by the four installed design skills): composer deleted; the global-QWidget-fill bug that painted opaque squares behind every rounded surface is fixed (window fill is opt-in, corners pixel-verified transparent); shadow made visible (alpha 42, SHADOW_MARGIN 30); contrast pass (blue-600/650/700 primary ramp, ink-600 placeholders/overlines, clay-600 error text); full state coverage (focus rings, disabled primary, quiet pressed, disabled inputs, checkmark, styled scrollbars, drawn combo/spin chevrons); motion layer (AnimatedButton tweens, pill<->card morph, mic press scale + pulse + level-driven wave bars, HUD 90/150 ms fades + done swell, text settle, drag release settle, reduce_motion gate); panel status machine (live Listening timer, Transcribing, Copied/Inserted reverts, errors reach the panel); voice BUILDS on the draft (ui/draft.py append + undo take; empty takes can't wipe); QoL: verbatim chip, Esc/Ctrl+Enter/Ctrl+Shift+C, tray click-to-open + status dot + honest update action, close-to-tray (the pill is dismissable), mic picker in tabbed settings (fits 1080p), injection applies live, missing-model guard, second-launch MessageBox, first-run Retry + ready notification. 142 tests green, ruff clean. Tag `v0.1.0-beta` still awaits owner Release publish. OPEN, in order: owner re-test on Windows (dictation accuracy + the new look; field reports reopen segments); phase 4 ingest/store; phase 5 summaries+Q&A; phase 6 bridge; phase 7 packaging + installer release.
