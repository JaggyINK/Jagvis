"""The game data: Game, Position, Move, GameMode and Color.

The python-chess library knows all the chess rules. Our classes only wrap it
with the names of the class diagram.
"""
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
    """A move written in SAN, the usual chess notation: "e4", "Nf3", "O-O"."""

    notation: str
    color: Color


def color_from_turn(turn):
    """python-chess says True for white and False for black."""
    if turn == chess.WHITE:
        return Color.WHITE
    return Color.BLACK


class Position:
    """A position written as a FEN text. The side to play (turn) comes from the FEN."""

    def __init__(self, fen):
        try:
            board = chess.Board(fen)
        except ValueError as error:
            raise InvalidFen(f"Invalid FEN: {fen}") from error
        # python-chess accepts impossible boards (no king...). We refuse them.
        if not board.is_valid():
            raise InvalidFen(f"Invalid FEN: {fen}")
        self.fen = fen
        self.turn = color_from_turn(board.turn)

    def to_board(self):
        """Give a new python-chess board for this position."""
        return chess.Board(self.fen)

    def legal_moves(self):
        board = self.to_board()
        return [Move(board.san(move), self.turn) for move in board.legal_moves]

    def __eq__(self, other):
        return isinstance(other, Position) and self.fen == other.fen

    def __repr__(self):
        return f"Position({self.fen!r})"


class Game:
    """A game: we replay its moves from the start position when we need the board."""

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
        # We play the given moves one by one: a wrong move raises IllegalMove.
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
        # Keep the clean notation ("Qh4#" even if we got "Qh4").
        self.moves.append(Move(board.san(chess_move), move.color))

    def current_position(self):
        return Position(self._board().fen())

    def can_advise(self):
        """Fair play rule: no help at all during an official game."""
        return self.mode != GameMode.OFFICIAL

    def is_over(self):
        return self._board().is_game_over()

    def to_pgn(self):
        pgn_game = chess.pgn.Game.from_board(self._board())
        pgn_game.headers["Event"] = f"Jarvis Chess ({self.mode.value})"
        pgn_game.headers["Date"] = self.date.strftime("%Y.%m.%d")
        if self.player_color == Color.WHITE:
            pgn_game.headers["White"] = "Player"
            pgn_game.headers["Black"] = "Opponent"
        else:
            pgn_game.headers["White"] = "Opponent"
            pgn_game.headers["Black"] = "Player"
        return str(pgn_game)
