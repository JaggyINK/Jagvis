"""Le client Groq : construction à partir de GROQ_KEY et appel protégé."""
import os

from groq import Groq

from jagvis_echecs.erreurs import ConfigurationInvalide, ServiceIndisponible


def creer_client_groq():
    cle = os.environ.get("GROQ_KEY")
    if not cle:
        raise ConfigurationInvalide("la variable GROQ_KEY n'est pas définie.")
    return Groq(api_key=cle)


def demander_a_groq(client, modele, messages):
    """Envoie les messages et renvoie le texte de la réponse, sans espaces autour.

    Toute panne (réseau, quota, clé refusée) devient ServiceIndisponible, avec
    l'erreur d'origine chaînée pour le débogage.
    """
    try:
        reponse = client.chat.completions.create(model=modele, messages=messages, temperature=0)
    except Exception as erreur:
        raise ServiceIndisponible("Le service de langage est indisponible.") from erreur
    texte = reponse.choices[0].message.content
    if not texte or not texte.strip():
        raise ServiceIndisponible("Le service de langage n'a rien répondu.")
    return texte.strip()
