"""Tests d'acceptation : les scénarios du diagramme de cas d'utilisation.

Les vrais composants de Jarvis sont assemblés. Seuls les services externes sont
remplacés : Groq (FauxClientGroq), Stockfish (FauxMoteurUCI) et les lunettes.
"""
import io

import chess
import chess.pgn

from jagvis_echecs.assistant_llm import AssistantLLM
from jagvis_echecs.historique import Historique
from jagvis_echecs.import_lichess import ImportLichess
from jagvis_echecs.jarvis import MESSAGE_REFUS, Jarvis
from jagvis_echecs.modele import Couleur, ModeJeu
from jagvis_echecs.moteur import MoteurEchecs
from jagvis_echecs.reconnaissance import ReconnaissancePlateau
from jagvis_echecs.resultats import Gravite
from tests.doubles import PHOTO_PNG, FauxClientGroq, FauxMoteurUCI, FausseLunettes

DEPART = chess.STARTING_BOARD_FEN


def placement_apres(*coups_san):
    plateau = chess.Board()
    for coup in coups_san:
        plateau.push_san(coup)
    return plateau.board_fen()


def assembler_jarvis(tmp_path, lunettes, vision, texte, moteur_uci):
    return Jarvis(
        lunettes=lunettes,
        reconnaissance=ReconnaissancePlateau(client=vision),
        moteur=MoteurEchecs(ouvrir_moteur=moteur_uci.ouvrir),
        assistant=AssistantLLM(client=texte),
        historique=Historique(str(tmp_path / "parties")),
        import_lichess=ImportLichess(telecharger=lambda url, entetes: ""),
    )


def test_E1_conseil_en_mode_entrainement(tmp_path):
    lunettes = FausseLunettes(photos=[PHOTO_PNG])
    vision = FauxClientGroq([f"Voici la FEN : {DEPART} w KQkq - 0 1"])
    texte = FauxClientGroq(["Prends le centre avec ton pion."])
    moteur_uci = FauxMoteurUCI(meilleurs={DEPART: "e2e4"})
    jarvis = assembler_jarvis(tmp_path, lunettes, vision, texte, moteur_uci)
    jarvis.demarrer_partie(ModeJeu.ENTRAINEMENT, Couleur.BLANC)

    conseil = jarvis.conseiller_coup()

    assert "e4" in conseil
    assert lunettes.paroles[-1] == conseil
    assert len(vision.appels) == 1 and len(texte.appels) == 1
    assert moteur_uci.ferme


def test_E2_aucun_conseil_en_mode_officiel(tmp_path):
    lunettes = FausseLunettes(photos=[PHOTO_PNG])
    vision = FauxClientGroq([f"{DEPART} w KQkq - 0 1"])
    texte = FauxClientGroq([])
    moteur_uci = FauxMoteurUCI()
    jarvis = assembler_jarvis(tmp_path, lunettes, vision, texte, moteur_uci)
    jarvis.demarrer_partie(ModeJeu.OFFICIEL, Couleur.BLANC)

    conseil = jarvis.conseiller_coup()

    assert conseil == MESSAGE_REFUS
    assert lunettes.paroles[-1] == MESSAGE_REFUS
    assert moteur_uci.positions_analysees == []
    assert texte.appels == []


def test_E3_partie_suivie_alerte_gaffe_puis_analyse(tmp_path):
    coups = ["f3", "e5", "g4", "Qh4#"]
    photos = [PHOTO_PNG] * len(coups)
    vision = FauxClientGroq([placement_apres(*coups[: i + 1]) for i in range(len(coups))])
    # Après g4, les Noirs matent en 1 : du point de vue des Blancs, c'est Mate(-1).
    moteur_uci = FauxMoteurUCI(mats={placement_apres("f3", "e5", "g4"): -1})
    lunettes = FausseLunettes(photos=photos)
    jarvis = assembler_jarvis(tmp_path, lunettes, vision, FauxClientGroq([]), moteur_uci)
    partie = jarvis.demarrer_partie(ModeJeu.AMICAL, Couleur.BLANC)

    for _ in coups:
        jarvis.suivre_partie()

    assert [coup.notation for coup in partie.coups] == coups
    assert any("gaffe" in parole.lower() for parole in lunettes.paroles)
    assert partie.est_terminee()

    analyse = jarvis.analyser_partie()

    gaffes = [erreur for erreur in analyse.erreurs if erreur.gravite == Gravite.GAFFE]
    assert [erreur.coup.notation for erreur in gaffes] == ["g4"]
    sauvegardee = Historique(str(tmp_path / "parties")).charger(partie.id)
    assert [coup.notation for coup in sauvegardee.coups] == coups
    relue = chess.pgn.read_game(io.StringIO(jarvis.exporter_pgn()))
    assert relue.end().board().is_checkmate()
    assert len(list(relue.mainline_moves())) == len(coups)
