# MIRA → Open-World RPG World Models: Milestones & Goal Prompts

Target experiences: Breath of the Wild / Tears of the Kingdom / Elden Ring — third-person
open-world action RPGs with analog control, huge diverse environments, persistent world state,
menus/UI, and long-horizon spatial memory requirements.

Each milestone lists: **Goal**, **Why it's ordered here**, **Deliverables**, and a **Goal Prompt**
you can hand directly to an agent/engineer to kick off the work.

---

## M0 — Decouple the library from Rocket League

**Goal:** Make `src/mira` game-agnostic. Extract RL-specific assumptions behind pluggable
interfaces so every later milestone is additive rather than a fork.

**Why first:** `data/physics.py`, `state.py`, `events.py`, `DEFAULT_RL_KEYS`, and the dataset
schema all hard-code Rocket League. Cheap to fix now, expensive after three games exist.

**Deliverables:**
- `GameSpec` abstraction: dataset schema v2 with per-game state/event payloads (typed, versioned),
  RL as the first implementation.
- Action vocabulary fully config-driven end to end (it mostly is — audit `n_keys` checkpoint
  pinning and the `REMOVED_CONFIG_FIELDS` tolerance path for vocab migration).
- Remove RL naming from generic code paths; `configs/dataset/rocket_league.yaml` becomes one
  instance of a documented dataset-config contract.
- `pixi run verify` green; all existing checkpoints still load.

**Goal Prompt:**
> Refactor MIRA so no module under `src/mira/{codec,world_model,ml,inference,training}` imports
> Rocket-League-specific symbols. Introduce a `GameSpec` (pydantic) that bundles: action config,
> per-frame state schema, event schema, and video parameters (fps, native size). Port the RL
> pipeline onto it with zero behavior change (existing checkpoints load, `pixi run verify` passes,
> training curves match on a smoke run). Document the new dataset-config contract in
> `configs/README.md`.

---

## M1 — Generalized action space (gamepad + continuous axes)

**Goal:** Extend `ActionTensors`/`ActionEncoder` to gamepad input: 2 analog sticks, 2 analog
triggers, ~16 buttons, plus camera control — while remaining backward compatible with the RL
keyboard vocab.

**Why here:** BotW/TotK/Elden Ring are analog-first; controllability of the world model is bounded
by action-representation fidelity. `ActionTensors` already carries `mouse_movements (B,T,2)` and a
NaN-masked sensitivity scalar, so the pattern (continuous channels + learned "absent" token)
exists — generalize it.

**Deliverables:**
- `ActionTensors` v2: multi-hot buttons + named continuous axes `(B, T, n_axes)` with per-axis
  presence masking (NaN → learned token, matching the existing mouse-sensitivity trick).
- Encoder changes + unit tests mirroring `tests/data`/`tests/world_model` conventions.
- Action-rate handling: 60Hz input streams downsampled to latent rate (extend the integer
  `downsampling_factor` contract; OR for buttons, mean/last for axes).
- RL checkpoints unaffected (axes all-masked ⇒ identical conditioning).

**Goal Prompt:**
> Extend MIRA's action pipeline to gamepad input. Add continuous axes (left/right stick x/y,
> L2/R2 triggers) and an expanded button vocabulary to `ActionConfig`/`ActionTensors`, with
> per-channel presence masking so keyboard-only RL data and gamepad RPG data share one encoder.
> Define the downsampling contract for continuous axes (buttons stay OR-over-window). Prove
> backward compatibility: an RL checkpoint produces bit-identical rollouts through the
> deterministic harness in `src/mira/inference/rollout.py`.

---

## M2 — RPG data capture & ingestion pipeline

**Goal:** A capture harness producing MIRA-format shards from real gameplay: synchronized video +
gamepad JSONL + metadata, starting with one game (Elden Ring on PC is the pragmatic first target —
native PC input capture; BotW/TotK require emulation and carry legal/ToS considerations to resolve
before committing).

**Deliverables:**
- Capture tool: fixed-fps video (30fps recommended) + per-frame gamepad state + session metadata,
  written as `(match, chunk)` WebDataset shards with `index.json` per the schema-v2 contract.
- Chunking policy for long sessions (RL uses ~4s/80-frame chunks; pick chunk length to support the
  M5 long-context work — e.g. 30–60s chunks with intra-chunk clip sampling).
- Scene/segment annotation pass: automatic detection of menus, loading screens, cutscenes, deaths,
  fast-travel (needed by M6); store as events on the shared clock like `events.py` does for goals.
- Target: 100+ hours for the first game before M4 training.

