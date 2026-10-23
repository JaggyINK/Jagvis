"""The Groq client: built from the GROQ_KEY variable, and a safe way to call it."""
import os

from groq import Groq

from jagvis_chess.errors import ConfigError, ServiceDown


def make_groq_client():
    key = os.environ.get("GROQ_KEY")
    if not key:
        raise ConfigError("the GROQ_KEY variable is not set.")
    return Groq(api_key=key)


def ask_groq(client, model, messages):
    """Send the messages and give back the answer text, without spaces around.

    Any problem (network, quota, wrong key) becomes ServiceDown. The first
    error is kept inside ("from error") to help with debugging.
    """
    try:
        response = client.chat.completions.create(model=model, messages=messages, temperature=0)
    except Exception as error:
        raise ServiceDown("The language service is down.") from error
    text = response.choices[0].message.content
    if not text or not text.strip():
        raise ServiceDown("The language service gave an empty answer.")
    return text.strip()
