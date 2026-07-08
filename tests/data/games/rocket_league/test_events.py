from mira.data.events import parse_anchors
from mira.data.games.rocket_league.events import replay_spans


def test_replay_spans_pairing_and_clamping():
    anchors = parse_anchors(
        [
            {"event_type": 3, "event_name": "GoalReplayStarted", "master_sec": 5.0},
            {"event_type": 4, "event_name": "GoalReplayEnded", "master_sec": 10.0},
            {"event_type": 3, "event_name": "GoalReplayStarted", "master_sec": 95.0},  # dangling
        ]
    )

    spans = replay_spans(anchors, fps=20, recording_offset_sec=0.0, n_frames=2000)

    assert spans[0] == (100, 200)
    assert spans[1] == (1900, 2000)  # dangling start extends to end
