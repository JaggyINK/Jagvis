"""Fake objects for the tests, written by hand.

None of them uses the network or starts Stockfish. Each one writes down what
it gets, so the tests can check what happened.
"""
from types import SimpleNamespace

import chess
import chess.engine

# Fake bytes that start like a real PNG file.
PNG_PHOTO = b"\x89PNG\r\n\x1a\n" + b"fake image"


class FakeGroqClient:
    """Works like groq.Groq: client.chat.completions.create(...) gives prepared answers.

    An answer can be a text, or an error to raise.
    """

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **settings):
        self.calls.append(settings)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        message = SimpleNamespace(content=answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeUciEngine:
    """Works like chess.engine.SimpleEngine (the Stockfish program).

    Scores are seen by white, and found by where the pieces are (the first
    part of the FEN).
    """

    def __init__(self, scores=None, mates=None, best_moves=None):
        self.scores = scores or {}
        self.mates = mates or {}
        self.best_moves = best_moves or {}
        self.analysed_positions = []
        self.opened_paths = []
        self.limits = []
        self.closed = False

    def open(self, path):
        self.opened_paths.append(path)
        return self

    def analyse(self, board, limit):
        self.analysed_positions.append(board.fen())
        self.limits.append(limit)
        key = board.board_fen()
        if key in self.mates:
            score = chess.engine.PovScore(chess.engine.Mate(self.mates[key]), chess.WHITE)
        else:
            score = chess.engine.PovScore(chess.engine.Cp(self.scores.get(key, 0)), chess.WHITE)
        if key in self.best_moves:
            best = chess.Move.from_uci(self.best_moves[key])
        else:
            best = next(iter(board.legal_moves))
        return {"score": score, "pv": [best]}

    def quit(self):
        self.closed = True


class FakeGlasses:
    """Replaces the glasses: photos are ready in advance, what Jarvis says is written down."""

    def __init__(self, photos=(), log=None, heard=()):
        self.photos = list(photos)
        self.heard = list(heard)
        self.spoken = []
        self.shown = []
        self.log = log if log is not None else []

    def take_photo(self):
        self.log.append("take_photo")
        return self.photos.pop(0)

    def listen(self):
        self.log.append("listen")
        return self.heard.pop(0)

    def speak(self, text):
        self.log.append("speak")
        self.spoken.append(text)

    def show(self, text):
        self.log.append("show")
        self.shown.append(text)


# --- Fakes of the Jarvis tools (for tests/unit/test_jarvis.py) ----------------
# They all write in the same "log": the tests can check the order of the calls.


class FakeBoardReader:
    def __init__(self, positions=(), log=None, failure=None):
        self.positions = list(positions)
        self.photos = []
        self.failure = failure
        self.log = log if log is not None else []

    def read_position(self, photo):
        self.log.append("read_position")
        self.photos.append(photo)
        if self.failure:
            raise self.failure
        return self.positions.pop(0)


class FakeEngine:
    """Gives the evaluations in order. When only one is left, it keeps giving it."""

    def __init__(self, evaluations=(), analysis=None, log=None, failure=None):
        self.evaluations = list(evaluations)
        self.analysis = analysis
        self.failure = failure
        self.evaluated_positions = []
        self.analyzed_games = []
        self.log = log if log is not None else []

    def evaluate(self, position):
        self.log.append("evaluate")
        self.evaluated_positions.append(position)
        if self.failure:
            raise self.failure
        if len(self.evaluations) > 1:
            return self.evaluations.pop(0)
        return self.evaluations[0]

    def analyze(self, game):
        self.log.append("analyze")
        self.analyzed_games.append(game)
        return self.analysis


class FakeAssistant:
    def __init__(self, text="Coach explanation.", log=None, failure=None):
        self.text = text
        self.failure = failure
        self.questions = []
        self.log = log if log is not None else []

    def explain(self, position, evaluation):
        self.log.append("explain")
        self.questions.append((position, evaluation))
        if self.failure:
            raise self.failure
        return self.text


class FakeHistory:
    def __init__(self, log=None):
        self.games = {}
        self.log = log if log is not None else []

    def save(self, game):
        self.log.append("save")
        self.games[game.id] = game


class FakeLichessImport:
    def __init__(self, game=None, log=None, failure=None):
        self.game = game
        self.failure = failure
        self.ids = []
        self.log = log if log is not None else []

    def fetch_game(self, id):
        self.log.append("fetch_game")
        self.ids.append(id)
        if self.failure:
            raise self.failure
        return self.game
