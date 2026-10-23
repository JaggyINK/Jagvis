"""History: each game is saved as one JSON file in a folder.

A file <id>.json looks like this:
{"id": "...", "date": "2026-10-23T14:05:00", "mode": "official",
 "player_color": "black", "moves": [{"notation": "e4", "color": "white"}]}
"""
import json
import re
from datetime import datetime
from pathlib import Path

from jagvis_chess.errors import BrokenSaveFile, GameNotFound, InvalidId, JagvisError
from jagvis_chess.model import Color, Game, GameMode, Move

# Only letters, digits, "_" and "-": an id like "../secret" cannot leave the folder.
VALID_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


def check_id(id):
    if not isinstance(id, str) or not VALID_ID.fullmatch(id):
        raise InvalidId(f"Invalid game id: {id!r}")


def game_to_dict(game):
    return {
        "id": game.id,
        "date": game.date.isoformat(),
        "mode": game.mode.value,
        "player_color": game.player_color.value,
        "moves": [{"notation": move.notation, "color": move.color.value} for move in game.moves],
    }


def game_from_dict(data):
    moves = [Move(move["notation"], Color(move["color"])) for move in data["moves"]]
    return Game(
        mode=GameMode(data["mode"]),
        player_color=Color(data["player_color"]),
        id=data["id"],
        date=datetime.fromisoformat(data["date"]),
        moves=moves,
    )


class History:
    def __init__(self, folder):
        self.folder = folder
        Path(folder).mkdir(parents=True, exist_ok=True)

    def _file(self, id):
        check_id(id)
        return Path(self.folder) / f"{id}.json"

    def save(self, game):
        text = json.dumps(game_to_dict(game), ensure_ascii=False, indent=2)
        self._file(game.id).write_text(text, encoding="utf-8")

    def load(self, id):
        file = self._file(id)
        if not file.exists():
            raise GameNotFound(f"Game not found: {id}")
        try:
            return game_from_dict(json.loads(file.read_text(encoding="utf-8")))
        except (ValueError, KeyError, TypeError, JagvisError) as error:
            raise BrokenSaveFile(f"The file of game {id} cannot be read.") from error

    def list_games(self):
        games = []
        for file in Path(self.folder).glob("*.json"):
            try:
                games.append(self.load(file.stem))
            except (BrokenSaveFile, InvalidId):
                continue  # one broken file must not hide the other games
        return sorted(games, key=lambda game: game.date)
