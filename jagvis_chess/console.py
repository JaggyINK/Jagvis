"""Console: talk to Jarvis by typing commands in the terminal.

Start it with: python -m jagvis_chess.console
"""
import os
import sys

from dotenv import load_dotenv

from jagvis_chess.assistant import LLMAssistant
from jagvis_chess.board_reader import BoardReader
from jagvis_chess.engine import ChessEngine
from jagvis_chess.errors import ConfigError, JagvisError
from jagvis_chess.glasses import ConsoleGlasses
from jagvis_chess.history import History
from jagvis_chess.jarvis import Jarvis
from jagvis_chess.lichess_import import LichessImport
from jagvis_chess.model import Color, GameMode

HELP = (
    "Commands: new <training|friendly|official> <white|black>, advice, "
    "follow, explain, play, analyze, import <lichess id>, pgn, quit"
)
MODES = {mode.value: mode for mode in GameMode}
COLORS = {color.value: color for color in Color}


def run_command(jarvis, command):
    """Run one command. Give back the help text if the command is not understood."""
    words = command.lower().split()
    if words == ["advice"]:
        jarvis.suggest_move()
    elif words == ["follow"]:
        jarvis.follow_game()
    elif words == ["explain"]:
        jarvis.explain_move()
    elif words == ["play"]:
        jarvis.play_against_me()
    elif words == ["analyze"]:
        jarvis.analyze_game()
    elif words == ["pgn"]:
        jarvis.export_pgn()
    elif len(words) == 3 and words[0] == "new" and words[1] in MODES and words[2] in COLORS:
        jarvis.start_game(MODES[words[1]], COLORS[words[2]])
    elif len(words) == 2 and words[0] == "import":
        # Keep the original word: Lichess ids care about upper and lower case.
        jarvis.import_game(command.split()[1])
    else:
        return HELP
    return None


def run(jarvis, glasses):
    glasses.speak(HELP)
    while True:
        try:
            command = glasses.listen()
        except EOFError:  # Ctrl-D
            break
        if command.lower() in ("quit", "q"):
            break
        try:
            answer = run_command(jarvis, command)
        except JagvisError as error:
            answer = f"Error: {error}"
        if answer:
            glasses.speak(answer)
    glasses.speak("Goodbye!")


def build_jarvis():
    """Build the real Jarvis. Raises ConfigError if GROQ_KEY is missing."""
    return Jarvis(
        glasses=ConsoleGlasses(),
        board_reader=BoardReader(),
        engine=ChessEngine(stockfish_path=os.environ.get("STOCKFISH_PATH", "stockfish")),
        assistant=LLMAssistant(),
        history=History(os.environ.get("JAGVIS_GAMES", "games")),
        lichess_import=LichessImport(token=os.environ.get("LICHESS_TOKEN")),
    )


def main():
    load_dotenv()
    try:
        jarvis = build_jarvis()
    except ConfigError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    run(jarvis, jarvis.glasses)
    return 0


if __name__ == "__main__":  # pragma: no cover (tested in a subprocess by test_cli.py)
    sys.exit(main())
