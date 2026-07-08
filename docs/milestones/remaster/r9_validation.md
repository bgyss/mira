# R9 — Validate Fidelity, Mod Safety, and Remaster Quality

**Objective:** the validation suite proving the remaster is faithful where it should be, editable
where intended, and stable during play — culminating in a **scorecard** that separates
original-game fidelity, remaster visual quality, runtime performance, and editability. The hard
part is preserving causal structure, not producing nicer frames.

## 0. Context & prerequisites

- **Depends on:** R8 (bundles + replay runner are the execution vehicle). Most individual tests
  already exist scattered across R3–R6 — R9's job is to *complete the gaps, unify them against
  bundles, and produce the scorecard*, not to rebuild them.
- All tests run against a bundle, not the working tree — anything else invalidates the
  packability claim.

## 1. Test suites

### 1.1 Golden-path quest tests

The slice's quest: start → progress → completion, plus the failure path, with save/load
performed around each key state (save before flag, load, complete — flag correct). Driven by
recorded input scripts through the replay runner; assertions on schema state.

### 1.2 Combat tests

Damage numbers, dodge/parry timing windows, hitboxes (positional probes), cooldowns,
invulnerability windows, enemy death, rewards, and post-combat state cleanup (no orphaned
entities/timers). Sourced from R3's rules with parameters as oracles; scripted encounter replays.

### 1.3 Object persistence tests

Doors, chests, pickups, NPC movement, destroyed objects, off-camera re-entry — each: change
state, leave (camera and area), return, assert schema state AND rendered appearance (R5's
persistence metric) agree.

### 1.4 Visual tests

Style consistency across locations, temporal stability (warp error), HUD/text readability (OCR),
animation continuity (no pops at latent-window seams), object identity preservation — the
R4/R5 metric suites run on standard trace sets, per adapter combination.

### 1.5 Mod safety tests

For a set of representative edits made via the R7 API (moved encounter, changed item stat,
altered timing adapter): edited encounters reachable, puzzles solvable (R7's checkers as test
oracles), quest graph valid, and the R6 unrelated-regression diff clean.

## 2. The scorecard

One generated document per bundle version, four sections with pass/fail + trend metrics:

1. **Original-game fidelity** — 1.1/1.2/1.3 pass rates, mechanics-replay mismatch taxonomy counts
   (from R3, tracked over time).
2. **Remaster visual quality** — 1.4 metrics vs the R4 baseline ladder.
3. **Runtime performance** — R8 latency breakdown vs budget, per adapter combination.
4. **Editability** — 1.5 pass rates + editor-workflow checks (R7 demo scenario automated).

## 3. Phased execution

1. **Phase A — Inventory & gap analysis.** Map every existing R3–R8 test to the four scorecard
   sections; list gaps (expect: save/load-around-state coverage, combat window probes, cleanup
   checks).
2. **Phase B — Fill gaps.** Implement missing suites (§1.1–1.5) against bundles.
3. **Phase C — Scorecard generator.** Automated report from a bundle + suite run; CI wiring
   (full run nightly; smoke subset per PR).
4. **Phase D — Baseline & sign-off.** Run against the current bundle; triage failures with
   owners; publish scorecard v1 against the R0 success criteria.

## 4. Non-goals

- No new capabilities — failures here create backlog items in the owning milestone's area.
- No human playtesting protocol (borrow M8's if live-play evaluation is wanted; scripted
  validation is R9's scope).

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Neural nondeterminism makes visual tests flaky | Fixed seeds + metric thresholds with tolerance bands, never bit-exactness for frames |
| Suite runtime too long for CI | Tiered: per-PR smoke set, nightly full, per-release exhaustive |
| Scorecard gamed by threshold-tuning | Thresholds trace to the R0 success criteria; changes require a documented decision |
| Save/load edge cases combinatorially explode | Scope to key quest/combat states enumerated from the R2 quest/flag schema (finite for the slice) |

## 6. Effort & definition of done

A (~½ week) → B (~2–3 weeks) → C (~1 week) → D (~1 week).

**Done when:** all five suites run against a bundle in CI; scorecard auto-generates with the four
sections; scorecard v1 published and reviewed against R0's success criteria; every failing item
has an owner and a milestone assignment.
