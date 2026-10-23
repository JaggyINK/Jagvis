# Suivi du projet Jagvis — Jarvis Chess

> Fichier de suivi **mis à jour après chaque demande**. Il sert à ne pas perdre le
> fil et à faciliter la revue de code : ce qui est fait, pourquoi, où le vérifier,
> et ce qui reste à faire.
>
> Dernière mise à jour : 23/10/2026, demande n°3. Branche : `feature/jarvis-echecs`.

---

## 1. L'idée en une phrase

Le joueur porte des lunettes connectées (Meta). Pendant une partie d'échecs, les
lunettes **photographient l'échiquier**, Jarvis **reconnaît la position** (modèle de
vision Groq), **demande le meilleur coup à Stockfish**, le fait **expliquer par un
LLM** (Groq) et **le dit à voix haute**. Jarvis suit aussi la partie, prévient en cas
de gaffe, analyse la partie terminée, l'importe depuis Lichess et l'exporte en PGN.

**Règle fair-play** : en mode **OFFICIAL**, Jarvis ne donne **aucun conseil**, ne
prend **aucune photo pour conseiller** et ne lance **aucune alerte** pendant la
partie. Il fait seulement le suivi, puis l'analyse une fois la partie finie.

Références : `docs/jarvis_echecs_classes.puml` (diagramme de classes validé par le
prof), `docs/jarvis_echecs_cas_utilisation.puml` et les recommandations du TP
« Mini-JARVIS » (non commité : c'est l'énoncé du prof, le dépôt est public).

---

## 2. Comment lancer

```bash
uv venv --python 3.12 .venv               # une seule fois
uv pip install --python .venv/bin/python -r requirements-dev.txt

.venv/bin/pytest                           # tous les tests SANS réseau ni Stockfish
.venv/bin/pytest --cov=jagvis_chess --cov-report=term-missing   # + couverture
.venv/bin/pytest -m stockfish              # vrai Stockfish (brew install stockfish)
.venv/bin/pytest -m groq                   # vraie API Groq : coûte du quota !

.venv/bin/python -m jagvis_chess.console   # Jarvis dans le terminal (lunettes simulées)
```

Commandes de la console : `new <training|friendly|official> <white|black>`,
`advice`, `follow`, `explain`, `play`, `analyze`, `import <id lichess>`, `pgn`, `quit`.

Variables d'environnement (fichier `.env`, jamais commité) :

