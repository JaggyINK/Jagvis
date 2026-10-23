"""ImportLichess : récupère une partie publique sur lichess.org au format PGN.

API utilisée : GET https://lichess.org/game/export/{id} (aucune clé nécessaire).
Le téléchargement est injectable : les tests ne font aucun appel réseau.
"""
import io
import re
import urllib.error
import urllib.request
from datetime import datetime

import chess.pgn

from jagvis_echecs.erreurs import IdentifiantInvalide, PartieIntrouvable, PgnInvalide, ServiceIndisponible
from jagvis_echecs.modele import Coup, Couleur, ModeJeu, Partie, couleur_de

URL_EXPORT = "https://lichess.org/game/export/{id}"
DELAI_SECONDES = 10
# 8 caractères pour la partie, ou 12 quand l'URL contient aussi le camp du joueur.
IDENTIFIANT_LICHESS = re.compile(r"[A-Za-z0-9]{8}([A-Za-z0-9]{4})?")


def telecharger_http(url, entetes):
    """Télécharge un texte et transforme les pannes en erreurs de Jarvis."""
    requete = urllib.request.Request(url, headers=entetes)
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_SECONDES) as reponse:
            return reponse.read().decode("utf-8")
    except urllib.error.HTTPError as erreur:
        if erreur.code == 404:
            raise PartieIntrouvable(f"Partie Lichess introuvable : {url}") from erreur
        if erreur.code == 429:
            raise ServiceIndisponible("Lichess limite les requêtes : réessaie dans une minute.") from erreur
        raise ServiceIndisponible(f"Lichess a répondu une erreur {erreur.code}.") from erreur
    except (urllib.error.URLError, TimeoutError) as erreur:
        raise ServiceIndisponible("Lichess est injoignable.") from erreur


def lire_date(entetes):
    """Lit UTCDate + UTCTime (« 2026.10.20 » et « 18:30:05 »). None si illisible."""
    texte = f"{entetes.get('UTCDate', '')} {entetes.get('UTCTime', '00:00:00')}"
    try:
        return datetime.strptime(texte, "%Y.%m.%d %H:%M:%S")
    except ValueError:
        return None


class ImportLichess:
    def __init__(self, token=None, telecharger=telecharger_http):
        self.token = token
        self.telecharger = telecharger

    def recuperer_partie(self, id):
        if not isinstance(id, str) or not IDENTIFIANT_LICHESS.fullmatch(id):
            raise IdentifiantInvalide(f"Identifiant Lichess invalide : {id!r}")
        id = id[:8]

        entetes = {"Accept": "application/x-chess-pgn"}
        if self.token:
            entetes["Authorization"] = f"Bearer {self.token}"
        texte = self.telecharger(URL_EXPORT.format(id=id), entetes)

        jeu = chess.pgn.read_game(io.StringIO(texte))
        if jeu is None or jeu.errors:
            raise PgnInvalide("La partie Lichess n'a pas pu être lue.")
        variante = jeu.headers.get("Variant", "Standard")
        if variante != "Standard":
            raise PgnInvalide(f"Variante non prise en charge : {variante}")

        plateau = jeu.board()
        coups = []
        for mouvement in jeu.mainline_moves():
            coups.append(Coup(plateau.san(mouvement), couleur_de(plateau.turn)))
            plateau.push(mouvement)
        if not coups:
            raise PgnInvalide("La partie Lichess ne contient aucun coup.")

        classee = "rated" in jeu.headers.get("Event", "").lower()
        return Partie(
            mode=ModeJeu.OFFICIEL if classee else ModeJeu.AMICAL,
            couleur_joueur=Couleur.BLANC,
            id=id,
            date=lire_date(jeu.headers),
            coups=coups,
        )
