import os

from groq import Groq

from jagvis_chess.errors import ConfigError, ServiceDown


def make_groq_client():
    key = os.environ.get("GROQ_KEY")
    if not key:
        raise ConfigError("the GROQ_KEY variable is not set.")
    return Groq(api_key=key)


def ask_groq(client, model, messages):
    try:
        response = client.chat.completions.create(model=model, messages=messages, temperature=0)
    except Exception as error:  # réseau, quota, mauvaise clé...
        raise ServiceDown("The language service is down.") from error
    text = response.choices[0].message.content
    if not text or not text.strip():
        raise ServiceDown("The language service gave an empty answer.")
    return text.strip()
