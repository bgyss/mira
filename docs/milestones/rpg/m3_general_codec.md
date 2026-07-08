# M3 — General-Purpose Codec (Multi-Domain RAEv2)

**Objective:** retrain the frozen RAEv2 codec on a mixed RPG + Rocket League corpus at a chosen
resolution/fps operating point, so one latent space serves all downstream world models. Ship one
winning checkpoint as **the** frozen codec for M4+.

## 0. Context & prerequisites

- **Depends on:** M2 (RPG shards; ≥20h is enough to start, full 100h before the final run).
- Ground truth: `src/mira/codec` — frozen DINOv3-L/16 encoder + layer aggregation →
  strided-conv bottleneck → ViT video decoder (`vit_decoder.py`); trained with
  L1 + LPIPS + DINO-latent-consistency (`loss.py`) via `scripts/train_codec.py`
  (needs `RS_DINO_WEIGHTS_DIR`). The DINO backbone is general; the bottleneck/decoder were fit to
  RL's visual statistics.
- Real-time budget authority: `scripts/bench_wm_speed.py`. M8 needs single-frame decode + one
  denoise window inside the per-frame budget at ≥20fps — the resolution decision made here is a
  **latency decision**, not just a quality decision.

## 1. Design decisions to make (each recorded in a decision log in this doc's repo dir)

1. **Resolution/fps operating point.** Candidates: 360p@30, 480p@30 (RL is currently lower/20fps).
   Decide by: HUD/text legibility at each resolution × decode latency from
   `bench_wm_speed.py` × training-compute cost. Elden Ring HUD text is the forcing function.
2. **Latent capacity.** Sweep latent channel count (e.g. current, 1.5×, 2×) and temporal
   downsampling td=1 vs td=2. Open-world content (foliage, fog, HDR skies) will demand more
   capacity than RL; the question is how much before world-model cost explodes (latent dim feeds
   directly into DiT token width/count).
3. **Mixed-corpus recipe.** Sampling weights RPG:RL (start 70:30); whether RL is upscaled to the
   new resolution or letterboxed; per-domain augmentation. Keep RL in the mix — M7's joint
   training needs one latent space, and codec forgetting RL would silently poison it.
4. **Aspect ratio.** RL and Elden Ring differ; pick one canonical train shape + crop/pad policy,
   documented in the dataset configs.

## 2. Phased execution

### Phase A — Eval harness first

1. Per-domain reconstruction eval: L1 / LPIPS / DINO-consistency computed **separately for RPG and
   RL** held-out sets (never a single blended number).
2. **HUD/text legibility metric** (new, in `src/mira/training/metrics/`): curated frame set of
   health bars, damage numbers, menus, region toasts; metric = OCR agreement (recognize text on
   original vs reconstruction) + a masked-region LPIPS on HUD boxes. Unit-tested with fixtures.
3. Baseline: run the harness on the **current RL codec** applied to RPG frames — this is the
   number to beat and the motivation record.

### Phase B — Sweeps

1. Latent capacity × temporal downsampling grid (small config variants of
   `configs/train_codec.yaml`), short runs (~fraction of full schedule) on the mixed corpus.
2. Resolution candidates evaluated at matched compute; for each, measure decode latency with
   `bench_wm_speed.py` on the target inference GPU.
3. **Downstream ablation (the decisive one):** for the top 2–3 codec candidates, train a small
   world model (existing small config under `configs/model/latent_world_model/`) for a fixed
   short budget and compare rollout quality (existing Frechet-DINO/drift metrics). Reconstruction
   metrics alone have historically mispredicted downstream quality — do not skip this.

### Phase C — Full training run

1. Train the winning configuration to completion on the full mixed corpus.
2. Final eval: per-domain reconstruction + HUD metric + latency profile; side-by-side
   reconstruction galleries per biome/time-of-day and RL, reviewed by a human.

### Phase D — Ship & freeze

1. Publish checkpoint with its config snapshot; record the operating point (resolution, fps, td,
   latent dims) in a `codec_card.md` next to the checkpoint and in `configs/README.md`.
2. Update world-model configs' latent-dim interpolations (`${...}`) to source from the new codec
   config; verify `train_world_model.py` composes cleanly with
   `model.architecture.config.codec_checkpoint` pointing at it.
3. Regression: RL reconstruction must not degrade beyond an agreed epsilon vs the old codec.

## 3. Non-goals

- No codec architecture redesign (same RAEv2 topology; only width/td/resolution knobs).
- No world-model training beyond the small ablation probes (M4).
- No torch upgrade — respect the torch 2.8 / torchcodec 0.7.0 / FFmpeg 7 pin (`pixi.toml` header);
  `torch.compile` on the codec graph breaks on newer torch.

## 4. Tests & verification

- HUD-legibility metric unit tests (fixtures with known text).
- Config tests mirroring `tests/codec/test_config.py` for any new config fields.
- Checkpoint load test: new codec loads through the same frozen-codec path
  `LatentWorldModel` uses (`codec_checkpoint`), including under `torch.compile`.
- `pixi run verify` green; decision log updated at each phase gate.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Reconstruction metrics don't predict WM rollout quality | Phase B.3 downstream ablation is mandatory before committing full compute |
| Higher resolution blows the M8 latency budget | Latency measured per candidate in Phase B; budget is a hard constraint, not a tiebreaker |
| RL quality regresses (joint-training poisoning) | Per-domain eval + explicit RL epsilon gate in Phase D |
| Compute cliff (this is the first of three) | Short-run sweeps before the single full run; only one full-schedule training |
| DINO gated weights availability on the training cluster | Verify `RS_DINO_WEIGHTS_DIR` provisioning before Phase B scheduling |

## 6. Sequencing & effort

A (~3 days) → B (~1–2 weeks incl. queue time) → C (~1 week GPU) → D (~2 days). Phase A can start
as soon as M2 Phase A yields any RPG shards.

**Definition of done:** one frozen codec checkpoint + codec card; per-domain metrics reported
(RPG + RL, incl. HUD legibility) with RL non-regression; operating point satisfies the
`bench_wm_speed.py` real-time budget; downstream small-WM ablation documented; world-model
configs updated; `pixi run verify` green.
