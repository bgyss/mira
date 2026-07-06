# M0 Refactor Plan — Decouple MIRA from Rocket League

**Objective:** every module under `src/mira/{codec,world_model,ml,inference,training}` is
game-agnostic; all Rocket-League-specific types, constants, and heuristics live behind a
`GameSpec` plug-in surface in `src/mira/data`, with RL as the first (and initially only)
implementation. **Zero behavior change**: existing checkpoints load, training curves match on a
smoke run, `pixi run verify` stays green.

## 0. Ground truth: where the coupling actually is (audit result)

Grep audit (`DEFAULT_RL_KEYS|[Rr]ocket`) shows the model stack is already almost clean — the
coupling is concentrated in `src/mira/data`:

| File | Coupling | Severity |
|---|---|---|
| `data/state.py` | `Vec3/Quat/GameInfo/BallState/CarState/FrameState` TypedDicts; RL arena coordinate docs | **Hard** — RL physics schema |
| `data/physics.py` | `ball_track`, `ball_moves`, `local_car`, `frozen_steps`, `step_badges`, `consistency_checks` — all RL semantics | **Hard** |
| `data/events.py` | `Event`, `parse_anchors`, `replay_spans` (goal-replay detection) | **Mixed** — `Event`/clock anchoring is generic; replay spans are RL |
| `data/actions.py` | `DEFAULT_RL_KEYS`, `KeyVocab.default()` → RL keys; keyboard-only `.jsonl` parsing contract | **Mixed** — parsing is generic, default vocab is RL |
| `data/schema.py` | `Anchor/Perspective/MatchEntry/Index` — docstring says RL but structure is generic (per-player mp4+jsonl+meta) | **Soft** — mostly naming/doc |
| `data/dataset.py` | `RocketScienceDataset`, `MatchClip`; `n_players=4` framing; `exclude_replays` plumbing into physics/events | **Mixed** |
| `data/training_loader.py` | imports `DEFAULT_RL_KEYS` as fallback (`create_loader(valid_keys=None)`); grouping invariant (contiguous player-ordered rows) is generic | **Soft** |
| `data/viz.py` | `_TEAM_COLORS` (blue/orange), `keystroke_timeline(keys=DEFAULT_RL_KEYS)` | **Soft** |
| `world_model/actions_config.py`, `layers/action_encoder.py` | RL only in docstrings/defaults (`source_fps=20` comment) | **Doc-only** |
| `mira/__init__.py`, `data/__init__.py` | "world model for Rocket League" naming, re-exports | **Doc-only** |
| `configs/` | `dataset/rocket_league.yaml`, `actions/rocket_league.yaml` — already per-game files; entry points reference them only via `defaults:` | **Already fine** |
| `tests/` | ~8 files construct RL fixtures directly | Update alongside |

Key insight: **`schema.py`'s Index/MatchEntry structure, the WebDataset (match, chunk) layout, the
clip/chunk contract, `ActionTensors`, and the loader grouping invariant are already generic.** M0
is mostly a *relocation + interface* job, not a redesign.

## 1. Target design: `GameSpec`

New module `src/mira/data/game_spec.py`:

```python
class GameSpec(BaseModel):
    """Everything game-specific the pipeline needs, bundled and versioned."""
    game_id: str                      # "rocket_league" — stable key, stored in dataset meta
    schema_version: int = 1
    action_config: ActionConfig       # existing type (valid_keys, source_fps, target_fps)
    video: VideoParams                # fps, native size — lifted from scattered config comments
    n_players_default: int = 1

    # Plug-in hooks (see §2 for signatures). Implemented per game via a registry,
    # not as methods on the pydantic model, so specs stay serializable.
```

Plus a registry:

```python
# src/mira/data/games/__init__.py
GAME_REGISTRY: dict[str, GamePlugin]   # "rocket_league" -> RocketLeaguePlugin

class GamePlugin(Protocol):
    spec: GameSpec
    def parse_frame_state(self, raw: dict) -> Mapping[str, Any]: ...     # replaces state.py TypedDicts as the pipeline-facing type
    def parse_events(self, anchors: list) -> list[Event]: ...           # events.py parse_anchors
    def exclusion_spans(self, events, fps, n_frames) -> list[Span]: ... # generalizes replay_spans/exclude_replays
    def quality_checks(self, clip) -> list[Check]: ...                  # physics.py consistency_checks / step_badges
    def viz_theme(self) -> VizTheme: ...                                # team colors, key layout for viz.py
```

