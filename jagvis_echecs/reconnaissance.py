"""ReconnaissancePlateau : photo de l'échiquier → Position (FEN).

On envoie la photo à un modèle de vision Groq et on cherche une FEN dans sa
réponse. Le client Groq est injecté : en test, un faux client répond.
"""
import base64
import re

from jagvis_echecs.client_groq import creer_client_groq, demander_a_groq
from jagvis_echecs.erreurs import FenInvalide, PhotoInvalide, ReconnaissanceImpossible
from jagvis_echecs.modele import Position

MODELE_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"
# Groq refuse les images de plus de 4 Mo envoyées en base64.
TAILLE_MAX_PHOTO = 4 * 1024 * 1024

CONSIGNE = (
    "Voici la photo d'un échiquier. Réponds uniquement par la FEN complète de la "
    "position (placement, trait, roques, prise en passant, demi-coups, coups)."
)

# Une rangée : pièces (pnbrqk) et chiffres 1 à 8. Huit rangées séparées par « / ».
RANGEE = r"[pnbrqkPNBRQK1-8]{1,8}"
FEN_DANS_UN_TEXTE = re.compile(
    rf"({RANGEE}(?:/{RANGEE}){{7}})(\s+[wb]\s+(?:-|[KQkq]{{1,4}})\s+(?:-|[a-h][36])\s+\d+\s+\d+)?"
)


def type_mime(photo):
    """Reconnaît le format grâce aux premiers octets du fichier."""
    if photo.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if photo.startswith(b"\x89PNG"):
        return "image/png"
    return None


def verifier_photo(photo):
    if not photo:
        raise PhotoInvalide("La photo est vide.")
    if type_mime(photo) is None:
        raise PhotoInvalide("Format de photo non pris en charge : JPEG ou PNG attendu.")
    if len(photo) > TAILLE_MAX_PHOTO:
        raise PhotoInvalide("La photo dépasse 4 Mo.")


def extraire_fen(texte):
    trouve = FEN_DANS_UN_TEXTE.search(texte)
    if trouve is None:
        raise ReconnaissanceImpossible("Je n'ai pas reconnu d'échiquier sur la photo.")
    placement, suite = trouve.group(1), trouve.group(2)
    # Sans le reste de la FEN, on suppose : Blancs au trait, pas de roque possible.
    return placement + (suite if suite else " w - - 0 1")


class ReconnaissancePlateau:
    def __init__(self, modele=MODELE_VISION, client=None):
        self.modele = modele
        self.client = client or creer_client_groq()

    def detecter_position(self, photo):
        verifier_photo(photo)
        image = f"data:{type_mime(photo)};base64,{base64.b64encode(photo).decode()}"
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": CONSIGNE},
                {"type": "image_url", "image_url": {"url": image}},
            ],
        }]
        fen = extraire_fen(demander_a_groq(self.client, self.modele, messages))
        try:
            return Position(fen)
        except FenInvalide as erreur:
            raise ReconnaissanceImpossible(f"La position reconnue n'est pas valide : {fen}") from erreur
