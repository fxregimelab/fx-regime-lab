"""Operator accounting uses whole-thesis outcomes, not individual partial fills."""

import pytest

from src.paper.operator_score import ScoreEvent, replay_score


def test_asymmetric_rewards_and_calibration_are_separate() -> None:
    report = replay_score([
        ScoreEvent("t1", "model-a", "settlement", net_r=-1, probability=0.8, outcome=False),
        ScoreEvent("t2", "model-a", "settlement", net_r=1, probability=0.8, outcome=True),
    ])
    assert report.score == 98
    assert report.net_r == 0
    assert report.brier == pytest.approx(0.34)
    assert report.settled_trades == 2


def test_model_swap_does_not_reset_desk_score() -> None:
    report = replay_score([
        ScoreEvent("a", "model-a", "violation"),
        ScoreEvent("b", "model-b", "settlement", net_r=1),
    ])
    assert report.score == 84
    assert report.mode == "reduced"
    assert report.allowed_grades == ("A+", "A")
    assert report.slot_mult == 0.75


def test_profit_cannot_erase_unreviewed_process_breach() -> None:
    events = [ScoreEvent("v", "a", "violation")]
    events += [ScoreEvent(str(i), "a", "settlement", net_r=3) for i in range(10)]
    report = replay_score(events)
    assert report.score == 100
    assert report.mode == "reduced"  # Latch requires review, not a profitable gamble.


def test_pause_is_latched_until_external_remediation() -> None:
    events = [ScoreEvent(str(i), "a", "violation") for i in range(3)]
    events.append(ScoreEvent("win", "b", "settlement", net_r=3))
    report = replay_score(events)
    assert report.mode == "paused"
    assert report.slot_mult == 0


def test_duplicate_settlement_is_rejected_not_rewarded_twice() -> None:
    event = ScoreEvent("thesis-1", "a", "settlement", net_r=1)
    with pytest.raises(ValueError, match="Duplicate"):
        replay_score([event, event])


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_bad_outcome_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        replay_score([ScoreEvent("x", "a", "settlement", net_r=value)])


def test_no_trades_is_not_success_or_failure() -> None:
    report = replay_score([])
    assert report.brier is None
    assert report.net_r == 0
    assert report.settled_trades == 0
    assert report.score == 100


def test_probability_requires_a_predefined_binary_outcome() -> None:
    with pytest.raises(ValueError):
        replay_score([ScoreEvent("x", "a", "settlement", net_r=1, probability=0.7)])


def test_large_profit_and_loss_points_are_bounded() -> None:
    report = replay_score([
        ScoreEvent("loss", "a", "settlement", net_r=-100),
        ScoreEvent("win", "a", "settlement", net_r=100),
    ])
    assert report.score == 94  # -18 cap then +12 cap, not a reset to 100.
    assert report.mode == "full"
