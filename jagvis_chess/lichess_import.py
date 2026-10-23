import io
import re
import urllib.error
import urllib.request
from datetime import datetime

import chess.pgn

from jagvis_chess.errors import GameNotFound, InvalidId, InvalidPgn, ServiceDown
from jagvis_chess.model import Color, Game, GameMode, Move, color_from_turn

EXPORT_URL = "https://lichess.org/game/export/{id}"
# 8 caractères, ou 12 quand le lien contient aussi le camp du joueur.
VALID_LICHESS_ID = re.compile(r"[A-Za-z0-9]{8}([A-Za-z0-9]{4})?")


def download(url, headers):
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise GameNotFound(f"Lichess game not found: {url}") from error
        if error.code == 429:
            raise ServiceDown("Lichess gets too many requests: try again in a minute.") from error
        raise ServiceDown(f"Lichess answered with error {error.code}.") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ServiceDown("Lichess cannot be reached.") from error


def read_date(headers):
    text = f"{headers.get('UTCDate', '')} {headers.get('UTCTime', '00:00:00')}"
    try:
        return datetime.strptime(text, "%Y.%m.%d %H:%M:%S")
    except ValueError:
        return None


def player_color(headers, username):
    if username and headers.get("Black", "").lower() == username.lower():
        return Color.BLACK
    return Color.WHITE


class LichessImport:
    def __init__(self, token=None, username=None, download=download):
        self.token = token
        self.username = username
        self.download = download

    def fetch_game(self, id):
        if not isinstance(id, str) or not VALID_LICHESS_ID.fullmatch(id):
            raise InvalidId(f"Invalid Lichess id: {id!r}")
        id = id[:8]

        headers = {"Accept": "application/x-chess-pgn"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        pgn = chess.pgn.read_game(io.StringIO(self.download(EXPORT_URL.format(id=id), headers)))

        if pgn is None or pgn.errors:
            raise InvalidPgn("The Lichess game cannot be read.")
        variant = pgn.headers.get("Variant", "Standard")
        if variant != "Standard":
            raise InvalidPgn(f"Variant not supported: {variant}")

        board = pgn.board()
        moves = []
        for chess_move in pgn.mainline_moves():
            moves.append(Move(board.san(chess_move), color_from_turn(board.turn)))
            board.push(chess_move)
        if not moves:
            raise InvalidPgn("The Lichess game has no moves.")

        rated = "rated" in pgn.headers.get("Event", "").lower()
        return Game(
            mode=GameMode.OFFICIAL if rated else GameMode.FRIENDLY,
            player_color=player_color(pgn.headers, self.username),
            id=id,
            date=read_date(pgn.headers),
            moves=moves,
        )
