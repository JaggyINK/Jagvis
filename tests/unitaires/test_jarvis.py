from types import SimpleNamespace

import chess
import pytest

from jagvis_echecs.erreurs import (
    ActionInterdite,
    AucunePartie,
    PartieIntrouvable,
    PartieTerminee,
    ReconnaissanceImpossible,
    ServiceIndisponible,
)
from jagvis_echecs.jarvis import MESSAGE_REFUS, Jarvis
from jagvis_echecs.modele import Coup, Couleur, ModeJeu, Partie, Position
from jagvis_echecs.resultats import Analyse, Evaluation
from tests.doubles import (
    PHOTO_PNG,
    FausseLunettes,
    FausseReconnaissance,
    FauxAssistant,
    FauxHistorique,
    FauxImportLichess,
    FauxMoteur,
)

DEPART = chess.STARTING_FEN
E4 = Coup("e4", Couleur.BLANC)
CONSEIL_E4 = Evaluation(meilleur_coup=E4, score=30)


def position_apres(*coups_san, trait="w"):
    """Position vue par la caméra : seul le placement des pièces compte."""
    plateau = chess.Board()
    for coup in coups_san:
        plateau.push_san(coup)
    return Position(f"{plateau.board_fen()} {trait} - - 0 1")


class PartieEspion(Partie):
    """Une vraie Partie qui note dans le journal quand on lui demande peut_conseiller()."""

    def __init__(self, journal, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.journal = journal

    def peut_conseiller(self):
        self.journal.append("peut_conseiller")
        return super().peut_conseiller()


@pytest.fixture
def outils():
    """Tous les doubles de Jarvis, branchés sur un même journal d'appels."""
    journal = []
    return SimpleNamespace(
        journal=journal,
        lunettes=FausseLunettes(photos=[PHOTO_PNG] * 5, journal=journal),
        reconnaissance=FausseReconnaissance(positions=[Position(DEPART)], journal=journal),
        moteur=FauxMoteur(evaluations=[CONSEIL_E4], journal=journal),
        assistant=FauxAssistant(journal=journal),
        historique=FauxHistorique(journal=journal),
        import_lichess=FauxImportLichess(journal=journal),
    )


def creer_jarvis(outils):
    return Jarvis(
        lunettes=outils.lunettes,
        reconnaissance=outils.reconnaissance,
        moteur=outils.moteur,
        assistant=outils.assistant,
        historique=outils.historique,
        import_lichess=outils.import_lichess,
    )


def jarvis_avec_partie(outils, mode=ModeJeu.ENTRAINEMENT, couleur=Couleur.BLANC, coups=()):
    jarvis = creer_jarvis(outils)
    partie = PartieEspion(outils.journal, mode, couleur)
    for notation in coups:
        partie.jouer(Coup(notation, partie.position_actuelle().trait))
    jarvis.partie_en_cours = partie
    return jarvis


# --- JAR-01 et JAR-02 : construction et démarrage -----------------------------


def test_JAR01_jarvis_recoit_ses_outils_et_n_a_pas_de_partie(outils):
    jarvis = creer_jarvis(outils)

    assert jarvis.lunettes is outils.lunettes
    assert jarvis.reconnaissance is outils.reconnaissance
    assert jarvis.moteur is outils.moteur
    assert jarvis.assistant is outils.assistant
    assert jarvis.historique is outils.historique
    assert jarvis.import_lichess is outils.import_lichess
    assert jarvis.partie_en_cours is None


def test_JAR02_demarrer_une_partie(outils):
    jarvis = creer_jarvis(outils)

    partie = jarvis.demarrer_partie(ModeJeu.AMICAL, Couleur.NOIR)

    assert jarvis.partie_en_cours is partie
    assert (partie.mode, partie.couleur_joueur, partie.coups) == (ModeJeu.AMICAL, Couleur.NOIR, [])
    assert outils.lunettes.paroles == ["Partie amical démarrée : tu joues les noirs."]


# --- JAR-03 à JAR-07 : conseiller_coup ----------------------------------------


def test_JAR03_conseil_dans_l_ordre_du_diagramme(outils):
    jarvis = jarvis_avec_partie(outils)

    conseil = jarvis.conseiller_coup()

    assert outils.journal == [
        "prendre_photo", "detecter_position", "peut_conseiller", "evaluer", "expliquer", "parler",
    ]
    assert conseil == "Meilleur coup : e4. Explication du coach."
    assert outils.lunettes.paroles == [conseil]
    assert outils.reconnaissance.photos_recues == [PHOTO_PNG]
    assert outils.assistant.demandes == [(Position(DEPART), CONSEIL_E4)]


def test_JAR04_mode_officiel_refus_sans_moteur_ni_llm(outils):
    jarvis = jarvis_avec_partie(outils, mode=ModeJeu.OFFICIEL)

    conseil = jarvis.conseiller_coup()

    assert conseil == MESSAGE_REFUS
    assert outils.journal == ["prendre_photo", "detecter_position", "peut_conseiller", "parler"]
    assert outils.lunettes.paroles == [MESSAGE_REFUS]


@pytest.mark.parametrize(
    "action",
    ["conseiller_coup", "suivre_partie", "expliquer_coup", "jouer_contre_moi", "analyser_partie", "exporter_pgn"],
)
def test_JAR05_rien_sans_partie_en_cours(outils, action):
    jarvis = creer_jarvis(outils)

    with pytest.raises(AucunePartie, match="Aucune partie en cours : démarre ou importe une partie."):
        getattr(jarvis, action)()
    assert outils.journal == []  # pas même une photo


def test_JAR06_le_conseil_est_pour_le_camp_du_joueur(outils):
    # La caméra ne sait pas qui doit jouer : Jarvis impose la couleur du joueur.
    outils.reconnaissance.positions = [position_apres("e4", trait="w")]
    jarvis = jarvis_avec_partie(outils, couleur=Couleur.NOIR)

    jarvis.conseiller_coup()

    assert outils.moteur.positions_evaluees[0].trait == Couleur.NOIR


def test_JAR06_position_impossible_pour_le_joueur(outils):
    # Les Noirs sont en échec : ce ne peut pas être aux Blancs de jouer.
    outils.reconnaissance.positions = [position_apres("e4", "f5", "Qh5+", trait="b")]
    jarvis = jarvis_avec_partie(outils, couleur=Couleur.BLANC)

    with pytest.raises(ReconnaissanceImpossible, match="La position vue n'est pas jouable pour les blancs."):
        jarvis.conseiller_coup()
    assert "evaluer" not in outils.journal


def test_JAR07_sans_llm_le_conseil_reste_utile(outils):
    outils.assistant.panne = ServiceIndisponible("Le service de langage est indisponible.")
    jarvis = jarvis_avec_partie(outils)

    conseil = jarvis.conseiller_coup()

    assert conseil == "Meilleur coup : e4."
    assert outils.lunettes.paroles == [conseil]


def test_JAR07_les_autres_pannes_remontent(outils):
    outils.moteur.panne = ServiceIndisponible("Stockfish est introuvable ou ne répond pas : stockfish")
    jarvis = jarvis_avec_partie(outils)

    with pytest.raises(ServiceIndisponible, match="Stockfish"):
        jarvis.conseiller_coup()
    assert outils.lunettes.paroles == []


# --- JAR-08 et JAR-09 : suivre_partie ------------------------------------------


def test_JAR08_suivre_enregistre_le_coup_vu(outils):
    outils.reconnaissance.positions = [position_apres("e4")]
    jarvis = jarvis_avec_partie(outils, mode=ModeJeu.OFFICIEL)

    jarvis.suivre_partie()

    assert jarvis.partie_en_cours.coups == [E4]
    assert outils.lunettes.affichages == ["Coup joué : e4"]
    assert "evaluer" not in outils.journal  # mode officiel : aucun calcul pendant la partie


def test_JAR08_rien_ne_change_si_la_position_est_la_meme(outils):
    outils.reconnaissance.positions = [position_apres("e4")]
    jarvis = jarvis_avec_partie(outils, coups=["e4"])

    jarvis.suivre_partie()

    assert len(jarvis.partie_en_cours.coups) == 1
    assert outils.lunettes.affichages == []


def test_JAR08_position_vue_impossible(outils):
    outils.reconnaissance.positions = [position_apres("e4", "e5")]  # deux coups d'un coup
    jarvis = jarvis_avec_partie(outils)

    with pytest.raises(ReconnaissanceImpossible, match="La position vue ne correspond à aucun coup légal."):
        jarvis.suivre_partie()
    assert jarvis.partie_en_cours.coups == []


def test_JAR08_fin_de_partie_sauvegardee_et_annoncee(outils):
    outils.reconnaissance.positions = [position_apres("f3", "e5", "g4", "Qh4#")]
    jarvis = jarvis_avec_partie(outils, couleur=Couleur.NOIR, coups=["f3", "e5", "g4"])

    jarvis.suivre_partie()

    assert jarvis.partie_en_cours.est_terminee()
    assert outils.historique.parties[jarvis.partie_en_cours.id] is jarvis.partie_en_cours
    assert outils.lunettes.paroles == ["La partie est terminée."]


def evaluations(avant, apres_pour_l_adversaire):
    return [
        Evaluation(meilleur_coup=E4, score=avant),
        Evaluation(meilleur_coup=Coup("e5", Couleur.NOIR), score=apres_pour_l_adversaire),
    ]


def test_JAR09_alerte_quand_le_joueur_gaffe(outils):
    outils.reconnaissance.positions = [position_apres("e4")]
    outils.moteur.evaluations = evaluations(avant=20, apres_pour_l_adversaire=400)  # perte : 420
    jarvis = jarvis_avec_partie(outils, mode=ModeJeu.AMICAL)

    jarvis.suivre_partie()

    assert outils.lunettes.paroles == ["Attention : e4 est une gaffe !"]
    assert outils.moteur.positions_evaluees == [Position(DEPART), jarvis.partie_en_cours.position_actuelle()]


def test_JAR09_pas_d_alerte_pour_une_simple_erreur(outils):
    outils.reconnaissance.positions = [position_apres("e4")]
    outils.moteur.evaluations = evaluations(avant=20, apres_pour_l_adversaire=200)  # perte : 220
    jarvis = jarvis_avec_partie(outils)

    jarvis.suivre_partie()

    assert outils.lunettes.paroles == []


def test_JAR09_pas_d_alerte_pour_le_coup_de_l_adversaire(outils):
    outils.reconnaissance.positions = [position_apres("e4")]
    jarvis = jarvis_avec_partie(outils, couleur=Couleur.NOIR)

    jarvis.suivre_partie()

    assert "evaluer" not in outils.journal


def test_JAR09_moteur_en_panne_le_suivi_continue(outils):
    outils.reconnaissance.positions = [position_apres("e4")]
    outils.moteur.panne = ServiceIndisponible("Stockfish est introuvable ou ne répond pas : stockfish")
    jarvis = jarvis_avec_partie(outils)

    jarvis.suivre_partie()

    assert jarvis.partie_en_cours.coups == [E4]
    assert outils.lunettes.paroles == []


# --- JAR-10 : expliquer_coup ----------------------------------------------------


def test_JAR10_expliquer_le_dernier_coup(outils):
    outils.moteur.evaluations = [Evaluation(meilleur_coup=Coup("d4", Couleur.BLANC), score=25)]
    jarvis = jarvis_avec_partie(outils, coups=["e4"])

    texte = jarvis.expliquer_coup()

    assert texte == "Dernier coup : e4. Le meilleur coup était d4. Explication du coach."
    assert outils.moteur.positions_evaluees == [Position(DEPART)]  # la position AVANT le coup
    assert outils.lunettes.paroles == [texte]


def test_JAR10_rien_a_expliquer(outils):
    jarvis = jarvis_avec_partie(outils)

    with pytest.raises(ActionInterdite, match="Aucun coup à expliquer."):
        jarvis.expliquer_coup()


def test_JAR10_refus_pendant_une_partie_officielle(outils):
    jarvis = jarvis_avec_partie(outils, mode=ModeJeu.OFFICIEL, coups=["e4"])

    assert jarvis.expliquer_coup() == MESSAGE_REFUS
    assert "evaluer" not in outils.journal


def test_JAR10_permis_apres_une_partie_officielle_et_sans_llm(outils):
    outils.assistant.panne = ServiceIndisponible("Le service de langage est indisponible.")
    outils.moteur.evaluations = [Evaluation(meilleur_coup=Coup("Qh4#", Couleur.NOIR), score=9999, mat_en=1)]
    jarvis = jarvis_avec_partie(outils, mode=ModeJeu.OFFICIEL, coups=["f3", "e5", "g4", "Qh4#"])

    assert jarvis.expliquer_coup() == "Dernier coup : Qh4#. Le meilleur coup était Qh4#."


# --- JAR-11 : jouer_contre_moi ----------------------------------------------------


def test_JAR11_jarvis_joue_le_meilleur_coup(outils):
    e5 = Coup("e5", Couleur.NOIR)
    outils.moteur.evaluations = [Evaluation(meilleur_coup=e5, score=0)]
    jarvis = jarvis_avec_partie(outils, mode=ModeJeu.ENTRAINEMENT, coups=["e4"])

    coup = jarvis.jouer_contre_moi()

    assert coup == e5
    assert jarvis.partie_en_cours.coups[-1] == e5
    assert outils.lunettes.paroles == ["Je joue e5."]


@pytest.mark.parametrize(
    "mode, coups, erreur, message",
    [
        (ModeJeu.AMICAL, [], ActionInterdite, "C'est à toi de jouer."),
        (ModeJeu.OFFICIEL, ["e4"], ActionInterdite, "En mode officiel, ton adversaire est humain"),
        (ModeJeu.AMICAL, ["f3", "e5", "g4", "Qh4#"], PartieTerminee, "La partie est terminée."),
    ],
)
def test_JAR11_jarvis_refuse_de_jouer(outils, mode, coups, erreur, message):
    jarvis = jarvis_avec_partie(outils, mode=mode, coups=coups)

    with pytest.raises(erreur, match=message):
        jarvis.jouer_contre_moi()
    assert "evaluer" not in outils.journal


# --- JAR-12 : analyser_partie -------------------------------------------------------


def test_JAR12_analyser_sauvegarde_et_annonce_le_resume(outils):
    outils.moteur.analyse = Analyse(precision=100.0, erreurs=[])
    jarvis = jarvis_avec_partie(outils, coups=["e4", "e5"])

    analyse = jarvis.analyser_partie()

    assert analyse is outils.moteur.analyse
    assert outils.journal == ["analyser", "sauvegarder", "parler"]
    assert outils.lunettes.paroles == ["Précision : 100 %. Aucune erreur, bravo !"]


@pytest.mark.parametrize(
    "mode, coups, message",
    [
        (ModeJeu.AMICAL, [], "Aucun coup à analyser."),
        (ModeJeu.OFFICIEL, ["e4"], "En mode officiel, l'analyse n'est possible qu'après la partie."),
    ],
)
def test_JAR12_analyse_refusee(outils, mode, coups, message):
    jarvis = jarvis_avec_partie(outils, mode=mode, coups=coups)

    with pytest.raises(ActionInterdite, match=message):
        jarvis.analyser_partie()
    assert "analyser" not in outils.journal


# --- JAR-13 : importer_partie ---------------------------------------------------------


def test_JAR13_importer_devient_la_partie_en_cours(outils):
    importee = Partie(ModeJeu.AMICAL, Couleur.BLANC, id="AbCd1234", coups=[E4])
    outils.import_lichess.partie = importee
    jarvis = creer_jarvis(outils)

    partie = jarvis.importer_partie("AbCd1234")

    assert partie is importee and jarvis.partie_en_cours is importee
    assert outils.import_lichess.identifiants == ["AbCd1234"]
    assert outils.historique.parties == {"AbCd1234": importee}
    assert outils.lunettes.paroles == ["Partie AbCd1234 importée : 1 coup(s)."]


def test_JAR13_echec_d_import_la_partie_en_cours_ne_change_pas(outils):
    outils.import_lichess.panne = PartieIntrouvable("Partie Lichess introuvable")
    jarvis = jarvis_avec_partie(outils)
    avant = jarvis.partie_en_cours

    with pytest.raises(PartieIntrouvable):
        jarvis.importer_partie("AbCd1234")
    assert jarvis.partie_en_cours is avant
    assert outils.historique.parties == {}


# --- JAR-14 : exporter_pgn -------------------------------------------------------------


def test_JAR14_exporter_affiche_et_renvoie_le_pgn(outils):
    jarvis = jarvis_avec_partie(outils, coups=["e4"])

    pgn = jarvis.exporter_pgn()

    assert pgn == jarvis.partie_en_cours.vers_pgn()
    assert outils.lunettes.affichages == [pgn]
