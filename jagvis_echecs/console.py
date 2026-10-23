"""Console : on parle à Jarvis par des commandes tapées dans le terminal.

Lancement : python -m jagvis_echecs
"""
import os
import sys

from dotenv import load_dotenv

from jagvis_echecs.assistant_llm import AssistantLLM
from jagvis_echecs.erreurs import ConfigurationInvalide, JagvisErreur
from jagvis_echecs.historique import Historique
from jagvis_echecs.import_lichess import ImportLichess
from jagvis_echecs.jarvis import Jarvis
from jagvis_echecs.lunettes import LunettesConsole
from jagvis_echecs.modele import Couleur, ModeJeu
from jagvis_echecs.moteur import MoteurEchecs
from jagvis_echecs.reconnaissance import ReconnaissancePlateau

AIDE = (
    "Commandes : nouvelle <entrainement|amical|officiel> <blanc|noir>, conseil, "
    "suivre, expliquer, joue, analyse, import <id lichess>, pgn, quitter"
)

# Les commandes sans argument et la méthode de Jarvis qu'elles appellent.
COMMANDES_SIMPLES = {
    "conseil": "conseiller_coup",
    "suivre": "suivre_partie",
    "expliquer": "expliquer_coup",
    "joue": "jouer_contre_moi",
    "analyse": "analyser_partie",
    "pgn": "exporter_pgn",
}
MODES = {mode.value: mode for mode in ModeJeu}
COULEURS = {couleur.value: couleur for couleur in Couleur}


def executer_commande(jarvis, commande):
    """Exécute une commande. Renvoie l'aide si la commande n'est pas comprise."""
    mots = commande.lower().split()
    if len(mots) == 1 and mots[0] in COMMANDES_SIMPLES:
        getattr(jarvis, COMMANDES_SIMPLES[mots[0]])()
    elif len(mots) == 3 and mots[0] == "nouvelle" and mots[1] in MODES and mots[2] in COULEURS:
        jarvis.demarrer_partie(MODES[mots[1]], COULEURS[mots[2]])
    elif len(mots) == 2 and mots[0] == "import":
        # On reprend le mot d'origine : les identifiants Lichess distinguent les majuscules.
        jarvis.importer_partie(commande.split()[1])
    else:
        return AIDE
    return None


def boucle(jarvis, lunettes):
    lunettes.parler(AIDE)
    while True:
        try:
            commande = lunettes.ecouter()
        except EOFError:  # Ctrl-D
            break
        if commande.lower() in ("quitter", "q"):
            break
        try:
            reponse = executer_commande(jarvis, commande)
        except JagvisErreur as erreur:
            reponse = f"Erreur : {erreur}"
        if reponse:
            lunettes.parler(reponse)
    lunettes.parler("À bientôt !")


def assembler_jarvis():
    """Construit le vrai Jarvis. Lève ConfigurationInvalide si GROQ_KEY manque."""
    return Jarvis(
        lunettes=LunettesConsole(),
        reconnaissance=ReconnaissancePlateau(),
        moteur=MoteurEchecs(chemin_stockfish=os.environ.get("STOCKFISH_PATH", "stockfish")),
        assistant=AssistantLLM(),
        historique=Historique(os.environ.get("JAGVIS_PARTIES", "parties")),
        import_lichess=ImportLichess(token=os.environ.get("LICHESS_TOKEN")),
    )


def main():
    load_dotenv()
    try:
        jarvis = assembler_jarvis()
    except ConfigurationInvalide as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 2
    boucle(jarvis, jarvis.lunettes)
    return 0
