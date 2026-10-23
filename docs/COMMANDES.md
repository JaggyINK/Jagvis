# Les commandes à taper

Toujours depuis le dossier du projet :

```bash
cd "/Users/anna/Documents/cours/dev/projet cour jagvis/Jagvis"
```

Astuce : après `source .venv/bin/activate`, tu peux écrire `pytest` et `python`
au lieu de `.venv/bin/pytest` et `.venv/bin/python`.

---

## 1. Installer (une seule fois)

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
echo "GROQ_KEY=ta_cle_groq" > .env      # ne jamais commiter ce fichier
```

**Stockfish 19** est déjà installé dans `~/.local/bin/stockfish`. Pour vérifier :
`which stockfish`. Pour le réinstaller sans Homebrew :

```bash
cd /tmp
curl -LO https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-macos-universal.tar.gz
shasum -a 256 stockfish-macos-universal.tar.gz   # comparer avec l'empreinte de la page GitHub
tar -xzf stockfish-macos-universal.tar.gz stockfish/stockfish-macos-universal
install -m 755 stockfish/stockfish-macos-universal ~/.local/bin/stockfish
```

---

## 2. Lancer les tests

| Ce que tu veux | Commande |
|---|---|
| **Tous les tests** (gratuit, sans réseau) | `.venv/bin/pytest` → `201 passed, 3 deselected` |
| Le nom de chaque test | `.venv/bin/pytest -v` |
| S'arrêter au premier échec | `.venv/bin/pytest -x` |
| Relancer ceux qui ont échoué | `.venv/bin/pytest --lf` |
| Seulement les tests unitaires | `.venv/bin/pytest tests/unit` |
| Seulement acceptation et bout en bout | `.venv/bin/pytest tests/functional` |
| Un seul fichier | `.venv/bin/pytest tests/unit/test_jarvis.py` |
| Une exigence | `.venv/bin/pytest -k JAR03` |
| Toutes les règles fair-play | `.venv/bin/pytest -k "JAR04 or MOD08"` |
| Les scénarios complets | `.venv/bin/pytest -k "E1 or E2 or E3"` |

Les identifiants sont dans le nom des tests : `MOD` modèle, `RES` résultats,
`HIS` historique, `ENG` moteur, `LIC` Lichess, `LLM` assistant, `BRD` lecture de
la photo, `GLS` lunettes, `JAR` Jarvis, `CON` console, `E1`–`E5` scénarios.

### Couverture

```bash
.venv/bin/pytest --cov=jagvis_chess --cov-report=term-missing   # dans le terminal → 100 %
.venv/bin/pytest --cov=jagvis_chess --cov-report=html && open htmlcov/index.html
.venv/bin/pytest --cov=jagvis_chess --cov-fail-under=90          # échoue sous 90 %
```

### Avec les vrais services (exclus par défaut)

| Commande | Ce que ça teste | Attention |
|---|---|---|
| `.venv/bin/pytest -m stockfish -rs` | le vrai Stockfish (ENG-07) | — |
| `.venv/bin/pytest -m groq -rs` | le vrai Groq (LLM-05, BRD-07) | ⚠️ consomme du quota |
| `.venv/bin/pytest -m ""` | absolument tout | ⚠️ appelle aussi Groq |

BRD-07 a besoin d'une vraie photo : `tests/photos/start.jpg` (position de départ).
`-rs` affiche pourquoi un test est sauté.

---

## 3. Jouer sans les lunettes

Le terminal remplace les lunettes. Jarvis écrit ce qu'il dit (`[Jarvis] …`), et une
« photo » est une image sur ton disque.

```bash
.venv/bin/python -m jagvis_chess.console
```

Pour les photos : fais une capture d'écran d'un échiquier sur
https://lichess.org/editor (`Cmd + Maj + 4`), ou prends ton échiquier en photo
(JPEG ou PNG, 3 Mo maximum). Quand Jarvis demande `Photo path:`, glisse le fichier
dans le terminal.

| Tape | Effet |
|---|---|
| `new training white` | nouvelle partie (`training`, `friendly` ou `official` ; `white` ou `black`) |
| `advice` | photo → meilleur coup expliqué |
| `follow` | photo → Jarvis note le coup joué (et alerte en cas de gaffe) |
| `explain` | explique le dernier coup |
| `play` | Jarvis joue le coup de l'adversaire |
| `analyze` | précision et liste des erreurs |
| `import AbCd1234` | importe une partie Lichess (les 8 caractères après `lichess.org/`) |
| `pgn` | affiche la partie en PGN |
| `quit` | quitter (ou `Ctrl-D`) |

Essais rapides :
- **Fair-play** : `new official white` puis `advice` → refus, aucune photo demandée.
- **Jarvis joue** : `new training black` puis `play` → Jarvis joue `e4`.
- **Lichess** : `import <id>` puis `analyze` puis `pgn`. Mets
  `LICHESS_USERNAME=ton_pseudo` dans `.env` pour que Jarvis sache quel camp tu jouais.

Les parties sont enregistrées dans `games/`.

---

## 4. Git

```bash
git status
.venv/bin/pytest -q                                        # tout doit être vert
git log --format=%B @{u}..HEAD                             # relire les messages avant d'envoyer
git push                                                   # vers ton fork uniquement
```

On ne pousse jamais vers `upstream` (le dépôt du prof) : c'est bloqué volontairement.

Nettoyer les fichiers générés : `rm -rf .pytest_cache .coverage htmlcov`
