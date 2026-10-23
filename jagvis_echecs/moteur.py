"""MoteurEchecs : interroge Stockfish via python-chess.

Le lancement de Stockfish est injectable (ouvrir_moteur) : les tests passent
un faux moteur et ne lancent jamais le vrai programme.
"""
import chess
import chess.engine

from jagvis_echecs.erreurs import ConfigurationInvalide, PartieTerminee, ServiceIndisponible
from jagvis_echecs.modele import Coup, Couleur, couleur_de
from jagvis_echecs.resultats import Analyse, Erreur, Evaluation, gravite_pour_perte

PROFONDEUR_MIN = 1
PROFONDEUR_MAX = 30
# Un mat compte comme une énorme avance : 10 000 centipions (moins la distance au mat).
SCORE_MAT = 10_000


def score_en_centipions(score_pov):
    return score_pov.score(mate_score=SCORE_MAT)


class MoteurEchecs:
    def __init__(self, chemin_stockfish="stockfish", profondeur=12,
                 ouvrir_moteur=chess.engine.SimpleEngine.popen_uci):
        if not PROFONDEUR_MIN <= profondeur <= PROFONDEUR_MAX:
            raise ConfigurationInvalide(
                f"La profondeur doit être entre {PROFONDEUR_MIN} et {PROFONDEUR_MAX}."
            )
        self.chemin_stockfish = chemin_stockfish
        self.profondeur = profondeur
        self.ouvrir_moteur = ouvrir_moteur

    def _erreur_stockfish(self):
        return ServiceIndisponible(
            f"Stockfish est introuvable ou ne répond pas : {self.chemin_stockfish}"
        )

    def _ouvrir(self):
        try:
            return self.ouvrir_moteur(self.chemin_stockfish)
        except (OSError, chess.engine.EngineError) as erreur:
            raise self._erreur_stockfish() from erreur

    def _analyser_plateau(self, moteur, plateau):
        try:
            return moteur.analyse(plateau, chess.engine.Limit(depth=self.profondeur))
        except (OSError, chess.engine.EngineError) as erreur:
            raise self._erreur_stockfish() from erreur

    @staticmethod
    def _fermer(moteur):
        try:
            moteur.quit()
        except (OSError, chess.engine.EngineError):
            pass  # Stockfish est peut-être déjà arrêté : rien d'autre à faire

    def evaluer(self, position):
        plateau = position.vers_plateau()
        if plateau.is_game_over():
            raise PartieTerminee("La position est terminée : aucun coup à proposer.")
        moteur = self._ouvrir()
        try:
            infos = self._analyser_plateau(moteur, plateau)
        finally:
            self._fermer(moteur)
        score = infos["score"].pov(plateau.turn)
        meilleur = infos["pv"][0]
        return Evaluation(
            meilleur_coup=Coup(plateau.san(meilleur), couleur_de(plateau.turn)),
            score=score_en_centipions(score),
            mat_en=score.mate(),
        )

    def _score_des_blancs(self, moteur, plateau):
        """Score de la position du point de vue des Blancs."""
        if plateau.is_checkmate():
            # Le camp au trait est maté : on n'a pas besoin de Stockfish.
            return -SCORE_MAT if plateau.turn == chess.WHITE else SCORE_MAT
        if plateau.is_game_over():
            return 0  # pat ou nulle
        return score_en_centipions(self._analyser_plateau(moteur, plateau)["score"].white())

    def analyser(self, partie):
        plateau = chess.Board()
        moteur = self._ouvrir()  # un seul lancement de Stockfish pour toute la partie
        try:
            # scores[i] = score avant le coup i ; scores[i + 1] = score après.
            scores = [self._score_des_blancs(moteur, plateau)]
            for coup in partie.coups:
                plateau.push_san(coup.notation)
                scores.append(self._score_des_blancs(moteur, plateau))
        finally:
            self._fermer(moteur)

        signe = 1 if partie.couleur_joueur == Couleur.BLANC else -1
        erreurs = []
        coups_du_joueur = 0
        for numero, coup in enumerate(partie.coups):
            if coup.couleur != partie.couleur_joueur:
                continue
            coups_du_joueur += 1
            perte = signe * scores[numero] - signe * scores[numero + 1]
            gravite = gravite_pour_perte(perte)
            if gravite:
                erreurs.append(Erreur(coup, perte, gravite))

        if coups_du_joueur == 0:
            return Analyse(precision=100.0, erreurs=[])
        precision = 100 * (coups_du_joueur - len(erreurs)) / coups_du_joueur
        return Analyse(precision=precision, erreurs=erreurs)
