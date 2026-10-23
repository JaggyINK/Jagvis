"""Construction du vrai client Groq, à partir de la variable GROQ_KEY."""
import os

from groq import Groq

from jagvis_echecs.erreurs import ConfigurationInvalide


def creer_client_groq():
    cle = os.environ.get("GROQ_KEY")
    if not cle:
        raise ConfigurationInvalide("la variable GROQ_KEY n'est pas définie.")
    return Groq(api_key=cle)
