"""What the engine gives back: Evaluation, Analysis, BadMove and Severity.

Scores are in centipawns: 100 centipawns is about one pawn.
"""
from dataclasses import dataclass
from enum import Enum

from jagvis_chess.model import Move

# The smallest loss (in centipawns) for each severity.
INACCURACY_LOSS = 50
MISTAKE_LOSS = 100
BLUNDER_LOSS = 300


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
