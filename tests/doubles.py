"""Doubles de test écrits à la main.

Aucun ne fait d'appel réseau ni ne lance Stockfish. Chacun enregistre ce qu'il
reçoit, pour que les tests vérifient les effets plutôt que des détails internes.
"""
from types import SimpleNamespace

import chess
import chess.engine

# De faux octets qui commencent comme un vrai fichier PNG.
PHOTO_PNG = b"\x89PNG\r\n\x1a\n" + b"fausse image"


class FauxClientGroq:
    """Imite groq.Groq : client.chat.completions.create(...) rejoue des réponses.

    Une réponse peut être un texte, ou une exception à lever.
    """

    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.appels = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **parametres):
        self.appels.append(parametres)
        reponse = self.reponses.pop(0)
        if isinstance(reponse, Exception):
            raise reponse
        message = SimpleNamespace(content=reponse)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FauxMoteurUCI:
    """Imite chess.engine.SimpleEngine (le processus Stockfish).

    Les scores sont donnés du point de vue des Blancs, par placement des pièces
    (la première partie de la FEN).
    """

    def __init__(self, scores=None, mats=None, meilleurs=None):
        self.scores = scores or {}
        self.mats = mats or {}
        self.meilleurs = meilleurs or {}
        self.positions_analysees = []
        self.chemins_ouverts = []
        self.limites = []
        self.ferme = False

    def ouvrir(self, chemin):
        self.chemins_ouverts.append(chemin)
        return self

    def analyse(self, plateau, limite):
        self.positions_analysees.append(plateau.fen())
        self.limites.append(limite)
        cle = plateau.board_fen()
        if cle in self.mats:
            score = chess.engine.PovScore(chess.engine.Mate(self.mats[cle]), chess.WHITE)
        else:
            score = chess.engine.PovScore(chess.engine.Cp(self.scores.get(cle, 0)), chess.WHITE)
        if cle in self.meilleurs:
            meilleur = chess.Move.from_uci(self.meilleurs[cle])
        else:
            meilleur = next(iter(plateau.legal_moves))
        return {"score": score, "pv": [meilleur]}

    def quit(self):
        self.ferme = True


class FausseLunettes:
    """Remplace les lunettes : photos préparées à l'avance, paroles enregistrées."""

    def __init__(self, photos=(), journal=None, paroles_entendues=()):
        self.photos = list(photos)
        self.paroles_entendues = list(paroles_entendues)
        self.paroles = []
        self.affichages = []
        self.journal = journal if journal is not None else []

    def prendre_photo(self):
        self.journal.append("prendre_photo")
        return self.photos.pop(0)

    def ecouter(self):
        self.journal.append("ecouter")
        return self.paroles_entendues.pop(0)

    def parler(self, texte):
        self.journal.append("parler")
        self.paroles.append(texte)

    def afficher(self, texte):
        self.journal.append("afficher")
        self.affichages.append(texte)
