# M1 — Generalized Action Space (Gamepad + Continuous Axes)

**Objective:** extend `ActionConfig`/`ActionTensors`/`ActionEncoder` to gamepad input — 2 analog
sticks, 2 analog triggers, an expanded button vocabulary — while keeping keyboard-only Rocket
League data and existing checkpoints working **bit-identically**.

## 0. Context & prerequisites

- **Depends on:** M0 (game-agnostic data layer; `GameSpec` carries `ActionConfig`).
- Ground truth in the code today:
  - `ActionTensors` (`src/mira/world_model/actions_config.py`) holds `key_presses (B,T,n_keys)`
    int32 multi-hot, `mouse_movements (B,T,2)` float32, and `game_mouse_sensitivity (B,)` float32
    with **NaN = "unknown"**, which `ActionEncoder` masks to a learned token
    (`nan_to_num` + `torch.where`). This is the presence-masking pattern to generalize.
  - `ActionEncoder` (`src/mira/world_model/layers/action_encoder.py`) embeds each key with its own
    `nn.Embedding(2, k)`, symlog-normalizes mouse deltas, temporally pools by
    `temporal_downsampling`, and prepends a learned initial-action token. It also has per-player
    subset-key dropout with `_WARMSTART_EXEMPT` params.
  - `tensorize_actions` (`src/mira/data/actions.py`) parses JSONL to multi-hot with **OR over the
    integer downsampling window** (`ActionConfig.downsampling_factor`, integer-only, upsampling
    rejected).
  - Checkpoints pin `n_keys` via the saved `ActionConfig`; the `REMOVED_CONFIG_FIELDS` discipline
    in `latent_world_model.py` governs config evolution.

## 1. Design

### 1.1 `ActionConfig` v2 (additive fields, old defaults = no-op)

```python
class AxisSpec(BaseModel):
    name: str                 # "lstick_x", "lstick_y", "rstick_x", "rstick_y", "l2", "r2", ...
    low: float = -1.0
    high: float = 1.0
    pool: Literal["mean", "last"] = "mean"   # per-axis downsampling reducer

class ActionConfig(BaseModel):
    valid_keys: list[str]                    # unchanged; now "buttons" for gamepads
    source_fps: int = 20
    target_fps: int = 10
    axes: list[AxisSpec] = []                # NEW; [] == keyboard-only == today's behavior
```

`axes=[]` must serialize/deserialize identically to today's configs so **old checkpoint config
snapshots load unchanged** (pydantic default-with-new-field, same trick as M0 Phase C).

### 1.2 `ActionTensors` v2

- New tensor `axis_values: (B, T, n_axes)` float32, **NaN = channel absent for this sample**
  (per-sample, per-channel presence — the generalization of the mouse-sensitivity trick).
- `n_axes = len(config.axes)`; keyboard-only data constructs `(B, T, 0)`.
- All container ops (`slice_time`, `slice_batch`, `cat_time`, `stack_action_tensors`, `to`,
  `pin_memory`, `clone`, `__repr__`) extended mechanically.
- `mouse_movements`/`game_mouse_sensitivity` are **kept as-is** (not migrated into axes) to avoid
  touching the RL checkpoint contract; migrating mouse into the axes framework is an explicit
  non-goal (revisit in M7 if the union action space needs it).

### 1.3 Encoder changes

- New `axes_mlp: Linear(n_axes, axis_dim)` branch with a learned per-axis absent-token, mirroring
  the sensitivity path: `mask = isnan(axis_values)`, `nan_to_num`, embed, `where(mask, token_row,
  embed)` — masking happens **per channel before the MLP mixes channels** (embed each axis to a
  small vector then concat, exactly like the per-key keyboard embeddings, so an absent axis
  contributes only its learned token).
- When `n_axes == 0` the branch is **not constructed** (no unused params — DDP aborts on those;
  see the `keyboard_dropout_token` precedent). This is what makes RL checkpoints load with zero
  `state_dict` diff.
- Dimension budget: today `dim` splits mouse/keyboard 50/50. With axes present, split three ways
  (`dim//4` axes, `dim//4` mouse, rest keyboard) — but **only when axes exist**, so the RL
  topology is untouched.
- Action dropout (CFG-style) extends to the axes branch: a dropped row replaces its axis embedding
  with the absent tokens.

### 1.4 Downsampling contract (60Hz input → latent rate)

- Buttons: **OR over the window** (unchanged, `tensorize_actions`).
- Axes: per-axis reducer from `AxisSpec.pool` — `mean` for sticks/triggers (default), `last`
  available for anything where the end-of-window value matters.
- Keep the integer-stride contract (`source_fps % target_fps == 0`); a 60Hz→10fps stream is
  stride 6. Non-integer rates are still rejected loudly.
