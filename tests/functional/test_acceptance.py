"""Acceptance tests: the stories of the use case diagram.

The real Jarvis parts are put together. Only the outside services are fake:
Groq (FakeGroqClient), Stockfish (FakeUciEngine) and the glasses.
"""
import io

import chess
import chess.pgn

from jagvis_chess.assistant import LLMAssistant
from jagvis_chess.board_reader import BoardReader
from jagvis_chess.engine import ChessEngine
from jagvis_chess.history import History
from jagvis_chess.jarvis import REFUSAL, Jarvis
from jagvis_chess.lichess_import import LichessImport
from jagvis_chess.model import Color, GameMode
from jagvis_chess.results import Severity
from tests.fakes import PNG_PHOTO, FakeGlasses, FakeGroqClient, FakeUciEngine

START = chess.STARTING_BOARD_FEN


def pieces_after(*san_moves):
    board = chess.Board()
    for san in san_moves:
        board.push_san(san)
    return board.board_fen()


def build_jarvis(tmp_path, glasses, vision, text, uci):
    return Jarvis(
        glasses=glasses,
        board_reader=BoardReader(client=vision),
        engine=ChessEngine(open_engine=uci.open),
        assistant=LLMAssistant(client=text),
        history=History(str(tmp_path / "games")),
        lichess_import=LichessImport(download=lambda url, headers: ""),
    )


def test_E1_advice_in_training_mode(tmp_path):
    glasses = FakeGlasses(photos=[PNG_PHOTO])
    vision = FakeGroqClient([f"Here is the FEN: {START} w KQkq - 0 1"])
    text = FakeGroqClient(["Take the center with your pawn."])
    uci = FakeUciEngine(best_moves={START: "e2e4"})
    jarvis = build_jarvis(tmp_path, glasses, vision, text, uci)
    jarvis.start_game(GameMode.TRAINING, Color.WHITE)

    advice = jarvis.suggest_move()

    assert "e4" in advice
    assert glasses.spoken[-1] == advice
    assert len(vision.calls) == 1 and len(text.calls) == 1
    assert uci.closed


def test_E2_no_advice_in_official_mode(tmp_path):
    glasses = FakeGlasses(photos=[PNG_PHOTO])
    vision = FakeGroqClient([])
    text = FakeGroqClient([])
    uci = FakeUciEngine()
    jarvis = build_jarvis(tmp_path, glasses, vision, text, uci)
    jarvis.start_game(GameMode.OFFICIAL, Color.WHITE)

    advice = jarvis.suggest_move()

    assert advice == REFUSAL
    assert glasses.spoken[-1] == REFUSAL
    assert glasses.photos == [PNG_PHOTO]  # the photo was never taken
    assert vision.calls == [] and text.calls == []
    assert uci.analysed_positions == []


def test_E3_followed_game_blunder_warning_then_analysis(tmp_path):
    moves = ["f3", "e5", "g4", "Qh4#"]
    vision = FakeGroqClient([pieces_after(*moves[: i + 1]) for i in range(len(moves))])
    # After g4, black mates in one: seen by white, this is Mate(-1).
    uci = FakeUciEngine(mates={pieces_after("f3", "e5", "g4"): -1})
    glasses = FakeGlasses(photos=[PNG_PHOTO] * len(moves))
    jarvis = build_jarvis(tmp_path, glasses, vision, FakeGroqClient([]), uci)
    game = jarvis.start_game(GameMode.FRIENDLY, Color.WHITE)

    for _ in moves:
        jarvis.follow_game()

    assert [move.notation for move in game.moves] == moves
    assert any("blunder" in sentence.lower() for sentence in glasses.spoken)
    assert game.is_over()

    analysis = jarvis.analyze_game()

    blunders = [bad for bad in analysis.bad_moves if bad.severity == Severity.BLUNDER]
    assert [bad.move.notation for bad in blunders] == ["g4"]
    saved = History(str(tmp_path / "games")).load(game.id)
    assert [move.notation for move in saved.moves] == moves
    read_back = chess.pgn.read_game(io.StringIO(jarvis.export_pgn()))
    assert read_back.end().board().is_checkmate()
    assert len(list(read_back.mainline_moves())) == len(moves)
