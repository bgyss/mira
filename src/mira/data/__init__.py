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

from .actions import DEFAULT_RL_KEYS, KeyVocab, tensorize_actions
from .dataset import GameDataset, MatchClip, RocketScienceDataset
from .events import Event, replay_spans
from .games import GAME_REGISTRY
from .schema import Anchor, Index, MatchEntry, Perspective
from .state import BallState, CarState, FrameState, GameInfo, Quat, Vec3

__all__ = [
    "GameDataset",
    "RocketScienceDataset",
    "MatchClip",
    "Index",
    "MatchEntry",
    "Perspective",
    "Anchor",
    "Vec3",
    "Quat",
    "GameInfo",
    "BallState",
    "CarState",
    "FrameState",
    "KeyVocab",
    "DEFAULT_RL_KEYS",
    "tensorize_actions",
    "Event",
    "replay_spans",
    "GAME_REGISTRY",
]
