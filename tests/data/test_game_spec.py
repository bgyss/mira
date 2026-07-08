from __future__ import annotations

import pytest

import mira.data as data_api
import mira.data.actions as actions_api
from mira.data.dataset import GameDataset, RocketScienceDataset
from mira.data.events import replay_spans
from mira.data.game_spec import GamePlugin, GameSpec
from mira.data.games import GAME_REGISTRY, resolve_game
from mira.data.games.rocket_league.keys import DEFAULT_RL_KEYS


def test_registry_resolves_rocket_league_plugin():
    plugin = resolve_game("rocket_league")

    assert plugin is GAME_REGISTRY["rocket_league"]
    assert plugin.spec.game_id == "rocket_league"
    assert plugin.spec.schema_version == 1
    assert plugin.spec.action_config.valid_keys


def test_unknown_game_error_lists_available_games():
    with pytest.raises(ValueError, match="rocket_league"):
        resolve_game("unknown")


def test_game_spec_serialization_round_trip():
    spec = resolve_game("rocket_league").spec

    restored = GameSpec.model_validate(spec.model_dump())

    assert restored == spec


def test_rocket_league_plugin_matches_protocol():
    plugin: GamePlugin = resolve_game("rocket_league")

    assert plugin.parse_events([]) == []
    assert plugin.exclusion_spans([], fps=20, recording_offset_sec=0.0, n_frames=10) == []


def test_deprecated_dataset_alias_warns(tmp_path):
    (tmp_path / "index.json").write_text('{"total_samples": 0, "entries": []}')

    with pytest.warns(DeprecationWarning, match="GameDataset"):
        ds = RocketScienceDataset.from_local(tmp_path)

    assert isinstance(ds, GameDataset)


def test_deprecated_replay_spans_warns():
    with pytest.warns(DeprecationWarning, match="rocket_league"):
        assert replay_spans([], fps=20, recording_offset_sec=0.0, n_frames=10) == []


def test_deprecated_key_reexports_warn():
    with pytest.warns(DeprecationWarning, match="DEFAULT_RL_KEYS"):
        assert actions_api.DEFAULT_RL_KEYS == DEFAULT_RL_KEYS
    with pytest.warns(DeprecationWarning, match="DEFAULT_RL_KEYS"):
        assert data_api.DEFAULT_RL_KEYS == DEFAULT_RL_KEYS
