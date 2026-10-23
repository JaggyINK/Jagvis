"""AssistantLLM : explique un coup en langage naturel grâce à un LLM Groq.

Le client Groq est injecté : en test, un faux client rejoue des réponses.
"""
from jagvis_echecs.client_groq import creer_client_groq
from jagvis_echecs.erreurs import ServiceIndisponible

MODELE_TEXTE = "openai/gpt-oss-120b"

CONSIGNE = (
    "Tu es Jarvis, un coach d'échecs qui parle dans des lunettes connectées. "
    "Explique en français, en deux phrases courtes, pourquoi le meilleur coup "
    "proposé par le moteur est bon. Ne propose jamais un autre coup."
)


class AssistantLLM:
    def __init__(self, modele=MODELE_TEXTE, client=None):
        self.modele = modele
        self.client = client or creer_client_groq()

    def expliquer(self, position, evaluation):
        question = (
            f"Position (FEN) : {position.fen}\n"
            f"Trait : {position.trait.value}\n"
            f"Meilleur coup : {evaluation.meilleur_coup.notation}\n"
            f"Évaluation : {evaluation.score} centipions pour le camp au trait"
        )
        if evaluation.mat_en is not None:
            question += f"\nMat en {evaluation.mat_en}"
        messages = [
            {"role": "system", "content": CONSIGNE},
            {"role": "user", "content": question},
        ]
        try:
            reponse = self.client.chat.completions.create(
                model=self.modele, messages=messages, temperature=0
            )
        except Exception as erreur:  # réseau, quota, clé refusée... : tout se vaut ici
            raise ServiceIndisponible("Le service de langage est indisponible.") from erreur
        texte = reponse.choices[0].message.content
        if not texte or not texte.strip():
            raise ServiceIndisponible("Le service de langage n'a rien répondu.")
        return texte.strip()
