# DarkeVox Operating Directive

The owner's standing instructions, engineered into an executable order. Read together with `PLAN.md` (vision and phases) and `.claude/skills/refinement-loop/` (the process contract). Any session, human or watchdog-fired, starts here.

## Mission

Ship DarkeVox to release grade: dictation that hears correctly, polish that never rewrites the speaker, a UI a design-conscious user is happy to look at, then the full PLAN.md roadmap (Compose tab, context engine, grounded dictation, installer). The bar is a product the owner can hand to someone else without apologizing for anything.

## Standing priorities, in order

1. **Field reports.** What the owner hit on the real machine outranks everything. Open reports: words misrecognized (mitigated: beam search 5, mic selection, dictionary; awaiting re-test), polisher rewriting content (mitigated: fidelity rule, temperature 0, email tone defanged; awaiting re-test), UI "looks terrible" on the real machine (needs a screenshot to target; offscreen renders look right, so suspect fonts/DPI).
2. Red tests or a broken main. Fix before any feature.
3. The refinement loop on the active segment until two sweeps run dry (voice pipeline first).
4. PLAN.md phases in order: 3 (Compose), 4 (ingest/store), 5 (tiered summary + Q&A), 6 (bridge + dictionary UI), 7 (packaging, installer, real release automation).

## Operating rules

- Every iteration ships: ruff clean, pytest green, visual changes rendered and looked at, commit, push branch and `main` (direct PAT push; the session's credential proxy is read-only).
- Reviewers are independent parallel agents with skeptic verification; unverified findings never drive fixes (see refinement-loop).
- The task ledger (TaskList) is the memory that survives resets and compaction. Update it before every ship.
- The hourly watchdog runs ONE bounded iteration per firing against this file and the ledger, and parks anything that needs the owner instead of guessing.
- Honesty is load-bearing: what needs the owner's Windows machine goes to TESTPLAN.md unchecked; blocked platform actions (e.g. the proxy refuses Release creation) get reported with the one-step workaround, not worked around silently.

## Current state (update on every ship)

Phases 0-2 complete and field-running. Panel, updater, refinement skill, voice-fidelity pass shipped. Tag `v0.1.0-beta` pushed; the owner clicks Releases > Draft from that tag to publish it. Loop iterations on voice: 2 of 3 minimum done (six-dimension audit; post-panel two-agent review). Next: iteration 3 sweep results, logo/UI pass, then phase 3.
