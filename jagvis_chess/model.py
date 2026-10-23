import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import chess
import chess.pgn

from jagvis_chess.errors import GameOver, IllegalMove, InvalidFen


class Color(Enum):
    WHITE = "white"
    BLACK = "black"


class GameMode(Enum):
    TRAINING = "training"
    FRIENDLY = "friendly"
    OFFICIAL = "official"


@dataclass(frozen=True)
class Move:
    notation: str  # notation SAN : "e4", "Nf3", "O-O"...
    color: Color


def color_from_turn(turn):
    return Color.WHITE if turn == chess.WHITE else Color.BLACK


class Position:
    def __init__(self, fen):
        try:
            board = chess.Board(fen)
        except ValueError as error:
            raise InvalidFen(f"Invalid FEN: {fen}") from error
        if not board.is_valid():  # par exemple un plateau sans roi
            raise InvalidFen(f"Invalid FEN: {fen}")
        self.fen = fen
        self.turn = color_from_turn(board.turn)

    def to_board(self):
        return chess.Board(self.fen)

    def legal_moves(self):
        board = self.to_board()
        return [Move(board.san(move), self.turn) for move in board.legal_moves]

    def __eq__(self, other):
        return isinstance(other, Position) and self.fen == other.fen


class Game:
    def __init__(self, mode, player_color, id=None, date=None, moves=()):
        if not isinstance(mode, GameMode):
            raise TypeError(f"mode must be a GameMode, not {mode!r}")
        if not isinstance(player_color, Color):
            raise TypeError(f"player_color must be a Color, not {player_color!r}")
        self.id = id or uuid.uuid4().hex[:12]
        self.date = date or datetime.now()
        self.mode = mode
        self.player_color = player_color
        self.moves = []
        for move in moves:
            self.play(move)

    def _board(self):
        board = chess.Board()
        for move in self.moves:
            board.push_san(move.notation)
        return board

    def play(self, move):
        board = self._board()
        if board.is_game_over():
            raise GameOver("The game is over.")
        if move.color != color_from_turn(board.turn):
            raise IllegalMove(f"It is not {move.color.value}'s turn.")
        try:
            chess_move = board.parse_san(move.notation)
        except ValueError as error:
            raise IllegalMove(f"Illegal move: {move.notation}") from error
        self.moves.append(Move(board.san(chess_move), move.color))

    def current_position(self):
        return Position(self._board().fen())

    def can_advise(self):
        return self.mode != GameMode.OFFICIAL

    def is_over(self):
        return self._board().is_game_over()

    def to_pgn(self):
        pgn = chess.pgn.Game.from_board(self._board())
        pgn.headers["Event"] = f"Jarvis Chess ({self.mode.value})"
        pgn.headers["Date"] = self.date.strftime("%Y.%m.%d")
        if self.player_color == Color.WHITE:
            pgn.headers["White"], pgn.headers["Black"] = "Player", "Opponent"
        else:
            pgn.headers["White"], pgn.headers["Black"] = "Opponent", "Player"
        return str(pgn)
