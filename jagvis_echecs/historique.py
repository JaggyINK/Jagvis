"""Historique : une partie = un fichier JSON dans un dossier.

Format d'un fichier <id>.json :
{"id": "...", "date": "2026-10-23T14:05:00", "mode": "officiel",
 "couleur_joueur": "noir", "coups": [{"notation": "e4", "couleur": "blanc"}]}
"""
import json
import re
from datetime import datetime
from pathlib import Path

from jagvis_echecs.erreurs import (
    HistoriqueCorrompu,
    IdentifiantInvalide,
    JagvisErreur,
    PartieIntrouvable,
)
from jagvis_echecs.modele import Coup, Couleur, ModeJeu, Partie

# Lettres, chiffres, « _ » et « - » seulement : un identifiant comme
# « ../secret » ne peut pas sortir du dossier de l'historique.
IDENTIFIANT_VALIDE = re.compile(r"[A-Za-z0-9_-]{1,64}")


def verifier_identifiant(id):
    if not isinstance(id, str) or not IDENTIFIANT_VALIDE.fullmatch(id):
        raise IdentifiantInvalide(f"Identifiant de partie invalide : {id!r}")


def partie_vers_dict(partie):
    return {
        "id": partie.id,
        "date": partie.date.isoformat(),
        "mode": partie.mode.value,
        "couleur_joueur": partie.couleur_joueur.value,
        "coups": [{"notation": coup.notation, "couleur": coup.couleur.value} for coup in partie.coups],
    }


def partie_depuis_dict(donnees):
    coups = [Coup(coup["notation"], Couleur(coup["couleur"])) for coup in donnees["coups"]]
    return Partie(
        mode=ModeJeu(donnees["mode"]),
        couleur_joueur=Couleur(donnees["couleur_joueur"]),
        id=donnees["id"],
        date=datetime.fromisoformat(donnees["date"]),
        coups=coups,
    )


class Historique:
    def __init__(self, dossier):
        self.dossier = dossier
        Path(dossier).mkdir(parents=True, exist_ok=True)

    def _fichier(self, id):
        verifier_identifiant(id)
        return Path(self.dossier) / f"{id}.json"

    def sauvegarder(self, partie):
        texte = json.dumps(partie_vers_dict(partie), ensure_ascii=False, indent=2)
        self._fichier(partie.id).write_text(texte, encoding="utf-8")

    def charger(self, id):
        fichier = self._fichier(id)
        if not fichier.exists():
            raise PartieIntrouvable(f"Partie introuvable : {id}")
        try:
            return partie_depuis_dict(json.loads(fichier.read_text(encoding="utf-8")))
        except (ValueError, KeyError, TypeError, JagvisErreur) as erreur:
            raise HistoriqueCorrompu(f"Le fichier de la partie {id} est illisible.") from erreur

    def lister(self):
        parties = []
        for fichier in Path(self.dossier).glob("*.json"):
            try:
                parties.append(self.charger(fichier.stem))
            except (HistoriqueCorrompu, IdentifiantInvalide):
                continue  # un fichier abîmé ne doit pas empêcher de voir les autres
        return sorted(parties, key=lambda partie: partie.date)