Design rules:

- **Generic core, per-game leaves.** `Event`, `Check`, `Badge`, `Span`, `Index`, `MatchEntry`,
  `ActionTensors`, `KeyVocab` stay in generic modules. Anything mentioning balls, cars, goals,
  or arena coordinates moves to `src/mira/data/games/rocket_league/`.
- **The world model never sees `GameSpec` internals** — it continues to consume only
  `ActionConfig` + `VideoActionBatch`. `GameSpec` is a data-pipeline concept.
- **`game_id` written into dataset meta and checkpoints** (via the existing config snapshot), so
  later milestones can route per-game behavior; for M0 it's informational only.
- **Frame-state is opaque to the generic pipeline** (`Mapping[str, Any]` carried through
  `MatchClip`); only game plug-ins and per-game tooling interpret it. This avoids inventing a
  premature universal game-state schema — M6 will design conditioning-facing state properly.

## 2. Phased execution (each phase lands green and independently revertable)

### Phase A — Carve out the generic/RL split in `data/` (mechanical moves)

1. Create `src/mira/data/games/rocket_league/` and move, verbatim:
   - `physics.py` → `games/rocket_league/physics.py`
   - `state.py` → `games/rocket_league/state.py`
   - RL parts of `events.py` (`replay_spans`) → `games/rocket_league/events.py`;
     keep `Event`, `frame_index`, `events_in_frame_window`, `overlaps_any` in generic `events.py`.
   - `DEFAULT_RL_KEYS` → `games/rocket_league/keys.py`; keep `KeyVocab`, `tensorize_actions`
     generic. `KeyVocab.default()` loses its RL default — becomes explicit at call sites.
   - `_TEAM_COLORS` + RL key-layout bits of `viz.py` → `games/rocket_league/viz.py`; generic
     rendering (frame grids, timelines parameterized by `keys`) stays.
2. Leave deprecation re-exports in the old locations for one release
   (`from mira.data.games.rocket_league.physics import *  # noqa` + `DeprecationWarning`) so any
   external notebooks keep working; delete at end of M0.
3. Fix all internal imports; run `pixi run verify`.

**No logic changes in this phase.** Pure moves make the review diff trivial to audit.

### Phase B — Introduce `GameSpec` + registry, thread it through the loaders

1. Add `game_spec.py` + `games/__init__.py` registry with `RocketLeaguePlugin` implementing the
   Protocol by delegating to the Phase-A modules.
2. `dataset.py`:
   - Rename `RocketScienceDataset` → `GameDataset` (alias `RocketScienceDataset = GameDataset`
     kept as deprecated re-export; `from_hub` keeps its current repo defaults).
   - Constructor takes `game: str | GamePlugin = "rocket_league"` (default preserves behavior).
   - `exclude_replays: bool` → generalized `exclude_spans: bool` calling
     `plugin.exclusion_spans(...)`; keep `exclude_replays` as a deprecated kwarg alias.
3. `training_loader.py`:
   - `create_loader`'s `DEFAULT_RL_KEYS` fallback is replaced by
     `GAME_REGISTRY[game_id].spec.action_config` resolution; the Hydra path is unaffected because
     `configs/actions/rocket_league.yaml` already supplies `valid_keys` explicitly.
   - Document (in the module docstring + a test) the grouping invariant as a **generic contract**:
     "a group is `n_players` consecutive player-ordered rows" — no RL wording.
4. `schema.py`: doc rewrite only ("per-perspective media + action stream + meta"); add optional
   `game_id: str | None` and `schema_version: int = 1` fields to `Index` (default `None`/`1` so
   existing `index.json` files validate unchanged — pydantic optional-with-default is
   forward-compatible both ways).

### Phase C — Config & entry-point contract

1. Write the **dataset-config contract** into `configs/README.md`: required keys
   (`train_index`, `test_index`, `n_players`, `target_fps`, `frame_size`, `actions` sub-config,
   new optional `game: rocket_league`), and how `actions@actions` composition works.
2. `configs/dataset/rocket_league.yaml`: add `game: rocket_league`; scripts pass it through to
   `create_loader`. Default in code remains `rocket_league` so old configs (and old checkpoint
   config snapshots) resolve identically — this is the checkpoint-compat linchpin.
