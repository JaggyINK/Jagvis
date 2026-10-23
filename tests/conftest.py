import os
import shutil

import pytest
from dotenv import load_dotenv

load_dotenv()

# Les tests marqués « stockfish » ou « groq » sont sautés si l'outil ou la clé manque,
# même quand on les demande avec -m.
NO_STOCKFISH = shutil.which("stockfish") is None
NO_GROQ_KEY = not os.environ.get("GROQ_KEY")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "stockfish" in item.keywords and NO_STOCKFISH:
            item.add_marker(pytest.mark.skip(reason="Stockfish is not installed"))
        if "groq" in item.keywords and NO_GROQ_KEY:
            item.add_marker(pytest.mark.skip(reason="GROQ_KEY is not set"))
