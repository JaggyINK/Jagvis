"""Tests end-to-end : on lance vraiment « python -m jagvis_echecs » dans un sous-processus."""
import os
import subprocess
import sys


def lancer_jarvis(tmp_path, groq_key, entree):
    # Une variable déjà définie (même vide) n'est pas écrasée par le fichier .env.
    env = {**os.environ, "GROQ_KEY": groq_key, "JAGVIS_PARTIES": str(tmp_path / "parties")}
    return subprocess.run(
        [sys.executable, "-m", "jagvis_echecs"],
        input=entree, capture_output=True, text=True, env=env, timeout=30,
    )


def test_E4_sans_cle_groq(tmp_path):
    resultat = lancer_jarvis(tmp_path, groq_key="", entree="")

    assert resultat.returncode == 2
    assert resultat.stderr == "Erreur : la variable GROQ_KEY n'est pas définie.\n"


def test_E5_une_session_sans_partie_puis_quitter(tmp_path):
    resultat = lancer_jarvis(tmp_path, groq_key="cle-de-test", entree="conseil\nquitter\n")

    assert resultat.returncode == 0
    assert "Erreur : Aucune partie en cours" in resultat.stdout
    assert "À bientôt !" in resultat.stdout
    assert "Traceback" not in resultat.stdout + resultat.stderr
