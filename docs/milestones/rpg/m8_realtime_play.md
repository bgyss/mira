# M8 — Real-Time Interactive Play

**Objective:** a human plays the generated RPG live — gamepad in, frames out — at **≥20fps** with
bounded per-frame latency, using the streaming kv-cache + M5 memory + the M6 explicit
mechanics/state loop. Deliver a local play client, save/load + replay for explicit state + model
context, and a human evaluation protocol.

## 0. Context & prerequisites

- **Depends on:** M5 (memory system), M6 (mechanics/state loop), M7 (best checkpoint; a
  single-game M5/M6 checkpoint is an acceptable de-risking start), M3 (latency operating point).
- Existing machinery: streaming path in `src/mira/inference/rollout.py` (kv-cache),
  `world_model/schedule.py` (inference noise schedule — the home for few-step samplers),
  `scripts/bench_wm_speed.py` (profiling authority). **Torch pin is a hard constraint**:
  torch 2.8 + torchcodec 0.7.0 (newer torch breaks `torch.compile` on the codec graph), so
  the main speed levers are step-distilled sampling, compile tuning within 2.8, and quantization
  — not framework upgrades.

## 1. Design

### 1.1 Hybrid runtime loop (the M6 ownership doc made executable)

```text
gamepad poll (≥60Hz)
  -> input buffer, bucketed to latent-frame windows (M1 downsampling contract)
  -> explicit mechanics/state step (M6 graph: menus, stamina, ... — authoritative)
  -> conditioning assembly: actions + segment token + state vector + game token
  -> world model: one denoise window on the streaming kv-cache (+ M5 memory reads)
  -> codec decode -> present frame (+ HUD overlay debug mode)
```

- Mechanics runs on CPU per tick and is never blocked by the GPU; if a frame deadline is missed,
  the model drops to the next window but mechanics state stays exact.
- Server/client split: inference server (GPU host) + thin client (SDL window + gamepad); local
  loopback first, so a remote-GPU demo is free later.

### 1.2 Latency budget (published doc, per-stage)

At 20fps: 50ms/frame end-to-end. Budget lines: input→conditioning (≤2ms), mechanics (≤1ms),
denoise (the fight — measured per step count), decode (measured in M3), present + overhead.
Every optimization PR updates the budget table from `bench_wm_speed.py` runs.

### 1.3 Speed levers, in order

1. **Few-step sampler distillation** (the main lever): distill the flow-matching model to a
   1–4 step sampler (e.g. consistency/shortcut-style distillation over `schedule.py`'s schedule);
   quality tracked with M4/M5/M6 metrics vs step count.
2. `torch.compile` tuning of the streaming path (static shapes, cuda graphs where possible).
3. Quantization (fp8/int8 weight-only first) on DiT and decoder; per-metric regression gates.
4. Pipeline overlap: decode frame t while denoising t+1.

### 1.4 Save/load & replay

- Save = explicit mechanics state + adapter/config selection + RNG seeds + model context
  (kv-cache and M5 memory bank serialization) — **never pixels alone**. Versioned container.
- Replay = recorded input stream + initial save ⇒ deterministic re-generation on the same
  checkpoint (fixed seeds, deterministic sampler); replay determinism is a test, not a hope.

### 1.5 Human evaluation protocol

- Task-based sessions: reach a visible landmark; fight one enemy; open/use a menu; leave and
  return to a location (M5 in the loop). 5-point ratings on control fidelity, coherence, memory;
  plus objective task-completion and "breaks-first" annotation (what failed, when, category).
- Fixed protocol doc + scoring sheet before any sessions; ≥N sessions per build to compare
  builds.

## 2. Phased execution

1. **Phase A — Offline real-time proof.** Full-quality sampler, no human: measure the loop on
   recorded inputs; identify the gap to 50ms; publish budget v1.
2. **Phase B — Distillation.** Few-step sampler to quality/speed target (gate: M4
   controllability within an agreed epsilon of the many-step teacher).
3. **Phase C — Live client.** Gamepad ingestion, mechanics-in-the-loop, presentation; internal
   playtests; latency budget v2 with the real loop.
4. **Phase D — Save/load, replay, and human eval.** Serialization + determinism tests; run the
   protocol; "where it breaks first" report.

## 3. Non-goals

- No browser/WebGPU port, no multi-user server, no matchmaking — local single-player only.
- No new model capabilities: M8 consumes M5/M6/M7 checkpoints; capability gaps found here become
  backlog items for those tracks.

## 4. Tests & verification

- Deterministic replay test: same save + same input stream ⇒ bit-identical latents on fixed
  hardware/seed.
- Serialization round-trip tests (mechanics state, kv-cache, memory bank).
- Latency CI check: `bench_wm_speed.py` scenario asserting the shipped configuration meets the
  per-frame budget on the reference GPU.
- Sampler-distillation quality gates: automated M4/M5/M6 metric comparison vs teacher.
- `pixi run verify` green.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Distillation quality cliff below ~4 steps | Step-count/quality curve measured early in Phase B; 20fps target allows more steps if decode is cheap |
| kv-cache + memory bank serialization too large for save files | Compress/quantize context; measure; worst case persist mechanics state + short context tail and accept a warm-up |
| GC/Python overhead jitters the frame loop | Preallocated buffers, no per-frame allocation in the hot path; jitter percentiles in the budget table |
| Human eval reveals compounding drift under free play | Expected — that's the report's purpose; M5 memory config knobs are the first response |
| compile/quantization regressions under torch 2.8 pin | Metric gates per lever; each lever independently revertable |

## 6. Sequencing & effort

A (~1–2 weeks) → B (~3–4 weeks) → C (~2–3 weeks) → D (~2 weeks).

**Definition of done:** a human plays live at ≥20fps sustained on the reference GPU with the
mechanics loop authoritative; latency budget doc current; save/load + deterministic replay tested;
distilled sampler within quality epsilon on M4/M5/M6 metrics; human-eval report with
"breaks-first" analysis; `pixi run verify` green.
