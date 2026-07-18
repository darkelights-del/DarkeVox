---
name: refinement-loop
description: The DarkeVox quality loop - run repeated sweep/verify/fix/prove/ship iterations with independent parallel reviewers until two consecutive sweeps come back dry. Use when polishing a feature to release grade, before any tagged release, after any field bug report from the user, and on every watchdog firing that finds open refinement tasks. Builds on swarm-orchestration for the reviewer fleet.
---

# Refinement Loop

One iteration is a full professional pass: independent reviewers sweep, skeptics kill the false positives, confirmed findings get fixed at the root, proof runs, and the result ships. The loop repeats until it runs dry, defined below. Never call something "polished" that has not survived a dry sweep; feeling done is not a criterion.

## Priority order, always

1. **Field reports.** Anything the user actually hit on the real machine outranks every internal finding. Reproduce the mechanism from their symptom before fixing (a timeout that is really a cold model load needs warming, not a longer timeout).
2. **The never-lose-words invariant** and anything else in darkevox-guidelines' hard rules.
3. Confirmed internal findings, severity order.
4. Coverage gaps and docs drift.

## One iteration

**SCOPE.** Name the segment under refinement (voice pipeline, panel, packaging...) and the files in it. An unscoped sweep produces noise.

**SWEEP.** Dispatch independent reviewers in parallel, one dimension each, contracts per swarm-orchestration (self-contained, read-only, JSON findings with file/line/claim/evidence). Standard dimensions: threading and state machines, spec/guideline compliance, UX against darkevox-ui-style, regression risk versus the previous commit's guarantees, test quality, docs/prose drift. On a capped box, dispatch reviewers as direct parallel agents (split-off pattern); mid-tier models suffice for single-file judgment.

**VERIFY.** Every finding gets an adversarial skeptic told to refute it; uncertain means refuted. Only confirmed findings proceed. Never launder a plausible-but-unverified claim into a fix.

**FIX.** Root cause, minimal diff, per darkevox-guidelines. Every confirmed finding gets a test that would have caught it, or a written reason why no test can.

**PROVE.** `ruff check .` clean, full pytest green, and for anything visual: render it offscreen and actually look at the image. A UI change without a viewed screenshot is unproven. Anything only the real Windows machine can prove goes to TESTPLAN.md as an unchecked item and into the next message to the user.

**SHIP.** Commit with an honest message (counts, what was refuted as well as fixed), push branch and main. An iteration that doesn't ship didn't happen.

## Exit condition

The segment is done when **two consecutive sweeps confirm zero new findings** and all field reports on it are closed or explicitly waiting on user testing. Then tag if a release is due. Three iterations is the floor for a segment the user called rough, not the ceiling.

## Continuity across sessions and limits

The loop survives resets through three artifacts, kept current every iteration:

- **The task ledger** (TaskCreate/TaskUpdate): one task per open segment or phase, updated before every ship. A fresh session reads the ledger and PLAN.md and continues without archaeology.
- **The watchdog Routine**: an hourly trigger that re-enters the session and runs at most one bounded iteration against the ledger. It fixes red tests before touching features, ships every time, and never starts a second iteration in one firing. Manage with list_triggers / update_trigger / delete_trigger; the user can kill it any time by asking.
- **PLAN.md** as the vision of record. When scope changes mid-loop (user message), amend PLAN.md in the same commit.

Budget hygiene: when context grows long, finish the current iteration's FIX and PROVE, ship, update the ledger, and let compaction take the transcript; never leave a half-applied fix uncommitted across a compaction boundary.

## Honesty rules

No fabricated verification: a check without observable output did not happen. Refuted findings are reported as refuted, not silently dropped. If the loop cannot meet an exit condition (needs the user's machine, needs a decision), it says so and parks the item visibly instead of spinning.
