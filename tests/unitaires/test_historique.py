from datetime import datetime

import pytest

from jagvis_echecs.erreurs import HistoriqueCorrompu, IdentifiantInvalide, PartieIntrouvable
from jagvis_echecs.historique import Historique
from jagvis_echecs.modele import Coup, Couleur, ModeJeu, Partie


def nouvelle_partie(id="abc123", date=datetime(2026, 10, 23, 14, 5), coups=("e4", "e5")):
    partie = Partie(ModeJeu.OFFICIEL, Couleur.NOIR, id=id, date=date)
    for notation in coups:
        partie.jouer(Coup(notation, partie.position_actuelle().trait))
    return partie


def test_HIS01_une_partie_sauvegardee_est_rechargee_a_l_identique(tmp_path):
    partie = nouvelle_partie()
    Historique(str(tmp_path)).sauvegarder(partie)

    rechargee = Historique(str(tmp_path)).charger("abc123")

    assert rechargee.id == partie.id
    assert rechargee.date == partie.date
    assert rechargee.mode == ModeJeu.OFFICIEL
    assert rechargee.couleur_joueur == Couleur.NOIR
    assert rechargee.coups == partie.coups


def test_HIS01_sauvegarder_deux_fois_remplace_l_ancienne_version(tmp_path):
    historique = Historique(str(tmp_path))
    partie = nouvelle_partie(coups=["e4"])
    historique.sauvegarder(partie)
    partie.jouer(Coup("e5", Couleur.NOIR))

    historique.sauvegarder(partie)

    assert len(historique.charger("abc123").coups) == 2
    assert len(historique.lister()) == 1


def test_HIS02_lister_un_historique_vide(tmp_path):
    assert Historique(str(tmp_path)).lister() == []


def test_HIS02_lister_de_la_plus_ancienne_a_la_plus_recente(tmp_path):
    historique = Historique(str(tmp_path))
    historique.sauvegarder(nouvelle_partie(id="recente", date=datetime(2026, 10, 23)))
    historique.sauvegarder(nouvelle_partie(id="ancienne", date=datetime(2025, 1, 1)))

    assert [partie.id for partie in historique.lister()] == ["ancienne", "recente"]


def test_HIS03_charger_une_partie_inconnue(tmp_path):
    with pytest.raises(PartieIntrouvable, match="Partie introuvable : zzz"):
        Historique(str(tmp_path)).charger("zzz")


def test_HIS04_le_dossier_est_cree_s_il_n_existe_pas(tmp_path):
    dossier = tmp_path / "sous" / "dossier"

    Historique(str(dossier)).sauvegarder(nouvelle_partie())

    assert (dossier / "abc123.json").exists()


@pytest.mark.parametrize("id", ["../secret", "a/b", "", "x" * 65, "é"])
def test_HIS05_un_identifiant_dangereux_est_refuse(tmp_path, id):
    historique = Historique(str(tmp_path))

    with pytest.raises(IdentifiantInvalide, match="Identifiant de partie invalide"):
        historique.charger(id)
    with pytest.raises(IdentifiantInvalide):
        historique.sauvegarder(nouvelle_partie(id=id or "?"))


def test_HIS06_un_fichier_corrompu_donne_une_erreur_claire(tmp_path):
    (tmp_path / "abc123.json").write_text("{ pas du json", encoding="utf-8")

    with pytest.raises(HistoriqueCorrompu, match="Le fichier de la partie abc123 est illisible."):
        Historique(str(tmp_path)).charger("abc123")


def test_HIS06_un_fichier_avec_un_coup_faux_est_corrompu(tmp_path):
    historique = Historique(str(tmp_path))
    historique.sauvegarder(nouvelle_partie())
    fichier = tmp_path / "abc123.json"
    fichier.write_text(fichier.read_text(encoding="utf-8").replace('"e4"', '"e7"'), encoding="utf-8")

    with pytest.raises(HistoriqueCorrompu):
        historique.charger("abc123")


def test_HIS06_lister_ignore_les_fichiers_corrompus(tmp_path):
    historique = Historique(str(tmp_path))
    historique.sauvegarder(nouvelle_partie(id="bonne"))
    (tmp_path / "mauvaise.json").write_text("[]", encoding="utf-8")

    assert [partie.id for partie in historique.lister()] == ["bonne"]
