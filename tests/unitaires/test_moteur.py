import chess
import chess.engine
import pytest

from jagvis_echecs.erreurs import ConfigurationInvalide, PartieTerminee, ServiceIndisponible
from jagvis_echecs.modele import Coup, Couleur, ModeJeu, Partie, Position
from jagvis_echecs.moteur import MoteurEchecs
from jagvis_echecs.resultats import Gravite
from tests.doubles import FauxMoteurUCI

DEPART = chess.STARTING_BOARD_FEN
APRES_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
MAT_DU_LION = ["f3", "e5", "g4", "Qh4#"]
APRES_G4 = "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR"


def partie_avec(notations, couleur=Couleur.BLANC):
    partie = Partie(ModeJeu.AMICAL, couleur)
    for notation in notations:
        partie.jouer(Coup(notation, partie.position_actuelle().trait))
    return partie


class MoteurQuiPlante(FauxMoteurUCI):
    def analyse(self, plateau, limite):
        raise chess.engine.EngineTerminatedError("Stockfish s'est arrêté")


def moteur_introuvable(chemin):
    raise FileNotFoundError(chemin)


def test_MOT01_reglages_par_defaut():
    moteur = MoteurEchecs()

    assert moteur.chemin_stockfish == "stockfish"
    assert moteur.profondeur == 12


@pytest.mark.parametrize("profondeur", [0, 31, -5])
def test_MOT01_profondeur_hors_limites(profondeur):
    with pytest.raises(ConfigurationInvalide, match="La profondeur doit être entre 1 et 30."):
        MoteurEchecs(profondeur=profondeur)


def test_MOT02_evaluer_donne_le_meilleur_coup_et_le_score():
    uci = FauxMoteurUCI(scores={DEPART: 30}, meilleurs={DEPART: "e2e4"})
    moteur = MoteurEchecs(chemin_stockfish="/opt/stockfish", profondeur=8, ouvrir_moteur=uci.ouvrir)

    evaluation = moteur.evaluer(Position(chess.STARTING_FEN))

    assert evaluation.meilleur_coup == Coup("e4", Couleur.BLANC)
    assert evaluation.score == 30
    assert evaluation.mat_en is None
    assert uci.chemins_ouverts == ["/opt/stockfish"]
    assert uci.limites[0].depth == 8
    assert uci.ferme


def test_MOT02_le_score_est_vu_par_le_camp_au_trait():
    uci = FauxMoteurUCI(scores={APRES_E4: 80}, meilleurs={APRES_E4: "e7e5"})
    position = Position(APRES_E4 + " b KQkq - 0 1")

    evaluation = MoteurEchecs(ouvrir_moteur=uci.ouvrir).evaluer(position)

    assert evaluation.score == -80
    assert evaluation.meilleur_coup == Coup("e5", Couleur.NOIR)


def test_MOT03_un_mat_force_est_signale():
    fen = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"
    placement = fen.split()[0]
    uci = FauxMoteurUCI(mats={placement: 1}, meilleurs={placement: "a1a8"})

    evaluation = MoteurEchecs(ouvrir_moteur=uci.ouvrir).evaluer(Position(fen))

    assert evaluation.meilleur_coup.notation == "Ra8#"
    assert evaluation.mat_en == 1
    assert evaluation.score > 9000


def test_MOT04_pas_d_evaluation_d_une_position_terminee():
    uci = FauxMoteurUCI()
    position = partie_avec(MAT_DU_LION).position_actuelle()

    with pytest.raises(PartieTerminee, match="La position est terminée : aucun coup à proposer."):
        MoteurEchecs(ouvrir_moteur=uci.ouvrir).evaluer(position)
    assert uci.chemins_ouverts == []


def test_MOT05_stockfish_introuvable():
    moteur = MoteurEchecs(chemin_stockfish="/rien/stockfish", ouvrir_moteur=moteur_introuvable)

    with pytest.raises(ServiceIndisponible, match="Stockfish est introuvable ou ne répond pas : /rien/stockfish"):
        moteur.evaluer(Position(chess.STARTING_FEN))


def test_MOT05_stockfish_plante_pendant_l_analyse_et_il_est_ferme():
    uci = MoteurQuiPlante()

    with pytest.raises(ServiceIndisponible):
        MoteurEchecs(ouvrir_moteur=uci.ouvrir).evaluer(Position(chess.STARTING_FEN))
    assert uci.ferme


def test_MOT06_analyser_trouve_la_gaffe_du_joueur():
    uci = FauxMoteurUCI(mats={APRES_G4: -1})

    analyse = MoteurEchecs(ouvrir_moteur=uci.ouvrir).analyser(partie_avec(MAT_DU_LION))

    assert [(erreur.coup.notation, erreur.gravite) for erreur in analyse.erreurs] == [("g4", Gravite.GAFFE)]
    assert analyse.erreurs[0].perte > 300
    assert analyse.precision == 50.0
    assert uci.chemins_ouverts == ["stockfish"]  # un seul lancement pour toute la partie
    assert len(uci.positions_analysees) == 4  # la position finale (mat) n'est pas envoyée
    assert uci.ferme


def test_MOT06_seuls_les_coups_du_joueur_sont_analyses():
    uci = FauxMoteurUCI(mats={APRES_G4: -1})

    analyse = MoteurEchecs(ouvrir_moteur=uci.ouvrir).analyser(partie_avec(MAT_DU_LION, Couleur.NOIR))

    assert analyse.erreurs == []
    assert analyse.precision == 100.0


def test_MOT06_partie_sans_coup():
    uci = FauxMoteurUCI()

    analyse = MoteurEchecs(ouvrir_moteur=uci.ouvrir).analyser(partie_avec([]))

    assert (analyse.precision, analyse.erreurs) == (100.0, [])


def test_MOT06_une_petite_perte_n_est_pas_une_erreur():
    uci = FauxMoteurUCI(scores={DEPART: 30, APRES_E4: 0})

    analyse = MoteurEchecs(ouvrir_moteur=uci.ouvrir).analyser(partie_avec(["e4"]))

    assert analyse.erreurs == []


@pytest.mark.stockfish
def test_MOT07_le_vrai_stockfish_trouve_le_mat_en_un():
    position = Position("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")

    evaluation = MoteurEchecs(profondeur=10).evaluer(position)

    assert evaluation.meilleur_coup.notation == "Ra8#"
    assert evaluation.mat_en == 1


class MoteurDejaArrete(FauxMoteurUCI):
    def quit(self):
        raise chess.engine.EngineTerminatedError("déjà arrêté")


def test_MOT05_fermer_un_stockfish_deja_arrete_ne_plante_pas():
    uci = MoteurDejaArrete(meilleurs={DEPART: "e2e4"})

    evaluation = MoteurEchecs(ouvrir_moteur=uci.ouvrir).evaluer(Position(chess.STARTING_FEN))

    assert evaluation.meilleur_coup.notation == "e4"


def test_MOT06_un_pat_vaut_zero_sans_appeler_stockfish():
    pat = [
        "e3", "a5", "Qh5", "Ra6", "Qxa5", "h5", "h4", "Rah6", "Qxc7", "f6",
        "Qxd7+", "Kf7", "Qxb7", "Qd3", "Qxb8", "Qh7", "Qxc8", "Kg6", "Qe6",
    ]
    uci = FauxMoteurUCI()

    analyse = MoteurEchecs(ouvrir_moteur=uci.ouvrir).analyser(partie_avec(pat))

    assert len(uci.positions_analysees) == len(pat)  # la position de pat n'est pas envoyée
    assert analyse.erreurs == []
