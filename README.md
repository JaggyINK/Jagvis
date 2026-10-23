# Jagvis — Jarvis Chess

A chess helper for smart glasses. The glasses take a photo of the board,
Jarvis finds the position, asks Stockfish for the best move, explains it with
an LLM (Groq) and says it out loud. No advice in official games (fair play).

## Folders

```
docs/diagrams/   class and use case diagrams (PlantUML)
jagvis_chess/    the code
tests/unit/      one test file per module
tests/functional/  full stories and end-to-end tests
SUIVI.md         follow-up notes for the code review (in French)
docs/COMMANDES.md  every command to type: tests, coverage, console (in French)
```

## Start

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
echo "GROQ_KEY=your_groq_key" > .env

.venv/bin/pytest                          # tests without network or Stockfish
.venv/bin/python -m jagvis_chess.console  # play in the terminal
```
