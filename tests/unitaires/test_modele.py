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