**Goal Prompt:**
> Build a gameplay capture pipeline for a PC action RPG: record video at a fixed fps with
> per-frame gamepad state (sticks, triggers, buttons) and write MIRA schema-v2 WebDataset shards
> with an `index.json`. Include an offline annotation pass that tags menu/loading/cutscene/death
> spans as events. Add a `configs/dataset/<game>.yaml` and validate end-to-end by loading shards
> through `RocketScienceDataset`-equivalent APIs and visualizing clips in the marimo browser.

---

## M3 — General-purpose codec (multi-domain RAEv2)

**Goal:** Retrain the frozen codec on visually diverse footage (RPG game + RL + optionally other
games) at higher resolution, so one latent space serves all downstream world models.

**Why here:** The DINOv3-L/16 backbone is already general; the strided-conv bottleneck and ViT
decoder were fit to RL's visual statistics. Open worlds (foliage, fog, HDR skies, text/HUD) will
stress reconstruction — expect to need more latent capacity and explicit HUD/text fidelity checks.

**Deliverables:**
- Codec trained on a mixed corpus; evaluate reconstruction (L1/LPIPS/DINO-consistency) per domain,
  with a dedicated HUD/text-legibility eval (health bars, damage numbers, menus).
- Resolution/fps decision recorded (e.g. 360p→480p @ 30fps) with a latency budget analysis against
  `scripts/bench_wm_speed.py` real-time targets.
- Ablation: latent channel count / temporal downsampling (td=1 vs td=2) vs. downstream rollout
  quality on a small world model.

**Goal Prompt:**
> Retrain the RAEv2 codec (`src/mira/codec`) on a mixed corpus of RPG and Rocket League footage.
> Sweep latent capacity and temporal downsampling; report per-domain L1/LPIPS/DINO-consistency
> plus a HUD-text legibility metric. Choose the resolution/fps operating point that keeps
> single-frame decode + one denoise window within the real-time budget measured by
> `scripts/bench_wm_speed.py`. Ship the winning checkpoint as the frozen codec for all M4+ work.

---

## M4 — First RPG world model (short-horizon control fidelity)

**Goal:** Train `LatentWorldModel` on one RPG with the M1 action space and M3 codec. Success is
*controllability*, not photorealism: stick deflection steers the character, camera responds to the
right stick, jump/attack/dodge produce the right animations, terrain is respected.

**Deliverables:**
- Training config `configs/model/...` + `configs/dataset/<game>.yaml` composition; runs via the
  existing Hydra entry point with only config-level changes (validates M0–M3).
- New controllability metrics in `training/metrics/`: action-swap tests (same context, different
  action ⇒ measurably different latents), stick-direction ↔ optical-flow agreement, and
  event-conditioned checks (attack input ⇒ attack animation onset).
- Qualitative rollout gallery across biomes/times-of-day.

**Goal Prompt:**
> Train MIRA's flow-matching world model on the captured RPG dataset using the general codec and
> gamepad action encoder. Add a controllability metric suite: (1) counterfactual action swaps must
> diverge rollouts, (2) left-stick direction must correlate with character motion flow, (3) button
> events must trigger the corresponding animation within k latent frames. Iterate on action
> conditioning strength (e.g. action-token dropout / CFG on actions) until the model passes
> thresholds on all three, and document the failure modes.

---

## M5 — Long-horizon memory & spatial consistency

**Goal:** The defining RPG challenge: leave an area, come back, and it's still the same area.
Extend context far beyond the current denoise window with an explicit memory mechanism.

**Deliverables:**
- Baseline measurement first: revisit-consistency metric (loop trajectories in the data; compare
  first-visit vs return-visit latents/pixels at matched poses) + long-rollout drift curves
  extending the existing `world_model_metrics.py` drift work.
- Architecture track (evaluate ≥2): (a) much longer kv-cache windows with chunked/sparse
  attention; (b) retrieval-augmented memory — store past latent frames keyed by
  estimated pose/visual similarity and cross-attend (WorldMem-style); (c) a compressed persistent
  state token bank updated recurrently. RoPE's lack of learned positional params helps (a).
- Training changes: longer chunks (from M2), curriculum from short to long rollouts,
  teacher-forced memory reads.

**Goal Prompt:**
> Give MIRA's world model long-horizon spatial memory. First build the eval: mine loop
> trajectories from the RPG dataset and implement a revisit-consistency metric plus 60s+ rollout
> drift curves. Then implement and compare (i) extended sparse-attention context and (ii) a
> retrieval memory of past latent frames with cross-attention reads, warm-starting both from the
> M4 checkpoint (mirror how `MultiWrapperWorldModel.load_state_dict` warm-starts across shapes).
> Report the consistency/compute Pareto frontier and ship the winner behind a config flag.