| Variable | Rôle | Défaut |
|---|---|---|
| `GROQ_KEY` | clé API Groq | **obligatoire** |
| `STOCKFISH_PATH` | chemin du programme Stockfish | `stockfish` |
| `JAGVIS_GAMES` | dossier de l'historique (JSON) | `games` |
| `LICHESS_USERNAME` | ton pseudo Lichess, pour savoir quel camp tu jouais | aucun (Blancs) |
| `LICHESS_TOKEN` | jeton Lichess (facultatif, l'API est publique) | aucun |

---

## 3. Le code est en anglais : correspondance avec le diagramme

Tu as demandé du code en anglais, avec des noms simples. Le diagramme du prof
reste en français dans `docs/`. Voici la table pour passer de l'un à l'autre.

| Diagramme (français) | Code (anglais) | Fichier |
|---|---|---|
| `Jarvis` | `Jarvis` | `jarvis.py` |
| `lunettes`, `reconnaissance`, `moteur`, `assistant`, `historique`, `import_lichess`, `partie_en_cours` | `glasses`, `board_reader`, `engine`, `assistant`, `history`, `lichess_import`, `current_game` | `jarvis.py` |
| `demarrer_partie(mode, couleur)` | `start_game(mode, color)` | |
| `suivre_partie()` | `follow_game()` | |
| `conseiller_coup()` | `suggest_move()` | |
| `expliquer_coup()` | `explain_move()` | |
| `jouer_contre_moi()` | `play_against_me()` | |
| `analyser_partie()` | `analyze_game()` | |
| `importer_partie(id_lichess)` | `import_game(lichess_id)` | |
| `exporter_pgn()` | `export_pgn()` | |
| `Lunettes` : `prendre_photo`, `ecouter`, `parler`, `afficher` | `Glasses` : `take_photo`, `listen`, `speak`, `show` | `glasses.py` |
| `ReconnaissancePlateau` : `modele`, `detecter_position(photo)` | `BoardReader` : `model`, `read_position(photo)` | `board_reader.py` |
| `MoteurEchecs` : `chemin_stockfish`, `profondeur`, `evaluer`, `analyser` | `ChessEngine` : `stockfish_path`, `depth`, `evaluate`, `analyze` | `engine.py` |
| `AssistantLLM` : `modele`, `expliquer(position, evaluation)` | `LLMAssistant` : `model`, `explain(position, evaluation)` | `assistant.py` |
| `ImportLichess` : `token`, `recuperer_partie(id)` | `LichessImport` : `token`, `fetch_game(id)` | `lichess_import.py` |
| `Historique` : `dossier`, `sauvegarder`, `charger`, `lister` | `History` : `folder`, `save`, `load`, `list_games` | `history.py` |
| `Partie` : `id`, `date`, `mode`, `couleur_joueur`, `coups` | `Game` : `id`, `date`, `mode`, `player_color`, `moves` | `model.py` |
| `jouer`, `position_actuelle`, `peut_conseiller`, `est_terminee`, `vers_pgn` | `play`, `current_position`, `can_advise`, `is_over`, `to_pgn` | |
| `Position` : `fen`, `trait`, `coups_legaux()` | `Position` : `fen`, `turn`, `legal_moves()` | |
| `Coup` : `notation`, `couleur` | `Move` : `notation`, `color` | |
| `ModeJeu` : ENTRAINEMENT, AMICAL, OFFICIEL | `GameMode` : TRAINING, FRIENDLY, OFFICIAL | |
| `Couleur` : BLANC, NOIR | `Color` : WHITE, BLACK | |
| `Evaluation` : `meilleur_coup`, `score`, `mat_en` | `Evaluation` : `best_move`, `score`, `mate_in` | `results.py` |
| `Analyse` : `precision`, `erreurs`, `resume()` | `Analysis` : `accuracy`, `bad_moves`, `summary()` | |
| `Erreur` : `coup`, `perte`, `gravite` | `BadMove` : `move`, `loss`, `severity` | |
| `Gravite` : IMPRECISION, ERREUR, GAFFE | `Severity` : INACCURACY, MISTAKE, BLUNDER | |

`Erreur` est devenu `BadMove` (« mauvais coup ») pour ne pas confondre avec les
erreurs Python (`errors.py`) ni avec `Severity.MISTAKE`.

Les messages que Jarvis dit au joueur sont aussi en anglais, pour que tout le code
soit dans une seule langue. On peut les traduire plus tard en un seul endroit par
fichier.

---

## 4. Architecture

```
  terminal ──► console.py   boucle de commandes, attrape JagvisError → « Error: … »
                   │
               ┌───▼────┐
               │ Jarvis │  jarvis.py : le chef d'orchestre, reçoit ses 6 outils
               └───┬────┘
   ┌───────────┬───┴───────┬──────────────┬────────────┬──────────────┐
   ▼           ▼           ▼              ▼            ▼              ▼
 Glasses   BoardReader  ChessEngine   LLMAssistant   History    LichessImport
 glasses.py board_reader engine.py    assistant.py   history.py lichess_import.py
 (interface) photo→FEN   Stockfish    explique       JSON       PGN par HTTP
     │           └──── groq_client.py ────┘  (appel Groq protégé, partagé)
 ConsoleGlasses
 (terminal)

 Données : model.py (Game, Position, Move, GameMode, Color)
 Résultats : results.py (Evaluation, Analysis, BadMove, Severity + calculs de perte et de précision)
 Erreurs : errors.py (JagvisError et ses sous-classes)
```

**Injection de dépendances** (recommandation du TP) : chaque classe **reçoit** ce
qui coûte cher ou passe par le réseau. En test, on donne une fausse version écrite
à la main (`tests/fakes.py`), sans bibliothèque de mock :

| Classe | Ce qu'on lui donne | Fausse version en test |
|---|---|---|
| `ChessEngine` | `open_engine` (lance Stockfish) | `FakeUciEngine` |
| `LLMAssistant`, `BoardReader` | `client` Groq | `FakeGroqClient` |
| `LichessImport` | `download` (HTTP) | `FakeDownload` |
| `ConsoleGlasses` | `read` / `write` (input / print) | `FakeTerminal` |
| `Jarvis` | les 6 outils | `FakeGlasses`, `FakeBoardReader`, `FakeEngine`, `FakeAssistant`, `FakeHistory`, `FakeLichessImport` |

Les fausses versions des outils de Jarvis écrivent toutes dans un même **journal**
(`log`). Le test peut ainsi vérifier l'**ordre exact** des appels.

Ajouts par rapport au diagramme (les signatures du diagramme ne changent pas) :
paramètres d'injection, `Glasses` en classe abstraite avec `ConsoleGlasses`,
`Position.to_board()`, `color_from_turn()`, `severity_of()`, `move_loss()`,
`win_chance()`, `move_accuracy()`, `errors.py`, `groq_client.py`, `console.py`.

---

## 5. Décisions de la section 4 (prises par moi, comme demandé)

| # | Sujet | Décision finale | Pourquoi |
|---|---|---|---|
| 1 | Seuils de gravité | INACCURACY ≥ 50, MISTAKE ≥ 100, BLUNDER ≥ 300 centipions | Seuils classiques des outils d'analyse, faciles à expliquer |
| 1 bis | **Plafond des scores** | Les scores sont **bloqués entre −1000 et +1000** avant le calcul de la perte | Passer de +20 à +15 alors qu'on gagne déjà n'est pas une gaffe |
| 2 | Notation des coups | SAN (`e4`, `Nf3`, `O-O`, `Qh4#`) | C'est la notation des humains et du PGN |
| 3 | `mate_in` | `int` ou `None` | Il n'y a pas toujours de mat |
| 4 | **Précision** | **Formule de Lichess** : chaque coup du joueur reçoit une note de 0 à 100 selon la baisse de ses chances de gagner, la précision est la **moyenne** des notes | Plus juste que « % de coups sans erreur » : une petite imprécision compte un peu, une gaffe compte beaucoup |
| 5 | **Import Lichess** | Partie classée (« Rated ») → OFFICIAL, sinon FRIENDLY. **Le camp du joueur est trouvé avec `LICHESS_USERNAME`** (Blancs par défaut) | Sans ça, l'analyse portait sur les coups de l'adversaire quand on jouait les Noirs |
| 6 | Ajouts hors diagramme | Gardés (voir §4) | Indispensables pour tester sans réseau |
| 7 | **Ordre de `suggest_move`** | **Le fair-play est vérifié en premier** : `can_advise` → photo → position → évaluer → expliquer → parler. En OFFICIAL : `can_advise` → parler, **sans photo** | Aucune photo envoyée à une IA pendant un tournoi (fair-play et vie privée), et aucun appel payant inutile |
| 8 | Alerte de gaffe (cas A4) | Dans `follow_game`, seulement pour les coups du joueur et hors OFFICIAL | Le diagramme n'a pas de méthode dédiée, et c'est pendant le suivi qu'on voit le coup |
| + | **Roques après une photo** | Si le modèle ne donne que les pièces, on garde les roques encore possibles (roi et tour sur leur case de départ) | Avant, on retirait tous les roques : Jarvis ne pouvait jamais conseiller O-O |

Autres choix :
- `explain_move()` explique le **dernier coup joué**. En OFFICIAL, il est refusé
  tant que la partie n'est pas finie.
- `play_against_me()` est refusé en OFFICIAL : l'adversaire y est humain.
- Si le LLM est en panne, le conseil donne quand même le coup (`Best move: e4.`).
- Modèles Groq : texte `openai/gpt-oss-120b` (déjà utilisé par Jagvis), vision
  `meta-llama/llama-4-scout-17b-16e-instruct`. À vérifier dans la console Groq.

---

## 6. Garde-fous et cas d'erreurs

Toutes les erreurs prévues héritent de `JagvisError`. La console les attrape et
dit `Error: <message>`, **sans trace d'exception**. L'erreur technique d'origine
reste attachée (`raise … from …`) pour le débogage.

| Situation | Erreur | Message | Test |
|---|---|---|---|
| FEN mal écrite ou impossible (pas de roi…) | `InvalidFen` | `Invalid FEN: …` | MOD-03 |
| Coup illégal / hors de son tour | `IllegalMove` | `Illegal move: e5` / `It is not black's turn.` | MOD-07 |
| Jouer après mat ou pat | `GameOver` | `The game is over.` | MOD-07, JAR-11 |
| `mode` ou `color` qui n'est pas une enum | `TypeError` | — | MOD-05 |
| Perte négative, précision hors 0–100 | `ValueError` | — | RES-03/04 |
| Identifiant dangereux (`../secret`) | `InvalidId` | `Invalid game id: …` | HIS-05 |
| Partie absente de l'historique | `GameNotFound` | `Game not found: …` | HIS-03 |
| Fichier JSON abîmé ou coup faux dedans | `BrokenSaveFile` | `The file of game … cannot be read.` | HIS-06 |
| Un fichier abîmé dans le dossier | ignoré par `list_games()` | — | HIS-06 |
| Profondeur hors 1–30 | `ConfigError` | `The depth must be between 1 and 30.` | ENG-01 |
| Stockfish absent ou qui plante (toujours fermé ensuite) | `ServiceDown` | `Stockfish is missing or not answering: …` | ENG-05 |
| Évaluer une position finie | `GameOver` | `The game is over: there is no move to suggest.` | ENG-04 |
| Identifiant Lichess mal formé (avant tout réseau) | `InvalidId` | `Invalid Lichess id: …` | LIC-04 |
| Lichess : 404 / 429 / 500 / pas de réseau / plus de 10 s | `GameNotFound` / `ServiceDown` | voir `lichess_import.py` | LIC-06 |
| PGN illisible, vide, sans coup, variante | `InvalidPgn` | `The Lichess game cannot be read.` … | LIC-05 |
| `GROQ_KEY` absente | `ConfigError` | `the GROQ_KEY variable is not set.` | LLM-04, CON-04, E4 |
| Groq en panne / réponse vide | `ServiceDown` | `The language service is down.` / `… gave an empty answer.` | LLM-03, BRD-06 |
| Photo vide, pas JPEG/PNG, > 3 Mo (4 Mo en base64 = limite Groq) | `InvalidPhoto` | `The photo is empty.` … | BRD-01 |
| Photo introuvable sur le disque | `InvalidPhoto` | `Photo not found: …` | GLS-03 |
| Pas de FEN dans la réponse / FEN impossible | `BoardNotFound` | `I could not see a chessboard on the photo.` … | BRD-05 |
| Position vue impossible pour le camp du joueur | `BoardNotFound` | `… cannot be played by white.` | JAR-06 |
| Aucun coup légal ne mène à la position vue | `BoardNotFound` | `… does not match any legal move.` | JAR-08 |
| Action sans partie en cours (pas même une photo) | `NoGame` | `No current game: start or import a game.` | JAR-05 |
| **Conseil en OFFICIAL** | refus dit et renvoyé, **sans photo** | `Official mode: I give no advice during the game. Good luck!` | MOD-08, JAR-04, E2 |
| Analyse en OFFICIAL avant la fin | `NotAllowed` | `In official mode, the analysis is only possible after the game.` | JAR-12 |
| Jarvis joue en OFFICIAL / pas son tour | `NotAllowed` | `In official mode your opponent is a human…` / `It is your turn.` | JAR-11 |
| LLM en panne pendant un conseil | **mode dégradé** : le coup est quand même donné | `Best move: e4.` | JAR-07 |
| Moteur en panne pendant l'alerte | alerte ignorée, le suivi continue | — | JAR-09 |
| Gagner largement puis perdre un peu | pas d'alerte (scores plafonnés) | — | RES-05, ENG-06, JAR-09 |
| Import Lichess raté | la partie en cours ne change pas | — | JAR-13 |
| Commande inconnue, Ctrl-D | aide affichée / sortie propre | — | CON-02/03 |

---

## 7. Exigences et tests

| Id | Exigence | Fichier |
|---|---|---|
| **E1–E3** | Acceptation : conseil complet ; refus OFFICIAL sans photo ni IA ; partie suivie + alerte + analyse + sauvegarde + PGN | `tests/functional/test_acceptance.py` |
| **E4–E5** | E2E : `python -m jagvis_chess.console` sans clé (code 2), session puis `quit` (code 0) | `tests/functional/test_cli.py` |
| MOD-01…10 | Enums, Move, Position, Game (jouer, refus, fair-play, fin, PGN relu) | `tests/unit/test_model.py` |
| RES-01…07 | Gravité, Evaluation, BadMove, Analysis, **perte plafonnée, chance de gain, note d'un coup** | `test_results.py` |
| HIS-01…06 | Aller-retour JSON, tri, introuvable, dossier créé, id dangereux, fichier abîmé | `test_history.py` |
| ENG-01…07 | Réglages, evaluate, mat, position finie, pannes, analyze, vrai Stockfish (`@stockfish`) | `test_engine.py` |
| LIC-01…07 | URL, PGN → Game, mode, id invalide, PGN inutilisable, pannes HTTP, **camp via le pseudo** | `test_lichess_import.py` |
| LLM-01…05 | Requête, réponse, pannes, clé, vrai Groq (`@groq`) | `test_assistant.py` |
| BRD-01…07 | Photo refusée, envoi base64, FEN trouvée, **roques devinés**, réponse inutilisable, pannes, vrai Groq (`@groq`) | `test_board_reader.py` |
| GLS-01…03 | Interface abstraite, speak/show/listen, photo depuis un fichier | `test_glasses.py` |
| JAR-01…14 | Jarvis : **ordre de `suggest_move` (fair-play d'abord)**, refus OFFICIAL, trait imposé, mode dégradé, suivi, alerte, explain, play, analyze, import, export | `test_jarvis.py` |
| CON-01…04 | Commandes, aide, erreurs dites sans planter, `main()` | `test_console.py` |

Les tests `@stockfish` et `@groq` sont **exclus par défaut** (`pytest.ini`) et
**sautés automatiquement** si l'outil ou la clé manque (`tests/conftest.py`). Ils
ne vérifient jamais le texte d'un LLM, seulement des effets.

---

## 8. Historique TDD (commits)

| Étape | Commits |
|---|---|
| Demande 2 (code en français) | `chore` mise en place → `red` acceptation E1–E3 → cycles `red/green` MOD, RES, HIS, MOT, LIC, LLM, REC, LUN, JAR, CON + 3 `refactor` |
| Demande 3 | `refactor: translate the code to simple English` (même comportement, mêmes tests) |
| | `red/green: JAR-03, JAR-04, E2` fair-play vérifié en premier |
| | `red/green: RES-05 to RES-07, ENG-06, JAR-09` perte plafonnée + précision Lichess |
| | `red/green: LIC-07` camp du joueur via le pseudo Lichess |
| | `red/green: BRD-04` roques encore possibles |
| | `docs: README section for Jarvis Chess`, `docs: SUIVI.md` |

---

## 9. Guide de revue de code (ordre de lecture)

1. `docs/*.puml` puis la table du §3 : le contrat.
2. `jagvis_chess/errors.py` : toutes les erreurs possibles.
3. `model.py`, puis `results.py`, chacun avec son test dans `tests/unit/`.
4. Les outils : `history.py`, `engine.py`, `lichess_import.py`, `groq_client.py`,
   `assistant.py`, `board_reader.py`, `glasses.py`.
5. `jarvis.py` avec `tests/unit/test_jarvis.py` : lire `test_JAR03` (ordre) et
   `test_JAR04` (fair-play).
6. `tests/functional/test_acceptance.py` : les scénarios complets.
7. `console.py`.

À vérifier pendant la revue :
- [ ] `pytest` passe sans internet (aucun réseau, aucun Stockfish par défaut).
- [ ] Aucun test ne vérifie le texte d'un vrai LLM.
- [ ] Chaque nom du diagramme a son équivalent anglais (§3).
- [ ] Les décisions du §5 te conviennent.

---

## 10. Résultats actuels

- `pytest` : **202 tests réussis**, 3 désélectionnés (`@stockfish`, `@groq`).
- Couverture : **100 %** de `jagvis_chess`. Seules les 2 lignes
  `if __name__ == "__main__"` de `console.py` sont exclues ; elles sont testées en
  sous-processus par E4 et E5.
- Tests marqués : ENG-07 est sauté (Stockfish non installé). LLM-05 et BRD-07 n'ont
  pas été lancés, pour ne pas consommer de quota Groq sans ton accord.

---

## 11. Git et GitHub

- `origin` = `https://github.com/JaggyINK/Jagvis.git` (renommé, lien de fork conservé).
- `upstream` = dépôt du prof, pushurl `NE-PAS-POUSSER-chez-le-prof` (jamais modifié).
- Branches du fork sur GitHub : `main` (ta version), `prof` (version du prof),
  `feature/frontend-conversation-history`.
- ⚠️ `origin/prof` est **en retard** : il est à `db8c2d9`, alors que le prof en est à
  `15d207c` (`upstream/dev`) et `d8305c0` (`upstream/main`). La mise à jour se fait en
  avance rapide (aucun conflit).
- `main` local a 1 commit de plus que `origin/main` (README « Jagvis »).
- `feature/jarvis-echecs` n'est pas encore sur GitHub.
- **Rien n'a été poussé.**

---

## 12. Reste à faire

- [ ] Ta permission pour pousser : `main`, `feature/jarvis-echecs`, et la mise à jour de `prof`.
- [ ] Partie A.2 : où ranger les fichiers non commités du worktree du prof (rien n'a été touché).
- [ ] `brew install stockfish`, puis `pytest -m stockfish`.
- [ ] Ajouter une vraie photo `tests/photos/start.jpg`, puis `pytest -m groq` (coûte du quota).
- [ ] Brancher Jarvis Chess dans l'interface Streamlit de Jagvis (une `StreamlitGlasses`).
- [ ] Bonus du TP : GitHub Actions (`pytest --cov-fail-under=90`) et `REPONSES.md`.
- [ ] Facultatif : traduire aussi en anglais l'appli Streamlit de `main` (`app.py`, `db.py`, `jagvis_agent.py`).

---

## 13. Journal des demandes

| # | Date | Demande | Ce qui a été fait |
|---|---|---|---|
| 1 | 23/10/2026 | Partie A (réparer Git) + plan de la partie B | Worktree réparé, README « Jagvis » sur `main`, plan et 8 questions |
| 2 | 23/10/2026 | Recos du TP, architecture adaptée au diagramme, garde-fous, fichier de suivi | Branche `feature/jarvis-echecs` en TDD, 185 tests, 100 %, création de `SUIVI.md` |
| 3 | 23/10/2026 | Repo renommé ; code en anglais simple ; décider seul de la section 4 ; supprimer les fichiers inutiles | `origin` → `Jagvis.git` ; branches vérifiées ; code traduit (`jagvis_chess`) ; décisions 4, 5 et 7 changées + plafond des scores + roques (TDD) ; suppression de `__main__.py`, `.coveragerc`, des `__init__.py` vides des tests et de 2 copies en double ; 202 tests, 100 % |
