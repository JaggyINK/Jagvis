"""Le jeu : Partie, Position, Coup et les énumérations du diagramme.

python-chess fait tout le travail de règles du jeu. Nos classes l'enveloppent
pour parler le vocabulaire du diagramme (en français).
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import chess
import chess.pgn

from jagvis_echecs.erreurs import CoupIllegal, FenInvalide, PartieTerminee


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


class Partie:
    """Une partie, rejouée à partir de la position de départ et de ses coups."""

    def __init__(self, mode, couleur_joueur, id=None, date=None, coups=()):
        if not isinstance(mode, ModeJeu):
            raise TypeError(f"mode doit être un ModeJeu, pas {mode!r}")
        if not isinstance(couleur_joueur, Couleur):
            raise TypeError(f"couleur_joueur doit être une Couleur, pas {couleur_joueur!r}")
        self.id = id or uuid.uuid4().hex[:12]
        self.date = date or datetime.now()
        self.mode = mode
        self.couleur_joueur = couleur_joueur
        self.coups = []
        # On rejoue les coups reçus un par un : un coup faux lève CoupIllegal.
        for coup in coups:
            self.jouer(coup)

    def _plateau(self):
        plateau = chess.Board()
        for coup in self.coups:
            plateau.push_san(coup.notation)
        return plateau

    def jouer(self, coup):
        plateau = self._plateau()
        if plateau.is_game_over():
            raise PartieTerminee("La partie est terminée.")
        if coup.couleur != couleur_de(plateau.turn):
            raise CoupIllegal(f"Ce n'est pas aux {coup.couleur.value}s de jouer.")
        try:
            mouvement = plateau.parse_san(coup.notation)
        except ValueError as erreur:
            raise CoupIllegal(f"Coup illégal : {coup.notation}") from erreur
        # On garde la notation officielle (« Qh4# » même si on a reçu « Qh4 »).
        self.coups.append(Coup(plateau.san(mouvement), coup.couleur))

    def position_actuelle(self):
        return Position(self._plateau().fen())

    def peut_conseiller(self):
        """Règle fair-play : aucune aide pendant une partie officielle."""
        return self.mode != ModeJeu.OFFICIEL

    def est_terminee(self):
        return self._plateau().is_game_over()

    def vers_pgn(self):
        jeu = chess.pgn.Game.from_board(self._plateau())
        jeu.headers["Event"] = f"Jarvis Échecs ({self.mode.value})"
        jeu.headers["Date"] = self.date.strftime("%Y.%m.%d")
        if self.couleur_joueur == Couleur.BLANC:
            jeu.headers["White"], jeu.headers["Black"] = "Joueur", "Adversaire"
        else:
            jeu.headers["White"], jeu.headers["Black"] = "Adversaire", "Joueur"
        return str(jeu)
