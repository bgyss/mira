# M4 — First RPG World Model (Short-Horizon Control Fidelity)

**Objective:** train `LatentWorldModel` on the M2 dataset with the M1 action space and M3 codec.
Success is **controllability**, not photorealism: stick deflection steers the character, camera
follows the right stick, jump/attack/dodge trigger the right animations, terrain is respected.
This milestone also validates that M0–M3 compose — the run must require **only config-level
changes**.

## 0. Context & prerequisites

- **Depends on:** M1 (gamepad encoder), M2 (≥ initial tens of hours of shards), M3 (frozen codec).
- Existing machinery: `scripts/train_world_model.py` (Hydra), `LatentWorldModel`
  (flow-matching DiT, RoPE, streaming kv-cache inference), metrics under
  `src/mira/training/metrics/` (Frechet DINO, rollout drift), rollout viz in
  `training/visualization.py`, deterministic harness in `src/mira/inference/rollout.py`.

## 1. Design

### 1.1 Config composition (no code for the training path)

- `configs/dataset/elden_ring.yaml` (from M2) + a size pick from
  `configs/model/latent_world_model/` via the existing package-override syntax
  (`latent_world_model@architecture.config: 1b` etc.). Start at a mid size; scale after the
  controllability metrics pass at small scale.
- `n_players=1` — the multiplayer wrapper is unused; the plain `LatentWorldModel` path.
- Context length: RL uses 16-frame clips; with M2's 900-frame chunks, keep the same latent-window
  length initially (short-horizon milestone) but sample clips uniformly across chunks.

### 1.2 Controllability metric suite (new, `src/mira/training/metrics/controllability.py`)

All three run on held-out clips during validation, cheap enough for periodic eval:

1. **Counterfactual action swap.** Same context, two different action continuations (real vs
   resampled-from-another-clip); rollout both with shared noise; metric = latent divergence curve
   (e.g. per-frame L2 / DINO distance). Pass = divergence significantly above the same-action
   noise floor within k latent frames. (Generalizes the "action-swap divergence" idea; shared
   noise isolates the action effect.)
2. **Stick–flow agreement.** Decode short rollouts; compute optical flow (RAFT-small or
   Farnebäck — pick one, pin it) over the character-centric region; metric = circular correlation
   between left-stick direction and dominant flow direction, and right-stick vs global
   (camera) flow. Pass = correlation above threshold on clips with |stick| > deadzone.
3. **Event-conditioned animation onset.** For button events (attack/dodge/jump) in held-out
   traces, check the generated rollout produces the corresponding visual onset within k latent
   frames — implemented as a small frozen classifier trained on real footage (attack/dodge/roll
   /jump/none, trained from M2's event-annotated data), applied to generated frames.

Each metric ships with unit tests on synthetic fixtures (e.g. moving-square videos where flow
direction is known analytically).

### 1.3 Conditioning-strength levers (iterate until metrics pass)

- Action-token dropout probability (CFG-style; encoder already supports dropout tokens) and
  action CFG scale at inference.
- Action embedding dim share (M1 §1.3 split), encoder depth on the axes branch.
- Loss weighting toward early denoise steps if actions are being ignored (diagnose via
  action-swap divergence at different noise levels).
- Data: filter low-motion/menu spans (use M2 annotations) from training clips for this milestone
  — menu dynamics belong to M6.

## 2. Phased execution

### Phase A — Metrics before model

Implement §1.2 and run it on **real held-out data as a sanity ceiling** (real continuations must
pass trivially) and on an RL checkpoint over RL data (regression harness for the metrics
themselves). Merge with tests.

### Phase B — First training run

1. Small config, subset of data, short schedule; confirm the loop runs end-to-end (loader,
   encoder, codec, DiT, checkpointing, wandb, viz) with **config-only changes**. Any code change
   needed here is a bug in M0–M3 — fix upstream, don't fork.
2. Rollout gallery across biomes/times-of-day wired into the tracker.

### Phase C — Controllability iteration

1. Grid over conditioning levers (§1.3); track the three metrics per run.
2. Define pass thresholds from Phase A ceilings (e.g. ≥70% of real-data stick–flow correlation);
   iterate until all three pass at the small scale.
3. Document failure modes as they're found (e.g. camera ignores right stick in lock-on segments;
   attack onset lags; sprint vs walk conflation) — this catalog seeds M5/M6 priorities.

### Phase D — Scale run

1. Scale model size / data / schedule; re-verify metrics don't regress and quality improves.
2. Final report: metric table, gallery, failure-mode catalog, recommended checkpoint for M5/M6.

## 3. Non-goals

- Long-horizon consistency / revisits (M5). Menus, HUD-value coherence, death/loading transitions
  (M6) — menu spans are *excluded* here. Multi-game (M7). Real-time latency (M8).
- No photorealism bar: Frechet scores are tracked but are not the gate.

## 4. Tests & verification

- Unit tests for each metric (synthetic fixtures with known answers).
- Hydra smoke test `tests/world_model/`-style for the new config composition (loads, one train
  step on fixture data).
- Metrics integrated into the validation loop behind config flags; `pixi run verify` green.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Model ignores actions (common failure: video prior dominates) | CFG-style action dropout + swap-divergence diagnostics per noise level; Phase C is budgeted for this explicitly |
| Optical-flow metric noisy on cluttered scenes | Restrict to high-deflection clips, character-region cropping, report with confidence intervals |
| Animation classifier weak ⇒ metric untrustworthy | Validate classifier ≥95% accuracy on real held-out frames before using it as a judge |
| Data insufficient (biome/action coverage gaps) | M2's coverage matrix; Phase C failure modes feed capture priorities while M2 Phase C is still running |
| Config-only goal broken by unforeseen coupling | Treat as an M0–M3 defect: fix in the owning layer with a regression test |

## 6. Sequencing & effort

A (~1 week) → B (~3 days + GPU) → C (~2–3 weeks, the substance) → D (~1 week GPU).

**Definition of done:** a checkpoint that passes all three controllability thresholds; metrics
merged with tests; rollout gallery across biomes; failure-mode catalog written; training required
config changes only; `pixi run verify` green.
