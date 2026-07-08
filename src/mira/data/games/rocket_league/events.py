"""Rocket League event helpers."""

from __future__ import annotations

from ...events import Event

REPLAY_START = "GoalReplayStarted"
REPLAY_END = "GoalReplayEnded"


def replay_spans(
    events: list[Event], fps: float, recording_offset_sec: float, n_frames: int
) -> list[tuple[int, int]]:
    """Frame-index [start, end) spans covering goal-replay segments."""
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for e in sorted(events, key=lambda x: x.master_sec):
        f = e.frame_index(fps, recording_offset_sec)
        if e.event_name == REPLAY_START:
            start = f
        elif e.event_name == REPLAY_END and start is not None:
            lo, hi = max(0, min(start, f)), min(n_frames, max(start, f))
            if hi > lo:
                spans.append((lo, hi))
            start = None
    if start is not None:
        lo = max(0, min(start, n_frames))
        if n_frames > lo:
            spans.append((lo, n_frames))
    return spans
