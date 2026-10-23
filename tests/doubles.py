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


# --- Doubles des composants de Jarvis (tests unitaires de jarvis.py) ----------
# Tous écrivent dans le même « journal » : on peut vérifier l'ordre des appels.


class FausseReconnaissance:
    def __init__(self, positions=(), journal=None, panne=None):
        self.positions = list(positions)
        self.photos_recues = []
        self.panne = panne
        self.journal = journal if journal is not None else []

    def detecter_position(self, photo):
        self.journal.append("detecter_position")
        self.photos_recues.append(photo)
        if self.panne:
            raise self.panne
        return self.positions.pop(0)


class FauxMoteur:
    """Rejoue des évaluations dans l'ordre ; ensuite, renvoie toujours la dernière."""

    def __init__(self, evaluations=(), analyse=None, journal=None, panne=None):
        self.evaluations = list(evaluations)
        self.analyse = analyse
        self.panne = panne
        self.positions_evaluees = []
        self.parties_analysees = []
        self.journal = journal if journal is not None else []

    def evaluer(self, position):
        self.journal.append("evaluer")
        self.positions_evaluees.append(position)
        if self.panne:
            raise self.panne
        if len(self.evaluations) > 1:
            return self.evaluations.pop(0)
        return self.evaluations[0]

    def analyser(self, partie):
        self.journal.append("analyser")
        self.parties_analysees.append(partie)
        return self.analyse


class FauxAssistant:
    def __init__(self, texte="Explication du coach.", journal=None, panne=None):
        self.texte = texte
        self.panne = panne
        self.demandes = []
        self.journal = journal if journal is not None else []

    def expliquer(self, position, evaluation):
        self.journal.append("expliquer")
        self.demandes.append((position, evaluation))
        if self.panne:
            raise self.panne
        return self.texte


class FauxHistorique:
    def __init__(self, journal=None):
        self.parties = {}
        self.journal = journal if journal is not None else []

    def sauvegarder(self, partie):
        self.journal.append("sauvegarder")
        self.parties[partie.id] = partie

    def charger(self, id):
        return self.parties[id]

    def lister(self):
        return list(self.parties.values())


class FauxImportLichess:
    def __init__(self, partie=None, journal=None, panne=None):
        self.partie = partie
        self.panne = panne
        self.identifiants = []
        self.journal = journal if journal is not None else []

    def recuperer_partie(self, id):
        self.journal.append("recuperer_partie")
        self.identifiants.append(id)
        if self.panne:
            raise self.panne
        return self.partie
