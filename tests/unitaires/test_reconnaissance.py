import base64
from pathlib import Path

import pytest

from jagvis_echecs.erreurs import PhotoInvalide, ReconnaissanceImpossible, ServiceIndisponible
from jagvis_echecs.modele import Couleur, Position
from jagvis_echecs.reconnaissance import MODELE_VISION, TAILLE_MAX_PHOTO, ReconnaissancePlateau
from tests.doubles import PHOTO_PNG, FauxClientGroq

PHOTO_JPEG = b"\xff\xd8\xff\xe0" + b"fausse image"
DEPART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
APRES_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
PHOTO_REELLE = Path(__file__).parent.parent / "photos" / "depart.jpg"


@pytest.mark.parametrize(
    "photo, message",
    [
        (b"", "La photo est vide."),
        (None, "La photo est vide."),
        (b"GIF89a" + b"x", "Format de photo non pris en charge : JPEG ou PNG attendu."),
        (PHOTO_PNG + b"x" * TAILLE_MAX_PHOTO, "La photo dépasse 4 Mo."),
    ],
)
def test_REC01_photo_refusee_avant_tout_appel(photo, message):
    client = FauxClientGroq([])

    with pytest.raises(PhotoInvalide, match=message):
        ReconnaissancePlateau(client=client).detecter_position(photo)
    assert client.appels == []


@pytest.mark.parametrize("photo, type_mime", [(PHOTO_PNG, "image/png"), (PHOTO_JPEG, "image/jpeg")])
def test_REC02_la_photo_est_envoyee_au_modele_de_vision(photo, type_mime):
    client = FauxClientGroq([DEPART])

    ReconnaissancePlateau(client=client).detecter_position(photo)

    appel = client.appels[0]
    assert appel["model"] == MODELE_VISION
    assert appel["temperature"] == 0
    contenu = appel["messages"][0]["content"]
    image = next(partie for partie in contenu if partie["type"] == "image_url")
    attendu = f"data:{type_mime};base64,{base64.b64encode(photo).decode()}"
    assert image["image_url"]["url"] == attendu


def test_REC03_la_fen_est_extraite_du_texte_du_modele():
    client = FauxClientGroq([f"Bien sûr ! Voici la position :\n```\n{APRES_E4}\n```"])

    position = ReconnaissancePlateau(client=client).detecter_position(PHOTO_PNG)

    assert position == Position(APRES_E4)
    assert position.trait == Couleur.NOIR


def test_REC04_placement_seul_complete_avec_valeurs_par_defaut():
    client = FauxClientGroq(["rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"])

    position = ReconnaissancePlateau(client=client).detecter_position(PHOTO_PNG)

    assert position.fen == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w - - 0 1"


@pytest.mark.parametrize(
    "reponse, message",
    [
        ("Je ne vois pas d'échiquier.", "Je n'ai pas reconnu d'échiquier sur la photo."),
        ("8/8/8/8/8/8/8/8 w - - 0 1", "La position reconnue n'est pas valide"),
        ("rnbqkbnr/pppppppp/9/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1", "pas reconnu|pas valide"),
    ],
)
def test_REC05_reponse_sans_position_valide(reponse, message):
    client = FauxClientGroq([reponse])

    with pytest.raises(ReconnaissanceImpossible, match=message):
        ReconnaissancePlateau(client=client).detecter_position(PHOTO_PNG)


@pytest.mark.parametrize("panne, message", [
    (ConnectionError("timeout"), "Le service de langage est indisponible."),
    (None, "Le service de langage n'a rien répondu."),
])
def test_REC06_groq_en_panne_ou_muet(panne, message):
    client = FauxClientGroq([panne])

    with pytest.raises(ServiceIndisponible, match=message):
        ReconnaissancePlateau(client=client).detecter_position(PHOTO_PNG)


@pytest.mark.groq
@pytest.mark.skipif(not PHOTO_REELLE.exists(), reason="ajoute tests/photos/depart.jpg pour ce test")
def test_REC07_le_vrai_modele_reconnait_une_vraie_photo():
    position = ReconnaissancePlateau().detecter_position(PHOTO_REELLE.read_bytes())

    # On vérifie l'effet (une position valide), pas le texte du modèle.
    assert isinstance(position, Position)
