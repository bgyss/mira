# R5 — State-Conditioned World Model for Visual Dynamics

**Objective:** add MIRA-style latent prediction for animation continuity, camera motion, and
interaction appearance during *interactive* play — while the R3 mechanics graph stays
authoritative for state. Prove with an ablation that explicit state conditioning beats a
pixel/action-only world model on persistence, interaction fidelity, and replay consistency.

## 0. Context & prerequisites

- **Depends on:** R3 (state deltas as conditioning source), R4 (conditioning contract, codec
  decision, metrics), R1/R2 (data + schema).
- **Reuses heavily:** `LatentWorldModel` + flow-matching DiT + streaming kv-cache; the M6
  segment/state conditioning design (this is its remaster-track instantiation — share encoders
  where the shapes allow); M4's controllability metric playbook.

## 1. Design

### 1.1 Conditioning path (the causal order is the contract)

```text
input -> mechanics graph (authoritative) -> state deltas + events
      -> state/event encoders -> conditioning tokens (with actions)
      -> world model predicts next latent frame -> decode (through the R4 style path)
```

The model is a renderer/dynamics prior. It never invents door states, health, or inventory — it
renders their consequences. Training consumes past frames, input, explicit state, event tokens,
and future frames; state encoders follow M6 §1.1–1.2 (segment tokens, structured-state vector with
per-element NaN masking) extended with **in-view object tokens** (per-object embedding of
`object_id` class/pose/state for the k nearest visible objects — the remaster-specific addition).

### 1.2 Ablation (a first-class deliverable)

Two models at matched compute/data: (A) pixel+action only (M4-style), (B) + full state/event
conditioning. Report on the §1.3 metrics. This evidence justifies (or falsifies) the hybrid
thesis for the whole remaster program.

### 1.3 Metrics

- **Action-swap divergence** and **state-swap correctness** (swap a door-open delta for
  door-closed: the rollout must render the right one) — swap tests per the M4 playbook.
- **Object persistence & off-camera re-entry:** pan away from a state-changed object, pan back —
  correct state rendered (scored with the R4 identity metric + a state classifier).
- **Loop/revisit consistency** and **long-rollout drift:** reuse M5's metrics on the slice's
  revisit traces.

## 2. Phased execution

1. **Phase A — Data plumbing.** Training samples pairing shards with per-frame schema
   state/events; encoder modules (share/extend M6's); Hydra config for the remaster dataset.
2. **Phase B — Baseline (A).** Pixel+action model on slice data; run all metrics — the ablation
   floor.
3. **Phase C — State-conditioned model (B).** Train with conditioning dropout (robustness to
   missing state); iterate conditioning strength per the M4 levers until swap tests pass.
4. **Phase D — Ablation report + integration.** A vs B scorecard; wire the winner behind the R4
   decode path; interactive smoke test: scripted inputs through mechanics → model → frames.

## 3. Non-goals

- No adapters (R6), editor (R7), or real-time optimization (R8 profiles what ships here).
- No mechanics inside the model — any gameplay logic discovered missing goes to R3's backlog.

## 4. Tests & verification

- Encoder unit tests (object tokens, NaN masking, dropout) mirroring `tests/world_model`.
- Swap-test metric unit tests on synthetic fixtures.
- End-to-end determinism: fixed seed mechanics+model rollout reproducible (R8's replay
  foundation).
- `pixi run verify` green.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Model shortcuts around state tokens (reads pixels instead) | Conditioning dropout + state-swap tests as gates; strengthen per M4 levers |
| Object-token set varies per frame (ragged) | Fixed k-nearest slots + presence mask (the M1 pattern again) |
| Slice corpus too small for a good dynamics prior | Warm-start from the M4/M7 RPG checkpoint if the codec is shared — measure; else scope rollout-length claims down |
| Divergence between M6 and R5 conditioning code | Shared encoder modules, one owner; cross-track review |

## 6. Effort & definition of done

A (~1–2 weeks) → B (~1–2 weeks GPU) → C (~3 weeks) → D (~1 week).

**Done when:** state-conditioned model beats the pixel/action baseline on state-swap,
persistence, re-entry, and revisit metrics at matched compute; ablation report published;
mechanics→model interactive smoke path runs deterministically; metrics + tests in CI.
