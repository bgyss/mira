"""Deprecated Rocket League visualization helpers.

Use :mod:`mira.data.games.rocket_league.viz` for game-specific rendering helpers.
"""

import warnings

from .games.rocket_league.viz import *  # noqa: F401,F403
from .games.rocket_league.viz import _TEAM_COLORS  # noqa: F401

warnings.warn(
    "mira.data.viz is deprecated; use mira.data.games.rocket_league.viz instead.",
    DeprecationWarning,
    stacklevel=2,
)
