"""Jarvis : le chef d'orchestre.

Jarvis ne sait rien faire seul : il reçoit ses six outils dans son constructeur
(injection de dépendances). En test, chacun est remplacé par un double.
"""
from jagvis_echecs.erreurs import (
    ActionInterdite,
    AucunePartie,
    FenInvalide,
    PartieTerminee,
    ReconnaissanceImpossible,
    ServiceIndisponible,
)
from jagvis_echecs.modele import Couleur, Coup, ModeJeu, Partie, Position, couleur_de
from jagvis_echecs.resultats import Gravite, gravite_pour_perte

MESSAGE_REFUS = "Mode officiel : je ne donne aucun conseil pendant la partie. Bonne chance !"


def position_au_trait_de(position, couleur):
    """La caméra ne sait pas qui doit jouer : on impose le trait à `couleur`."""
    champs = position.fen.split()
    trait = "w" if couleur == Couleur.BLANC else "b"
    if champs[1] != trait:
        champs[1] = trait
        champs[3] = "-"  # la prise en passant n'a plus de sens si on change le trait
    try:
        return Position(" ".join(champs))
    except FenInvalide as erreur:
        raise ReconnaissanceImpossible(
            f"La position vue n'est pas jouable pour les {couleur.value}s."
        ) from erreur


def trouver_coup_joue(partie, position_vue):
    """Cherche le coup légal qui mène de la partie à la position vue.

    Renvoie None si rien n'a bougé. On compare seulement le placement des
    pièces : la photo ne dit pas qui doit jouer.
    """
    plateau = partie.position_actuelle().vers_plateau()
    placement_vu = position_vue.fen.split()[0]
    if plateau.board_fen() == placement_vu:
        return None
    for mouvement in plateau.legal_moves:
        plateau.push(mouvement)
        trouve = plateau.board_fen() == placement_vu
        plateau.pop()
        if trouve:
            return Coup(plateau.san(mouvement), couleur_de(plateau.turn))
    raise ReconnaissanceImpossible("La position vue ne correspond à aucun coup légal.")


class Jarvis:
    def __init__(self, lunettes, reconnaissance, moteur, assistant, historique, import_lichess):
        self.lunettes = lunettes
        self.reconnaissance = reconnaissance
        self.moteur = moteur
        self.assistant = assistant
        self.historique = historique
        self.import_lichess = import_lichess
        self.partie_en_cours = None

    def _partie(self):
        if self.partie_en_cours is None:
            raise AucunePartie("Aucune partie en cours : démarre ou importe une partie.")
        return self.partie_en_cours

    def _expliquer_sans_bloquer(self, position, evaluation):
        """L'explication du LLM est un bonus : s'il est en panne, on s'en passe."""
        try:
            return " " + self.assistant.expliquer(position, evaluation)
        except ServiceIndisponible:
            return ""

    def demarrer_partie(self, mode, couleur):
        self.partie_en_cours = Partie(mode, couleur)
        self.lunettes.parler(f"Partie {mode.value} démarrée : tu joues les {couleur.value}s.")
        return self.partie_en_cours

    def conseiller_coup(self):
        partie = self._partie()
        photo = self.lunettes.prendre_photo()
        position = self.reconnaissance.detecter_position(photo)
        if not partie.peut_conseiller():
            self.lunettes.parler(MESSAGE_REFUS)
            return MESSAGE_REFUS
        position = position_au_trait_de(position, partie.couleur_joueur)
        evaluation = self.moteur.evaluer(position)
        conseil = f"Meilleur coup : {evaluation.meilleur_coup.notation}."
        conseil += self._expliquer_sans_bloquer(position, evaluation)
        self.lunettes.parler(conseil)
        return conseil

    def suivre_partie(self):
        partie = self._partie()
        photo = self.lunettes.prendre_photo()
        position_vue = self.reconnaissance.detecter_position(photo)
        coup = trouver_coup_joue(partie, position_vue)
        if coup is None:
            return
        avant = partie.position_actuelle()
        partie.jouer(coup)
        self.lunettes.afficher(f"Coup joué : {coup.notation}")
        if partie.est_terminee():
            self.historique.sauvegarder(partie)
            self.lunettes.parler("La partie est terminée.")
            return
        if coup.couleur == partie.couleur_joueur and partie.peut_conseiller():
            self._alerter_si_gaffe(coup, avant, partie.position_actuelle())

    def _alerter_si_gaffe(self, coup, avant, apres):
        try:
            score_avant = self.moteur.evaluer(avant).score
            score_apres = self.moteur.evaluer(apres).score
        except ServiceIndisponible:
            return  # l'alerte est un bonus : le suivi de la partie continue
        # Après le coup, c'est l'adversaire qui a le trait : son score est l'opposé du nôtre.
        perte = score_avant + score_apres
        if gravite_pour_perte(perte) == Gravite.GAFFE:
            self.lunettes.parler(f"Attention : {coup.notation} est une gaffe !")

    def expliquer_coup(self):
        partie = self._partie()
        if not partie.coups:
            raise ActionInterdite("Aucun coup à expliquer.")
        if not partie.peut_conseiller() and not partie.est_terminee():
            self.lunettes.parler(MESSAGE_REFUS)
            return MESSAGE_REFUS
        dernier = partie.coups[-1]
        avant = Partie(partie.mode, partie.couleur_joueur, coups=partie.coups[:-1]).position_actuelle()
        evaluation = self.moteur.evaluer(avant)
        texte = (
            f"Dernier coup : {dernier.notation}. "
            f"Le meilleur coup était {evaluation.meilleur_coup.notation}."
        )
        texte += self._expliquer_sans_bloquer(avant, evaluation)
        self.lunettes.parler(texte)
        return texte

    def jouer_contre_moi(self):
        partie = self._partie()
        if partie.mode == ModeJeu.OFFICIEL:
            raise ActionInterdite(
                "En mode officiel, ton adversaire est humain : je ne joue pas à sa place."
            )
        if partie.est_terminee():
            raise PartieTerminee("La partie est terminée.")
        position = partie.position_actuelle()
        if position.trait == partie.couleur_joueur:
            raise ActionInterdite("C'est à toi de jouer.")
        coup = self.moteur.evaluer(position).meilleur_coup
        partie.jouer(coup)
        self.lunettes.parler(f"Je joue {coup.notation}.")
        return coup

    def analyser_partie(self):
        partie = self._partie()
        if not partie.coups:
            raise ActionInterdite("Aucun coup à analyser.")
        if partie.mode == ModeJeu.OFFICIEL and not partie.est_terminee():
            raise ActionInterdite("En mode officiel, l'analyse n'est possible qu'après la partie.")
        analyse = self.moteur.analyser(partie)
        self.historique.sauvegarder(partie)
        self.lunettes.parler(analyse.resume())
        return analyse

    def importer_partie(self, id_lichess):
        partie = self.import_lichess.recuperer_partie(id_lichess)
        self.historique.sauvegarder(partie)
        self.partie_en_cours = partie
        self.lunettes.parler(f"Partie {partie.id} importée : {len(partie.coups)} coup(s).")
        return partie

    def exporter_pgn(self):
        pgn = self._partie().vers_pgn()
        self.lunettes.afficher(pgn)
        return pgn
