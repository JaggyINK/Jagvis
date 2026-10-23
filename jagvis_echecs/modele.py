"""Le jeu : Partie, Position, Coup et les énumérations du diagramme.

python-chess fait tout le travail de règles du jeu. Nos classes l'enveloppent
pour parler le vocabulaire du diagramme (en français).
"""
from dataclasses import dataclass
from enum import Enum

import chess

from jagvis_echecs.erreurs import FenInvalide


class Couleur(Enum):
    BLANC = "blanc"
    NOIR = "noir"


class ModeJeu(Enum):
    ENTRAINEMENT = "entrainement"
    AMICAL = "amical"
    OFFICIEL = "officiel"


@dataclass(frozen=True)
class Coup:
    """Un coup en notation algébrique (SAN), par exemple « e4 » ou « Nf3 »."""

    notation: str
    couleur: Couleur


def couleur_de(trait_python_chess):
    """python-chess note le trait True (Blancs) ou False (Noirs)."""
    return Couleur.BLANC if trait_python_chess == chess.WHITE else Couleur.NOIR


class Position:
    """Une position décrite par sa FEN. Le trait est lu dans la FEN."""

    def __init__(self, fen):
        try:
            plateau = chess.Board(fen)
        except ValueError as erreur:
            raise FenInvalide(f"FEN invalide : {fen}") from erreur
        # Board() accepte des positions impossibles (pas de roi...) : on les refuse.
        if not plateau.is_valid():
            raise FenInvalide(f"FEN invalide : {fen}")
        self.fen = fen
        self.trait = couleur_de(plateau.turn)

    def vers_plateau(self):
        """Renvoie un nouveau plateau python-chess pour cette position."""
        return chess.Board(self.fen)

    def coups_legaux(self):
        plateau = self.vers_plateau()
        return [Coup(plateau.san(coup), self.trait) for coup in plateau.legal_moves]

    def __eq__(self, autre):
        return isinstance(autre, Position) and self.fen == autre.fen

    def __repr__(self):
        return f"Position({self.fen!r})"
