# Jagvis

Assistant conversationnel inspiré de J.A.R.V.I.S. : une interface Streamlit qui
discute avec un LLM via l'API Groq, garde les conversations dans une base SQLite,
résume les longs échanges et se souvient de l'utilisateur.

## Lancer le projet

```bash
pip install -r requirements.txt
echo "GROQ_KEY=ta_cle_groq" > .env
streamlit run app.py
```

## Jarvis Chess

A chess helper for smart glasses: the glasses take a photo of the board,
Jarvis finds the position, asks Stockfish for the best move, explains it with
an LLM and says it out loud. No advice in official games (fair play).

```bash
pip install -r requirements-dev.txt
pytest                              # tests without network or Stockfish
python -m jagvis_chess.console      # play in the terminal
```

Class diagram: `docs/jarvis_echecs_classes.puml`. Follow-up notes: `SUIVI.md`.
