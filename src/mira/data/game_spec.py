"""Game plug-in metadata and registry-facing protocols."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from mira.world_model.actions_config import ActionConfig

from .events import Event


class VideoParams(BaseModel):
    """Native video characteristics for a game dataset."""

    fps: int = 20
    frame_size: tuple[int, int] | None = None


class GameSpec(BaseModel):
    """Serializable description of a game integration."""

    model_config = ConfigDict(frozen=True)

    game_id: str
    schema_version: int = 1
    action_config: ActionConfig
    video: VideoParams = VideoParams()
    n_players_default: int = 1


@dataclass(frozen=True)
class VizTheme:
    """Optional visualization defaults exposed by a game plug-in."""

    team_colors: Mapping[int, tuple[int, int, int]]
    key_layout: tuple[str, ...]


@dataclass(frozen=True)
class QualityCheck:
    """A game-specific quality check result."""

    name: str
    ok: bool
    details: Mapping[str, Any] | None = None


class GamePlugin(Protocol):
    """Runtime hooks for game-specific dataset behavior."""

    spec: GameSpec

    def parse_frame_state(self, raw: dict[str, Any]) -> Mapping[str, Any]: ...

    def parse_events(self, anchors: list[Any]) -> list[Event]: ...

    def exclusion_spans(
        self, events: list[Event], fps: float, recording_offset_sec: float, n_frames: int
    ) -> list[tuple[int, int]]: ...

    def quality_checks(self, clip: Any) -> list[QualityCheck]: ...

    def viz_theme(self) -> VizTheme: ...
