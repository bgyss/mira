"""Deprecated Rocket League frame-state types.

Use :mod:`mira.data.games.rocket_league.state` for game-specific state types.
"""

import warnings

from .games.rocket_league.state import *  # noqa: F401,F403

warnings.warn(
    "mira.data.state is deprecated; use mira.data.games.rocket_league.state instead.",
    DeprecationWarning,
    stacklevel=2,
)
