"""Les résultats du moteur : Evaluation, Analyse, Erreur et Gravite.

Les scores sont en centipions : 100 centipions valent à peu près un pion.
"""
from dataclasses import dataclass
from enum import Enum

from jagvis_echecs.modele import Coup

# Perte minimale (en centipions) pour chaque gravité.
SEUIL_IMPRECISION = 50
SEUIL_ERREUR = 100
SEUIL_GAFFE = 300


class Gravite(Enum):
    IMPRECISION = "imprécision"
    ERREUR = "erreur"
    GAFFE = "gaffe"


def gravite_pour_perte(perte):
    """Classe une perte en centipions. Sous 50, ce n'est pas une erreur : None."""
    if perte >= SEUIL_GAFFE:
        return Gravite.GAFFE
    if perte >= SEUIL_ERREUR:
        return Gravite.ERREUR
    if perte >= SEUIL_IMPRECISION:
        return Gravite.IMPRECISION
    return None


@dataclass(frozen=True)
class Evaluation:
    """Ce que pense le moteur d'une position, du point de vue du camp au trait.

    mat_en vaut None s'il n'y a pas de mat forcé. Positif : le camp au trait
    mate ; négatif : il se fait mater.
    """

    meilleur_coup: Coup
    score: int
    mat_en: int | None = None


@dataclass(frozen=True)
class Erreur:
    coup: Coup
    perte: int
    gravite: Gravite

    def __post_init__(self):
        if self.perte < 0:
            raise ValueError("La perte ne peut pas être négative.")


@dataclass
class Analyse:
    precision: float
    erreurs: list[Erreur]

    def __post_init__(self):
        if not 0 <= self.precision <= 100:
            raise ValueError("La précision doit être entre 0 et 100.")

    def resume(self):
        debut = f"Précision : {self.precision:.0f} %."
        if not self.erreurs:
            return f"{debut} Aucune erreur, bravo !"
        gaffes = self._compter(Gravite.GAFFE)
        erreurs = self._compter(Gravite.ERREUR)
        imprecisions = self._compter(Gravite.IMPRECISION)
        return f"{debut} Gaffes : {gaffes}, erreurs : {erreurs}, imprécisions : {imprecisions}."

    def _compter(self, gravite):
        return sum(1 for erreur in self.erreurs if erreur.gravite == gravite)
