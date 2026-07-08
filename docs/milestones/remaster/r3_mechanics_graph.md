# R3 — Recover an Explicit Mechanics Graph

**Objective:** an executable, inspectable rules layer for the slice's gameplay — movement/
collision, interaction, one combat exchange, inventory/menu, one quest flag — implemented as a
typed mechanics graph with a deterministic simulator, validated by replaying captured traces and
classifying every mismatch.

## 0. Context & prerequisites

- **Depends on:** R2 schema v1 frozen (the graph reads/writes schema state exclusively).
- **Shares design with:** the RPG-track M6 §1.4 mechanics prototype — same node/rule
  representation and package conventions (`mechanics` package), so the two tracks converge on one
  rules engine. If M6 has landed, extend it; if not, build here and M6 consumes it.
- R1's determinism catalog (which subsystems drift) directly scopes what "replayable" means.

## 1. Design

### 1.1 Graph representation

- Typed nodes: `{rule_id, reads: [state paths], writes: [state paths], condition, effect,
  priority, timers/cooldowns, emits: [event types]}`; declarative (data + small pure functions),
  serializable to rule files so R7's editor can display and edit them.
- Deterministic simulator: `step(state, input, dt) -> (state', events)` — fixed evaluation order
  by priority, explicit RNG stream (seeded, recorded), no wall-clock reads.

### 1.2 First rule set (exactly the slice's loops)

1. Movement + collision response (against R1 collision/navmesh refs).
2. Door/chest interaction (affordance check → state flip → event).
3. Item pickup → inventory add → world object removal.
4. Health/stamina deltas: one combat exchange (player hit → enemy damage → death → reward),
   including timers (attack windup, cooldown, i-frames if the slice has them).
5. One quest flag update; one menu open/close transition.

### 1.3 Rule recovery workflow (repeatable, documented per rule)

Priority order: (1) read source/mod scripts where available (R0 chose for this) — transcribe with
provenance links; (2) state-trace mining — fit parameters (damage numbers, speeds, cooldowns)
from R1 traces; (3) manual annotation from play observation; (4) learned rule *suggestions*
(candidate condition→effect pairs mined from state deltas) that a human promotes to rules — never
auto-accepted. Every rule records its recovery source.

### 1.4 Mismatch taxonomy (the replay test's output contract)

Every divergence between simulated and captured state is classified as exactly one of:
**missing rule**, **incorrect parameter**, **missing state field** (feeds back to R2 as a
migration), or **nondeterministic original behavior** (documented tolerance). The taxonomy report
is a deliverable — it is the honest map of what the graph does and doesn't capture.

## 2. Phased execution

1. **Phase A — Engine core.** Graph representation + simulator + rule-file format; unit-test
   harness for single rules; movement/collision as the first rule (hardest, most data).
2. **Phase B — Interaction & inventory rules.** Rules 2/3/5 + menu transition; per-rule unit
   tests + trace-replay tests on interaction-heavy traces.
3. **Phase C — Combat.** Rule 4 with parameter fitting from traces; timers/cooldowns; replay
   tests on the reserved combat traces.
4. **Phase D — Full-trace replay & taxonomy.** Replay the entire regression split; produce the
   mismatch report; iterate until remaining mismatches are all classified and either fixed or
   accepted with rationale.

## 3. Non-goals

- No rules beyond the slice's loops; no AI/pathfinding beyond replaying recorded NPC state
  (NPC decision-making stays trace-driven until a later milestone needs it live).
- No neural components (R5 consumes the graph's deltas; nothing neural lives here).
- No editor UI (R7) — but rule files must already be human-readable.

## 4. Tests & verification

- Per-rule unit tests (given state+input ⇒ expected deltas/events).
- Property tests: health/stamina bounds, inventory conservation, no writes outside declared
  `writes`.
- Trace-replay suite over the regression split with per-frame state diff and the §1.4
  classification; tolerance config per field (pose epsilon vs exact flags).
- Simulator determinism test: same seed + inputs ⇒ identical state hash.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Collision fidelity rathole (physics is hard) | Use engine collision data/refs from R1 rather than re-deriving; accept documented pose epsilon |
| Hidden mechanics not in scripts or traces | The taxonomy makes gaps explicit; "missing rule" backlog is prioritized by gameplay impact, not completeness |
| Parameter overfitting to few traces | Fit on one trace subset, validate on held-out replays |
| Divergence cascades (one early mismatch ruins the diff) | Replay harness supports re-anchoring to captured state at checkpoints, scoring windows independently |
| Engine drift vs M6's mechanics package | One shared package + cross-track design review before Phase A |

## 6. Effort & definition of done

A (~2 weeks) → B (~1 week) → C (~1–2 weeks) → D (~1 week).

**Done when:** all five rule groups implemented with per-rule provenance; the regression split
replays with every mismatch classified under the taxonomy; simulator is deterministic; rule files
serialize/deserialize; property + unit + replay suites green in CI.
