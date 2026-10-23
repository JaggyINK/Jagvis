import chess
import pytest

from jagvis_echecs.erreurs import FenInvalide
from jagvis_echecs.modele import Coup, Couleur, ModeJeu, Position

DEPART = chess.STARTING_FEN
MAT_DU_BERGER = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"


def test_MOD01_enumerations_du_diagramme():
    assert [couleur.name for couleur in Couleur] == ["BLANC", "NOIR"]
    assert [mode.name for mode in ModeJeu] == ["ENTRAINEMENT", "AMICAL", "OFFICIEL"]


def test_MOD02_deux_coups_identiques_sont_egaux():
    assert Coup("e4", Couleur.BLANC) == Coup("e4", Couleur.BLANC)
    assert Coup("e4", Couleur.BLANC) != Coup("e4", Couleur.NOIR)


@pytest.mark.parametrize(
    "fen, trait",
    [
        (DEPART, Couleur.BLANC),
        ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", Couleur.NOIR),
    ],
)
def test_MOD03_le_trait_vient_de_la_fen(fen, trait):
    position = Position(fen)

    assert position.fen == fen
    assert position.trait == trait


@pytest.mark.parametrize(
    "fen",
    [
        "",
        "n'importe quoi",
        "8/8/8/8/8/8/8/8 w - - 0 1",  # aucun roi : FEN bien écrite mais position impossible
    ],
)
def test_MOD03_une_fen_invalide_est_refusee(fen):
    with pytest.raises(FenInvalide, match="FEN invalide"):
        Position(fen)


def test_MOD04_vingt_coups_legaux_au_depart():
    coups = Position(DEPART).coups_legaux()

    assert len(coups) == 20
    assert Coup("e4", Couleur.BLANC) in coups
    assert Coup("Nf3", Couleur.BLANC) in coups


def test_MOD04_coups_legaux_identiques_a_python_chess():
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    plateau = chess.Board(fen)
    attendus = {plateau.san(coup) for coup in plateau.legal_moves}

    notations = {coup.notation for coup in Position(fen).coups_legaux()}

    assert notations == attendus
    assert "O-O" in notations and "O-O-O" in notations


def test_MOD04_aucun_coup_legal_quand_on_est_mat():
    assert Position(MAT_DU_BERGER).coups_legaux() == []


# --- Partie -----------------------------------------------------------------
import io
from datetime import datetime

import chess.pgn

from jagvis_echecs.erreurs import CoupIllegal, PartieTerminee
from jagvis_echecs.modele import Partie

DATE = datetime(2026, 10, 23, 14, 5)
MAT_DU_LION = ["f3", "e5", "g4", "Qh4#"]
# Le pat le plus rapide connu (Sam Loyd) : les Noirs n'ont plus de coup légal.
PAT_EN_10_COUPS = [
    "e3", "a5", "Qh5", "Ra6", "Qxa5", "h5", "h4", "Rah6", "Qxc7", "f6",
    "Qxd7+", "Kf7", "Qxb7", "Qd3", "Qxb8", "Qh7", "Qxc8", "Kg6", "Qe6",
]


def partie_avec(notations, mode=ModeJeu.AMICAL, couleur=Couleur.BLANC):
    partie = Partie(mode, couleur, date=DATE)
    for notation in notations:
        partie.jouer(Coup(notation, partie.position_actuelle().trait))
    return partie


def test_MOD05_une_nouvelle_partie_est_vide():
    partie = Partie(ModeJeu.ENTRAINEMENT, Couleur.NOIR, date=DATE)

    assert partie.mode == ModeJeu.ENTRAINEMENT
    assert partie.couleur_joueur == Couleur.NOIR
    assert partie.date == DATE
    assert partie.coups == []
    assert partie.position_actuelle() == Position(DEPART)


def test_MOD05_chaque_partie_a_son_propre_identifiant():
    premiere = Partie(ModeJeu.AMICAL, Couleur.BLANC)
    seconde = Partie(ModeJeu.AMICAL, Couleur.BLANC)

    assert premiere.id and seconde.id and premiere.id != seconde.id
    assert isinstance(premiere.date, datetime)


@pytest.mark.parametrize("mode, couleur", [("officiel", Couleur.BLANC), (ModeJeu.AMICAL, "blanc")])
def test_MOD05_mode_et_couleur_doivent_etre_des_enumerations(mode, couleur):
    with pytest.raises(TypeError):
        Partie(mode, couleur)


def test_MOD05_les_coups_donnes_a_la_creation_sont_verifies():
    with pytest.raises(CoupIllegal):
        Partie(ModeJeu.AMICAL, Couleur.BLANC, coups=[Coup("e5", Couleur.BLANC)])


def test_MOD06_jouer_ajoute_le_coup_et_change_le_trait():
    partie = partie_avec(["e4"])

    assert partie.coups == [Coup("e4", Couleur.BLANC)]
    assert partie.position_actuelle().trait == Couleur.NOIR


def test_MOD07_un_coup_illegal_est_refuse():
    partie = partie_avec([])

    with pytest.raises(CoupIllegal, match="Coup illégal : e5"):
        partie.jouer(Coup("e5", Couleur.BLANC))
    assert partie.coups == []


def test_MOD07_on_ne_joue_pas_hors_de_son_tour():
    partie = partie_avec([])

    with pytest.raises(CoupIllegal, match="Ce n'est pas aux noirs de jouer."):
        partie.jouer(Coup("e5", Couleur.NOIR))


def test_MOD07_on_ne_joue_plus_apres_la_fin():
    partie = partie_avec(MAT_DU_LION)

    with pytest.raises(PartieTerminee, match="La partie est terminée."):
        partie.jouer(Coup("a3", Couleur.BLANC))


@pytest.mark.parametrize(
    "mode, attendu",
    [(ModeJeu.ENTRAINEMENT, True), (ModeJeu.AMICAL, True), (ModeJeu.OFFICIEL, False)],
)
def test_MOD08_pas_de_conseil_en_mode_officiel(mode, attendu):
    assert Partie(mode, Couleur.BLANC).peut_conseiller() is attendu


@pytest.mark.parametrize(
    "coups, terminee",
    [([], False), (["e4", "e5"], False), (MAT_DU_LION, True), (PAT_EN_10_COUPS, True)],
)
def test_MOD09_fin_de_partie_par_mat_ou_pat(coups, terminee):
    assert partie_avec(coups).est_terminee() is terminee


def test_MOD10_le_pgn_est_relu_par_python_chess():
    partie = partie_avec(MAT_DU_LION, couleur=Couleur.BLANC)

    relue = chess.pgn.read_game(io.StringIO(partie.vers_pgn()))

    plateau = relue.board()
    notations = []
    for coup in relue.mainline_moves():
        notations.append(plateau.san(coup))
        plateau.push(coup)
    assert notations == MAT_DU_LION
    assert relue.headers["Date"] == "2026.10.23"
    assert relue.headers["White"] == "Joueur"
    assert relue.headers["Result"] == "0-1"
