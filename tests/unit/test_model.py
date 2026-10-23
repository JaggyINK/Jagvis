import io
from datetime import datetime

import chess
import chess.pgn
import pytest

from jagvis_chess.errors import GameOver, IllegalMove, InvalidFen
from jagvis_chess.model import Color, Game, GameMode, Move, Position

START = chess.STARTING_FEN
SCHOLARS_MATE = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
DATE = datetime(2026, 10, 23, 14, 5)
FOOLS_MATE = ["f3", "e5", "g4", "Qh4#"]
# Le pat le plus rapide connu (Sam Loyd) : les Noirs n'ont plus de coup légal.
FAST_STALEMATE = [
    "e3", "a5", "Qh5", "Ra6", "Qxa5", "h5", "h4", "Rah6", "Qxc7", "f6",
    "Qxd7+", "Kf7", "Qxb7", "Qd3", "Qxb8", "Qh7", "Qxc8", "Kg6", "Qe6",
]


def game_with(notations, mode=GameMode.FRIENDLY, color=Color.WHITE):
    game = Game(mode, color, date=DATE)
    for notation in notations:
        game.play(Move(notation, game.current_position().turn))
    return game


# --- Énumérations, Move, Position --------------------------------------------------------


def test_MOD01_enums_of_the_diagram():
    assert [color.name for color in Color] == ["WHITE", "BLACK"]
    assert [mode.name for mode in GameMode] == ["TRAINING", "FRIENDLY", "OFFICIAL"]


def test_MOD02_two_same_moves_are_equal():
    assert Move("e4", Color.WHITE) == Move("e4", Color.WHITE)
    assert Move("e4", Color.WHITE) != Move("e4", Color.BLACK)


@pytest.mark.parametrize(
    "fen, turn",
    [
        (START, Color.WHITE),
        ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", Color.BLACK),
    ],
)
def test_MOD03_the_turn_comes_from_the_fen(fen, turn):
    position = Position(fen)

    assert position.fen == fen
    assert position.turn == turn


@pytest.mark.parametrize(
    "fen",
    [
        "",
        "nonsense",
        "8/8/8/8/8/8/8/8 w - - 0 1",  # pas de roi : bien écrite mais impossible
    ],
)
def test_MOD03_an_invalid_fen_is_refused(fen):
    with pytest.raises(InvalidFen, match="Invalid FEN"):
        Position(fen)


def test_MOD04_twenty_legal_moves_at_the_start():
    moves = Position(START).legal_moves()

    assert len(moves) == 20
    assert Move("e4", Color.WHITE) in moves
    assert Move("Nf3", Color.WHITE) in moves


def test_MOD04_same_legal_moves_as_python_chess():
    fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
    board = chess.Board(fen)
    expected = {board.san(move) for move in board.legal_moves}

    notations = {move.notation for move in Position(fen).legal_moves()}

    assert notations == expected
    assert "O-O" in notations and "O-O-O" in notations


def test_MOD04_no_legal_move_when_mated():
    assert Position(SCHOLARS_MATE).legal_moves() == []


# --- Game ----------------------------------------------------------------------------


def test_MOD05_a_new_game_is_empty():
    game = Game(GameMode.TRAINING, Color.BLACK, date=DATE)

    assert game.mode == GameMode.TRAINING
    assert game.player_color == Color.BLACK
    assert game.date == DATE
    assert game.moves == []
    assert game.current_position() == Position(START)


def test_MOD05_each_game_has_its_own_id():
    first = Game(GameMode.FRIENDLY, Color.WHITE)
    second = Game(GameMode.FRIENDLY, Color.WHITE)

    assert first.id and second.id and first.id != second.id
    assert isinstance(first.date, datetime)


@pytest.mark.parametrize("mode, color", [("official", Color.WHITE), (GameMode.FRIENDLY, "white")])
def test_MOD05_mode_and_color_must_be_enums(mode, color):
    with pytest.raises(TypeError):
        Game(mode, color)


def test_MOD05_moves_given_at_creation_are_checked():
    with pytest.raises(IllegalMove):
        Game(GameMode.FRIENDLY, Color.WHITE, moves=[Move("e5", Color.WHITE)])


def test_MOD06_play_adds_the_move_and_changes_the_turn():
    game = game_with(["e4"])

    assert game.moves == [Move("e4", Color.WHITE)]
    assert game.current_position().turn == Color.BLACK


def test_MOD07_an_illegal_move_is_refused():
    game = game_with([])

    with pytest.raises(IllegalMove, match="Illegal move: e5"):
        game.play(Move("e5", Color.WHITE))
    assert game.moves == []


def test_MOD07_you_cannot_play_out_of_turn():
    game = game_with([])

    with pytest.raises(IllegalMove, match="It is not black's turn."):
        game.play(Move("e5", Color.BLACK))


def test_MOD07_no_move_after_the_end():
    game = game_with(FOOLS_MATE)

    with pytest.raises(GameOver, match="The game is over."):
        game.play(Move("a3", Color.WHITE))


@pytest.mark.parametrize(
    "mode, expected",
    [(GameMode.TRAINING, True), (GameMode.FRIENDLY, True), (GameMode.OFFICIAL, False)],
)
def test_MOD08_no_advice_in_official_mode(mode, expected):
    assert Game(mode, Color.WHITE).can_advise() is expected


@pytest.mark.parametrize(
    "moves, over",
    [([], False), (["e4", "e5"], False), (FOOLS_MATE, True), (FAST_STALEMATE, True)],
)
def test_MOD09_game_ends_with_mate_or_stalemate(moves, over):
    assert game_with(moves).is_over() is over


def test_MOD10_python_chess_can_read_the_pgn():
    game = game_with(FOOLS_MATE, color=Color.WHITE)

    read_back = chess.pgn.read_game(io.StringIO(game.to_pgn()))

    board = read_back.board()
    notations = []
    for chess_move in read_back.mainline_moves():
        notations.append(board.san(chess_move))
        board.push(chess_move)
    assert notations == FOOLS_MATE
    assert read_back.headers["Date"] == "2026.10.23"
    assert read_back.headers["White"] == "Player"
    assert read_back.headers["Result"] == "0-1"


def test_MOD10_a_black_player_is_on_the_black_side_of_the_pgn():
    read_back = chess.pgn.read_game(io.StringIO(game_with(["e4"], color=Color.BLACK).to_pgn()))

    assert (read_back.headers["White"], read_back.headers["Black"]) == ("Opponent", "Player")
    assert read_back.headers["Event"] == "Jarvis Chess (friendly)"
