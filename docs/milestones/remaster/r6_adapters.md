# R6 — Build Mechanic and Style Adapters

**Objective:** make the remaster editable without full retraining. Freeze the base models, add an
adapter interface, ship one **mechanics adapter** (a scoped rule change) and one **style adapter**
(modernized look vs `faithful_v1`), with a regression suite proving adapters don't break
unrelated behavior.

## 0. Context & prerequisites

- **Depends on:** R5 (base world model + R4 renderer path), R3 (rule files — the mechanics
  adapter's substrate).
- Two very different "adapter" kinds, deliberately unified behind one interface so R7's editor
  and R8's runtime treat them uniformly:
  - **Mechanics adapters** are *symbolic*: overlays on R3 rule files (parameter overrides, rule
    swaps) — cheap, exact, testable.
  - **Style adapters** are *neural*: LoRA-style low-rank deltas (or conditioning-token swaps if
    R4 trained multi-style) on the frozen renderer/world model.

## 1. Design

### 1.1 Adapter interface

`{adapter_id, kind: mechanics|style, version, targets (rule ids | model surface), payload
(rule overlay file | checkpoint delta), compat (base model/graph versions), enable/disable}` —
serializable, composable (ordered stack), validated at load (compat check fails loudly, per the
repo's checkpoint-compat discipline). Selection is recorded in save files and replay headers
(R8 depends on this).

### 1.2 First mechanics adapter

Pick one scoped rule from the R3 set, e.g. **dodge/interaction timing** or **weapon reach**:
an overlay that changes only the named parameters. Acceptance: replaying the same trace inputs
with the adapter enabled shows the intended change (e.g. previously-failing dodge now succeeds)
while all non-targeted replay tests still pass.

### 1.3 First style adapter

`modern_v1` (relighting/material detail) trained as a low-rank delta over the frozen R4 renderer;
`faithful_v1` remains the identity reference. Acceptance: R4 metric suite passes for both;
identity-preservation and HUD metrics must not regress beyond epsilon under `modern_v1`.

### 1.4 Regression suite (the milestone's real product)

For every adapter: run the full R3 trace-replay suite + R5 persistence/swap metrics + R4 visual
metrics with the adapter ON, and diff against OFF. Only the declared `targets` may change.
Automated report: intended-change verification + unrelated-change detection.

## 2. Phased execution

1. **Phase A — Interface + loader.** Adapter model, stacking, compat validation; mechanics
   overlay application to the R3 engine; neural delta application to frozen checkpoints.
2. **Phase B — Mechanics adapter.** Build §1.2; regression suite v1 (mechanics side).
3. **Phase C — Style adapter.** Train §1.3; regression suite v2 (visual side).
4. **Phase D — Demo.** Editor-less toggle demo: same trace replayed with each adapter
   combination (off/off, mech/off, off/style, both), rendered side by side; report.

## 3. Non-goals

- No editor UI (R7 exposes these toggles); no new gameplay content; no more than one adapter of
  each kind; no runtime packaging (R8).

## 4. Tests & verification

- Interface unit tests: serialization, compat rejection, stack ordering determinism.
- Mechanics overlay tests: only declared parameters differ in the effective rule set.
- Neural delta tests: OFF ⇒ bit-identical to base model outputs (deterministic harness).
- The §1.4 regression suite wired into CI for both adapters.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Neural adapter leaks into unrelated visuals (style bleeds onto HUD) | Region-aware metrics (HUD masks) in the regression suite; train with HUD-preservation loss if needed |
| Mechanics change invalidates downstream traces (butterfly effects) | Expected and allowed *within declared targets*; the suite distinguishes targeted vs unrelated divergence by rule provenance |
| Adapter/base version skew | Compat field validated at load; fails loudly |
| LoRA insufficient for large style shifts | Fall back to conditioning-token multi-style training in R4's framework; record the decision |

## 6. Effort & definition of done

A (~1–2 weeks) → B (~1 week) → C (~2–3 weeks) → D (~½ week).

**Done when:** both adapters enable/disable cleanly at load; intended changes demonstrated on
replayed traces; regression suite shows no unrelated quest/inventory/collision/persistence/visual
regressions; OFF-state bit-identity proven; adapter selection serializes for save/replay.
