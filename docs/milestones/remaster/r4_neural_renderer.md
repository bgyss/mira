# R4 — Train a Neural Remaster Renderer

**Objective:** learn to convert old-game frame + state + legal assets into a consistent upgraded
presentation, beating simpler baselines, shipping first as a **faithful-remaster** style adapter
with temporal-consistency, identity-preservation, HUD/text, and trace-replay-fidelity metrics.

## 0. Context & prerequisites

- **Depends on:** R1 corpus, R2 schema (conditioning inputs), asset manifest (which assets may
  condition training and which may ship).
- **Reuses:** the M3 codec if its latent space covers the target's visuals (evaluate first —
  retro/low-poly footage may reconstruct fine); mira training infra (Hydra configs, tracker,
  metrics conventions). The renderer is per-frame/short-window image translation — distinct from
  R5's dynamics model.

## 1. Design

### 1.1 Conditioning contract (freeze before training)

Inputs per frame: old frame (or its latent), camera pose, in-view object state (IDs, classes,
poses, material/style tokens from R2), optional source-asset references (texture crops/mesh
renders for in-view objects), and a target style prompt or adapter ID. Output: remastered frame.
The contract is a typed record — R5, R7, and R8 all consume it.

### 1.2 Baseline ladder (in order; each is a shipping fallback for the next)

1. Off-the-shelf super-resolution/upscaling (no training).
2. Texture replacement via extracted assets (classical, engine-side if the engine allows).
3. Frame-to-frame video enhancement (temporal model, no state).
4. **State-conditioned neural renderer** (the target): diffusion/flow image-translation
   conditioned per §1.1, trained on (old frame → enhanced target) pairs.

Training targets for "faithful remaster": self-supervised enhancement targets (e.g.
higher-internal-resolution re-renders if the open engine can produce them — the R0 target choice
pays off here; else pass-3 outputs as pseudo-targets refined by adversarial/perceptual losses).

### 1.3 Metrics (built before the big model, run on all ladder rungs)

- **Temporal consistency:** warped-frame error (flow-warped t→t+1 difference) on generated video.
- **Object identity preservation:** DINO-feature similarity of the same `object_id` across
  frames/viewpoints; no unintended appearance drift when state is unchanged.
- **HUD/text legibility:** the M3 OCR-agreement metric, reused.
- **Input/action latency proxy:** per-frame inference cost (feeds R8's budget).
- **Trace-replay fidelity:** side-by-side original vs remastered playback of regression traces,
  scored for structural agreement (edges/layout via LPIPS-on-downsampled + human spot checks).

## 2. Phased execution

1. **Phase A — Metrics + baselines.** Implement §1.3; run rungs 1–3; publish the baseline
   scorecard (the numbers the neural renderer must beat).
2. **Phase B — Codec decision.** Evaluate the M3 codec on target footage; retrain/finetune the
   codec only if reconstruction fails the HUD/identity metrics (record the decision).
3. **Phase C — State-conditioned renderer.** Train rung 4; ablate conditioning inputs (no-state
   vs full-state — the value-of-state evidence matters for the whole program).
4. **Phase D — Faithful style adapter.** Package the winning configuration as the first named
   style adapter (`faithful_v1`) with its config, checkpoint, and metric card; galleries of
   original/remastered pairs across the slice's locations.

## 3. Non-goals

- No aggressive modernized styles (R6 adds the adapter mechanism and a second style).
- No future-frame prediction or action conditioning (R5).
- No editor integration (R7) beyond the metric galleries.

## 4. Tests & verification

- Metric unit tests on synthetic fixtures (known warps, known identity swaps, known text).
- Conditioning-contract round-trip tests; asset-manifest gate test (renderer never trains on
  `excluded` assets — enforced in the dataloader, tested).
- Hydra config smoke tests per repo convention; `pixi run verify` green if hosted in-repo.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| No good enhancement targets (nothing to learn toward) | Engine re-render path from R0's open target; else the pseudo-target ladder — decided in Phase A with evidence |
| Temporal flicker in per-frame translation | Short-window conditioning + consistency loss; the metric gates it; R5 exists partly for this |
| State conditioning ignored by the model | Ablation in Phase C; conditioning dropout + swap diagnostics (same playbook as M4) |
| Style drift makes objects unrecognizable (breaks R9 identity tests) | Identity-preservation metric is a gate, not a report |
| Asset license contamination | Manifest-driven dataloader gate with a test |

## 6. Effort & definition of done

A (~1–2 weeks) → B (~1 week) → C (~3–4 weeks incl. GPU) → D (~1 week).

**Done when:** `faithful_v1` beats every ladder rung on the metric suite; ablation quantifies the
value of state conditioning; galleries reviewed; conditioning contract frozen and documented;
metric suite + gates in CI.
