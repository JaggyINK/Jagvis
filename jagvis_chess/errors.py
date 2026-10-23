# Toutes les erreurs prévues. La console attrape JagvisError et affiche le message.


class JagvisError(Exception):
    pass


class InvalidFen(JagvisError):
    pass


class IllegalMove(JagvisError):
    pass


class GameOver(JagvisError):
    pass


class NoGame(JagvisError):
    pass


class NotAllowed(JagvisError):
    pass


class InvalidId(JagvisError):
    pass


class GameNotFound(JagvisError):
    pass


class BrokenSaveFile(JagvisError):
    pass


class InvalidPgn(JagvisError):
    pass


class InvalidPhoto(JagvisError):
    pass


class BoardNotFound(JagvisError):
    pass


class ServiceDown(JagvisError):
    pass


class ConfigError(JagvisError):
    pass
