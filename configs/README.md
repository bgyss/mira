# Hydra configs

Hydra YAML configuration for training and inference. Entry-point scripts under `scripts/` load
these via `@hydra.main(config_path="../configs")`, so any key can be overridden on the command line
as `key=value`.

```
configs/
  train_codec.yaml          # codec training (RAEv2 temporal-downsampling)
  train_world_model.yaml    # latent world-model training
  eval_world_model.yaml     # offline world-model evaluation
  model/                    # model architectures (codec, latent world model, multiplayer wrapper)
  dataset/                  # dataset source (train/test splits, game, n_players, target fps)
  actions/                  # action vocabulary and action sample rate
```

## Entry-point configs

- **`train_codec.yaml`** composes `model: raev2_codec_tdown` and `dataset: rocket_league`, plus the
  `run`, `wandb`, `dataloader`, `validation`, and `optim` blocks for codec reconstruction training.
- **`train_world_model.yaml`** composes `model: latent_world_model` and `dataset: rocket_league`,
  and adds a `world_model_metrics` block (rollout DINO/latent drift and Frechet curves) run every
  `validation.downstream_val_every`.
- **`eval_world_model.yaml`** is the offline-evaluation entry point. It carries only the
  `world_model_metrics` block; the checkpoint supplies its own model and dataset config, so this
  file just configures how the eval is run (set `checkpoint` and `output_dir` at eval time).

## `model/`

- **`raev2_codec_tdown.yaml`** — RAEv2 codec with 2× temporal downsampling: a frozen DINOv3-L/16
  backbone with layer aggregation and a strided-conv bottleneck feeding a ViT video decoder, with
  the L1 + LPIPS + DINO-latent-consistency loss weights.
- **`latent_world_model.yaml`** — single-player latent world model: a frozen codec (loaded from
  `codec_checkpoint`) plus an action-conditioned flow-matching diffusion transformer over the
  codec's latent grid.
- **`multi_wrapper_world_model.yaml`** — multiplayer world model: an inner `LatentWorldModel` that
  processes `n_players` per-player clips tiled into one vertically-stacked frame. A single-player
  checkpoint warm-starts into it via `run.finetune_from`.
- **`latent_world_model/1b.yaml`** — the 1B-parameter transformer size (hidden dim, heads, layers),
  selected by the package-override `latent_world_model@architecture.config: 1b`.

## `dataset/` and `actions/`

`dataset/rocket_league.yaml` points `train_index`/`test_index` at the local split directories (or
fetches them from the Hub) and sets `n_players` (1 for the codec, overridden to 4 for the
multiplayer world model) and `target_fps`. It pulls in the action vocabulary with
`/actions@actions: rocket_league`.

Dataset configs are expected to provide:

- `train_index` and `test_index`: split directories or explicit `index.json` paths.
- `game`: optional game plug-in id, defaulting to `rocket_league` for old configs.
- `n_players`: number of contiguous player-ordered perspectives per training group.
- `target_fps` and `frame_size`: decoded video sampling contract.
- `actions`: composed via `/actions@actions: ...`, with `valid_keys`, `source_fps`, and
  `target_fps`.

`actions/rocket_league.yaml` lists the 9-key release vocabulary and the action sample rate
`target_fps`. The loader uses the composed action config when present; otherwise it resolves
defaults from `mira.data.games.GAME_REGISTRY[dataset.game]`.

## Interpolation

Configs use Hydra/OmegaConf `${...}` interpolation to keep shared values in one place:

- `actions: ${dataset.actions}` lifts the dataset's action vocabulary to the top level for the
  loader.
- the top-level `run.compile` toggle threads into the codec's DINO compilation
  (`compile_dino: ${run.compile}`) and into the world-model metrics block (`compile: ${run.compile}`).
- the codec decoder reads encoder values it must match (e.g. `latent_dim: ${..encoder.latent_dim}`,
  `bottleneck.stride: ${...encoder.bottleneck.stride}`).

The world-model architecture size is selected via package-override syntax
(`latent_world_model@architecture.config`).
