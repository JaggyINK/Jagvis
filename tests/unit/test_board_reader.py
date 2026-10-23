import base64
from pathlib import Path

import pytest

from jagvis_chess.board_reader import MAX_PHOTO_SIZE, VISION_MODEL, BoardReader
from jagvis_chess.errors import BoardNotFound, InvalidPhoto, ServiceDown
from jagvis_chess.model import Color, Position
from tests.fakes import PNG_PHOTO, FakeGroqClient

JPEG_PHOTO = b"\xff\xd8\xff\xe0" + b"fake image"
START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
REAL_PHOTO = Path(__file__).parent.parent / "photos" / "start.jpg"


@pytest.mark.parametrize(
    "photo, message",
    [
        (b"", "The photo is empty."),
        (None, "The photo is empty."),
        (b"GIF89a" + b"x", "Photo format not supported: JPEG or PNG expected."),
        (PNG_PHOTO + b"x" * MAX_PHOTO_SIZE, "The photo is bigger than 3 MB."),
    ],
)
def test_BRD01_photo_refused_before_any_call(photo, message):
    client = FakeGroqClient([])

    with pytest.raises(InvalidPhoto, match=message):
        BoardReader(client=client).read_position(photo)
    assert client.calls == []


def test_BRD01_the_limit_comes_from_groq_4_mb_of_base64():
    # base64 makes data one third bigger: 3 MB of photo become 4 MB.
    assert MAX_PHOTO_SIZE == 3 * 1024 * 1024


@pytest.mark.parametrize("photo, image_type", [(PNG_PHOTO, "image/png"), (JPEG_PHOTO, "image/jpeg")])
def test_BRD02_the_photo_is_sent_to_the_vision_model(photo, image_type):
    client = FakeGroqClient([START])

    BoardReader(client=client).read_position(photo)

    call = client.calls[0]
    assert call["model"] == VISION_MODEL
    assert call["temperature"] == 0
    content = call["messages"][0]["content"]
    image = next(part for part in content if part["type"] == "image_url")
    expected = f"data:{image_type};base64,{base64.b64encode(photo).decode()}"
    assert image["image_url"]["url"] == expected


def test_BRD03_the_fen_is_found_in_the_model_text():
    client = FakeGroqClient([f"Sure! Here is the position:\n```\n{AFTER_E4}\n```"])

    position = BoardReader(client=client).read_position(PNG_PHOTO)

    assert position == Position(AFTER_E4)
    assert position.turn == Color.BLACK


@pytest.mark.parametrize(
    "pieces, castling",
    [
        ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR", "KQkq"),  # kings and rooks at home
        ("rnbq1bnr/ppppkppp/8/4p3/4P3/8/PPPPKPPP/RNBQ1BNR", "-"),  # both kings moved
        ("1nbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN1", "Qk"),  # two rooks are gone
    ],
)
def test_BRD04_pieces_only_keep_the_castling_still_possible(pieces, castling):
    client = FakeGroqClient([pieces])

    position = BoardReader(client=client).read_position(PNG_PHOTO)

    assert position.fen == f"{pieces} w {castling} - 0 1"


@pytest.mark.parametrize(
    "answer, message",
    [
        ("I do not see a chessboard.", "I could not see a chessboard on the photo."),
        ("8/8/8/8/8/8/8/8 w - - 0 1", "The position on the photo is not valid"),
        ("rnbqkbnr/pppppppp/9/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1", "could not see|not valid"),
    ],
)
def test_BRD05_answer_without_a_valid_position(answer, message):
    client = FakeGroqClient([answer])

    with pytest.raises(BoardNotFound, match=message):
        BoardReader(client=client).read_position(PNG_PHOTO)


@pytest.mark.parametrize("problem, message", [
    (ConnectionError("timeout"), "The language service is down."),
    (None, "The language service gave an empty answer."),
])
def test_BRD06_groq_down_or_silent(problem, message):
    client = FakeGroqClient([problem])

    with pytest.raises(ServiceDown, match=message):
        BoardReader(client=client).read_position(PNG_PHOTO)


@pytest.mark.groq
@pytest.mark.skipif(not REAL_PHOTO.exists(), reason="add tests/photos/start.jpg for this test")
def test_BRD07_the_real_model_reads_a_real_photo():
    position = BoardReader().read_position(REAL_PHOTO.read_bytes())

    # We check the effect (a valid position), not the words of the model.
    assert isinstance(position, Position)
