"""Les erreurs prévues de Jarvis Échecs.

Toutes héritent de JagvisErreur : l'interface n'a qu'une seule exception à
attraper pour montrer un message clair au joueur, sans trace d'exception.
"""


class JagvisErreur(Exception):
    """Erreur prévue : son message peut être montré tel quel au joueur."""


class FenInvalide(JagvisErreur):
    """La FEN ne décrit pas une position d'échecs valide."""


class CoupIllegal(JagvisErreur):
    """Le coup n'est pas jouable dans la position."""


class PartieTerminee(JagvisErreur):
    """On essaie de jouer ou d'évaluer alors que la partie est finie."""


class AucunePartie(JagvisErreur):
    """Jarvis n'a pas de partie en cours."""


class ActionInterdite(JagvisErreur):
    """Action refusée par une règle du jeu (tour de jeu, mode officiel...)."""


class IdentifiantInvalide(JagvisErreur):
    """Identifiant de partie mal formé (protège aussi le dossier de l'historique)."""


class PartieIntrouvable(JagvisErreur):
    """Aucune partie ne porte cet identifiant."""


class HistoriqueCorrompu(JagvisErreur):
    """Le fichier JSON d'une partie est illisible."""


class PgnInvalide(JagvisErreur):
    """Le PGN reçu ne peut pas être transformé en partie."""


class PhotoInvalide(JagvisErreur):
    """La photo est vide, trop grosse, introuvable ou dans un format inconnu."""


class ReconnaissanceImpossible(JagvisErreur):
    """Le modèle de vision n'a pas trouvé de position valide sur la photo."""


class ServiceIndisponible(JagvisErreur):
    """Un service externe (Groq, Stockfish, Lichess) ne répond pas."""


class ConfigurationInvalide(JagvisErreur):
    """Il manque un réglage (clé API, chemin...) ou il est incorrect."""
