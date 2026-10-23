# Toutes les commandes à taper

Toutes les commandes se lancent **depuis le dossier du projet** :

```bash
cd "/Users/anna/Documents/cours/dev/projet cour jagvis/Jagvis"
```

> Astuce : si tu tapes `source .venv/bin/activate` une fois dans ton terminal, tu
> peux écrire `pytest` et `python` au lieu de `.venv/bin/pytest` et
> `.venv/bin/python`. Pour quitter : `deactivate`.

---

## 1. Installer (une seule fois)

```bash
# Créer l'environnement Python 3.12
uv venv --python 3.12 .venv

# Installer les dépendances (application + tests)
uv pip install --python .venv/bin/python -r requirements-dev.txt

# La clé Groq, dans le fichier .env (ne jamais le commiter)
echo "GROQ_KEY=ta_cle_groq" > .env
```

Vérifier que tout est prêt :

```bash
.venv/bin/python --version          # doit afficher Python 3.12.x
.venv/bin/pytest --collect-only -q  # doit trouver 201 tests (+ 3 désélectionnés)
```

---

## 2. Les tests de tous les jours (sans Internet, sans Stockfish, gratuits)

| Ce que tu veux | Commande |
|---|---|
| **Lancer tous les tests** | `.venv/bin/pytest` |
| Résultat court | `.venv/bin/pytest -q` |
| Voir le nom de chaque test | `.venv/bin/pytest -v` |
| S'arrêter au premier échec | `.venv/bin/pytest -x` |
| Relancer seulement ceux qui ont échoué | `.venv/bin/pytest --lf` |
| Voir les `print()` pendant les tests | `.venv/bin/pytest -s` |

Résultat attendu : `201 passed, 3 deselected`. Les 3 tests désélectionnés sont
ceux qui utilisent le vrai Stockfish ou le vrai Groq (voir §5).

---

## 3. Lancer une partie des tests

### Par niveau

```bash
.venv/bin/pytest tests/unit          # tests unitaires (une classe à la fois)
.venv/bin/pytest tests/functional    # tests d'acceptation (E1–E3) et de bout en bout (E4–E5)
```

### Par fichier (un fichier = un module)

```bash
.venv/bin/pytest tests/unit/test_model.py           # Game, Position, Move
.venv/bin/pytest tests/unit/test_results.py         # gravité, précision
.venv/bin/pytest tests/unit/test_history.py         # sauvegarde JSON
.venv/bin/pytest tests/unit/test_engine.py          # Stockfish (faux moteur)
.venv/bin/pytest tests/unit/test_lichess_import.py  # import Lichess (faux réseau)
.venv/bin/pytest tests/unit/test_assistant.py       # LLM (faux Groq)
.venv/bin/pytest tests/unit/test_board_reader.py    # photo → FEN (faux Groq)
.venv/bin/pytest tests/unit/test_glasses.py         # lunettes console
.venv/bin/pytest tests/unit/test_jarvis.py          # Jarvis, le chef d'orchestre
.venv/bin/pytest tests/unit/test_console.py         # commandes du terminal
.venv/bin/pytest tests/functional/test_acceptance.py
.venv/bin/pytest tests/functional/test_cli.py
```

### Par exigence (l'identifiant est dans le nom du test)

```bash
.venv/bin/pytest -k JAR03              # l'ordre de suggest_move
.venv/bin/pytest -k JAR04              # le refus en mode officiel
.venv/bin/pytest -k "JAR04 or MOD08"   # toutes les règles fair-play
.venv/bin/pytest -k MOD                # tout le modèle (MOD-01 à MOD-10)
.venv/bin/pytest -k "E1 or E2 or E3"   # les scénarios d'acceptation
.venv/bin/pytest -k blunder            # tous les tests dont le nom contient « blunder »
```

Les préfixes : `MOD` modèle, `RES` résultats, `HIS` historique, `ENG` moteur,
`LIC` Lichess, `LLM` assistant, `BRD` lecture de la photo, `GLS` lunettes,
`JAR` Jarvis, `CON` console, `E1`–`E5` acceptation et bout en bout.

### Un seul test précis

```bash
.venv/bin/pytest "tests/unit/test_jarvis.py::test_JAR03_advice_checks_the_fair_play_rule_first"
```

---

## 4. La couverture (quelle part du code est testée)

```bash
# Dans le terminal, avec les lignes non testées
.venv/bin/pytest --cov=jagvis_chess --cov-report=term-missing

# En page web : ouvre ensuite htmlcov/index.html
.venv/bin/pytest --cov=jagvis_chess --cov-report=html
open htmlcov/index.html

# Échoue si la couverture passe sous 90 % (comme le demande le TP)
.venv/bin/pytest --cov=jagvis_chess --cov-fail-under=90
```

Résultat attendu : `TOTAL ... 100%`.

---

## 5. Les tests avec les vrais services (lents, et Groq consomme du quota)

Ces tests sont **exclus par défaut**. Ils sont **sautés** si l'outil ou la clé manque.

