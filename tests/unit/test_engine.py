import chess
import chess.engine
import pytest

from jagvis_chess.engine import ChessEngine
from jagvis_chess.errors import ConfigError, GameOver, ServiceDown
from jagvis_chess.model import Color, Game, GameMode, Move, Position
from jagvis_chess.results import Severity
from tests.fakes import FakeUciEngine

START = chess.STARTING_BOARD_FEN
AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR"
FOOLS_MATE = ["f3", "e5", "g4", "Qh4#"]
AFTER_G4 = "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR"
BACK_RANK_MATE = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"
FAST_STALEMATE = [
    "e3", "a5", "Qh5", "Ra6", "Qxa5", "h5", "h4", "Rah6", "Qxc7", "f6",
    "Qxd7+", "Kf7", "Qxb7", "Qd3", "Qxb8", "Qh7", "Qxc8", "Kg6", "Qe6",
]


def game_with(notations, color=Color.WHITE):
    game = Game(GameMode.FRIENDLY, color)
    for notation in notations:
        game.play(Move(notation, game.current_position().turn))
    return game


class CrashingEngine(FakeUciEngine):
    def analyse(self, board, limit):
        raise chess.engine.EngineTerminatedError("Stockfish stopped")


class AlreadyStoppedEngine(FakeUciEngine):
    def quit(self):
        raise chess.engine.EngineTerminatedError("already stopped")


def missing_stockfish(path):
    raise FileNotFoundError(path)


def test_ENG01_default_settings():
    engine = ChessEngine()

    assert engine.stockfish_path == "stockfish"
    assert engine.depth == 12


@pytest.mark.parametrize("depth", [0, 31, -5])
def test_ENG01_depth_out_of_range(depth):
    with pytest.raises(ConfigError, match="The depth must be between 1 and 30."):
        ChessEngine(depth=depth)


def test_ENG02_evaluate_gives_the_best_move_and_the_score():
    uci = FakeUciEngine(scores={START: 30}, best_moves={START: "e2e4"})
    engine = ChessEngine(stockfish_path="/opt/stockfish", depth=8, open_engine=uci.open)

    evaluation = engine.evaluate(Position(chess.STARTING_FEN))

    assert evaluation.best_move == Move("e4", Color.WHITE)
    assert evaluation.score == 30
    assert evaluation.mate_in is None
    assert uci.opened_paths == ["/opt/stockfish"]
    assert uci.limits[0].depth == 8
    assert uci.closed


def test_ENG02_the_score_is_seen_by_the_side_to_play():
    uci = FakeUciEngine(scores={AFTER_E4: 80}, best_moves={AFTER_E4: "e7e5"})
    position = Position(AFTER_E4 + " b KQkq - 0 1")

    evaluation = ChessEngine(open_engine=uci.open).evaluate(position)

    assert evaluation.score == -80
    assert evaluation.best_move == Move("e5", Color.BLACK)


def test_ENG03_a_forced_mate_is_reported():
    pieces = BACK_RANK_MATE.split()[0]
    uci = FakeUciEngine(mates={pieces: 1}, best_moves={pieces: "a1a8"})

    evaluation = ChessEngine(open_engine=uci.open).evaluate(Position(BACK_RANK_MATE))

    assert evaluation.best_move.notation == "Ra8#"
    assert evaluation.mate_in == 1
    assert evaluation.score > 9000


def test_ENG04_no_evaluation_of_a_finished_position():
    uci = FakeUciEngine()
    position = game_with(FOOLS_MATE).current_position()

    with pytest.raises(GameOver, match="The game is over: there is no move to suggest."):
        ChessEngine(open_engine=uci.open).evaluate(position)
    assert uci.opened_paths == []


def test_ENG05_stockfish_is_missing():
    engine = ChessEngine(stockfish_path="/nothing/stockfish", open_engine=missing_stockfish)

    with pytest.raises(ServiceDown, match="Stockfish is missing or not answering: /nothing/stockfish"):
        engine.evaluate(Position(chess.STARTING_FEN))


def test_ENG05_stockfish_crashes_and_is_still_closed():
    uci = CrashingEngine()

    with pytest.raises(ServiceDown):
        ChessEngine(open_engine=uci.open).evaluate(Position(chess.STARTING_FEN))
    assert uci.closed


def test_ENG05_closing_a_stopped_stockfish_does_not_crash():
    uci = AlreadyStoppedEngine(best_moves={START: "e2e4"})

    evaluation = ChessEngine(open_engine=uci.open).evaluate(Position(chess.STARTING_FEN))

    assert evaluation.best_move.notation == "e4"


def test_ENG06_analyze_finds_the_player_blunder():
    uci = FakeUciEngine(mates={AFTER_G4: -1})

    analysis = ChessEngine(open_engine=uci.open).analyze(game_with(FOOLS_MATE))

    assert [(bad.move.notation, bad.severity) for bad in analysis.bad_moves] == [("g4", Severity.BLUNDER)]
    assert analysis.bad_moves[0].loss > 300
    assert analysis.accuracy == 50.0
    assert uci.opened_paths == ["stockfish"]  # Stockfish starts only once for the game
    assert len(uci.analysed_positions) == 4  # the final mate position is not sent
    assert uci.closed


def test_ENG06_only_the_player_moves_are_checked():
    uci = FakeUciEngine(mates={AFTER_G4: -1})

    analysis = ChessEngine(open_engine=uci.open).analyze(game_with(FOOLS_MATE, Color.BLACK))

    assert analysis.bad_moves == []
    assert analysis.accuracy == 100.0


def test_ENG06_game_without_moves():
    uci = FakeUciEngine()

    analysis = ChessEngine(open_engine=uci.open).analyze(game_with([]))

    assert (analysis.accuracy, analysis.bad_moves) == (100.0, [])


def test_ENG06_a_small_loss_is_not_a_bad_move():
    uci = FakeUciEngine(scores={START: 30, AFTER_E4: 0})

    analysis = ChessEngine(open_engine=uci.open).analyze(game_with(["e4"]))

    assert analysis.bad_moves == []


def test_ENG06_a_stalemate_is_zero_without_asking_stockfish():
    uci = FakeUciEngine()

    analysis = ChessEngine(open_engine=uci.open).analyze(game_with(FAST_STALEMATE))

    assert len(uci.analysed_positions) == len(FAST_STALEMATE)  # the stalemate is not sent
    assert analysis.bad_moves == []


@pytest.mark.stockfish
def test_ENG07_the_real_stockfish_finds_mate_in_one():
    evaluation = ChessEngine(depth=10).evaluate(Position(BACK_RANK_MATE))

    assert evaluation.best_move.notation == "Ra8#"
    assert evaluation.mate_in == 1
