# Suivi du projet — Jarvis Chess

Mis à jour après chaque demande. Dernière mise à jour : 23/10/2026 (demande n°9).
Branche : `feature/jarvis-chess`.

Pour comprendre l'app : [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Pour les commandes : [`docs/COMMANDES.md`](docs/COMMANDES.md).

---

## 1. Où on en est

- L'app est **complète et testée**, sauf la partie lunettes : on n'a pas encore le SDK
  Meta, donc le terminal joue leur rôle (`ConsoleGlasses`).
- **201 tests** passent en moins d'une seconde, sans réseau ni Stockfish.
  Couverture : **100 %**.
- Avec les vrais services :
  - **Stockfish 19** est installé et ENG-07 passe ;
  - le **vrai Groq** répond et LLM-05 passe ;
  - BRD-07 (lecture d'une vraie photo) attend une photo `tests/photos/start.jpg`.
- Essai réel : l'analyse de `f3 e5 g4 Qh4#` trouve `g4` = gaffe et `f3` = imprécision.

---

## 2. Les fichiers

```
Jagvis/
├── README.md              présentation courte (anglais)
├── SUIVI.md               ce fichier
├── requirements.txt       groq, python-dotenv, python-chess
├── requirements-dev.txt   + pytest, pytest-mock, pytest-cov
├── pytest.ini             exclut les tests « stockfish » et « groq » par défaut
├── docs/
│   ├── ARCHITECTURE.md    comment marche l'app, avec schémas
│   ├── COMMANDES.md       toutes les commandes
│   └── diagrams/          les deux diagrammes du prof (.puml)
├── jagvis_chess/          le code (un fichier par classe ou groupe logique)
└── tests/
    ├── fakes.py           les fausses versions écrites à la main
    ├── conftest.py        saute les tests si Stockfish ou la clé manque
    ├── unit/              un fichier de test par module
    └── functional/        scénarios complets (E1–E3) et console (E4–E5)
```

Fichiers à ne jamais commiter : `.env` (clé Groq), `.venv/`, `games/` (parties sauvegardées).

---

## 3. Diagramme du prof → code

Le code est en anglais, les commentaires en français. Le diagramme reste en français.

| Diagramme | Code |
|---|---|
| `Jarvis` : `demarrer_partie`, `suivre_partie`, `conseiller_coup`, `expliquer_coup`, `jouer_contre_moi`, `analyser_partie`, `importer_partie`, `exporter_pgn` | `Jarvis` : `start_game`, `follow_game`, `suggest_move`, `explain_move`, `play_against_me`, `analyze_game`, `import_game`, `export_pgn` |
| `Lunettes` : `prendre_photo`, `ecouter`, `parler`, `afficher` | `Glasses` : `take_photo`, `listen`, `speak`, `show` |
| `ReconnaissancePlateau.detecter_position` | `BoardReader.read_position` |
| `MoteurEchecs` : `evaluer`, `analyser` | `ChessEngine` : `evaluate`, `analyze` |
| `AssistantLLM.expliquer` | `LLMAssistant.explain` |
| `ImportLichess.recuperer_partie` | `LichessImport.fetch_game` |
| `Historique` : `sauvegarder`, `charger`, `lister` | `History` : `save`, `load`, `list_games` |
| `Partie` : `jouer`, `position_actuelle`, `peut_conseiller`, `est_terminee`, `vers_pgn` | `Game` : `play`, `current_position`, `can_advise`, `is_over`, `to_pgn` |
| `Position` (`fen`, `trait`, `coups_legaux`) / `Coup` (`notation`, `couleur`) | `Position` (`fen`, `turn`, `legal_moves`) / `Move` (`notation`, `color`) |
| `ModeJeu` ENTRAINEMENT / AMICAL / OFFICIEL ; `Couleur` BLANC / NOIR | `GameMode` TRAINING / FRIENDLY / OFFICIAL ; `Color` WHITE / BLACK |
| `Evaluation` (`meilleur_coup`, `score`, `mat_en`) | `Evaluation` (`best_move`, `score`, `mate_in`) |
| `Analyse` (`precision`, `erreurs`, `resume`) / `Erreur` (`coup`, `perte`, `gravite`) | `Analysis` (`accuracy`, `bad_moves`, `summary`) / `BadMove` (`move`, `loss`, `severity`) |
| `Gravite` IMPRECISION / ERREUR / GAFFE | `Severity` INACCURACY / MISTAKE / BLUNDER |

`Erreur` est devenu `BadMove` pour ne pas le confondre avec les erreurs Python.

Ajouts au diagramme, sans changer ses méthodes :
- `Glasses` est une interface, avec `ConsoleGlasses` pour le terminal ;
- les outils reçoivent ce qu'il faut remplacer en test (`client` Groq, `open_engine`, `download`) ;
- trois fichiers en plus : `errors.py`, `groq_client.py`, `console.py`.

---

## 4. Les choix importants (et pourquoi)

| Choix | Pourquoi |
|---|---|
| **Fair-play vérifié en premier** : en officiel, ni photo, ni Groq, ni Stockfish | Aucune IA n'est sollicitée pendant un tournoi, et ça n'entraîne aucun coût inutile |
| Gravité : imprécision ≥ 50, erreur ≥ 100, gaffe ≥ 300 centipions | Ce sont les seuils classiques des outils d'analyse |
| Scores plafonnés à ±1000 | Perdre un peu quand on gagne déjà largement n'est pas une gaffe |
| Précision = formule de Lichess (moyenne des notes des coups) | Plus juste qu'un simple « % de coups sans erreur » |
| Coups en notation SAN (`e4`, `Nf3`) | C'est la notation des humains et du PGN |
| Le trait est imposé au joueur pour un conseil | Une photo ne dit pas qui doit jouer |
| Photo avec seulement les pièces → on garde les roques encore possibles | Sinon Jarvis ne conseillerait jamais de roquer |
| LLM en panne → le coup est quand même donné | L'explication est un bonus |
| Import Lichess : partie classée → OFFICIAL ; camp trouvé avec `LICHESS_USERNAME` | Pour analyser tes coups, pas ceux de l'adversaire |
| `explain_move` = le dernier coup joué ; `play_against_me` refusé en officiel | Cohérent avec la règle fair-play |
| Modèles Groq : texte `openai/gpt-oss-120b`, vision `meta-llama/llama-4-scout-17b-16e-instruct` | Le premier était déjà utilisé dans Jagvis |

---

## 5. Les tests

- **Unitaires** (`tests/unit/`) : une classe à la fois. Tout ce qui est extérieur est
  remplacé par une fausse version écrite à la main.
- **Acceptation** (E1–E3) :
  - un conseil complet ;
  - le refus en mode officiel ;
  - une partie suivie avec alerte, analyse, sauvegarde et PGN.
- **Bout en bout** (E4–E5) : on lance vraiment la console. Sans clé, elle s'arrête
  avec le code 2 ; avec une clé, une session se termine proprement.
- Les faux outils de Jarvis notent tout dans un **journal commun** : le test JAR-03
  vérifie l'ordre exact des appels de `suggest_move`.
- Chaque test porte l'id de son exigence (`MOD`, `RES`, `HIS`, `ENG`, `LIC`, `LLM`,
  `BRD`, `GLS`, `JAR`, `CON`, `E1`–`E5`).
