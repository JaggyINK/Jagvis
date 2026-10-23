import base64
import re

import chess

from jagvis_chess.errors import BoardNotFound, InvalidFen, InvalidPhoto
from jagvis_chess.groq_client import ask_groq, make_groq_client
from jagvis_chess.model import Position

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_PHOTO_SIZE = 3 * 1024 * 1024  # Groq accepte 4 Mo en base64, soit environ 3 Mo de photo

INSTRUCTIONS = (
    "This is a photo of a chessboard. Answer only with the full FEN of the "
    "position (pieces, side to play, castling, en passant, halfmove, fullmove)."
)

ROW = r"[pnbrqkPNBRQK1-8]{1,8}"
FEN_IN_TEXT = re.compile(
    rf"({ROW}(?:/{ROW}){{7}})(\s+[wb]\s+(?:-|[KQkq]{{1,4}})\s+(?:-|[a-h][36])\s+\d+\s+\d+)?"
)


def image_type(photo):
    if photo.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if photo.startswith(b"\x89PNG"):
        return "image/png"
    return None


def check_photo(photo):
    if not photo:
        raise InvalidPhoto("The photo is empty.")
    if image_type(photo) is None:
        raise InvalidPhoto("Photo format not supported: JPEG or PNG expected.")
    if len(photo) > MAX_PHOTO_SIZE:
        raise InvalidPhoto("The photo is bigger than 3 MB.")


def find_fen(text):
    found = FEN_IN_TEXT.search(text)
    if found is None:
        raise BoardNotFound("I could not see a chessboard on the photo.")
    pieces, rest = found.groups()
    if rest:
        return pieces + rest
    return complete_fen(pieces)


def complete_fen(pieces):
    # Le modèle n'a donné que les pièces : on dit que les Blancs jouent et on garde
    # les roques encore possibles (roi et tour sur leur case de départ).
    try:
        board = chess.Board(f"{pieces} w KQkq - 0 1")
    except ValueError as error:
        raise BoardNotFound(f"The position on the photo is not valid: {pieces}") from error
    board.castling_rights = board.clean_castling_rights()
    return board.fen()


class BoardReader:
    def __init__(self, model=VISION_MODEL, client=None):
        self.model = model
        self.client = client or make_groq_client()

    def read_position(self, photo):
        check_photo(photo)
        image = f"data:{image_type(photo)};base64,{base64.b64encode(photo).decode()}"
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": INSTRUCTIONS},
                {"type": "image_url", "image_url": {"url": image}},
            ],
        }]
        fen = find_fen(ask_groq(self.client, self.model, messages))
        try:
            return Position(fen)
        except InvalidFen as error:
            raise BoardNotFound(f"The position on the photo is not valid: {fen}") from error
