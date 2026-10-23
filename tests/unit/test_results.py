import pytest

from jagvis_chess.model import Color, Move
from jagvis_chess.results import (
    Analysis,
    BadMove,
    Evaluation,
    Severity,
    move_accuracy,
    move_loss,
    severity_of,
    win_chance,
)

E4 = Move("e4", Color.WHITE)


@pytest.mark.parametrize(
    "loss, severity",
    [
        (-30, None),  # the move was better than expected
        (0, None),
        (49, None),
        (50, Severity.INACCURACY),
        (99, Severity.INACCURACY),
        (100, Severity.MISTAKE),
        (299, Severity.MISTAKE),
        (300, Severity.BLUNDER),
        (9999, Severity.BLUNDER),
    ],
)
def test_RES01_severity_from_the_loss_in_centipawns(loss, severity):
    assert severity_of(loss) == severity


def test_RES02_evaluation_without_mate():
    evaluation = Evaluation(best_move=E4, score=35)

    assert evaluation.best_move == E4
    assert evaluation.score == 35
    assert evaluation.mate_in is None


def test_RES03_a_bad_move_keeps_its_move_loss_and_severity():
    bad_move = BadMove(move=E4, loss=320, severity=Severity.BLUNDER)

    assert (bad_move.move, bad_move.loss, bad_move.severity) == (E4, 320, Severity.BLUNDER)


def test_RES03_a_negative_loss_is_refused():
    with pytest.raises(ValueError, match="The loss cannot be negative"):
        BadMove(move=E4, loss=-1, severity=Severity.INACCURACY)


@pytest.mark.parametrize("accuracy", [-0.1, 100.1])
def test_RES04_accuracy_is_a_percentage(accuracy):
    with pytest.raises(ValueError, match="between 0 and 100"):
        Analysis(accuracy=accuracy, bad_moves=[])


def test_RES04_summary_counts_bad_moves_by_severity():
    bad_moves = [
        BadMove(E4, 400, Severity.BLUNDER),
        BadMove(E4, 60, Severity.INACCURACY),
        BadMove(E4, 70, Severity.INACCURACY),
    ]

    summary = Analysis(accuracy=62.4, bad_moves=bad_moves).summary()

    assert summary == "Accuracy: 62 %. Blunders: 1, mistakes: 0, inaccuracies: 2."


def test_RES04_summary_without_bad_moves():
    assert Analysis(accuracy=100.0, bad_moves=[]).summary() == "Accuracy: 100 %. No bad moves, well done!"


@pytest.mark.parametrize(
    "before, after, loss",
    [
        (100, -100, 200),
        (0, -10000, 1000),  # scores are capped at 1000: a mate counts like +1000
        (2000, 1500, 0),  # still winning big: this is not a bad move
        (-50, 20, 0),  # the position got better: no loss
    ],
)
def test_RES05_loss_of_a_move_with_capped_scores(before, after, loss):
    assert move_loss(before, after) == loss


def test_RES06_win_chance_in_percent():
    assert win_chance(0) == 50
    assert win_chance(1000) > 97
    assert win_chance(-300) == pytest.approx(100 - win_chance(300))


@pytest.mark.parametrize(
    "before, after, low, high",
    [
        (0, 0, 99.9, 100),  # nothing lost: perfect move
        (30, 0, 80, 99.9),  # a tiny loss: still good
        (0, -10000, 0, 15),  # gives a mate: very bad
    ],
)
def test_RES07_accuracy_of_one_move(before, after, low, high):
    assert low <= move_accuracy(before, after) <= high
