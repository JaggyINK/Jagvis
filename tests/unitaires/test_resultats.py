import pytest

from jagvis_echecs.modele import Coup, Couleur
from jagvis_echecs.resultats import Analyse, Erreur, Evaluation, Gravite, gravite_pour_perte

E4 = Coup("e4", Couleur.BLANC)


@pytest.mark.parametrize(
    "perte, gravite",
    [
        (-30, None),  # le coup joué était meilleur que prévu
        (0, None),
        (49, None),
        (50, Gravite.IMPRECISION),
        (99, Gravite.IMPRECISION),
        (100, Gravite.ERREUR),
        (299, Gravite.ERREUR),
        (300, Gravite.GAFFE),
        (9999, Gravite.GAFFE),
    ],
)
def test_RES01_gravite_selon_la_perte_en_centipions(perte, gravite):
    assert gravite_pour_perte(perte) == gravite


def test_RES02_evaluation_sans_mat():
    evaluation = Evaluation(meilleur_coup=E4, score=35)

    assert evaluation.meilleur_coup == E4
    assert evaluation.score == 35
    assert evaluation.mat_en is None


def test_RES03_une_erreur_garde_son_coup_sa_perte_et_sa_gravite():
    erreur = Erreur(coup=E4, perte=320, gravite=Gravite.GAFFE)

    assert (erreur.coup, erreur.perte, erreur.gravite) == (E4, 320, Gravite.GAFFE)


def test_RES03_une_perte_negative_est_refusee():
    with pytest.raises(ValueError, match="La perte ne peut pas être négative"):
        Erreur(coup=E4, perte=-1, gravite=Gravite.IMPRECISION)


@pytest.mark.parametrize("precision", [-0.1, 100.1])
def test_RES04_la_precision_est_un_pourcentage(precision):
    with pytest.raises(ValueError, match="entre 0 et 100"):
        Analyse(precision=precision, erreurs=[])


def test_RES04_resume_compte_les_erreurs_par_gravite():
    erreurs = [
        Erreur(E4, 400, Gravite.GAFFE),
        Erreur(E4, 60, Gravite.IMPRECISION),
        Erreur(E4, 70, Gravite.IMPRECISION),
    ]

    resume = Analyse(precision=62.5, erreurs=erreurs).resume()

    assert resume == "Précision : 62 %. Gaffes : 1, erreurs : 0, imprécisions : 2."


def test_RES04_resume_sans_erreur():
    assert Analyse(precision=100.0, erreurs=[]).resume() == "Précision : 100 %. Aucune erreur, bravo !"
