import math
from dataclasses import dataclass
from enum import Enum

from jagvis_chess.model import Move

# Les scores sont en centipions : 100 = environ un pion.
INACCURACY_LOSS = 50
MISTAKE_LOSS = 100
BLUNDER_LOSS = 300
SCORE_CAP = 1000  # au-delà de +1000, la partie est déjà gagnée


class Severity(Enum):
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


def severity_of(loss):
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
    # Les deux scores sont vus par le joueur qui a joué le coup.
    return max(0, capped(score_before) - capped(score_after))


# Les deux formules ci-dessous viennent de Lichess.
def win_chance(score):
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * score)) - 1)


def move_accuracy(score_before, score_after):
    drop = max(0, win_chance(capped(score_before)) - win_chance(capped(score_after)))
    accuracy = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0, min(100, accuracy))


@dataclass(frozen=True)
class Evaluation:
    best_move: Move
    score: int  # vu par le camp qui doit jouer
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
