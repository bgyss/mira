"""Game plug-in registry."""

from __future__ import annotations

from collections.abc import Mapping
from functools import cached_property
from typing import TYPE_CHECKING, Any

from ..events import Event, parse_anchors

if TYPE_CHECKING:
    from ..game_spec import GamePlugin, QualityCheck, VizTheme


class RocketLeaguePlugin:
    """Rocket League implementation of the dataset plug-in hooks."""

    @cached_property
    def spec(self):
        from mira.world_model.actions_config import ActionConfig

        from ..game_spec import GameSpec, VideoParams
        from .rocket_league.keys import DEFAULT_RL_KEYS

        return GameSpec(
            game_id="rocket_league",
            schema_version=1,
            action_config=ActionConfig(valid_keys=list(DEFAULT_RL_KEYS), source_fps=20, target_fps=10),
            video=VideoParams(fps=20),
            n_players_default=1,
        )

    def parse_frame_state(self, raw: dict[str, Any]) -> Mapping[str, Any]:
        return raw

    def parse_events(self, anchors: list[Any]) -> list[Event]:
        return parse_anchors(anchors)

    def exclusion_spans(
        self, events: list[Event], fps: float, recording_offset_sec: float, n_frames: int
    ) -> list[tuple[int, int]]:
        from .rocket_league.events import replay_spans

        return replay_spans(events, fps, recording_offset_sec, n_frames)

    def quality_checks(self, clip: Any) -> list["QualityCheck"]:
        return []

    def viz_theme(self) -> "VizTheme":
        from ..game_spec import VizTheme
        from .rocket_league.keys import DEFAULT_RL_KEYS
        from .rocket_league.viz import _TEAM_COLORS

        return VizTheme(team_colors=_TEAM_COLORS, key_layout=DEFAULT_RL_KEYS)


GAME_REGISTRY: dict[str, "GamePlugin"] = {"rocket_league": RocketLeaguePlugin()}


def resolve_game(game: str | "GamePlugin") -> "GamePlugin":
    if isinstance(game, str):
        try:
            return GAME_REGISTRY[game]
        except KeyError as err:
            raise ValueError(f"Unknown game {game!r}; available games: {sorted(GAME_REGISTRY)}") from err
    return game


__all__ = [
    "GAME_REGISTRY",
    "RocketLeaguePlugin",
    "resolve_game",
]