- New `tensorize_axes(lines, axes, source_fps, target_fps, keep_last_partial)` alongside
  `tensorize_actions`, sharing `compute_stride` so frames/buttons/axes stay aligned.

### 1.5 JSONL capture format extension (consumed by M2)

Each line gains an optional `"axes": {"lstick_x": -0.42, ...}` object. Absent key ⇒ NaN for that
axis that frame (absent the whole clip ⇒ all-NaN ⇒ learned token). Document this in the
dataset-config contract section of `configs/README.md`.

## 2. Phased execution

### Phase A — Containers & parsing (no model changes)

1. `AxisSpec` + `ActionConfig.axes`; extend `ActionTensors` per §1.2.
2. `tensorize_axes` in `src/mira/data/actions.py`; loader (`training_loader.py`) fills
   `axis_values` (all-NaN `(B,T,0)`→`(B,T,n_axes)` depending on config).
3. Tests (see §4). `pixi run verify` green; **no encoder change yet** — RL path constructs
   `(B,T,0)` axes and everything downstream ignores them.

### Phase B — Encoder axes branch

1. Add the axes branch per §1.3, constructed only when `n_axes > 0`.
2. Thread `n_axes`/axis names from `ActionConfig` through the world-model config to the encoder
   (same route `valid_keys`/`key_field_names` takes today).
3. Prove state-dict equivalence: `n_axes == 0` encoder has **exactly** today's parameter set.

### Phase C — Backward-compatibility proof

1. Load an existing RL checkpoint; run the deterministic harness in
   `src/mira/inference/rollout.py` (fixed seed, `noise_level=0.0`) pre/post — latents
   **bit-identical**.
2. Old checkpoint config snapshot (no `axes` field) loads; add a snapshot fixture test.
3. Smoke train ~200 steps on RL data pre/post; loss curves overlay.

### Phase D — Synthetic gamepad end-to-end

1. Build a tiny synthetic gamepad dataset fixture (random axes + buttons JSONL) under
   `tests/data/fixtures/`; run a 2-layer world-model forward/backward through the full
   loader→encoder→DiT path.
2. Sanity: axis perturbation changes the conditioning embedding; all-NaN axis column reproduces
   the absent token exactly.

## 3. Non-goals

- No union multi-game vocabulary or per-game channel routing (M7).
- No mouse-to-axes migration (see §1.2).
- No capture tooling (M2) and no real gamepad data training (M4).
- No changes to `mouse_movements` semantics, chunk length, or fps.

## 4. Tests & verification

Mirror `tests/data` / `tests/world_model` conventions:

- `tests/world_model/test_actions_config.py`: axes container ops (slice/cat/stack with axes;
  mixed-presence NaN semantics; `(B,T,0)` degenerate case).
- `tests/data/test_actions.py`: `tensorize_axes` mean/last pooling, stride alignment with
  `tensorize_actions`, `keep_last_partial`, absent-axis→NaN.
- `tests/world_model/test_action_encoder.py`: finite embeddings/grads with all-NaN axes
  (mirrors the existing all-NaN-sensitivity tests); `n_axes==0` param topology identical to
  legacy; dropout covers axes branch; per-player dropout still warm-start exempt.
- Checkpoint compat: pre-M1 config snapshot loads; deterministic-rollout bit-identity script
  (write it in Phase A so B/C can be checked incrementally).
- `pixi run verify` as the merge gate per phase.

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Hidden `state_dict` diff for RL checkpoints (new unused params) | Construct axes branch only when `n_axes > 0`; explicit param-topology test |
| `ActionConfig` equality checks (`cat_time`, `stack_action_tensors` assert `config ==`) break on mixed configs | Axes are part of config; mixing keyboard+gamepad in one batch is out of scope until M7 — assert loudly |
| Axis normalization mismatch across games (stick range, deadzone) | `AxisSpec.low/high` normalization at tensorize time; deadzones handled in capture (M2), not the encoder |
| `torch.compile` graph break from data-dependent axes branch | Branch decided at construction, not per-forward; no dynamic control flow on tensor values |
| DDP unused-parameter abort | Same discipline as `keyboard_dropout_token`: never construct params that a config can leave unused |

## 6. Sequencing & effort

A (~1 day) → B (~1 day) → C (~½ day, mostly harness runs) → D (~½ day). Write the determinism
script first.

**Definition of done:** gamepad axes flow JSONL→`ActionTensors`→encoder→DiT on a synthetic
fixture; RL checkpoint rollouts bit-identical; old config snapshots load; `n_axes==0` encoder
param-topology unchanged; downsampling contract documented in `configs/README.md`;
`pixi run verify` green.
