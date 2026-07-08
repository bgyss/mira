"""mira.data: loaders for indexed game datasets.

Each sample bundles the perspectives of one match chunk; a clip is taken from within one chunk.

Public API:
    GameDataset, RocketScienceDataset, MatchClip — load time-aligned clips (random access / streaming)
    Index, MatchEntry, Perspective, Anchor — typed schema for the dataset index (`index.json`)
    KeyVocab, tensorize_actions — multi-hot keyboard action parsing
    Event — discrete game events with frame-index mapping
    GAME_REGISTRY — game-specific plug-in hooks

The `physics` and `viz` submodules are optional helpers over a clip's per-frame state: `physics` is
numpy-only, while `viz` needs the `viz` extra plus a system `ffmpeg` on PATH.
"""

import warnings

from .actions import KeyVocab, tensorize_actions
from .dataset import GameDataset, MatchClip, RocketScienceDataset
from .events import Event
from .games import GAME_REGISTRY
from .schema import Anchor, Index, MatchEntry, Perspective

__all__ = [
    "GameDataset",
    "RocketScienceDataset",
    "MatchClip",
    "Index",
    "MatchEntry",
    "Perspective",
    "Anchor",
    "KeyVocab",
    "tensorize_actions",
    "Event",
    "GAME_REGISTRY",
]


def __getattr__(name: str):
    if name == "DEFAULT_RL_KEYS":
        warnings.warn(
            "mira.data.DEFAULT_RL_KEYS is deprecated; use "
            "mira.data.games.rocket_league.keys.DEFAULT_RL_KEYS instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .games.rocket_league.keys import DEFAULT_RL_KEYS

        return DEFAULT_RL_KEYS
    if name == "replay_spans":
        warnings.warn(
            "mira.data.replay_spans is deprecated; use "
            "mira.data.games.rocket_league.events.replay_spans instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .events import replay_spans

        return replay_spans
    if name in {"Vec3", "Quat", "GameInfo", "BallState", "CarState", "FrameState"}:
        warnings.warn(
            f"mira.data.{name} is deprecated; use mira.data.games.rocket_league.state.{name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from .games.rocket_league import state

        return getattr(state, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
