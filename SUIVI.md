# Suivi du projet Jagvis — Jarvis Échecs

> Fichier de suivi **mis à jour après chaque demande**. Il sert à ne pas perdre le
> fil et à faciliter la revue de code : on y trouve ce qui est fait, pourquoi,
> où le vérifier, et ce qui reste à faire.
>
> Dernière mise à jour : 23/10/2026 — branche `feature/jarvis-echecs`.

---

## 1. L'idée en une phrase

Le joueur porte des lunettes connectées (Meta). Pendant une partie d'échecs, les
lunettes **photographient l'échiquier**, Jarvis **reconnaît la position** (modèle de
vision Groq), **demande le meilleur coup à Stockfish**, le fait **expliquer par un
LLM** (Groq) et **le dit à voix haute**. Jarvis suit aussi la partie, alerte en
cas de gaffe, analyse la partie terminée, l'importe depuis Lichess et l'exporte
en PGN.

**Règle fair-play** (diagramme de cas d'utilisation) : en mode **OFFICIEL**, Jarvis
ne donne **aucun conseil ni alerte** pendant la partie, seulement le suivi, puis
l'analyse une fois la partie finie.

Documents de référence (normatifs) :
- `docs/jarvis_echecs_classes.puml` — diagramme de classes validé par le prof ;
- `docs/jarvis_echecs_cas_utilisation.puml` — diagramme de cas d'utilisation ;
- les recommandations du TP « Mini-JARVIS — Tests automatisés en TDD » (non commité :
  c'est l'énoncé du formateur, le dépôt est public).

---

## 2. Comment lancer

```bash
uv venv --python 3.12 .venv               # une seule fois
uv pip install --python .venv/bin/python -r requirements-dev.txt

.venv/bin/pytest                           # tous les tests SANS réseau ni Stockfish
.venv/bin/pytest --cov=jagvis_echecs --cov-report=term-missing   # + couverture
.venv/bin/pytest -m stockfish              # vrai Stockfish (brew install stockfish)
.venv/bin/pytest -m groq                   # vraie API Groq : coûte du quota !

.venv/bin/python -m jagvis_echecs          # Jarvis dans le terminal (lunettes simulées)
```

Variables d'environnement (fichier `.env`, jamais commité) :

| Variable | Rôle | Défaut |
|---|---|---|
| `GROQ_KEY` | clé API Groq | **obligatoire** pour lancer Jarvis |
| `STOCKFISH_PATH` | chemin du programme Stockfish | `stockfish` |
| `JAGVIS_PARTIES` | dossier de l'historique (JSON) | `parties` |
| `LICHESS_TOKEN` | jeton Lichess (facultatif, l'API est publique) | aucun |

---

## 3. Architecture

```
                         ┌──────────────────────────┐
  terminal ──► console.py│  boucle de commandes     │  attrape JagvisErreur → « Erreur : … »
                         └────────────┬─────────────┘
                                      │
                               ┌──────▼──────┐
                               │   Jarvis    │  jarvis.py : le chef d'orchestre
                               └──┬──┬──┬──┬─┘  (reçoit ses 6 outils dans __init__)
        ┌──────────────┬──────────┘  │  │  └───────────┬───────────────┐
        ▼              ▼             ▼  ▼              ▼               ▼
   Lunettes   ReconnaissancePlateau  MoteurEchecs  AssistantLLM   Historique   ImportLichess
  lunettes.py   reconnaissance.py    moteur.py    assistant_llm.py historique.py import_lichess.py
  (interface)   photo → FEN (Groq)   Stockfish     explique (Groq)  JSON/dossier  PGN via HTTP
        │              │                 │              │
  LunettesConsole      └── client_groq.py ┘ (appel protégé commun)
   (terminal)

   Données (modele.py) : Partie, Position, Coup, ModeJeu, Couleur
   Résultats (resultats.py) : Evaluation, Analyse, Erreur, Gravite
   Erreurs (erreurs.py) : JagvisErreur et ses sous-classes
```

### Pourquoi c'est découpé comme ça

- **Un module par responsabilité**, comme demandé : `modele.py` pour le jeu,
  `resultats.py` pour ce que renvoie le moteur, un module par outil technique,
  puis `jarvis.py`.
- **Injection de dépendances** (recommandation du TP) : Jarvis ne crée pas ses outils, il
  les reçoit. De même, chaque outil reçoit ce qui coûte cher ou passe par le réseau :

  | Outil | Ce qui est injecté | Double utilisé en test |
  |---|---|---|
  | `MoteurEchecs` | `ouvrir_moteur` (lance Stockfish) | `FauxMoteurUCI` |
  | `AssistantLLM` | `client` Groq | `FauxClientGroq` |
  | `ReconnaissancePlateau` | `client` Groq | `FauxClientGroq` |
  | `ImportLichess` | `telecharger` (HTTP) | `FauxTelechargement` |
  | `LunettesConsole` | `lire` / `ecrire` (input / print) | `Console` |
  | `Jarvis` | les 6 outils | `FausseLunettes`, `FausseReconnaissance`, `FauxMoteur`, `FauxAssistant`, `FauxHistorique`, `FauxImportLichess` |

  Tous les doubles sont **écrits à la main** dans `tests/doubles.py`, sans
  bibliothèque de mock. Les doubles de Jarvis écrivent dans un **journal commun**,
  ce qui permet de vérifier l'**ordre** des appels.
- **python-chess fait les règles du jeu** (coups légaux, mat, pat, PGN, SAN). Nos
  classes l'enveloppent pour parler le vocabulaire du diagramme.

### Ce qui a été ajouté au diagramme (sans changer ses signatures)

| Ajout | Pourquoi |
|---|---|
| Paramètres d'injection optionnels (`client`, `ouvrir_moteur`, `telecharger`, `lire`, `ecrire`) | Tester sans réseau ni Stockfish |
| `Lunettes` = classe abstraite + `LunettesConsole` | Pas encore de SDK Meta : on simule dans le terminal |
| `Position.vers_plateau()` | Obtenir un plateau python-chess |
| `couleur_de()` dans `modele.py` | Convertir le trait de python-chess (True/False) en `Couleur` |
| `gravite_pour_perte()` + constantes de seuils dans `resultats.py` | Les seuils au même endroit |
| `erreurs.py` | Erreurs typées avec message clair, comme `errors.py` dans le TP |
| `client_groq.py` | Appel Groq protégé, partagé par AssistantLLM et ReconnaissancePlateau |
| `console.py` + `__main__.py` | Pouvoir utiliser Jarvis : `python -m jagvis_echecs` |

---

## 4. Décisions prises (à valider ou corriger)

Tu n'avais pas encore répondu à ces 8 questions. J'ai appliqué mes propositions par
défaut ; chacune se change facilement.

| # | Question | Décision appliquée | Où la changer |
|---|---|---|---|
| 1 | Seuils de gravité | IMPRECISION ≥ 50, ERREUR ≥ 100, GAFFE ≥ 300 centipions ; < 50 = pas d'erreur | `resultats.py` (constantes `SEUIL_*`) |
| 2 | `Coup.notation` | Notation SAN (`e4`, `Nf3`, `O-O`, `Qh4#`) | `modele.py` |
| 3 | `Evaluation.mat_en` | `int \| None` (None = pas de mat forcé) | `resultats.py` |
| 4 | `Analyse.precision` | % des coups **du joueur** sans `Erreur` (100 si aucun coup) | `moteur.py` → `analyser` |
| 5 | Import Lichess | `Rated…` → OFFICIEL, sinon AMICAL ; `couleur_joueur = BLANC` ; token facultatif | `import_lichess.py` |
| 6 | Ajouts hors diagramme | Voir le tableau du §3 | — |
| 7 | Ordre de `conseiller_coup` | Ton ordre exact : photo → position → `peut_conseiller` → évaluer → expliquer → parler. En OFFICIEL, la photo est donc prise, puis refusée | `jarvis.py` |
| 8 | « Être alerté d'une gaffe » (A4) | Intégré à `suivre_partie`, seulement pour les coups du joueur et hors OFFICIEL | `jarvis.py` → `_alerter_si_gaffe` |

Autres choix à connaître :
- **Le trait sur la photo** : la caméra ne sait pas qui doit jouer. Pour un conseil,
  Jarvis impose la couleur du joueur. Pour le suivi, il compare seulement le
  placement des pièces.
- **Roques après une photo** : si le modèle de vision ne donne que le placement, on
  complète avec `w - - 0 1`, donc sans droit au roque. Limite connue.
- **`expliquer_coup()`** (sans argument dans le diagramme) explique le **dernier coup
  joué** de la partie suivie : position avant le coup, meilleur coup du moteur, puis
  explication du LLM. En OFFICIEL, il est refusé tant que la partie n'est pas finie.
- **`jouer_contre_moi()`** est refusé en OFFICIEL : l'adversaire y est humain.
- Modèles Groq : texte `openai/gpt-oss-120b` (déjà utilisé par Jagvis), vision
  `meta-llama/llama-4-scout-17b-16e-instruct`. À vérifier dans la console Groq.

---

## 5. Garde-fous et cas d'erreurs

Toutes les erreurs prévues héritent de `JagvisErreur`. La console les attrape et
dit `Erreur : <message>`, **sans trace d'exception**. Les erreurs techniques
d'origine sont **chaînées** (`raise … from …`) pour le débogage.

| Situation | Erreur levée | Message | Test |
|---|---|---|---|
| FEN mal écrite ou position impossible (pas de roi…) | `FenInvalide` | `FEN invalide : …` | MOD-03 |
| Coup illégal | `CoupIllegal` | `Coup illégal : e5` | MOD-07 |
| Jouer hors de son tour | `CoupIllegal` | `Ce n'est pas aux noirs de jouer.` | MOD-07 |
| Jouer après mat ou pat | `PartieTerminee` | `La partie est terminée.` | MOD-07, JAR-11 |
| `mode` ou `couleur` qui n'est pas une énumération | `TypeError` | — | MOD-05 |
| Perte négative, précision hors 0–100 | `ValueError` | — | RES-03/04 |
| Identifiant de partie dangereux (`../secret`) | `IdentifiantInvalide` | `Identifiant de partie invalide : …` | HIS-05 |
| Partie absente de l'historique | `PartieIntrouvable` | `Partie introuvable : …` | HIS-03 |
| Fichier JSON abîmé ou coup faux dedans | `HistoriqueCorrompu` | `Le fichier de la partie … est illisible.` | HIS-06 |
| Un fichier abîmé dans l'historique | ignoré par `lister()` | — | HIS-06 |
| Profondeur Stockfish hors 1–30 | `ConfigurationInvalide` | `La profondeur doit être entre 1 et 30.` | MOT-01 |
| Stockfish absent ou qui plante | `ServiceIndisponible` | `Stockfish est introuvable ou ne répond pas : …` | MOT-05 |
| Stockfish toujours fermé, même en cas d'erreur | `finally: quit()` | — | MOT-05 |
| Évaluer une position finie | `PartieTerminee` | `La position est terminée : aucun coup à proposer.` | MOT-04 |
| Identifiant Lichess mal formé (avant tout appel réseau) | `IdentifiantInvalide` | `Identifiant Lichess invalide : …` | LIC-04 |
| Lichess : 404 / 429 / 500 / pas de réseau / délai dépassé (10 s) | `PartieIntrouvable` / `ServiceIndisponible` | voir `import_lichess.py` | LIC-06 |
| PGN illisible, vide, sans coup, variante (Chess960…) | `PgnInvalide` | `La partie Lichess n'a pas pu être lue.` … | LIC-05 |
| `GROQ_KEY` absente | `ConfigurationInvalide` | `la variable GROQ_KEY n'est pas définie.` | LLM-04, CON-04, E4 |
| Groq en panne / réponse vide | `ServiceIndisponible` | `Le service de langage est indisponible.` / `… n'a rien répondu.` | LLM-03, REC-06 |
| Photo vide, pas JPEG/PNG, > 3 Mo (4 Mo en base64, limite Groq) | `PhotoInvalide` | `La photo est vide.` … | REC-01 |
| Photo introuvable sur le disque | `PhotoInvalide` | `Photo introuvable : …` | LUN-03 |
| Pas de FEN dans la réponse de vision / FEN impossible | `ReconnaissanceImpossible` | `Je n'ai pas reconnu d'échiquier sur la photo.` … | REC-05 |
| Position vue impossible pour le camp du joueur | `ReconnaissanceImpossible` | `La position vue n'est pas jouable pour les blancs.` | JAR-06 |
| Position vue sans coup légal qui y mène | `ReconnaissanceImpossible` | `La position vue ne correspond à aucun coup légal.` | JAR-08 |
| Action sans partie en cours (pas même une photo prise) | `AucunePartie` | `Aucune partie en cours : démarre ou importe une partie.` | JAR-05 |
| **Conseil en mode OFFICIEL** | refus (texte renvoyé et dit) | `Mode officiel : je ne donne aucun conseil pendant la partie. Bonne chance !` | MOD-08, JAR-04, E2 |
| Analyse en OFFICIEL avant la fin | `ActionInterdite` | `En mode officiel, l'analyse n'est possible qu'après la partie.` | JAR-12 |
| Jarvis joue en OFFICIEL / pas son tour | `ActionInterdite` | `En mode officiel, ton adversaire est humain…` / `C'est à toi de jouer.` | JAR-11 |
| LLM en panne pendant un conseil | **mode dégradé** : le coup est quand même donné | `Meilleur coup : e4.` | JAR-07 |
| Moteur en panne pendant l'alerte de gaffe | alerte ignorée, le suivi continue | — | JAR-09 |
| Import Lichess raté | la partie en cours **ne change pas** | — | JAR-13 |
| Commande inconnue, Ctrl-D | aide affichée / sortie propre | — | CON-02/03 |

---

## 6. Exigences et tests

Chaque exigence porte un identifiant, cité dans le nom du test (recommandation du TP).

| Id | Exigence | Fichier de test |
|---|---|---|
| **E1** | Acceptation : conseil complet en mode entraînement (photo → FEN → Stockfish → LLM → voix) | `tests/fonctionnels/test_acceptation.py` |
| **E2** | Acceptation : aucun conseil en OFFICIEL, ni Stockfish ni LLM appelés | idem |
| **E3** | Acceptation : partie suivie, alerte de gaffe, fin, analyse, sauvegarde, PGN | idem |
| **E4–E5** | E2E : `python -m jagvis_echecs` sans clé (code 2) / session puis `quitter` (code 0) | `tests/fonctionnels/test_cli.py` |
| MOD-01…10 | Énumérations, Coup, Position (trait, FEN invalide, coups légaux = python-chess), Partie (jouer, refus, fair-play, fin, PGN relu) | `tests/unitaires/test_modele.py` |
| RES-01…04 | Seuils de gravité, Evaluation, Erreur, Analyse et `resume()` | `test_resultats.py` |
| HIS-01…06 | Aller-retour JSON, lister trié, introuvable, dossier créé, identifiant dangereux, fichier corrompu | `test_historique.py` |
| MOT-01…07 | Réglages, évaluer (score vu par le camp au trait), mat, position finie, pannes, analyser (gaffe, coups du joueur seulement), vrai Stockfish (`@stockfish`) | `test_moteur.py` |
| LIC-01…06 | URL et en-têtes, PGN → Partie, mode classé, identifiant invalide, PGN inutilisable, pannes HTTP | `test_import_lichess.py` |
| LLM-01…05 | Requête (modèle, FEN, coup, score), réponse, pannes, clé, vrai Groq (`@groq`) | `test_assistant_llm.py` |
| REC-01…07 | Photo refusée, envoi base64, extraction de FEN, placement seul, réponse inutilisable, pannes, vrai Groq (`@groq`) | `test_reconnaissance.py` |
| LUN-01…03 | Interface abstraite, parler/afficher/écouter, photo depuis un fichier | `test_lunettes.py` |
| JAR-01…14 | Construction, démarrage, **ordre de `conseiller_coup`**, refus OFFICIEL, sans partie, trait imposé, mode dégradé, suivi, alerte gaffe, expliquer, jouer, analyser, importer, exporter | `test_jarvis.py` |
| CON-01…04 | Commandes → méthodes de Jarvis, aide, erreurs dites sans planter, `main()` | `test_console.py` |

Les tests `@stockfish` et `@groq` sont **exclus par défaut** (`pytest.ini`) et
**sautés automatiquement** si l'outil ou la clé manque (`tests/conftest.py`). Ils
ne vérifient jamais le texte d'un LLM, seulement des effets.

---

## 7. Historique TDD (une ligne = un commit)

Ordre suivi : d'abord les tests d'acceptation (rouges), puis les données, les
résultats, l'historique, les outils techniques, Jarvis, et enfin la console.

| Étape | Commits |
|---|---|
| Mise en place | `chore: mise en place de Jarvis Échecs (diagrammes, pytest, erreurs)` |
| Boucle externe | `red: tests d'acceptation E1, E2 et E3` |
| Modèle | `red/green: MOD-01 à MOD-04`, `red/green: MOD-05 à MOD-10`, `refactor: imports des tests du modèle` |
| Résultats | `red/green: RES-01 à RES-04` |
| Historique | `red: HIS-01 à HIS-06`, `red: HIS-06 coup réellement illégal…`, `green: HIS-01 à HIS-06` |
| Moteur | `red/green: MOT-01 à MOT-07` |
| Lichess | `red/green: LIC-01 à LIC-06` |
| LLM | `red/green: LLM-01 à LLM-05` |
| Vision | `red/green: REC-01 à REC-07`, `refactor: appel Groq protégé partagé`, `red/green: REC-01 limite de 3 Mo` |
| Lunettes | `red/green: LUN-01 à LUN-03` |
| Jarvis | `red: JAR-01 à JAR-14`, `green: …, tests d'acceptation E1 à E3 au vert` |
| Couverture | `test: couverture des cas limites` |
| Console | `red/green: CON-01 à CON-04, tests E2E E4 et E5`, `refactor: retrait du marqueur reseau` |

---

## 8. Guide de revue de code (ordre de lecture conseillé)

1. `docs/*.puml` : le contrat.
2. `jagvis_echecs/erreurs.py` : toutes les erreurs possibles.
3. `modele.py`, puis `tests/unitaires/test_modele.py`. Vérifier : noms identiques au
   diagramme, `peut_conseiller()` False en OFFICIEL.
4. `resultats.py` : les seuils.
5. Les outils : `historique.py`, `moteur.py`, `import_lichess.py`, `client_groq.py`,
   `assistant_llm.py`, `reconnaissance.py`, `lunettes.py`, chacun avec son test.
6. `jarvis.py` avec `tests/unitaires/test_jarvis.py` : c'est le cœur, lire
   `test_JAR03` (l'ordre du déroulé) et `test_JAR04` (fair-play).
7. `tests/fonctionnels/test_acceptation.py` : les scénarios de bout en bout.
8. `console.py` : la boucle de commandes.

Points à vérifier pendant la revue :
- [ ] Aucun test par défaut n'appelle le réseau ni Stockfish (`pytest` passe sans internet).
- [ ] Aucun test ne vérifie le texte d'un vrai LLM.
- [ ] Les noms de classes, attributs et méthodes sont ceux du diagramme.
- [ ] Les décisions du §4 te conviennent.

---

## 9. Résultats actuels

- `pytest` : **185 tests réussis**, 3 désélectionnés (`@stockfish` et `@groq`).
- Couverture : **100 %** de `jagvis_echecs` (hors `__main__.py`, 3 lignes testées
  en sous-processus par E4/E5).
- Tests marqués : MOT-07 est sauté (Stockfish non installé). LLM-05 et REC-07 n'ont
  pas été lancés, pour ne pas consommer de quota Groq sans ton accord.

---

## 10. Reste à faire

- [ ] **Partie A.3** : cliquer sur **Rename** dans GitHub, puis
      `git remote set-url origin https://github.com/JaggyINK/Jagvis.git`.
- [ ] **Partie A.2** : choisir où ranger les fichiers non commités du worktree du prof
      (propositions faites, rien n'a été déplacé ni supprimé).
- [ ] Valider les décisions du §4 (surtout les seuils de gravité).
- [ ] `brew install stockfish`, puis `pytest -m stockfish`.
- [ ] Ajouter une vraie photo `tests/photos/depart.jpg`, puis `pytest -m groq` (coûte du quota).
- [ ] Un test réel Lichess (marqueur `reseau`) avec un identifiant de partie connu.
- [ ] Brancher Jarvis Échecs dans l'interface Streamlit de Jagvis (une `LunettesStreamlit`).
- [ ] Bonus du TP : GitHub Actions (`pytest --cov-fail-under=90`) et `REPONSES.md`.
- [ ] Pousser la branche, **seulement avec ton accord** (jamais sur `upstream`).

---

## 11. Journal des demandes

| Date | Demande | Ce qui a été fait |
|---|---|---|
| 23/10/2026 | Partie A (réparer Git après le renommage) + plan de la partie B | Worktree réparé (`git worktree repair`), README renommé « Jagvis » (commit sur `main`), plan et questions posés |
| 23/10/2026 | Appliquer les recos du TP, architecture adaptée au diagramme, garde-fous, fichier de suivi | Branche `feature/jarvis-echecs` : 13 modules, 185 tests, couverture 100 %, ce fichier `SUIVI.md` |