3. Checkpoint compatibility check: confirm the config snapshot loading path treats the new `game`
   key as *additive*. If any config model uses `extra="forbid"` on a block gaining a field, follow
   the existing discipline in `latent_world_model.py` (`drop_removed_fields` /
   `REMOVED_CONFIG_FIELDS`) — but inverted: new-field-with-old-default, which pydantic handles
   natively. Add an explicit test loading a pre-refactor checkpoint config snapshot
   (there's a fixture pattern in `tests/world_model/test_train_world_model_hydra.py`).

### Phase D — Naming & docs sweep (doc-only)

- `mira/__init__.py`: "a multiplayer world model for Rocket League" → "a real-time latent world
  model for interactive game experiences" (mention RL as the first supported game).
- `world_model/actions_config.py`, `layers/action_encoder.py`, `inference/rollout.py`,
  `data/training_loader.py`: rewrite docstrings to state contracts generically, moving RL
  specifics into "e.g. (Rocket League)" parentheticals or the RL plugin's docs.
- `CLAUDE.md` + `configs/README.md` + `scripts/README.md` updated to describe the
  `GameSpec`/registry architecture.

### Phase E — Tests & verification gate

1. **Move-following:** update the ~8 RL-referencing test files' imports; add
   `tests/data/games/rocket_league/` mirroring the new layout (repo convention: tests mirror
   `src/mira` package-by-package).
2. **New tests:**
   - `tests/data/test_game_spec.py`: registry resolution, unknown-game error, spec serialization
     round-trip, plugin Protocol conformance for RL.
   - Grouping-invariant contract test (generic, no RL fixtures).
   - Old-`index.json`-validates test (no `game_id` field).
   - Pre-refactor checkpoint config snapshot loads.
   - Deprecated aliases emit `DeprecationWarning` and behave identically.
3. **Behavioral equivalence (the "zero behavior change" proof):**
   - *Determinism anchor:* run `src/mira/inference/rollout.py`'s deterministic harness (fixed
     seed, `noise_level=0.0`, fixed schedule) on an existing checkpoint before and after the
     refactor — generated latents must be **bit-identical**.
   - *Loader equivalence:* hash the first N `VideoActionBatch`es from `create_loader` (fixed seed,
     `shuffle_buffer_size` fixed) pre/post refactor on a small local index.
   - *Smoke train:* ~200 steps of `train_world_model.py` pre/post; loss curves must overlay
     (wandb `mode=offline`).
4. `pixi run verify` (format + lint + typecheck + test) as the merge gate for every phase.

## 3. Explicit non-goals (deferred to later milestones)

- No new action channels or vocab changes (M1).
- No universal frame-state/conditioning schema — frame state stays opaque generic mapping (M6).
- No multi-game loader, no game-embedding token (M7).
- No changes to chunk length, clip sampling, or fps (M2/M3).
- No renaming of on-disk shard formats or `index.json` restructuring beyond additive fields.

## 4. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Hidden RL assumption in loader ordering/`n_players` framing breaks the multiplayer wrapper's `rearrange("(b p) ...")` | The grouping-invariant contract test in Phase B; run the multiplayer Hydra smoke test (`tests/world_model/test_train_world_model_hydra.py`) explicitly |
| Old checkpoints fail on new config keys | Additive-only config fields with defaults; dedicated snapshot-loading test in Phase C |
| External users import `RocketScienceDataset`/`DEFAULT_RL_KEYS` | One-release deprecation aliases with warnings |
| `from_hub` default repo semantics drift | Pin current behavior with a test before touching `dataset.py` |
| Typing regressions from moving TypedDicts (pyright strictness) | Phase A is verbatim moves; pyright in `pixi run verify` per phase |

## 5. Sequencing & effort

Phases are strictly ordered A→E but each lands independently. Rough sizing:

- **A** (moves + re-exports): ~½ day, large mechanical diff.
- **B** (GameSpec + threading): ~1 day, the substantive review.
- **C** (config contract + checkpoint compat): ~½ day.
- **D** (docs): ~2 hours.
- **E** (equivalence proofs): ~½–1 day, mostly running the harnesses; write the loader-hash and
  determinism scripts first so A–C can be checked incrementally rather than at the end.

**Definition of done:** grep for `[Rr]ocket|DEFAULT_RL_KEYS` returns hits only under
`src/mira/data/games/rocket_league/`, `configs/*/rocket_league.yaml`, tests of the RL plugin, and
deprecation shims; determinism anchor bit-identical; smoke-train curves overlay; `pixi run verify`
green; deprecation shims scheduled for deletion.