- Construit en TDD : un commit `red:`, puis `green:`, puis `refactor:`.

---

## 6. Git

- `origin` = `github.com/JaggyINK/Jagvis` (ton fork). `upstream` = le dépôt du prof,
  **bloqué en push** volontairement.
- Branches sur GitHub :
  - `main` : ta version, avec l'appli de conversation Streamlit ;
  - `prof` : la version du prof, à jour ;
  - `feature/jarvis-chess` : ce projet.
- Sur cette branche, l'appli de conversation a été retirée : elle reste sur `main`.
  ⚠️ Fusionner cette branche dans `main` la supprimerait aussi de `main`.
- Les messages des anciens commits ont été nettoyés (plus de ligne `Co-Authored-By`),
  puis la branche a été re-poussée.
- Les derniers commits de documentation ne sont pas encore poussés.

---

## 7. Reste à faire

- [ ] Ajouter une vraie photo `tests/photos/start.jpg`, puis `pytest -m groq` pour vérifier le modèle de vision.
- [ ] Essayer `advice` et `follow` dans la console avec des captures d'écran de lichess.org/editor.
- [ ] Décider : fusionner dans `main`, ou ouvrir une Pull Request pour la revue.
- [ ] Fichiers non commités du dossier du prof (`dia3-demo_agents-prof`) : où les ranger ?
- [ ] Supprimer la sauvegarde locale `refs/original/` (anciens messages de commit) :
      `git update-ref -d refs/original/refs/heads/main && git update-ref -d refs/original/refs/heads/feature/jarvis-chess`
- [ ] Facultatif (bonus du TP) : GitHub Actions qui lance les tests à chaque push.
- [ ] Plus tard : écrire une sous-classe de `Glasses` avec le SDK Meta. Rien d'autre ne change.

---

## 8. Historique des demandes

| # | Demande | Résultat |
|---|---|---|
| 1 | Réparer Git après le renommage, planifier | Worktree réparé, README « Jagvis » |
| 2 | Construire Jarvis Échecs en TDD avec les recos du TP | 185 tests, 100 %, garde-fous, ce fichier |
| 3 | Code en anglais simple, prendre les décisions seul | Code traduit ; fair-play en premier, précision Lichess, scores plafonnés, camp Lichess, roques |
| 4 | Dossier = uniquement le projet chess | Appli de conversation retirée de la branche, dossiers rangés |
| 5 | Pousser, expliquer l'app, simplifier, commentaires en français | `ARCHITECTURE.md`, code allégé, branche poussée, `prof` mis à jour |
| 6 | Nettoyer les messages de commit | Commits réécrits et re-poussés |
| 7 | Toutes les commandes dans un fichier | `COMMANDES.md` |
| 8 | Installer Stockfish | Stockfish 19 installé (empreinte vérifiée), ENG-07 vert |
| 9 | Simplifier et actualiser tous les `.md` | README, SUIVI, ARCHITECTURE et COMMANDES réécrits |
