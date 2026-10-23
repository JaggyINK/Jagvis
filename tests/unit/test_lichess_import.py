import io
import urllib.error
from datetime import datetime

import pytest

from jagvis_chess.errors import GameNotFound, InvalidId, InvalidPgn, ServiceDown
from jagvis_chess.lichess_import import LichessImport, download
from jagvis_chess.model import Color, GameMode, Move

RATED_PGN = """[Event "Rated Blitz game"]
[Site "https://lichess.org/AbCd1234"]
[UTCDate "2026.10.20"]
[UTCTime "18:30:05"]
[White "alice"]
[Black "bob"]
[Result "0-1"]
[Variant "Standard"]

1. f3 e5 2. g4 Qh4# 0-1
"""


class FakeDownload:
    # Remplace l'appel HTTP et note les requêtes.

    def __init__(self, text=RATED_PGN):
        self.text = text
        self.requests = []

    def __call__(self, url, headers):
        self.requests.append((url, headers))
        return self.text


def test_LIC01_url_and_headers_of_the_public_api():
    fake_download = FakeDownload()

    LichessImport(download=fake_download).fetch_game("AbCd1234")

    url, headers = fake_download.requests[0]
    assert url == "https://lichess.org/game/export/AbCd1234"
    assert headers["Accept"] == "application/x-chess-pgn"
    assert "Authorization" not in headers


def test_LIC01_the_token_is_sent_if_there_is_one():
    fake_download = FakeDownload()

    LichessImport(token="secret", download=fake_download).fetch_game("AbCd1234")

    assert fake_download.requests[0][1]["Authorization"] == "Bearer secret"


def test_LIC01_a_12_character_id_keeps_the_first_8():
    fake_download = FakeDownload()

    game = LichessImport(download=fake_download).fetch_game("AbCd1234wxyz")

    assert fake_download.requests[0][0].endswith("/AbCd1234")
    assert game.id == "AbCd1234"


def test_LIC02_the_pgn_becomes_a_game():
    game = LichessImport(download=FakeDownload()).fetch_game("AbCd1234")

    assert game.id == "AbCd1234"
    assert game.date == datetime(2026, 10, 20, 18, 30, 5)
    assert game.player_color == Color.WHITE
    assert [move.notation for move in game.moves] == ["f3", "e5", "g4", "Qh4#"]
    assert game.moves[1] == Move("e5", Color.BLACK)


@pytest.mark.parametrize(
    "event, mode",
    [("Rated Blitz game", GameMode.OFFICIAL), ("Casual Rapid game", GameMode.FRIENDLY)],
)
def test_LIC03_mode_depends_on_rated_or_not(event, mode):
    pgn = RATED_PGN.replace("Rated Blitz game", event)

    game = LichessImport(download=FakeDownload(pgn)).fetch_game("AbCd1234")

    assert game.mode == mode


@pytest.mark.parametrize("id", ["", "abc", "../../etc", "AbCd123!", "AbCd12345"])
def test_LIC04_invalid_id_without_any_network_call(id):
    fake_download = FakeDownload()

    with pytest.raises(InvalidId, match="Invalid Lichess id"):
        LichessImport(download=fake_download).fetch_game(id)
    assert fake_download.requests == []


def test_LIC04_unreadable_date_becomes_now():
    pgn = RATED_PGN.replace("2026.10.20", "????.??.??")

    game = LichessImport(download=FakeDownload(pgn)).fetch_game("AbCd1234")

    assert isinstance(game.date, datetime)


@pytest.mark.parametrize(
    "pgn, message",
    [
        ("", "The Lichess game cannot be read."),
        ("[Event \"Casual\"]\n\n*\n", "The Lichess game has no moves."),
        ("[Event \"Casual\"]\n\n1. e4 e4 *\n", "The Lichess game cannot be read."),
        (RATED_PGN.replace("Standard", "Chess960"), "Variant not supported: Chess960"),
    ],
)
def test_LIC05_unusable_pgn(pgn, message):
    with pytest.raises(InvalidPgn, match=message):
        LichessImport(download=FakeDownload(pgn)).fetch_game("AbCd1234")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *error):
        return False


def http_error(code):
    return urllib.error.HTTPError("https://lichess.org", code, "error", {}, None)


def test_LIC06_download_works(mocker):
    urlopen = mocker.patch("urllib.request.urlopen", return_value=FakeResponse(RATED_PGN.encode()))

    text = download("https://lichess.org/game/export/AbCd1234", {"Accept": "application/x-chess-pgn"})

    assert text == RATED_PGN
    request = urlopen.call_args.args[0]
    assert request.full_url == "https://lichess.org/game/export/AbCd1234"
    assert urlopen.call_args.kwargs["timeout"] == 10


@pytest.mark.parametrize(
    "problem, expected_error, message",
    [
        (http_error(404), GameNotFound, "Lichess game not found"),
        (http_error(429), ServiceDown, "Lichess gets too many requests"),
        (http_error(500), ServiceDown, "Lichess answered with error 500"),
        (urllib.error.URLError("no network"), ServiceDown, "Lichess cannot be reached"),
        (TimeoutError(), ServiceDown, "Lichess cannot be reached"),
    ],
)
def test_LIC06_network_problems(mocker, problem, expected_error, message):
    mocker.patch("urllib.request.urlopen", side_effect=problem)

    with pytest.raises(expected_error, match=message):
        download("https://lichess.org/game/export/AbCd1234", {})


@pytest.mark.parametrize(
    "username, color",
    [
        ("alice", Color.WHITE),
        ("BOB", Color.BLACK),  # majuscules ou minuscules, peu importe
        ("carol", Color.WHITE),  # absent de la partie : Blancs par défaut
        (None, Color.WHITE),
    ],
)
def test_LIC07_the_player_color_comes_from_the_username(username, color):
    game = LichessImport(username=username, download=FakeDownload()).fetch_game("AbCd1234")

    assert game.player_color == color
