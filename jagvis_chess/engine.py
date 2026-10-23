"""ChessEngine: asks Stockfish through python-chess.

How Stockfish is started can be swapped (open_engine). The tests give a fake
engine, so they never start the real program.
"""
import chess
import chess.engine

from jagvis_chess.errors import ConfigError, GameOver, ServiceDown
from jagvis_chess.model import Color, Move, color_from_turn
from jagvis_chess.results import Analysis, BadMove, Evaluation, severity_of

MIN_DEPTH = 1
MAX_DEPTH = 30
# A mate counts as a huge lead: 10 000 centipawns (minus the moves before mate).
MATE_SCORE = 10_000


def to_centipawns(score):
    return score.score(mate_score=MATE_SCORE)


class ChessEngine:
    def __init__(self, stockfish_path="stockfish", depth=12,
                 open_engine=chess.engine.SimpleEngine.popen_uci):
        if not MIN_DEPTH <= depth <= MAX_DEPTH:
            raise ConfigError(f"The depth must be between {MIN_DEPTH} and {MAX_DEPTH}.")
        self.stockfish_path = stockfish_path
        self.depth = depth
        self.open_engine = open_engine

    def _stockfish_error(self):
        return ServiceDown(f"Stockfish is missing or not answering: {self.stockfish_path}")

    def _open(self):
        try:
            return self.open_engine(self.stockfish_path)
        except (OSError, chess.engine.EngineError) as error:
            raise self._stockfish_error() from error

    def _ask(self, engine, board):
        try:
            return engine.analyse(board, chess.engine.Limit(depth=self.depth))
        except (OSError, chess.engine.EngineError) as error:
            raise self._stockfish_error() from error

    @staticmethod
    def _close(engine):
        try:
            engine.quit()
        except (OSError, chess.engine.EngineError):
            pass  # Stockfish may already be stopped: nothing else to do

    def evaluate(self, position):
        board = position.to_board()
        if board.is_game_over():
            raise GameOver("The game is over: there is no move to suggest.")
        engine = self._open()
        try:
            info = self._ask(engine, board)
        finally:
            self._close(engine)
        score = info["score"].pov(board.turn)
        best = info["pv"][0]
        return Evaluation(
            best_move=Move(board.san(best), color_from_turn(board.turn)),
            score=to_centipawns(score),
            mate_in=score.mate(),
        )

    def _white_score(self, engine, board):
        """Score of the position, seen by white."""
        if board.is_checkmate():
            # The side to play is mated: no need to ask Stockfish.
            return -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
        if board.is_game_over():
            return 0  # stalemate or draw
        return to_centipawns(self._ask(engine, board)["score"].white())

    def analyze(self, game):
        board = chess.Board()
        engine = self._open()  # start Stockfish only once for the whole game
        try:
            # scores[i] = score before move i, scores[i + 1] = score after it.
            scores = [self._white_score(engine, board)]
            for move in game.moves:
                board.push_san(move.notation)
                scores.append(self._white_score(engine, board))
        finally:
            self._close(engine)

        sign = 1 if game.player_color == Color.WHITE else -1
        bad_moves = []
        player_moves = 0
        for number, move in enumerate(game.moves):
            if move.color != game.player_color:
                continue
            player_moves += 1
            loss = sign * scores[number] - sign * scores[number + 1]
            severity = severity_of(loss)
            if severity:
                bad_moves.append(BadMove(move, loss, severity))

        if player_moves == 0:
            return Analysis(accuracy=100.0, bad_moves=[])
        accuracy = 100 * (player_moves - len(bad_moves)) / player_moves
        return Analysis(accuracy=accuracy, bad_moves=bad_moves)
