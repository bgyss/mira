# Entry-point scripts

Hydra applications for training, evaluation, and serving. Each reads its config from `configs/`
(override any key as `key=value`) and runs single-GPU, or multi-GPU under `torchrun`.

- `train_codec.py` — train the video codec.
- `train_world_model.py` — train the world model (single-player, or add
  `model=multi_wrapper_world_model dataset.n_players=4` for 4-player).
- `eval_world_model_offline.py` — offline evaluation of a trained world model (validation loss +
  rollout metrics) from a checkpoint.
- `bench_wm_speed.py` — micro-benchmark world-model rollout speed.

Dataset-specific behavior is routed through `mira.data.games.GAME_REGISTRY`. Current configs use
`dataset.game=rocket_league`; older configs without that key still resolve to Rocket League.

See [`configs/README.md`](../configs/README.md) for the config layout and the top-level
[`README.md`](../README.md) for example commands.
