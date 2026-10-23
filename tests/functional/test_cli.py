# Tests de bout en bout : on lance vraiment « python -m jagvis_chess.console ».
import os
import subprocess
import sys


def start_jarvis(tmp_path, groq_key, typed_text):
    # Une variable déjà définie (même vide) n'est pas remplacée par le fichier .env.
    env = {**os.environ, "GROQ_KEY": groq_key, "JAGVIS_GAMES": str(tmp_path / "games")}
    return subprocess.run(
        [sys.executable, "-m", "jagvis_chess.console"],
        input=typed_text, capture_output=True, text=True, env=env, timeout=30,
    )


def test_E4_without_groq_key(tmp_path):
    result = start_jarvis(tmp_path, groq_key="", typed_text="")

    assert result.returncode == 2
    assert result.stderr == "Error: the GROQ_KEY variable is not set.\n"


def test_E5_a_session_without_game_then_quit(tmp_path):
    result = start_jarvis(tmp_path, groq_key="test-key", typed_text="advice\nquit\n")

    assert result.returncode == 0
    assert "Error: No current game" in result.stdout
    assert "Goodbye!" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr
