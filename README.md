# Jagvis — Jarvis Chess

A chess helper for smart glasses. The glasses take a photo of the board, Jarvis
reads the position, asks Stockfish for the best move, explains it with an LLM
(Groq) and says it out loud. In official games it gives no help at all (fair play).

## Quick start

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
echo "GROQ_KEY=your_groq_key" > .env

.venv/bin/pytest                          # 201 tests, no network, no Stockfish
.venv/bin/python -m jagvis_chess.console  # play in the terminal
```

Stockfish must be installed for the real engine (`which stockfish`).

## Folders

```
docs/diagrams/      class and use case diagrams from the teacher (PlantUML)
docs/ARCHITECTURE.md  how the app works, with diagrams (French)
docs/COMMANDES.md   every command to type (French)
jagvis_chess/       the code
tests/unit/         one test file per module
tests/functional/   full stories and end-to-end tests
SUIVI.md            project follow-up for the code review (French)
```
