import chess
import chess.engine

from jagvis_chess.errors import ConfigError, GameOver, ServiceDown
from jagvis_chess.model import Color, Move, color_from_turn
from jagvis_chess.results import Analysis, BadMove, Evaluation, move_accuracy, move_loss, severity_of

MATE_SCORE = 10_000
STOCKFISH_ERRORS = (OSError, chess.engine.EngineError)


class ChessEngine:
    # open_engine lance Stockfish. Les tests donnent un faux moteur à la place.
    def __init__(self, stockfish_path="stockfish", depth=12,
                 open_engine=chess.engine.SimpleEngine.popen_uci):
        if not 1 <= depth <= 30:
            raise ConfigError("The depth must be between 1 and 30.")
        self.stockfish_path = stockfish_path
        self.depth = depth
        self.open_engine = open_engine

    def _stockfish_down(self):
        return ServiceDown(f"Stockfish is missing or not answering: {self.stockfish_path}")

    def _open(self):
        try:
            return self.open_engine(self.stockfish_path)
        except STOCKFISH_ERRORS as error:
            raise self._stockfish_down() from error

    def _ask(self, engine, board):
        try:
            return engine.analyse(board, chess.engine.Limit(depth=self.depth))
        except STOCKFISH_ERRORS as error:
            raise self._stockfish_down() from error

    def _close(self, engine):
        try:
            engine.quit()
        except STOCKFISH_ERRORS:
            pass  # déjà arrêté

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
            score=score.score(mate_score=MATE_SCORE),
            mate_in=score.mate(),
        )

    def _white_score(self, engine, board):
        if board.is_checkmate():
            return -MATE_SCORE if board.turn == chess.WHITE else MATE_SCORE
        if board.is_game_over():
            return 0
        return self._ask(engine, board)["score"].white().score(mate_score=MATE_SCORE)

    def analyze(self, game):
        board = chess.Board()
        engine = self._open()
        try:
            # scores[i] = score avant le coup i, scores[i + 1] = score après
            scores = [self._white_score(engine, board)]
            for move in game.moves:
                board.push_san(move.notation)
                scores.append(self._white_score(engine, board))
        finally:
            self._close(engine)

        sign = 1 if game.player_color == Color.WHITE else -1
        bad_moves = []
        accuracies = []
        for i, move in enumerate(game.moves):
            if move.color != game.player_color:
                continue
            before = sign * scores[i]
            after = sign * scores[i + 1]
            accuracies.append(move_accuracy(before, after))
            loss = move_loss(before, after)
            severity = severity_of(loss)
            if severity:
                bad_moves.append(BadMove(move, loss, severity))

        if not accuracies:
            return Analysis(accuracy=100.0, bad_moves=[])
        return Analysis(accuracy=sum(accuracies) / len(accuracies), bad_moves=bad_moves)
