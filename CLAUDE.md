# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MIRA is a real-time latent world model of Rocket League: a frozen video codec (RAEv2, built on a
DINOv3 backbone) feeds an action-conditioned flow-matching diffusion transformer that predicts the
next latent video frame autoregressively. `src/mira` is a library (`pip install mira[...]`);
`scripts/` holds the Hydra training/eval entry points; `configs/` holds the Hydra YAML.

## Commands

```bash
pixi run setup      # one-time: install mira + extras (GPU/CUDA torch)
pixi run setup-cpu  # same, CPU-only torch (no NVIDIA GPU on this machine)
pixi run test       # pytest -q
pixi run format      # ruff format src tests
pixi run lint        # ruff check src tests
pixi run typecheck   # pyright src tests
pixi run verify      # format + lint + typecheck + test (run this before considering work done)
pixi run explore     # marimo dataset browser (read-only)
pixi run edit        # marimo dataset browser (editable, headless :2718)
```

Single test / single file:

```bash
pixi run test tests/world_model/test_latent_world_model.py
pixi run test tests/world_model/test_latent_world_model.py::test_name -q
```

Training/eval scripts are Hydra apps (`@hydra.main(config_path="../configs")`) — override any
config key as `key=value` on the command line; multi-GPU runs go through `torchrun`.

```bash
python scripts/train_codec.py dataset.train_index=/path/to/train dataset.test_index=/path/to/test
python scripts/train_world_model.py model.architecture.config.codec_checkpoint=/path/to/codec_ckpt \
    dataset.train_index=/path/to/train dataset.test_index=/path/to/test
# 4-player, warm-started from a single-player checkpoint:
python scripts/train_world_model.py model=multi_wrapper_world_model dataset.n_players=4 \
    model.architecture.config.wm_config.codec_checkpoint=/path/to/codec_ckpt \
    run.finetune_from=/path/to/single_player_ckpt \
    dataset.train_index=/path/to/train dataset.test_index=/path/to/test
python scripts/eval_world_model_offline.py /path/to/checkpoint-1000/checkpoint.pth
```

Codec training needs the gated DINOv3-L/16 weights (`RS_DINO_WEIGHTS_DIR=/path/to/weights`);
world-model training/inference load the codec frozen from a checkpoint and don't need DINO weights.

torch/torchcodec are deliberately pinned (torch 2.8 + torchcodec 0.7.0 + FFmpeg 7) — see the header
comment in `pixi.toml` before touching that pin; newer torch breaks `torch.compile` on the codec
graph.

## Architecture

**Data pipeline** (`src/mira/data`): one WebDataset sample is one *(match, chunk)* — a ~4s window
(80 frames @ 20fps) bundling all 4 players' perspectives (`p{i}.mp4` + `p{i}.jsonl` + `meta.json`,
ordered by `player_id`). `schema.py` defines the `index.json` structure (`MatchEntry` per match,
used for random access); `dataset.py`'s `RocketScienceDataset` supports `load_match(...)` (random
access, reads only needed chunks) and `iter_clips(...)` (streaming, one chunk at a time). A *clip*
(fixed frame count, e.g. 16 @ 20fps) is always taken from within a single chunk — clips never span
chunk boundaries. `actions.py` tensorizes the 9-key `DEFAULT_RL_KEYS` vocabulary; `physics.py`/
`state.py` carry per-frame game state (ball, cars, score); `events.py` handles goals/boost pickups
etc. anchored to a shared match clock. `batch.py`'s `VideoActionBatch` is the collated training
batch shape. The data loader's grouping invariant: a match's 4 perspectives arrive contiguously and
player-id-ordered as `n_players` consecutive rows of the batch — several downstream components
(e.g. the multiplayer wrapper) rely on this to `rearrange("(b p) ... -> b p ...")`.

**Codec** (`src/mira/codec`): `VideoCodec` (RAEv2) — a frozen DINOv3-L/16 encoder with layer
aggregation feeds a strided-conv bottleneck, decoded back to pixels by a ViT video decoder
(`vit_decoder.py`). Trained with L1 + LPIPS + DINO-latent-consistency loss (`loss.py`). This codec
is trained once and then frozen for all world-model work.

**World model** (`src/mira/world_model`): `LatentWorldModel` (`latent_world_model.py`) loads a
frozen codec from a checkpoint, encodes video into its latent space, and trains a flow-matching
`DiffusionTransformer` to predict the next latent frame conditioned on actions (`ActionEncoder`,
RoPE positional encoding in `layers/rope.py` — no learned resolution-dependent positional params).
At inference it rolls out autoregressively with a streaming kv-cache (`schedule.py` builds the
inference noise schedule). `MultiWrapperWorldModel` (`multi_wrapper_world_model.py`) tiles
`n_players` per-player clips into one vertically-stacked frame and runs a single inner
`LatentWorldModel` over the tiled grid; because RoPE has no resolution-dependent learned weights, a
single-player checkpoint can warm-start directly into the tiled multiplayer model (see its
`load_state_dict`). Both expose the same surface (`config`, `codec`, `world_model`, `inference`,
`visualize`, ...), so the wrapper is a drop-in replacement in the trainer/metrics code.

**Config composition** (`configs/`, see `configs/README.md` for full detail): `train_codec.yaml`
and `train_world_model.yaml` are the Hydra entry-point configs, composing `model/` + `dataset/` +
`actions/` sub-configs plus `run`/`wandb`/`dataloader`/`validation`/`optim` blocks. Configs lean
heavily on OmegaConf `${...}` interpolation to keep shared values (e.g. latent dims, `run.compile`,
action vocab) defined once. World-model architecture *size* (not shape) is selected via Hydra
package-override syntax, e.g. `latent_world_model@architecture.config: 1b`.

**Training infra** (`src/mira/training`): `checkpoint_manager.py`/`checkpoints.py` handle save/load
(including the `REMOVED_CONFIG_FIELDS`-style tolerance for old checkpoints — see
`latent_world_model.py`'s `drop_removed_fields`, which only tolerates a removed field at its old
no-op value, not silently ignoring genuine uses), `distributed.py` for multi-GPU, `ema.py` for EMA
weights, `metrics/` for Frechet DINO/Inception and world-model rollout metrics (drift, downstream
Frechet curves), `tracker.py`/`visualization.py` for logging (wandb) and rollout visualizations.

## Notes for making changes

- When removing a config field that old checkpoints may still carry, add it to
  `REMOVED_CONFIG_FIELDS` (or the equivalent table) pinned to its old no-op value rather than
  loosening `extra="forbid"` — a checkpoint with a genuinely different value should still fail
  loudly.
- `tests/` mirrors `src/mira/` package-by-package (`tests/codec`, `tests/data`, `tests/world_model`,
  `tests/training`, `tests/ml`, `tests/inference`); most Hydra-config-loading behavior has a
  corresponding `test_*_hydra.py`.
