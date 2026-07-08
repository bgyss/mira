# M7 — Multi-Game Conditioning & Transfer

**Objective:** one model, many games. Game-identity conditioning, a union action space with
per-game channel masking, a mixed-dataset loader, and a rigorous transfer study (joint vs
per-game vs finetune-from-joint at matched compute). Flagship experiment: TotK-from-BotW transfer
— **contingent on the emulation legal review clearing those titles; the fallback flagship is
Elden Ring ↔ RL and a second PC game.**

## 0. Context & prerequisites

- **Depends on:** M5 + M6 (merged into the joint model), M1 (presence masks), M0 (`GameSpec`
  registry, `game_id` in dataset meta), M3 (shared latent space across domains).
- Loader invariant to preserve: a match's perspectives arrive contiguously player-ordered
  (`n_players` consecutive rows) — the multiplayer wrapper's `rearrange("(b p) ...")` depends on
  it. Mixed-game batches must respect it per-sample-group.

## 1. Design

### 1.1 Game-identity conditioning

- Learned game embedding token from `game_id` (via the M0 registry), injected alongside the
  segment/state tokens from M6. CFG-style dropout so a game token can be omitted (useful for
  probing what transfers).

### 1.2 Union action space with per-game masking

- Union vocabulary = union of all games' buttons + axes, built from registered `ActionConfig`s;
  per-game masks mark absent channels, which resolve to the M1 learned absent-tokens
  (buttons: a per-key "not present in this game" embedding, distinct from "present but not
  pressed" — extend `ActionTensors` with a per-channel validity mask sourced from the game's
  config rather than overloading NaN for buttons).
- Per-game action routing lives in the loader (map a game's native channels into union columns);
  the encoder sees one fixed-width space. Union layout is versioned and stored in the checkpoint
  config — adding a game later appends columns (warm-start via the established
  shape-tolerant `load_state_dict` pattern).

### 1.3 Mixed-dataset loader

- Multiple `index.json` sources with per-domain sampling weights; interleave at the
  (match, chunk) level; per-sample `game_id` flows into batch metadata.
- `configs/dataset/multi_game.yaml`: list of {index, game, weight, n_players}; per-game fps
  handling via each game's `ActionConfig`/video params (M3 fixed one canonical latent
  resolution — assert it).

### 1.4 Transfer study protocol (fixed before any training)

- Conditions at matched compute: (1) per-game single training; (2) joint; (3) finetune-from-joint
  per game; (4, if data allows) finetune-across-similar-games (TotK-from-BotW or equivalent).
- Report per-game: M4 controllability metrics, M5 revisit/drift, M6 mode-switch/HUD coherence,
  Frechet. Pre-register the comparison grid and seeds; equal validation sets across conditions.

## 2. Phased execution

1. **Phase A — Plumbing.** Union action space + masks + mixed loader + game token; unit tests;
   smoke train on RL + Elden Ring subsets. Gate: single-game configs through the new plumbing
   reproduce single-game results (no plumbing tax).
2. **Phase B — Joint training.** Full joint run (compute cliff #3); per-domain eval dashboards.
3. **Phase C — Transfer matrix.** Run the §1.4 grid; the finetune conditions branch from the
   joint checkpoint.
4. **Phase D — Report & recipe.** Written recommendation on the scaling recipe (when joint wins,
   when finetune wins, data-ratio sensitivity); ship `configs/dataset/multi_game.yaml` and the
   best checkpoints.

## 3. Non-goals

- No new games' capture pipelines beyond what M2's harness generalizes to (a second PC game reuses
  it; console emulation only if legally cleared).
- No per-game adapter modules (LoRA-style) — full-model conditions only; adapters are noted as
  follow-up if the matrix shows joint hurts specialists.
- No real-time work (M8).

## 4. Tests & verification

- Union-mapping unit tests: native→union round-trip per game; absent-channel tokens distinct from
  zero-valued channels; layout versioning.
- Mixed-loader tests: grouping invariant holds per game group; sampling weights realized within
  tolerance; `game_id` metadata correctness.
- Hydra smoke test for `multi_game.yaml`; checkpoint warm-start test (M5/M6 checkpoint → union
  layout).
- `pixi run verify` green.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Legal review blocks BotW/TotK | Fallback flagship named up front (second PC game); protocol is game-agnostic |
| Joint training degrades the strongest single game | Per-domain eval gates in Phase B; sampling-weight sweeps; note adapter follow-up |
| Union space churn when adding games | Versioned layout + append-only columns + warm-start tests |
| Matched-compute claims contested | Pre-registered protocol, fixed seeds, equal token budgets logged per condition |
| Data imbalance (100h RPG vs large RL corpus) | Weights are the experiment variable, not an afterthought; report sensitivity |

## 6. Sequencing & effort

A (~2–3 weeks) → B (~2 weeks GPU) → C (~3 weeks GPU) → D (~1 week). Sequence GPU budget with
M3/M5 — this is the third compute cliff.

**Definition of done:** mixed training runs from `configs/dataset/multi_game.yaml`; transfer
matrix complete with per-game M4/M5/M6 metrics at matched compute; scaling-recipe recommendation
written; union action space versioned with warm-start tests; `pixi run verify` green.
