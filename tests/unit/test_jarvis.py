from types import SimpleNamespace

import chess
import pytest

from jagvis_chess.errors import BoardNotFound, GameNotFound, GameOver, NoGame, NotAllowed, ServiceDown
from jagvis_chess.jarvis import REFUSAL, Jarvis
from jagvis_chess.model import Color, Game, GameMode, Move, Position
from jagvis_chess.results import Analysis, Evaluation
from tests.fakes import (
    PNG_PHOTO,
    FakeAssistant,
    FakeBoardReader,
    FakeEngine,
    FakeGlasses,
    FakeHistory,
    FakeLichessImport,
)

START = chess.STARTING_FEN
E4 = Move("e4", Color.WHITE)
E4_ADVICE = Evaluation(best_move=E4, score=30)


def position_after(*san_moves, turn="w"):
    """Position seen by the camera: only where the pieces are matters."""
    board = chess.Board()
    for san in san_moves:
        board.push_san(san)
    return Position(f"{board.board_fen()} {turn} - - 0 1")


class SpyGame(Game):
    """A real Game that writes in the log when someone calls can_advise()."""

    def __init__(self, log, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = log

    def can_advise(self):
        self.log.append("can_advise")
        return super().can_advise()


@pytest.fixture
def tools():
    """All the fake tools of Jarvis, writing in the same log."""
    log = []
    return SimpleNamespace(
        log=log,
        glasses=FakeGlasses(photos=[PNG_PHOTO] * 5, log=log),
        board_reader=FakeBoardReader(positions=[Position(START)], log=log),
        engine=FakeEngine(evaluations=[E4_ADVICE], log=log),
        assistant=FakeAssistant(log=log),
        history=FakeHistory(log=log),
        lichess_import=FakeLichessImport(log=log),
    )


def make_jarvis(tools):
    return Jarvis(
        glasses=tools.glasses,
        board_reader=tools.board_reader,
        engine=tools.engine,
        assistant=tools.assistant,
        history=tools.history,
        lichess_import=tools.lichess_import,
    )


def jarvis_with_game(tools, mode=GameMode.TRAINING, color=Color.WHITE, moves=()):
    jarvis = make_jarvis(tools)
    game = SpyGame(tools.log, mode, color)
    for notation in moves:
        game.play(Move(notation, game.current_position().turn))
    jarvis.current_game = game
    return jarvis


# --- JAR-01 and JAR-02: build and start ------------------------------------------


def test_JAR01_jarvis_gets_his_tools_and_has_no_game(tools):
    jarvis = make_jarvis(tools)

    assert jarvis.glasses is tools.glasses
    assert jarvis.board_reader is tools.board_reader
    assert jarvis.engine is tools.engine
    assert jarvis.assistant is tools.assistant
    assert jarvis.history is tools.history
    assert jarvis.lichess_import is tools.lichess_import
    assert jarvis.current_game is None


def test_JAR02_start_a_game(tools):
    jarvis = make_jarvis(tools)

    game = jarvis.start_game(GameMode.FRIENDLY, Color.BLACK)

    assert jarvis.current_game is game
    assert (game.mode, game.player_color, game.moves) == (GameMode.FRIENDLY, Color.BLACK, [])
    assert tools.glasses.spoken == ["New friendly game: you play black."]


# --- JAR-03 to JAR-07: suggest_move -------------------------------------------------


def test_JAR03_advice_checks_the_fair_play_rule_first(tools):
    jarvis = jarvis_with_game(tools)

    advice = jarvis.suggest_move()

    assert tools.log == [
        "can_advise", "take_photo", "read_position", "evaluate", "explain", "speak",
    ]
    assert advice == "Best move: e4. Coach explanation."
    assert tools.glasses.spoken == [advice]
    assert tools.board_reader.photos == [PNG_PHOTO]
    assert tools.assistant.questions == [(Position(START), E4_ADVICE)]


def test_JAR04_official_mode_refuses_without_photo_engine_or_llm(tools):
    jarvis = jarvis_with_game(tools, mode=GameMode.OFFICIAL)

    advice = jarvis.suggest_move()

    assert advice == REFUSAL
    assert tools.log == ["can_advise", "speak"]  # no photo is taken or sent
    assert tools.glasses.spoken == [REFUSAL]


@pytest.mark.parametrize(
    "action",
    ["suggest_move", "follow_game", "explain_move", "play_against_me", "analyze_game", "export_pgn"],
)
def test_JAR05_nothing_without_a_current_game(tools, action):
    jarvis = make_jarvis(tools)

    with pytest.raises(NoGame, match="No current game: start or import a game."):
        getattr(jarvis, action)()
    assert tools.log == []  # not even a photo


def test_JAR06_the_advice_is_for_the_player_side(tools):
    # The camera does not know who plays next: Jarvis sets the player color.
    tools.board_reader.positions = [position_after("e4", turn="w")]
    jarvis = jarvis_with_game(tools, color=Color.BLACK)

    jarvis.suggest_move()

    assert tools.engine.evaluated_positions[0].turn == Color.BLACK


def test_JAR06_position_impossible_for_the_player(tools):
    # Black is in check: it cannot be white's turn.
    tools.board_reader.positions = [position_after("e4", "f5", "Qh5+", turn="b")]
    jarvis = jarvis_with_game(tools, color=Color.WHITE)

    with pytest.raises(BoardNotFound, match="The position on the photo cannot be played by white."):
        jarvis.suggest_move()
    assert "evaluate" not in tools.log


def test_JAR07_without_llm_the_advice_is_still_useful(tools):
    tools.assistant.failure = ServiceDown("The language service is down.")
    jarvis = jarvis_with_game(tools)

    advice = jarvis.suggest_move()

    assert advice == "Best move: e4."
    assert tools.glasses.spoken == [advice]


def test_JAR07_other_problems_go_up(tools):
    tools.engine.failure = ServiceDown("Stockfish is missing or not answering: stockfish")
    jarvis = jarvis_with_game(tools)

    with pytest.raises(ServiceDown, match="Stockfish"):
        jarvis.suggest_move()
    assert tools.glasses.spoken == []


# --- JAR-08 and JAR-09: follow_game ------------------------------------------------------


def test_JAR08_follow_records_the_seen_move(tools):
    tools.board_reader.positions = [position_after("e4")]
    jarvis = jarvis_with_game(tools, mode=GameMode.OFFICIAL)

    jarvis.follow_game()

    assert jarvis.current_game.moves == [E4]
    assert tools.glasses.shown == ["Move played: e4"]
    assert "evaluate" not in tools.log  # official mode: no engine during the game


def test_JAR08_nothing_changes_if_the_position_is_the_same(tools):
    tools.board_reader.positions = [position_after("e4")]
    jarvis = jarvis_with_game(tools, moves=["e4"])

    jarvis.follow_game()

    assert len(jarvis.current_game.moves) == 1
    assert tools.glasses.shown == []


def test_JAR08_impossible_seen_position(tools):
    tools.board_reader.positions = [position_after("e4", "e5")]  # two moves at once
    jarvis = jarvis_with_game(tools)

    with pytest.raises(BoardNotFound, match="The position on the photo does not match any legal move."):
        jarvis.follow_game()
    assert jarvis.current_game.moves == []


def test_JAR08_end_of_game_is_saved_and_said(tools):
    tools.board_reader.positions = [position_after("f3", "e5", "g4", "Qh4#")]
    jarvis = jarvis_with_game(tools, color=Color.BLACK, moves=["f3", "e5", "g4"])

    jarvis.follow_game()

    assert jarvis.current_game.is_over()
    assert tools.history.games[jarvis.current_game.id] is jarvis.current_game
    assert tools.glasses.spoken == ["The game is over."]


def evaluations(before, after_for_opponent):
    return [
        Evaluation(best_move=E4, score=before),
        Evaluation(best_move=Move("e5", Color.BLACK), score=after_for_opponent),
    ]


def test_JAR09_warning_when_the_player_blunders(tools):
    tools.board_reader.positions = [position_after("e4")]
    tools.engine.evaluations = evaluations(before=20, after_for_opponent=400)  # loss: 420
    jarvis = jarvis_with_game(tools, mode=GameMode.FRIENDLY)

    jarvis.follow_game()

    assert tools.glasses.spoken == ["Watch out: e4 is a blunder!"]
    assert tools.engine.evaluated_positions == [Position(START), jarvis.current_game.current_position()]


def test_JAR09_no_warning_for_a_simple_mistake(tools):
    tools.board_reader.positions = [position_after("e4")]
    tools.engine.evaluations = evaluations(before=20, after_for_opponent=200)  # loss: 220
    jarvis = jarvis_with_game(tools)

    jarvis.follow_game()

    assert tools.glasses.spoken == []


def test_JAR09_no_warning_for_the_opponent_move(tools):
    tools.board_reader.positions = [position_after("e4")]
    jarvis = jarvis_with_game(tools, color=Color.BLACK)

    jarvis.follow_game()

    assert "evaluate" not in tools.log


def test_JAR09_engine_down_following_goes_on(tools):
    tools.board_reader.positions = [position_after("e4")]
    tools.engine.failure = ServiceDown("Stockfish is missing or not answering: stockfish")
    jarvis = jarvis_with_game(tools)

    jarvis.follow_game()

    assert jarvis.current_game.moves == [E4]
    assert tools.glasses.spoken == []


# --- JAR-10: explain_move -------------------------------------------------------------------


def test_JAR10_explain_the_last_move(tools):
    tools.engine.evaluations = [Evaluation(best_move=Move("d4", Color.WHITE), score=25)]
    jarvis = jarvis_with_game(tools, moves=["e4"])

    text = jarvis.explain_move()

    assert text == "Last move: e4. The best move was d4. Coach explanation."
    assert tools.engine.evaluated_positions == [Position(START)]  # the position BEFORE the move
    assert tools.glasses.spoken == [text]


def test_JAR10_nothing_to_explain(tools):
    jarvis = jarvis_with_game(tools)

    with pytest.raises(NotAllowed, match="No move to explain."):
        jarvis.explain_move()


def test_JAR10_refused_during_an_official_game(tools):
    jarvis = jarvis_with_game(tools, mode=GameMode.OFFICIAL, moves=["e4"])

    assert jarvis.explain_move() == REFUSAL
    assert "evaluate" not in tools.log


def test_JAR10_allowed_after_an_official_game_and_without_llm(tools):
    tools.assistant.failure = ServiceDown("The language service is down.")
    tools.engine.evaluations = [Evaluation(best_move=Move("Qh4#", Color.BLACK), score=9999, mate_in=1)]
    jarvis = jarvis_with_game(tools, mode=GameMode.OFFICIAL, moves=["f3", "e5", "g4", "Qh4#"])

    assert jarvis.explain_move() == "Last move: Qh4#. The best move was Qh4#."


# --- JAR-11: play_against_me ------------------------------------------------------------------


def test_JAR11_jarvis_plays_the_best_move(tools):
    e5 = Move("e5", Color.BLACK)
    tools.engine.evaluations = [Evaluation(best_move=e5, score=0)]
    jarvis = jarvis_with_game(tools, mode=GameMode.TRAINING, moves=["e4"])

    move = jarvis.play_against_me()

    assert move == e5
    assert jarvis.current_game.moves[-1] == e5
    assert tools.glasses.spoken == ["I play e5."]


@pytest.mark.parametrize(
    "mode, moves, error, message",
    [
        (GameMode.FRIENDLY, [], NotAllowed, "It is your turn."),
        (GameMode.OFFICIAL, ["e4"], NotAllowed, "In official mode your opponent is a human"),
        (GameMode.FRIENDLY, ["f3", "e5", "g4", "Qh4#"], GameOver, "The game is over."),
    ],
)
def test_JAR11_jarvis_refuses_to_play(tools, mode, moves, error, message):
    jarvis = jarvis_with_game(tools, mode=mode, moves=moves)

    with pytest.raises(error, match=message):
        jarvis.play_against_me()
    assert "evaluate" not in tools.log


# --- JAR-12: analyze_game ----------------------------------------------------------------------


def test_JAR12_analyze_saves_and_says_the_summary(tools):
    tools.engine.analysis = Analysis(accuracy=100.0, bad_moves=[])
    jarvis = jarvis_with_game(tools, moves=["e4", "e5"])

    analysis = jarvis.analyze_game()

    assert analysis is tools.engine.analysis
    assert tools.log == ["analyze", "save", "speak"]
    assert tools.glasses.spoken == ["Accuracy: 100 %. No bad moves, well done!"]


@pytest.mark.parametrize(
    "mode, moves, message",
    [
        (GameMode.FRIENDLY, [], "No move to analyze."),
        (GameMode.OFFICIAL, ["e4"], "In official mode, the analysis is only possible after the game."),
    ],
)
def test_JAR12_analysis_refused(tools, mode, moves, message):
    jarvis = jarvis_with_game(tools, mode=mode, moves=moves)

    with pytest.raises(NotAllowed, match=message):
        jarvis.analyze_game()
    assert "analyze" not in tools.log


# --- JAR-13: import_game --------------------------------------------------------------------------


def test_JAR13_the_imported_game_becomes_the_current_game(tools):
    imported = Game(GameMode.FRIENDLY, Color.WHITE, id="AbCd1234", moves=[E4])
    tools.lichess_import.game = imported
    jarvis = make_jarvis(tools)

    game = jarvis.import_game("AbCd1234")

    assert game is imported and jarvis.current_game is imported
    assert tools.lichess_import.ids == ["AbCd1234"]
    assert tools.history.games == {"AbCd1234": imported}
    assert tools.glasses.spoken == ["Game AbCd1234 imported: 1 move(s)."]


def test_JAR13_failed_import_keeps_the_current_game(tools):
    tools.lichess_import.failure = GameNotFound("Lichess game not found")
    jarvis = jarvis_with_game(tools)
    before = jarvis.current_game

    with pytest.raises(GameNotFound):
        jarvis.import_game("AbCd1234")
    assert jarvis.current_game is before
    assert tools.history.games == {}


# --- JAR-14: export_pgn ---------------------------------------------------------------------------


def test_JAR14_export_shows_and_gives_the_pgn(tools):
    jarvis = jarvis_with_game(tools, moves=["e4"])

    pgn = jarvis.export_pgn()

    assert pgn == jarvis.current_game.to_pgn()
    assert tools.glasses.shown == [pgn]
