import os
import shutil

import pytest
from dotenv import load_dotenv

load_dotenv()

# Les tests marqués « stockfish » ou « groq » sont sautés automatiquement si
# l'outil ou la clé manque, même quand on les demande avec -m.
STOCKFISH_ABSENT = shutil.which("stockfish") is None
CLE_GROQ_ABSENTE = not os.environ.get("GROQ_KEY")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "stockfish" in item.keywords and STOCKFISH_ABSENT:
            item.add_marker(pytest.mark.skip(reason="Stockfish n'est pas installé"))
        if "groq" in item.keywords and CLE_GROQ_ABSENTE:
            item.add_marker(pytest.mark.skip(reason="GROQ_KEY n'est pas définie"))
