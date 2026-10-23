"""All the errors that Jarvis expects.

They all come from JagvisError. So the console only has to catch one kind of
error to show a clear message to the player.
"""


class JagvisError(Exception):
    """An expected error. Its message can be shown to the player as it is."""


class InvalidFen(JagvisError):
    """The FEN text does not describe a real chess position."""


class IllegalMove(JagvisError):
    """The move cannot be played in this position."""


class GameOver(JagvisError):
    """The game is finished: no more moves."""


class NoGame(JagvisError):
    """Jarvis has no current game."""


class NotAllowed(JagvisError):
    """A game rule says no (not your turn, official mode...)."""


class InvalidId(JagvisError):
    """A game id with bad characters (it also protects the save folder)."""


class GameNotFound(JagvisError):
    """No game has this id."""


class BrokenSaveFile(JagvisError):
    """A saved game file cannot be read."""


class InvalidPgn(JagvisError):
    """The PGN text cannot be turned into a game."""


class InvalidPhoto(JagvisError):
    """The photo is empty, too big, missing or not a JPEG/PNG."""


class BoardNotFound(JagvisError):
    """The vision model did not find a valid position on the photo."""


class ServiceDown(JagvisError):
    """An outside service (Groq, Stockfish, Lichess) does not answer."""


class ConfigError(JagvisError):
    """A setting is missing or wrong (API key, path...)."""