| Ce que tu veux | Commande | Il faut |
|---|---|---|
| Le vrai Stockfish (ENG-07) | `.venv/bin/pytest -m stockfish` | Stockfish installé (§6) |
| Le vrai Groq (LLM-05, BRD-07) | `.venv/bin/pytest -m groq` | `GROQ_KEY` dans `.env` ⚠️ coûte du quota |
| Les deux | `.venv/bin/pytest -m "stockfish or groq"` | ⚠️ coûte du quota |
| **Absolument tout** | `.venv/bin/pytest -m ""` | ⚠️ appelle aussi Groq |
| Voir pourquoi un test est sauté | ajouter `-rs`, par ex. `.venv/bin/pytest -m stockfish -rs` | |

BRD-07 (le modèle de vision sur une vraie photo) a aussi besoin d'une photo :
`tests/photos/start.jpg`, un échiquier en position de départ.

---

## 6. Installer Stockfish (nécessaire pour jouer pour de vrai)

Sans Stockfish, les commandes `advice`, `explain`, `play` et `analyze` de la
console répondent `Error: Stockfish is missing or not answering`.

Homebrew n'est pas installé sur ce Mac. Deux possibilités :

**A. Installer Homebrew, puis Stockfish** (le plus simple ensuite) :

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install stockfish
which stockfish        # doit afficher un chemin
```

**B. Sans Homebrew** : télécharge la version macOS (Apple Silicon) sur
https://stockfishchess.org/download/ et décompresse-la. Puis indique son chemin
dans `.env` :

```bash
echo 'STOCKFISH_PATH=/chemin/vers/stockfish' >> .env
```

Vérifier : `.venv/bin/pytest -m stockfish -rs` doit afficher `1 passed`.

---

## 7. Utiliser Jarvis sans les lunettes

En attendant les lunettes, **le terminal joue leur rôle** : Jarvis écrit ce qu'il
« dit » (`[Jarvis] …`), et une « photo » est **un fichier image sur ton disque**.

```bash
.venv/bin/python -m jagvis_chess.console
```

### Obtenir des « photos » d'échiquier

- Le plus simple : une **capture d'écran** d'un échiquier sur
  https://lichess.org/editor (`Cmd + Maj + 4`, puis sélectionner le plateau). Elle
  est enregistrée en PNG sur le Bureau.
- Ou une **photo** de ton vrai échiquier, prise avec ton téléphone (JPEG ou PNG,
  3 Mo maximum).
- Quand Jarvis demande `Photo path:`, **glisse le fichier dans le terminal** puis
  appuie sur Entrée.

### Les commandes de la console

| Tape | Effet | Il faut |
|---|---|---|
| `new training white` | nouvelle partie d'entraînement, tu as les Blancs | — |
| `new friendly black` | partie amicale, tu as les Noirs | — |
| `new official white` | partie officielle (aucune aide pendant la partie) | — |
| `advice` | photo → meilleur coup expliqué | Groq + Stockfish |
| `follow` | photo → Jarvis note le coup joué (et alerte si gaffe) | Groq (+ Stockfish pour l'alerte) |
| `explain` | explique le dernier coup joué | Stockfish (+ Groq pour l'explication) |
| `play` | Jarvis joue le coup de l'adversaire | Stockfish |
| `analyze` | analyse de la partie (précision, gaffes) | Stockfish |
| `import AbCd1234` | importe une partie Lichess par son identifiant | Internet |
| `pgn` | affiche la partie au format PGN | — |
| `quit` (ou `Ctrl-D`) | quitter | — |

### Scénarios d'essai

**Sans Stockfish (dès maintenant)** : importer puis exporter une partie Lichess.

```
import AbCd1234     ← remplace par l'id d'une de tes parties (les 8 caractères après lichess.org/)
pgn
quit
```

Pour que Jarvis sache quel camp tu jouais : `echo 'LICHESS_USERNAME=ton_pseudo' >> .env`

**Avec Stockfish : vérifier le fair-play**

```
new official white
advice          → « Official mode: I give no advice during the game. Good luck! » (aucune photo demandée)
quit
```

**Avec Stockfish : un conseil**

```
new training white
advice          → glisse la capture de la position de départ
quit
```

**Avec Stockfish : suivre une partie, puis l'analyser**

Prends une capture après chaque coup, puis tape `follow` et donne la capture
correspondante. À la fin : `analyze` puis `pgn`. Les parties sont enregistrées
dans le dossier `games/`.

---

## 8. Git : avant de pousser

```bash
git status                              # rien d'oublié ?
.venv/bin/pytest -q                     # tout est vert ?
git log --format=%B origin/feature/jarvis-chess..HEAD | grep -ic claude   # doit afficher 0
git push                                # pousse feature/jarvis-chess sur ton fork
```

Ne jamais pousser vers `upstream`, le dépôt du prof. Il est bloqué volontairement
(`NE-PAS-POUSSER-chez-le-prof`).

---

## 9. Nettoyer les fichiers générés

```bash
rm -rf .pytest_cache .coverage htmlcov
find . -name __pycache__ -not -path "./.venv/*" -prune -exec rm -rf {} +
```
