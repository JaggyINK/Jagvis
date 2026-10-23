"""Jarvis: the conductor.

Jarvis cannot do anything alone: he gets his six tools in his constructor
(this is called dependency injection). In the tests, each tool is a fake.
"""
from jagvis_chess.errors import BoardNotFound, GameOver, InvalidFen, NoGame, NotAllowed, ServiceDown
from jagvis_chess.model import Color, Game, GameMode, Move, Position, color_from_turn
from jagvis_chess.results import Severity, move_loss, severity_of

REFUSAL = "Official mode: I give no advice during the game. Good luck!"


def with_turn(position, color):
    """The camera cannot know who plays next, so we set the turn to `color`."""
    parts = position.fen.split()
    turn = "w" if color == Color.WHITE else "b"
    if parts[1] != turn:
        parts[1] = turn
        parts[3] = "-"  # en passant makes no sense if we change the turn
    try:
        return Position(" ".join(parts))
    except InvalidFen as error:
        raise BoardNotFound(f"The position on the photo cannot be played by {color.value}.") from error


def find_played_move(game, seen_position):
    """Find the legal move that goes from the game to the position on the photo.

    Give None if nothing moved. We only compare where the pieces are: the
    photo does not say who plays next.
    """
    board = game.current_position().to_board()
    seen_pieces = seen_position.fen.split()[0]
    if board.board_fen() == seen_pieces:
        return None
    for chess_move in board.legal_moves:
        board.push(chess_move)
        is_match = board.board_fen() == seen_pieces
        board.pop()
        if is_match:
            return Move(board.san(chess_move), color_from_turn(board.turn))
    raise BoardNotFound("The position on the photo does not match any legal move.")


class Jarvis:
    def __init__(self, glasses, board_reader, engine, assistant, history, lichess_import):
        self.glasses = glasses
        self.board_reader = board_reader
        self.engine = engine
        self.assistant = assistant
        self.history = history
        self.lichess_import = lichess_import
        self.current_game = None

    def _game(self):
        if self.current_game is None:
            raise NoGame("No current game: start or import a game.")
        return self.current_game

    def _explanation(self, position, evaluation):
        """The LLM explanation is a bonus: if the LLM is down, we skip it."""
        try:
            return " " + self.assistant.explain(position, evaluation)
        except ServiceDown:
            return ""

    def start_game(self, mode, color):
        self.current_game = Game(mode, color)
        self.glasses.speak(f"New {mode.value} game: you play {color.value}.")
        return self.current_game

    def suggest_move(self):
        game = self._game()
        # Fair play first: in official mode, no photo is even taken.
        if not game.can_advise():
            self.glasses.speak(REFUSAL)
            return REFUSAL
        photo = self.glasses.take_photo()
        position = with_turn(self.board_reader.read_position(photo), game.player_color)
        evaluation = self.engine.evaluate(position)
        advice = f"Best move: {evaluation.best_move.notation}."
        advice += self._explanation(position, evaluation)
        self.glasses.speak(advice)
        return advice

    def follow_game(self):
        game = self._game()
        photo = self.glasses.take_photo()
        seen_position = self.board_reader.read_position(photo)
        move = find_played_move(game, seen_position)
        if move is None:
            return
        before = game.current_position()
        game.play(move)
        self.glasses.show(f"Move played: {move.notation}")
        if game.is_over():
            self.history.save(game)
            self.glasses.speak("The game is over.")
            return
        if move.color == game.player_color and game.can_advise():
            self._warn_if_blunder(move, before, game.current_position())

    def _warn_if_blunder(self, move, before, after):
        try:
            score_before = self.engine.evaluate(before).score
            score_after = self.engine.evaluate(after).score
        except ServiceDown:
            return  # the warning is a bonus: following the game goes on
        # After the move, the opponent plays: their score is the opposite of ours.
        loss = move_loss(score_before, -score_after)
        if severity_of(loss) == Severity.BLUNDER:
            self.glasses.speak(f"Watch out: {move.notation} is a blunder!")

    def explain_move(self):
        game = self._game()
        if not game.moves:
            raise NotAllowed("No move to explain.")
        if not game.can_advise() and not game.is_over():
            self.glasses.speak(REFUSAL)
            return REFUSAL
        last_move = game.moves[-1]
        before = Game(game.mode, game.player_color, moves=game.moves[:-1]).current_position()
        evaluation = self.engine.evaluate(before)
        text = f"Last move: {last_move.notation}. The best move was {evaluation.best_move.notation}."
        text += self._explanation(before, evaluation)
        self.glasses.speak(text)
        return text

    def play_against_me(self):
        game = self._game()
        if game.mode == GameMode.OFFICIAL:
            raise NotAllowed("In official mode your opponent is a human: I do not play for them.")
        if game.is_over():
            raise GameOver("The game is over.")
        position = game.current_position()
        if position.turn == game.player_color:
            raise NotAllowed("It is your turn.")
        move = self.engine.evaluate(position).best_move
        game.play(move)
        self.glasses.speak(f"I play {move.notation}.")
        return move

    def analyze_game(self):
        game = self._game()
        if not game.moves:
            raise NotAllowed("No move to analyze.")
        if game.mode == GameMode.OFFICIAL and not game.is_over():
            raise NotAllowed("In official mode, the analysis is only possible after the game.")
        analysis = self.engine.analyze(game)
        self.history.save(game)
        self.glasses.speak(analysis.summary())
        return analysis

    def import_game(self, lichess_id):
        game = self.lichess_import.fetch_game(lichess_id)
        self.history.save(game)
        self.current_game = game
        self.glasses.speak(f"Game {game.id} imported: {len(game.moves)} move(s).")
        return game

    def export_pgn(self):
        pgn = self._game().to_pgn()
        self.glasses.show(pgn)
        return pgn
