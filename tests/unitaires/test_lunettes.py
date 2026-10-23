import pytest

from jagvis_echecs.erreurs import PhotoInvalide
from jagvis_echecs.lunettes import Lunettes, LunettesConsole


class Console:
    """Remplace input() et print() : réponses préparées, sorties enregistrées."""

    def __init__(self, reponses=()):
        self.reponses = list(reponses)
        self.questions = []
        self.sorties = []

    def lire(self, question):
        self.questions.append(question)
        return self.reponses.pop(0)

    def ecrire(self, texte):
        self.sorties.append(texte)


def lunettes_console(*reponses):
    console = Console(reponses)
    return LunettesConsole(lire=console.lire, ecrire=console.ecrire), console


def test_LUN01_lunettes_est_une_interface():
    with pytest.raises(TypeError):
        Lunettes()

    class LunettesIncompletes(Lunettes):
        def parler(self, texte):
            pass

    with pytest.raises(TypeError):
        LunettesIncompletes()


def test_LUN02_parler_afficher_ecouter():
    lunettes, console = lunettes_console("  conseil  ")

    lunettes.parler("Joue e4.")
    lunettes.afficher("1. e4")
    entendu = lunettes.ecouter()

    assert console.sorties == ["[Jarvis] Joue e4.", "1. e4"]
    assert entendu == "conseil"


def test_LUN03_prendre_photo_lit_le_fichier_indique(tmp_path):
    photo = tmp_path / "mon plateau.jpg"
    photo.write_bytes(b"\xff\xd8 octets")
    # Glisser un fichier dans le terminal macOS l'entoure parfois de guillemets.
    lunettes, console = lunettes_console(f"'{photo}' ")

    assert lunettes.prendre_photo() == b"\xff\xd8 octets"
    assert console.questions == ["Chemin de la photo : "]


@pytest.mark.parametrize("chemin", ["/n/existe/pas.jpg", "{dossier}"])
def test_LUN03_photo_introuvable(tmp_path, chemin):
    lunettes, _ = lunettes_console(chemin.format(dossier=tmp_path))

    with pytest.raises(PhotoInvalide, match="Photo introuvable"):
        lunettes.prendre_photo()
