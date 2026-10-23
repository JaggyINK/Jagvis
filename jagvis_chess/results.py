"""What the engine gives back: Evaluation, Analysis, BadMove and Severity.

Scores are in centipawns: 100 centipawns is about one pawn.
"""
import math
from dataclasses import dataclass
from enum import Enum

from jagvis_chess.model import Move

# The smallest loss (in centipawns) for each severity.
INACCURACY_LOSS = 50
MISTAKE_LOSS = 100
BLUNDER_LOSS = 300
# Above +1000 (or under -1000) the game is already won (or lost): we stop counting.
SCORE_CAP = 1000


class Severity(Enum):
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


def severity_of(loss):
    """Sort a loss in centipawns. Under 50 it is not a bad move: we give None."""
    if loss >= BLUNDER_LOSS:
        return Severity.BLUNDER
    if loss >= MISTAKE_LOSS:
        return Severity.MISTAKE
    if loss >= INACCURACY_LOSS:
        return Severity.INACCURACY
    return None


def capped(score):
    return max(-SCORE_CAP, min(SCORE_CAP, score))


def move_loss(score_before, score_after):
    """Centipawns lost by a move. Both scores are seen by the player who moved."""
    return max(0, capped(score_before) - capped(score_after))


def win_chance(score):
    """Chance to win, in percent, for a score in centipawns (formula used by Lichess)."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * score)) - 1)


def move_accuracy(score_before, score_after):
    """Mark of one move from 0 to 100: the more win chance is lost, the lower (Lichess formula)."""
    drop = max(0, win_chance(capped(score_before)) - win_chance(capped(score_after)))
    mark = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0, min(100, mark))


@dataclass(frozen=True)
class Evaluation:
    """What the engine thinks of a position, seen by the side to play.

    mate_in is None when there is no forced mate. Positive: the side to play
    gives mate. Negative: the side to play gets mated.
    """

    best_move: Move
    score: int
    mate_in: int | None = None


@dataclass(frozen=True)
class BadMove:
    move: Move
    loss: int
    severity: Severity

    def __post_init__(self):
        if self.loss < 0:
            raise ValueError("The loss cannot be negative.")


@dataclass
class Analysis:
    accuracy: float
    bad_moves: list[BadMove]

    def __post_init__(self):
        if not 0 <= self.accuracy <= 100:
            raise ValueError("The accuracy must be between 0 and 100.")

    def summary(self):
        start = f"Accuracy: {self.accuracy:.0f} %."
        if not self.bad_moves:
            return f"{start} No bad moves, well done!"
        blunders = self._count(Severity.BLUNDER)
        mistakes = self._count(Severity.MISTAKE)
        inaccuracies = self._count(Severity.INACCURACY)
        return f"{start} Blunders: {blunders}, mistakes: {mistakes}, inaccuracies: {inaccuracies}."

    def _count(self, severity):
        return sum(1 for bad_move in self.bad_moves if bad_move.severity == severity)
