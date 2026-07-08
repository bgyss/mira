# M5 — Long-Horizon Memory & Spatial Consistency

**Objective:** leave an area, come back, and it's still the same area. Build the revisit/drift
evaluation first, then implement and compare at least two memory architectures warm-started from
the M4 checkpoint, and ship the winner behind a config flag.

## 0. Context & prerequisites

- **Depends on:** M4 checkpoint; M2's long chunks (30s+) and deliberately captured revisit loops.
- Existing machinery: rollout drift metrics in `src/mira/training/metrics/world_model_metrics.py`;
  streaming kv-cache inference; RoPE (`layers/rope.py`) has **no learned resolution/length
  positional params**, so context-length extension needs no positional surgery;
  `MultiWrapperWorldModel.load_state_dict` is the precedent for warm-starting across shape
  changes (mirror its approach for new memory modules).
- This is the second compute cliff — sweep small, train the winner once.

## 1. Phase A — Evaluation before architecture (mandatory gate)

1. **Loop mining.** From M2 data, find trajectories that revisit a location: use the tagged
   revisit-loop captures first; supplement by visual place recognition (DINO-feature
   nearest-neighbor between temporally distant frames of one session, geometrically verified).
   Output: a benchmark set of (first-visit clip, return-visit clip, matched-pose frame pairs).
2. **Revisit-consistency metric.** Condition the model on context ending at departure; roll out
   through the (action-replayed) return; compare generated return-visit frames to real ones at
   matched poses — DINO feature similarity + LPIPS, reported against two baselines:
   (a) copy-first-visit-frame (upper bound for a static world), (b) unconditional continuation of
   the M4 model (the number to beat).
3. **Long-rollout drift curves.** Extend the existing drift work to 60s+ rollouts with real action
   streams; report Frechet-DINO vs rollout length.
4. Run all of it on the M4 checkpoint → the baseline scorecard. Merge metrics with unit tests
   (synthetic scenes with known revisits) before any model work.

## 2. Phase B — Architecture tracks (implement ≥2, compare on the Phase A benchmark)

### Track (a): extended sparse-attention context

- Much longer kv-cache windows with chunked/sparse attention (e.g. sliding window + strided
  global tokens). RoPE extends natively; the cost is attention compute/memory — profile against
  `scripts/bench_wm_speed.py` since M8 inherits whatever ships.
- Training: longer clips (M2's 900-frame chunks), curriculum from M4's short windows to long,
  warm-start from M4.

### Track (b): retrieval-augmented memory (WorldMem-style)

- Memory bank of past latent frames keyed by estimated pose (Tier-2 state tap if available,
  else learned visual keys); cross-attention reads from retrieved entries in each DiT block (or a
  subset of blocks — ablate).
- New modules are warm-start-exempt (follow the `_WARMSTART_EXEMPT` pattern) so M4 weights load;
  train with teacher-forced memory reads first (ground-truth retrieval), then learned retrieval.
- Write policy: append every k frames with dedup by key similarity; bounded bank with LRU —
  the bank must serialize (M8 save/load needs it).

### Track (c, stretch): compressed persistent state-token bank

- Small recurrently updated token set carried across windows. Only pursue if (a)/(b) both plateau
  below target; document the decision either way.

## 3. Phase C — Compare, decide, ship

1. Consistency/compute Pareto: revisit metric + drift curves vs per-frame inference cost and
   memory footprint, for each track at matched training compute.
2. Ship the winner behind a config flag (`architecture.config.memory: none|long_context|
   retrieval`), default `none` so M4-style configs are untouched; checkpoint-compat discipline
   per `REMOVED_CONFIG_FIELDS` conventions.
3. Full-budget training run of the winner; final scorecard vs the Phase A baseline.

## 4. Non-goals

- No explicit object/entity persistence store (that is the remaster track / M6 boundary work);
  memory here is visual/latent.
- No multi-game memory (M7); no real-time optimization beyond profiling awareness (M8).

## 5. Tests & verification

- Metric unit tests (synthetic revisit scenes with known answers).
- Memory-module unit tests: bank write/read/dedup/serialize round-trip; retrieval determinism
  under fixed seed; warm-start test (M4 checkpoint loads into memory-enabled model).
- Config flag matrix in Hydra smoke tests: `memory: none` reproduces M4 behavior bit-identically
  on the deterministic harness.
- `pixi run verify` green.

## 6. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Pose estimates unavailable ⇒ retrieval keys weak | Learned visual keys as fallback; the benchmark itself only needs matched frames, not poses |
| Long-context training OOM / throughput collapse | Curriculum + chunked attention; gradient checkpointing; small-scale sweeps before committing |
| Metric rewards static worlds (penalizes real dynamics like NPC movement) | Score only on static scene regions (masking via DINO feature stability across real revisits) |
| Winner is too slow for M8 | Pareto framing makes cost a first-class axis; M8 latency budget is a published constraint from M3 |
| Teacher-forced retrieval doesn't transfer to learned retrieval | Staged training with an explicit transfer eval between stages |

## 7. Sequencing & effort

A (~2 weeks, gate) → B (~4–6 weeks, two tracks in parallel if staffed) → C (~2 weeks + final GPU
run).

**Definition of done:** revisit-consistency + 60s drift metrics merged with tests and baselined
on M4; ≥2 memory architectures compared on the same benchmark at matched compute; Pareto report
written; winner shipped behind a config flag with `memory: none` bit-identical to M4;
`pixi run verify` green.
