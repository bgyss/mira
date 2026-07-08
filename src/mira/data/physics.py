"""Deprecated Rocket League physics helpers.

Use :mod:`mira.data.games.rocket_league.physics` for game-specific helpers.
"""

import warnings

from .games.rocket_league.physics import *  # noqa: F401,F403

warnings.warn(
    "mira.data.physics is deprecated; use mira.data.games.rocket_league.physics instead.",
    DeprecationWarning,
    stacklevel=2,
)
