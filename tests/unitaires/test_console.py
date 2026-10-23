import pytest

from jagvis_echecs.console import AIDE, boucle, executer_commande, main
from jagvis_echecs.erreurs import AucunePartie
from jagvis_echecs.modele import Couleur, ModeJeu


class JarvisEspion:
    """Double de Jarvis : note les méthodes appelées et leurs arguments."""

    def __init__(self, panne=None):
        self.appels = []
        self.panne = panne

    def __getattr__(self, nom):
        def methode(*arguments):
            self.appels.append((nom, arguments))
            if self.panne:
                raise self.panne
        return methode


class Lunettes:
    def __init__(self, phrases):
        self.phrases = list(phrases)
        self.paroles = []

    def ecouter(self):
        if not self.phrases:
            raise EOFError  # Ctrl-D dans le terminal
        return self.phrases.pop(0)

    def parler(self, texte):
        self.paroles.append(texte)


@pytest.mark.parametrize(
    "commande, appel",
    [
        ("nouvelle amical noir", ("demarrer_partie", (ModeJeu.AMICAL, Couleur.NOIR))),
        ("NOUVELLE officiel blanc", ("demarrer_partie", (ModeJeu.OFFICIEL, Couleur.BLANC))),
        ("conseil", ("conseiller_coup", ())),
        ("suivre", ("suivre_partie", ())),
        ("expliquer", ("expliquer_coup", ())),
        ("joue", ("jouer_contre_moi", ())),
        ("analyse", ("analyser_partie", ())),
        ("import AbCd1234", ("importer_partie", ("AbCd1234",))),
        ("pgn", ("exporter_pgn", ())),
    ],
)
def test_CON01_chaque_commande_appelle_jarvis(commande, appel):
    jarvis = JarvisEspion()

    executer_commande(jarvis, commande)

    assert jarvis.appels == [appel]


@pytest.mark.parametrize("commande", ["", "danse", "nouvelle", "nouvelle rapide blanc", "nouvelle amical vert", "import"])
def test_CON02_commande_inconnue_ou_incomplete_renvoie_l_aide(commande):
    jarvis = JarvisEspion()

    assert executer_commande(jarvis, commande) == AIDE
    assert jarvis.appels == []


def test_CON03_une_erreur_prevue_est_dite_et_la_boucle_continue():
    jarvis = JarvisEspion(panne=AucunePartie("Aucune partie en cours : démarre ou importe une partie."))
    lunettes = Lunettes(["conseil", "danse", "quitter"])

    boucle(jarvis, lunettes)

    assert lunettes.paroles == [
        AIDE,
        "Erreur : Aucune partie en cours : démarre ou importe une partie.",
        AIDE,
        "À bientôt !",
    ]


def test_CON03_ctrl_d_quitte_proprement():
    lunettes = Lunettes([])

    boucle(JarvisEspion(), lunettes)

    assert lunettes.paroles[-1] == "À bientôt !"


def test_CON04_sans_cle_groq_code_2_et_message_clair(monkeypatch, mocker, capsys):
    mocker.patch("jagvis_echecs.console.load_dotenv")  # ne pas relire le vrai .env
    monkeypatch.delenv("GROQ_KEY", raising=False)

    code = main()

    assert code == 2
    sorties = capsys.readouterr()
    assert sorties.err == "Erreur : la variable GROQ_KEY n'est pas définie.\n"
    assert "Traceback" not in sorties.out + sorties.err


def test_CON04_avec_une_cle_jarvis_demarre_puis_quitte(monkeypatch, mocker, tmp_path):
    mocker.patch("jagvis_echecs.console.load_dotenv")
    monkeypatch.setenv("GROQ_KEY", "cle-de-test")  # construire le client Groq n'appelle pas le réseau
    monkeypatch.setenv("JAGVIS_PARTIES", str(tmp_path / "parties"))
    boucle_lancee = mocker.patch("jagvis_echecs.console.boucle")

    assert main() == 0
    jarvis, lunettes = boucle_lancee.call_args.args
    assert lunettes is jarvis.lunettes
    assert (tmp_path / "parties").is_dir()