---

## M6 — Discrete state: menus, UI, cuts, and game-state conditioning

**Goal:** Handle the non-physics half of RPGs — inventory screens, dialog boxes, map/fast-travel,
death/respawn, loading transitions — and persistent scalar state (health, stamina, rupees/runes).

**Deliverables:**
- Event/segment conditioning: feed M2's menu/cutscene/death annotations as conditioning tokens so
  discontinuous transitions are modeled as *conditioned* rather than hallucinated.
- Persistent-state channel: a small structured-state vector (health, stamina, inventory hash,
  time-of-day) encoded alongside actions; evaluate whether the model keeps HUD values coherent
  across rollouts.
- Mode-switch fidelity metric: opening/closing a menu from the same context must produce the
  correct discrete transition.

**Goal Prompt:**
> Teach the world model discrete game-state transitions. Add segment-type conditioning tokens
> (gameplay/menu/cutscene/loading) from the dataset annotations, and a structured-state
> conditioning vector (HUD-extractable scalars) alongside the action stream. Build metrics for
> mode-switch correctness and HUD-value coherence over 30s rollouts. Decide and document whether
> menus are generated by the same model or delegated to a separate branch, based on results.

---

## M7 — Multi-game conditioning & transfer

**Goal:** One model, many games. Add a game-identity embedding, train jointly on RL + the RPG(s),
and measure cross-game transfer (does RL physics knowledge speed up Elden Ring convergence? does a
BotW-trained model few-shot to TotK?).

**Deliverables:**
- Game/domain embedding token + per-game action-config routing (union vocabulary with masking,
  building on M1's presence masks).
- Mixed-dataset loader respecting the existing grouping invariants; per-domain sampling weights.
- Transfer study: joint vs. per-game vs. finetune-from-joint, on equal compute. TotK-from-BotW is
  the flagship transfer experiment (shared engine/world, new mechanics).

**Goal Prompt:**
> Extend MIRA to joint multi-game training: add a game-identity conditioning token, a union action
> space with per-game channel masking, and a mixed WebDataset loader with per-domain weights.
> Run the transfer matrix (joint vs. single-game vs. finetune-from-joint at matched compute) and
> report per-game controllability (M4 metrics) and consistency (M5 metrics). Ship
> `configs/dataset/multi_game.yaml` and a written recommendation on the scaling recipe.

---

## M8 — Real-time interactive play

**Goal:** A human plays the generated RPG live: gamepad in, frames out, at ≥20fps with bounded
per-frame latency, using the streaming kv-cache + memory system.

**Deliverables:**
- Streaming inference server (extend `inference/rollout.py`'s streaming path): live action
  ingestion, per-frame denoise + decode, `torch.compile`/quantization/distillation as needed
  (note the pinned torch 2.8 — a step-distilled few-step sampler is likely the main lever, since
  the schedule already lives in `world_model/schedule.py`).
- Latency budget doc: encode/denoise/decode breakdown vs. the M3 operating point.
- Human eval protocol: task-based play sessions (reach a landmark, fight an enemy, open a menu)
  scored for control fidelity, coherence, and memory.

**Goal Prompt:**
> Build MIRA's interactive mode: a streaming inference loop that accepts live gamepad input and
> renders generated frames at ≥20fps end-to-end. Profile encode/denoise/decode with
> `scripts/bench_wm_speed.py`, then close the gap via few-step sampler distillation and compile
> tuning (respect the torch 2.8/torchcodec 0.7.0 pin). Deliver a local play client and a human
> evaluation protocol with task-based scenarios, and report where the experience breaks first.

---

## Cross-cutting workstreams (run alongside all milestones)

- **Evaluation:** every milestone adds metrics to `src/mira/training/metrics/` with tests; never
  ship a capability without its measurement.
- **Checkpoint compatibility:** follow the `REMOVED_CONFIG_FIELDS` discipline — old checkpoints
  fail loudly on genuine incompatibilities, load silently only for true no-ops.
- **Legal/data governance:** resolve capture ToS questions (especially console emulation for
  BotW/TotK) before M2 invests in those titles; Elden Ring PC capture for personal research is the
  lower-risk starting point.
- **Compute planning:** M3 (codec retrain), M5 (long context), and M7 (joint training) are the
  compute cliffs; sequence GPU budget accordingly.

## Suggested ordering & rough dependency graph

```
M0 → M1 → M2 → M3 → M4 → M5 → M7 → M8
                     └──→ M6 ──┘
```

M6 can start once M4's model exists; M5 and M6 merge into M7's joint model; M8 consumes everything.
