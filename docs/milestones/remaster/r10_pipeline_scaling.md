# R10 — Scale from Slice to Remaster Pipeline

**Objective:** generalize the working prototype into a reusable pipeline — game/profile registry,
multi-area ingestion, shared schema contracts, adapter training recipes, a cost model — and a
grounded recommendation on which class of old games to target next. Only invest here after one
slice works end to end (R9 scorecard passing).

## 0. Context & prerequisites

- **Depends on:** R9 scorecard v1 (the proof the slice works); every R1–R8 component with its
  seams now visible from real use.
- Analog of the RPG track's M7 (multi-game) — reuse its registry/embedding/loader machinery for
  the neural side; the remaster-specific generalization is the *symbolic* side (schemas,
  extraction hooks, mechanics plugins).

## 1. Deliverables & design

### 1.1 Game/profile registry

Per-game profile bundling: extraction hooks (R1 instrumentation adapters), schema mappings (raw →
R2 records), mechanics plugins (engine-specific rule primitives for R3), renderer/world-model
adapter configs, and license constraints. Follows the M0 `GameSpec`/plugin registry pattern —
one registry across both tracks if feasible.

### 1.2 Multi-area ingestion

Second and third areas of the prototype game through the pipeline with **shared** schemas and
per-area manifests (entity DBs, quest graphs, test replays). This is the test that R2's schema
was general enough for its own game — expect and budget for migrations.

### 1.3 Foundation model strategy

Written strategy + first evidence: a shared game/video world model (leveraging the M7 joint
checkpoint if it exists) with per-game control + style adapters, vs per-game models. Small
experiment: does warm-starting area-2/game-2 from the slice's checkpoints cut training cost
measurably? (This mirrors M7's transfer matrix at remaster scale.)

### 1.4 Cost model

From the prototype's actuals: capture hours, annotation/review hours, training GPU-hours (R4, R5,
adapters), QA/validation time, and runtime performance per bundle — extrapolated per additional
area and per additional game, with the assumptions explicit.

### 1.5 Next-target recommendation

Score candidate *classes* of old games (open-engine 3D, 2D sprite RPGs, early console 3D via
cleared emulation, homebrew) on: observability, legal safety, automation potential (how much of
R1–R3 the registry covers), visual payoff, and mechanics-recovery automatability. Recommend one,
with the profile skeleton drafted.

## 2. Phased execution

1. **Phase A — Seam extraction.** Refactor R1–R8 prototype code into the registry/profile
   structure with the prototype game as profile #1 (the M0 playbook: relocation + interface,
   zero behavior change, R9 suite as the equivalence gate).
2. **Phase B — Multi-area.** Ingest area 2 (and 3 if cheap) end to end; fix schema/tooling
   generality gaps via versioned migrations; per-area R9 scorecards.
3. **Phase C — Transfer evidence + cost model.** §1.3 experiment; assemble §1.4 from tracked
   actuals.
4. **Phase D — Recommendation.** §1.5 memo + draft profile for the chosen next class; program
   review.

## 3. Non-goals

- No second *game* fully onboarded (that is the next program cycle; R10 delivers the machinery
  and the pick).
- No pipeline automation beyond what multi-area ingestion actually required — automate proven
  pain, not speculation.

## 4. Tests & verification

- Phase A equivalence gate: full R9 suite passes identically on the refactored pipeline.
- Registry tests: profile resolution, unknown-game errors, license-constraint propagation
  (mirroring M0's `test_game_spec.py` pattern).
- Per-area scorecards for every ingested area.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Premature generalization (registry shaped by one game) | Multi-area first (Phase B) exposes real variance before the next-game design hardens |
| Refactor regressions | R9 suite as the equivalence gate, per the M0 discipline |
| Cost model built on unrecorded actuals | Start time/GPU tracking retroactively from R4 logs and prospectively now — flag estimated vs measured |
| Recommendation driven by enthusiasm over rubric | Same scored-table format as R0, reviewed by the same gate |

## 6. Effort & definition of done

A (~2–3 weeks) → B (~2–3 weeks) → C (~2 weeks) → D (~1 week).

**Done when:** registry + profile #1 pass the full R9 suite; ≥2 areas ingested with shared
schemas and per-area scorecards; transfer/cost evidence documented; next-target memo reviewed and
signed off with a draft profile.
